"""
Cliente para Web Service de Distribuição de DF-e da SEFAZ.

Permite consultar e baixar NF-e em que o CNPJ é o destinatário (NF-e que
fornecedores emitiram contra a empresa — ou seja, "compras").

Referências oficiais:
- Nota Técnica 2014.002 — Web Service de Distribuição de DF-e
- https://www.nfe.fazenda.gov.br/portal/webServices.aspx

Conceitos centrais:
- NSU (Número Sequencial Único): identificador que a SEFAZ usa para paginar
  os documentos. O cliente persiste o último NSU consumido para evitar
  re-downloads (idempotência).
- Rate limit: após receber cStat 137 (sem dados) ou 656 (consumo indevido),
  a SEFAZ exige 1h de espera antes da próxima consulta. Bater nesse limite
  resseta o timer e pode bloquear o CNPJ.
"""

import os
import gzip
import base64
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Optional, List, Dict, Any
from defusedxml.ElementTree import fromstring as safe_xml_fromstring
from defusedxml.ElementTree import ParseError as XMLParseError
import sqlite3
from contextlib import contextmanager

import requests
from requests_pkcs12 import Pkcs12Adapter
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend
from filelock import FileLock

from .masking import mask_chave, mask_cnpj

logger = logging.getLogger(__name__)


class PathTraversalError(ValueError):
    """Caminho de XML aponta para fora do diretório de storage do CNPJ."""


NAMESPACES = {
    "nfe": "http://www.portalfiscal.inf.br/nfe",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "soap": "http://www.w3.org/2003/05/soap-envelope",
}

WEBSERVICE_URLS = {
    "homologacao": "https://hom1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx",
    "producao": "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx",
}


def _money_to_cents(value: str) -> int:
    try:
        return int(
            (Decimal(str(value or "0")) * 100).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
    except (InvalidOperation, ValueError):
        # MEDIUM-4: alertar quando valor monetário XML não parseia.
        # Retornar 0 silenciosamente poderia mascarar fraude.
        logger.warning(f"Valor monetário inválido no XML: {value!r}, usando 0")
        return 0


@dataclass
class NFeSummary:
    """Resumo de uma NF-e retornada pela consulta de distribuição."""

    nsu: str
    schema: str
    chave: Optional[str] = None
    cnpj_emitente: Optional[str] = None
    nome_emitente: Optional[str] = None
    ie_emitente: Optional[str] = None
    data_emissao: Optional[str] = None
    # 0=Entrada, 1=Saída
    tipo_operacao: Optional[str] = None
    valor_total: Optional[int] = None
    # 1=Autorizada, 2=Denegada
    situacao: Optional[str] = None
    protocolo: Optional[str] = None
    xml_content: Optional[str] = None
    # True se for XML completo (procNFe); False se for resumo (resNFe).
    is_complete: bool = False


@dataclass
class DistribuicaoResponse:
    """Resposta da consulta de distribuição."""

    # Um de: 'success', 'no_data', 'rate_limited', 'expired', 'error'
    status: str
    codigo: str
    motivo: str
    ultimo_nsu: str
    max_nsu: str
    documentos: List[NFeSummary] = field(default_factory=list)
    expired: bool = False


class SEFAZClient:
    """Cliente para comunicação com Web Service de Distribuição DF-e da SEFAZ."""

    def __init__(
        self,
        cnpj: str,
        cert_path: str,
        cert_password: str,
        ambiente: str = "homologacao",
        uf_autor: int = 35,
        storage_dir: Optional[str] = None,
        db_path: Optional[str] = None,
    ):
        """
        Args:
            cnpj: CNPJ da empresa (apenas dígitos, 14 caracteres).
            cert_path: caminho para o certificado .pfx ou .p12 (A1).
            cert_password: senha do certificado.
            ambiente: 'homologacao' (default, mais seguro) ou 'producao'.
            uf_autor: código IBGE da UF da empresa (ex: 35=SP, 33=RJ, 29=BA).
            storage_dir: diretório para salvar XMLs (default: ./nfe_storage).
            db_path: caminho do SQLite de controle (default: <storage>/nfe_sync.db).
        """
        self.cnpj = cnpj.replace(".", "").replace("/", "").replace("-", "")
        self.cert_path = cert_path
        self.cert_password = cert_password
        self.ambiente = ambiente
        self.uf_autor = uf_autor
        self.tp_amb = 1 if ambiente == "producao" else 2

        base_dir = Path(storage_dir or "./nfe_storage")
        self.storage_dir = base_dir / self.cnpj
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path or str(base_dir / "nfe_sync.db")
        self._init_database()

        self.session = self._create_session()
        self._load_certificate()

    @classmethod
    def from_env(cls) -> "SEFAZClient":
        """Cria um cliente lendo configuração de variáveis de ambiente.

        Variáveis lidas:
          - SEFAZ_CNPJ          (obrigatório)
          - SEFAZ_CERT_PATH     (obrigatório)
          - SEFAZ_CERT_PASSWORD (obrigatório)
          - SEFAZ_AMBIENTE      (default: homologacao — mais seguro)
          - SEFAZ_UF            (default: 35)
          - SEFAZ_STORAGE_DIR   (default: ./nfe_storage)

        Carrega .env automaticamente se python-dotenv estiver instalado.
        Use CONTAB_ENV_FILE para apontar um .env específico (evita carregar
        .env do diretório errado em execuções via CLI globalmente instalada).
        """
        try:
            from dotenv import load_dotenv

            # MEDIUM-1: carregamento explícito e auditável de .env
            env_file = os.environ.get("CONTAB_ENV_FILE")
            if env_file:
                load_dotenv(env_file)
                logger.info(f"Configuração carregada de {env_file}")
            elif Path(".env").exists():
                load_dotenv()
                logger.info(f"Configuração carregada de {Path('.env').resolve()}")
        except ImportError:
            pass

        cnpj = os.environ.get("SEFAZ_CNPJ", "").strip()
        cert_path = os.environ.get("SEFAZ_CERT_PATH", "").strip()
        cert_password = os.environ.get("SEFAZ_CERT_PASSWORD", "")
        ambiente = os.environ.get("SEFAZ_AMBIENTE", "homologacao").strip()
        storage_dir = os.environ.get("SEFAZ_STORAGE_DIR", "./nfe_storage")

        # MEDIUM-3: validação amigável de SEFAZ_UF (código IBGE numérico).
        uf_raw = os.environ.get("SEFAZ_UF", "35").strip()
        try:
            uf_autor = int(uf_raw)
        except ValueError:
            raise ValueError(
                f"SEFAZ_UF deve ser código IBGE numérico (ex: 35 para SP), "
                f"recebido: {uf_raw!r}. Veja a tabela completa em .env.example."
            )

        missing = []
        if not cnpj:
            missing.append("SEFAZ_CNPJ")
        if not cert_path:
            missing.append("SEFAZ_CERT_PATH")
        if not cert_password:
            missing.append("SEFAZ_CERT_PASSWORD")
        if missing:
            raise ValueError(
                f"Variáveis de ambiente obrigatórias não configuradas: {', '.join(missing)}. "
                f"Veja .env.example e copie para .env."
            )

        return cls(
            cnpj=cnpj,
            cert_path=cert_path,
            cert_password=cert_password,
            ambiente=ambiente,
            uf_autor=uf_autor,
            storage_dir=storage_dir,
        )

    def _load_certificate(self):
        with open(self.cert_path, "rb") as f:
            pfx_data = f.read()

        private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
            pfx_data,
            self.cert_password.encode()
            if isinstance(self.cert_password, str)
            else self.cert_password,
            default_backend(),
        )

        self._private_key = private_key
        self._certificate = certificate
        self._additional_certs = additional_certs

    def _create_session(self) -> requests.Session:
        session = requests.Session()

        adapter = Pkcs12Adapter(
            pkcs12_filename=self.cert_path,
            pkcs12_password=self.cert_password,
        )
        session.mount("https://", adapter)

        session.headers.update(
            {
                "Content-Type": "application/soap+xml; charset=utf-8",
                "Accept": "application/soap+xml",
            }
        )

        return session

    def _init_database(self):
        with self._db_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_control (
                    cnpj TEXT PRIMARY KEY,
                    ultimo_nsu TEXT DEFAULT '000000000000000',
                    max_nsu TEXT DEFAULT '000000000000000',
                    last_sync TIMESTAMP,
                    last_empty_query TIMESTAMP,
                    consecutive_656_count INTEGER DEFAULT 0,
                    total_downloaded INTEGER DEFAULT 0
                )
                """
            )
            try:
                conn.execute("SELECT last_empty_query FROM sync_control LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute(
                    "ALTER TABLE sync_control ADD COLUMN last_empty_query TIMESTAMP"
                )
            try:
                conn.execute("SELECT consecutive_656_count FROM sync_control LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute(
                    "ALTER TABLE sync_control ADD COLUMN consecutive_656_count INTEGER DEFAULT 0"
                )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS downloaded_nfe (
                    nsu TEXT PRIMARY KEY,
                    cnpj_destinatario TEXT,
                    chave TEXT UNIQUE,
                    cnpj_emitente TEXT,
                    nome_emitente TEXT,
                    data_emissao TEXT,
                    valor_total INTEGER,
                    situacao TEXT,
                    schema_type TEXT,
                    is_complete INTEGER,
                    file_path TEXT,
                    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed INTEGER DEFAULT 0,
                    processed_at TIMESTAMP
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chave ON downloaded_nfe(chave)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_emitente ON downloaded_nfe(cnpj_emitente)"
            )
            conn.commit()

    @contextmanager
    def _db_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def _rate_limit_lock(self):
        # Lock cross-process via filelock (POSIX flock + Windows LockFileEx).
        # AVISO: locks de filesystem falham silenciosamente em NFS — em deploy
        # distribuído, substituir por lock externo (Redis/etcd).
        lock_path = Path(self.db_path).with_suffix(".rate-limit.lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(str(lock_path)):
            yield

    def get_ultimo_nsu(self) -> str:
        with self._db_connection() as conn:
            result = conn.execute(
                "SELECT ultimo_nsu FROM sync_control WHERE cnpj = ?",
                (self.cnpj,),
            ).fetchone()
            return result["ultimo_nsu"] if result else "000000000000000"

    def can_query_distnsu(self) -> tuple[bool, int]:
        """Verifica se pode fazer consulta distNSU (regra 1h após cStat 137/656).

        Circuit breaker escalonado contra 656 (consumo indevido) consecutivos:
          - 0–1 consecutivos: 1h
          - 2 consecutivos: 2h
          - 3+ consecutivos: 4h (teto)
        """
        with self._db_connection() as conn:
            result = conn.execute(
                "SELECT last_empty_query, consecutive_656_count FROM sync_control WHERE cnpj = ?",
                (self.cnpj,),
            ).fetchone()

            if not result or not result["last_empty_query"]:
                return (True, 0)

            try:
                last_empty = datetime.fromisoformat(result["last_empty_query"])
            except (ValueError, TypeError):
                logger.warning(
                    f"last_empty_query inválido: {result['last_empty_query']}. Resetando."
                )
                conn.execute(
                    "UPDATE sync_control SET last_empty_query = NULL, consecutive_656_count = 0 WHERE cnpj = ?",
                    (self.cnpj,),
                )
                conn.commit()
                return (True, 0)

            elapsed = (datetime.now() - last_empty).total_seconds()

            consecutive = result["consecutive_656_count"] or 0
            if consecutive >= 3:
                wait_time = 14400
            elif consecutive >= 2:
                wait_time = 7200
            else:
                wait_time = 3600

            if elapsed >= wait_time:
                return (True, 0)

            return (False, int(wait_time - elapsed))

    def _mark_empty_query(self, is_656: bool = False):
        now = datetime.now().isoformat()
        with self._db_connection() as conn:
            if is_656:
                conn.execute(
                    """
                    INSERT INTO sync_control (cnpj, last_empty_query, consecutive_656_count)
                    VALUES (?, ?, 1)
                    ON CONFLICT(cnpj) DO UPDATE SET
                        last_empty_query = ?,
                        consecutive_656_count = COALESCE(consecutive_656_count, 0) + 1
                    """,
                    (self.cnpj, now, now),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO sync_control (cnpj, last_empty_query)
                    VALUES (?, ?)
                    ON CONFLICT(cnpj) DO UPDATE SET
                        last_empty_query = ?
                    """,
                    (self.cnpj, now, now),
                )
            conn.commit()

    def _reset_656_count(self):
        with self._db_connection() as conn:
            conn.execute(
                "UPDATE sync_control SET consecutive_656_count = 0 WHERE cnpj = ?",
                (self.cnpj,),
            )
            conn.commit()

    def _update_sync_control(self, ultimo_nsu: str, max_nsu: str, count: int):
        with self._db_connection() as conn:
            conn.execute(
                """
                INSERT INTO sync_control (cnpj, ultimo_nsu, max_nsu, last_sync, total_downloaded)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
                ON CONFLICT(cnpj) DO UPDATE SET
                    ultimo_nsu = excluded.ultimo_nsu,
                    max_nsu = excluded.max_nsu,
                    last_sync = CURRENT_TIMESTAMP,
                    total_downloaded = total_downloaded + excluded.total_downloaded
                """,
                (self.cnpj, ultimo_nsu, max_nsu, count),
            )
            conn.commit()

    def _sanitize_input(self, value: str) -> str:
        if not value:
            return ""
        return "".join(c for c in str(value) if c.isalnum() or c in ".-_")

    def _build_soap_envelope(self, inner_xml: str) -> str:
        return (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
            'xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
            "<soap12:Body>"
            '<nfeDistDFeInteresse xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">'
            f"<nfeDadosMsg>{inner_xml}</nfeDadosMsg>"
            "</nfeDistDFeInteresse>"
            "</soap12:Body>"
            "</soap12:Envelope>"
        )

    def _build_dist_nsu_request(self, ultimo_nsu: str) -> str:
        ultimo_nsu_safe = self._sanitize_input(ultimo_nsu).zfill(15)
        cnpj_safe = self._sanitize_input(self.cnpj)

        return (
            f'<distDFeInt versao="1.01" xmlns="http://www.portalfiscal.inf.br/nfe">'
            f"<tpAmb>{self.tp_amb}</tpAmb>"
            f"<CNPJ>{cnpj_safe}</CNPJ>"
            f"<distNSU><ultNSU>{ultimo_nsu_safe}</ultNSU></distNSU>"
            f"</distDFeInt>"
        )

    def _build_cons_chave_request(self, chave_nfe: str) -> str:
        chave_safe = self._sanitize_input(chave_nfe)
        cnpj_safe = self._sanitize_input(self.cnpj)

        return (
            f'<distDFeInt versao="1.01" xmlns="http://www.portalfiscal.inf.br/nfe">'
            f"<tpAmb>{self.tp_amb}</tpAmb>"
            f"<CNPJ>{cnpj_safe}</CNPJ>"
            f"<consChNFe><chNFe>{chave_safe}</chNFe></consChNFe>"
            f"</distDFeInt>"
        )

    def _parse_response(self, response_xml: str) -> DistribuicaoResponse:
        try:
            response_xml = response_xml.replace("xmlns=", "xmlns_original=")
            root = safe_xml_fromstring(response_xml)

            ret_dist = root.find(".//retDistDFeInt")
            if ret_dist is None:
                return DistribuicaoResponse(
                    status="error",
                    codigo="999",
                    motivo="Resposta inválida do servidor",
                    ultimo_nsu="",
                    max_nsu="",
                )

            codigo = ret_dist.findtext("cStat", "")
            motivo = ret_dist.findtext("xMotivo", "")
            ultimo_nsu = ret_dist.findtext("ultNSU", "000000000000000")
            max_nsu = ret_dist.findtext("maxNSU", "000000000000000")

            # Códigos SEFAZ:
            #   137 = Nenhum documento localizado
            #   138 = Documento(s) localizado(s)
            #   632 = Documento expirado/indisponível para download
            #   656 = Consumo Indevido (rate limit)
            if codigo == "656":
                return DistribuicaoResponse(
                    status="rate_limited",
                    codigo=codigo,
                    motivo=motivo,
                    ultimo_nsu=ultimo_nsu,
                    max_nsu=max_nsu,
                )

            if codigo == "632":
                return DistribuicaoResponse(
                    status="expired",
                    codigo=codigo,
                    motivo=motivo,
                    ultimo_nsu=ultimo_nsu,
                    max_nsu=max_nsu,
                    expired=True,
                )

            if codigo not in ("137", "138"):
                return DistribuicaoResponse(
                    status="error",
                    codigo=codigo,
                    motivo=motivo,
                    ultimo_nsu=ultimo_nsu,
                    max_nsu=max_nsu,
                )

            if codigo == "137":
                return DistribuicaoResponse(
                    status="no_data",
                    codigo=codigo,
                    motivo=motivo,
                    ultimo_nsu=ultimo_nsu,
                    max_nsu=max_nsu,
                )

            documentos = []
            lote = ret_dist.find("loteDistDFeInt")
            if lote is not None:
                for doc_zip in lote.findall("docZip"):
                    nsu = doc_zip.get("NSU", "")
                    schema = doc_zip.get("schema", "")

                    try:
                        compressed = base64.b64decode(doc_zip.text or "")
                        xml_content = gzip.decompress(compressed).decode("utf-8")
                    except Exception as e:
                        logger.warning(f"Erro ao descompactar NSU {nsu}: {e}")
                        continue

                    doc = self._parse_documento(nsu, schema, xml_content)
                    documentos.append(doc)

            return DistribuicaoResponse(
                status="success",
                codigo=codigo,
                motivo=motivo,
                ultimo_nsu=ultimo_nsu,
                max_nsu=max_nsu,
                documentos=documentos,
            )

        except XMLParseError as e:
            logger.error(f"Erro ao parsear resposta: {e}")
            return DistribuicaoResponse(
                status="error",
                codigo="998",
                motivo=f"Erro ao processar resposta: {e}",
                ultimo_nsu="",
                max_nsu="",
            )

    def _parse_documento(self, nsu: str, schema: str, xml_content: str) -> NFeSummary:
        doc = NFeSummary(nsu=nsu, schema=schema, xml_content=xml_content)

        try:
            xml_clean = xml_content.replace("xmlns=", "xmlns_original=")
            root = safe_xml_fromstring(xml_clean)

            if "resNFe" in schema or root.tag.endswith("resNFe"):
                doc.is_complete = False
                doc.chave = root.findtext(".//chNFe", "")
                doc.cnpj_emitente = root.findtext(".//CNPJ", "")
                doc.nome_emitente = root.findtext(".//xNome", "")
                doc.ie_emitente = root.findtext(".//IE", "")
                doc.data_emissao = root.findtext(".//dhEmi", "")
                doc.tipo_operacao = root.findtext(".//tpNF", "")
                doc.valor_total = _money_to_cents(root.findtext(".//vNF", "0") or "0")
                doc.situacao = root.findtext(".//cSitNFe", "")

            elif (
                "procNFe" in schema
                or root.tag.endswith("procNFe")
                or "nfeProc" in schema
            ):
                doc.is_complete = True
                doc.chave = root.findtext(".//chNFe", "")
                doc.protocolo = root.findtext(".//nProt", "")

                prot_cstat = root.findtext(".//protNFe//cStat", "")
                if prot_cstat in ("100",):
                    doc.situacao = "1"
                elif prot_cstat in ("110", "301", "302", "303"):
                    doc.situacao = "2"
                elif prot_cstat:
                    doc.situacao = prot_cstat
                else:
                    doc.situacao = "1"

                emit = root.find(".//emit")
                if emit is not None:
                    doc.cnpj_emitente = emit.findtext("CNPJ", "")
                    doc.nome_emitente = emit.findtext("xNome", "")
                    doc.ie_emitente = emit.findtext("IE", "")

                ide = root.find(".//ide")
                if ide is not None:
                    doc.data_emissao = ide.findtext("dhEmi", "")
                    doc.tipo_operacao = ide.findtext("tpNF", "")

                total = root.find(".//total/ICMSTot")
                if total is not None:
                    doc.valor_total = _money_to_cents(total.findtext("vNF", "0") or "0")

            elif "resEvento" in schema:
                doc.is_complete = False
                doc.chave = root.findtext(".//chNFe", "")

        except Exception as e:
            logger.warning(f"Erro ao parsear documento NSU {nsu}: {e}")

        return doc

    def _save_documento(self, doc: NFeSummary) -> str:
        if doc.is_complete:
            subdir = "completos"
        elif "resEvento" in doc.schema:
            subdir = "eventos"
        else:
            subdir = "resumos"

        save_dir = self.storage_dir / subdir
        save_dir.mkdir(exist_ok=True)

        # HIGH-1: doc.chave e doc.nsu vêm de XML retornado pela SEFAZ.
        # Em condições normais são seguros, mas defense-in-depth exige
        # validar formato + confinar dentro de storage_dir.
        if doc.chave:
            if not (doc.chave.isdigit() and len(doc.chave) == 44):
                raise PathTraversalError(
                    f"chNFe inesperada (não-numérica ou tamanho ≠ 44): {doc.chave!r}"
                )
            filename = f"{doc.chave}.xml"
        else:
            if not doc.nsu.isdigit():
                raise PathTraversalError(f"NSU inesperado (não-numérico): {doc.nsu!r}")
            filename = f"nsu_{doc.nsu}.xml"

        file_path = (save_dir / filename).resolve()
        # Confina o arquivo dentro do storage_dir do CNPJ atual.
        try:
            file_path.relative_to(self.storage_dir.resolve())
        except ValueError as exc:
            raise PathTraversalError(
                f"Path resolvido fora de {self.storage_dir}: {file_path}"
            ) from exc

        # LOW-2: alerta quando vai sobrescrever XML já baixado.
        if file_path.exists():
            logger.warning(
                f"Sobrescrevendo XML já existente: {file_path.name} "
                f"(re-download do mesmo documento)"
            )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(doc.xml_content or "")

        with self._db_connection() as conn:
            # Duas queries idênticas exceto pelo target do ON CONFLICT.
            # Separadas explicitamente para evitar f-string em SQL (B608).
            upsert_on_conflict_chave = """
                INSERT INTO downloaded_nfe
                (nsu, cnpj_destinatario, chave, cnpj_emitente, nome_emitente,
                 data_emissao, valor_total, situacao, schema_type, is_complete, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chave) DO UPDATE SET
                    nsu = excluded.nsu,
                    cnpj_destinatario = excluded.cnpj_destinatario,
                    chave = excluded.chave,
                    cnpj_emitente = excluded.cnpj_emitente,
                    nome_emitente = excluded.nome_emitente,
                    data_emissao = excluded.data_emissao,
                    valor_total = excluded.valor_total,
                    situacao = excluded.situacao,
                    schema_type = excluded.schema_type,
                    is_complete = excluded.is_complete,
                    file_path = excluded.file_path,
                    downloaded_at = CURRENT_TIMESTAMP
            """
            upsert_on_conflict_nsu = """
                INSERT INTO downloaded_nfe
                (nsu, cnpj_destinatario, chave, cnpj_emitente, nome_emitente,
                 data_emissao, valor_total, situacao, schema_type, is_complete, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(nsu) DO UPDATE SET
                    nsu = excluded.nsu,
                    cnpj_destinatario = excluded.cnpj_destinatario,
                    chave = excluded.chave,
                    cnpj_emitente = excluded.cnpj_emitente,
                    nome_emitente = excluded.nome_emitente,
                    data_emissao = excluded.data_emissao,
                    valor_total = excluded.valor_total,
                    situacao = excluded.situacao,
                    schema_type = excluded.schema_type,
                    is_complete = excluded.is_complete,
                    file_path = excluded.file_path,
                    downloaded_at = CURRENT_TIMESTAMP
            """
            query = upsert_on_conflict_chave if doc.chave else upsert_on_conflict_nsu
            conn.execute(
                query,
                (
                    doc.nsu,
                    self.cnpj,
                    doc.chave,
                    doc.cnpj_emitente,
                    doc.nome_emitente,
                    doc.data_emissao,
                    doc.valor_total,
                    doc.situacao,
                    doc.schema,
                    1 if doc.is_complete else 0,
                    str(file_path),
                ),
            )
            conn.commit()

        return str(file_path)

    def consultar_por_nsu(
        self, ultimo_nsu: Optional[str] = None, _skip_rate_check: bool = False
    ) -> DistribuicaoResponse:
        """Consulta documentos por NSU."""
        if not _skip_rate_check and not getattr(self, "_rate_limit_lock_active", False):
            with self._rate_limit_lock():
                self._rate_limit_lock_active = True
                try:
                    return self.consultar_por_nsu(ultimo_nsu, _skip_rate_check=False)
                finally:
                    self._rate_limit_lock_active = False

        if not _skip_rate_check:
            can_query, remaining = self.can_query_distnsu()
            if not can_query:
                logger.warning(
                    f"Rate limit ativo em consultar_por_nsu. Aguarde {remaining}s ({remaining // 60}min)"
                )
                return DistribuicaoResponse(
                    status="rate_limited",
                    codigo="656",
                    motivo=f"Rate limit local: aguarde {remaining} segundos",
                    ultimo_nsu=self.get_ultimo_nsu(),
                    max_nsu="",
                )

        if ultimo_nsu is None:
            ultimo_nsu = self.get_ultimo_nsu()

        ultimo_nsu = str(ultimo_nsu).zfill(15)
        logger.info(f"Consultando NSU a partir de: {ultimo_nsu}")

        body = self._build_dist_nsu_request(ultimo_nsu)
        envelope = self._build_soap_envelope(body)

        url = WEBSERVICE_URLS[self.ambiente]
        headers = {"Content-Type": "application/soap+xml; charset=utf-8"}
        try:
            response = self.session.post(
                url, data=envelope.encode("utf-8"), headers=headers, timeout=60
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição: {e}")
            return DistribuicaoResponse(
                status="error",
                codigo="997",
                motivo=f"Erro de comunicação: {e}",
                ultimo_nsu=ultimo_nsu,
                max_nsu="",
            )

        result = self._parse_response(response.text)

        if result.status == "rate_limited":
            self._mark_empty_query(is_656=True)
        elif result.status == "no_data":
            self._mark_empty_query()
        elif result.status == "success":
            self._reset_656_count()

        if result.status == "success":
            saved_count = 0
            for doc in result.documentos:
                self._save_documento(doc)
                saved_count += 1

            self._update_sync_control(result.ultimo_nsu, result.max_nsu, saved_count)
            logger.info(
                f"Baixados {saved_count} documentos. "
                f"Último NSU: {result.ultimo_nsu}, Max NSU: {result.max_nsu}"
            )

        return result

    def consultar_por_chave(
        self, chave_nfe: str, _skip_rate_check: bool = False
    ) -> DistribuicaoResponse:
        """Consulta uma NF-e específica por chave de acesso de 44 dígitos."""
        if not _skip_rate_check and not getattr(self, "_rate_limit_lock_active", False):
            with self._rate_limit_lock():
                self._rate_limit_lock_active = True
                try:
                    return self.consultar_por_chave(chave_nfe, _skip_rate_check=False)
                finally:
                    self._rate_limit_lock_active = False

        chave_nfe = chave_nfe.replace(" ", "")
        # MEDIUM-2: chave deve ser 44 dígitos numéricos (não só len==44).
        if not (chave_nfe.isdigit() and len(chave_nfe) == 44):
            return DistribuicaoResponse(
                status="error",
                codigo="996",
                motivo="Chave de acesso inválida (deve ter 44 dígitos numéricos)",
                ultimo_nsu="",
                max_nsu="",
            )

        if not _skip_rate_check:
            can_query, remaining = self.can_query_distnsu()
            if not can_query:
                logger.warning(
                    f"Rate limit ativo em consultar_por_chave. Aguarde {remaining}s"
                )
                return DistribuicaoResponse(
                    status="rate_limited",
                    codigo="656",
                    motivo=f"Rate limit local: aguarde {remaining} segundos",
                    ultimo_nsu="",
                    max_nsu="",
                )

        logger.info(f"Consultando chave: {mask_chave(chave_nfe)}")

        body = self._build_cons_chave_request(chave_nfe)
        envelope = self._build_soap_envelope(body)

        url = WEBSERVICE_URLS[self.ambiente]
        headers = {"Content-Type": "application/soap+xml; charset=utf-8"}
        try:
            response = self.session.post(
                url, data=envelope.encode("utf-8"), headers=headers, timeout=60
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição: {e}")
            return DistribuicaoResponse(
                status="error",
                codigo="997",
                motivo=f"Erro de comunicação: {e}",
                ultimo_nsu="",
                max_nsu="",
            )

        result = self._parse_response(response.text)

        if result.status == "rate_limited":
            self._mark_empty_query(is_656=True)

        if result.status == "success" and result.documentos:
            for doc in result.documentos:
                self._save_documento(doc)

        return result

    def sync(self, max_iterations: int = 100, force: bool = False) -> Dict[str, Any]:
        """Sincroniza todos os documentos pendentes (alias de sincronizar_tudo)."""
        return self.sincronizar_tudo(max_iterations=max_iterations, force=force)

    def sincronizar_tudo(
        self, max_iterations: int = 100, force: bool = False
    ) -> Dict[str, Any]:
        """Sincroniza todos os documentos pendentes.

        Cada iteração retorna até 50 documentos. Para um CNPJ que nunca
        sincronizou e tem muitas NF-e pendentes, pode ser necessário
        executar várias vezes (limitado pelo rate limit da SEFAZ).
        """
        stats = {
            "total_baixados": 0,
            "completos": 0,
            "resumos": 0,
            "eventos": 0,
            "erros": [],
            "rate_limited": False,
            "wait_seconds": 0,
            "inicio": datetime.now().isoformat(),
            "fim": None,
        }

        if force:
            logger.warning(
                "AUDIT: sincronizar_tudo com force=True — bypass de rate limit"
            )

        if not force:
            can_query, remaining = self.can_query_distnsu()
            if not can_query:
                logger.warning(
                    f"Rate limit ativo. Aguarde mais {remaining} segundos ({remaining // 60} min)"
                )
                stats["rate_limited"] = True
                stats["wait_seconds"] = remaining
                stats["erros"].append(
                    {
                        "iteracao": 0,
                        "codigo": "RATE_LIMIT_ACTIVE",
                        "motivo": f"Aguarde {remaining} segundos antes de consultar novamente",
                    }
                )
                stats["fim"] = datetime.now().isoformat()
                return stats

        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Iteração {iteration}/{max_iterations}")

            result = self.consultar_por_nsu(_skip_rate_check=force)

            if result.status == "rate_limited":
                logger.warning(f"Rate limited pela SEFAZ: {result.motivo}")
                stats["rate_limited"] = True
                stats["wait_seconds"] = 3600
                stats["erros"].append(
                    {
                        "iteracao": iteration,
                        "codigo": result.codigo,
                        "motivo": f"Rejeicao: {result.motivo}",
                    }
                )
                break

            if result.status == "error":
                stats["erros"].append(
                    {
                        "iteracao": iteration,
                        "codigo": result.codigo,
                        "motivo": result.motivo,
                    }
                )
                break

            if result.status == "expired":
                stats["erros"].append(
                    {
                        "iteracao": iteration,
                        "codigo": result.codigo,
                        "motivo": f"Documento expirado: {result.motivo}",
                    }
                )
                break

            if result.status == "no_data":
                logger.info("Sincronização completa — não há mais documentos")
                break

            for doc in result.documentos:
                stats["total_baixados"] += 1
                if doc.is_complete:
                    stats["completos"] += 1
                elif "resEvento" in doc.schema:
                    stats["eventos"] += 1
                else:
                    stats["resumos"] += 1

            if len(result.documentos) < 50:
                logger.info("Menos de 50 documentos retornados — finalizando")
                break

        stats["fim"] = datetime.now().isoformat()
        return stats

    def listar_nfe_baixadas(
        self,
        apenas_completas: bool = False,
        apenas_nao_processadas: bool = False,
        cnpj_emitente: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Lista NF-e baixadas do banco local com paginação.

        Nota de segurança: a cláusula WHERE é construída com `conditions`
        que são literais hardcoded no código (cnpj_destinatario, is_complete,
        processed, cnpj_emitente). Valores entram exclusivamente via `params`
        (placeholders `?`). Não há concatenação de input do usuário em SQL.
        Os `# nosec B608` abaixo refletem essa análise.
        """
        with self._db_connection() as conn:
            conditions = ["cnpj_destinatario = ?"]
            params = [self.cnpj]

            if apenas_completas:
                conditions.append("is_complete = 1")

            if apenas_nao_processadas:
                conditions.append("processed = 0")

            if cnpj_emitente:
                conditions.append("cnpj_emitente = ?")
                params.append(cnpj_emitente)

            where = " AND ".join(conditions)

            count_params = params.copy()
            total = conn.execute(
                f"SELECT COUNT(*) as total FROM downloaded_nfe WHERE {where}",  # nosec B608
                count_params,
            ).fetchone()["total"]

            params.extend([limit, offset])
            rows = conn.execute(
                f"""
                SELECT * FROM downloaded_nfe
                WHERE {where}
                ORDER BY downloaded_at DESC
                LIMIT ? OFFSET ?
                """,  # nosec B608
                params,
            ).fetchall()

            return {
                "data": [dict(row) for row in rows],
                "total": total,
            }

    def marcar_como_processada(self, chave: str) -> bool:
        with self._db_connection() as conn:
            conn.execute(
                """
                UPDATE downloaded_nfe
                SET processed = 1, processed_at = CURRENT_TIMESTAMP
                WHERE chave = ?
                """,
                (chave,),
            )
            conn.commit()
            return conn.total_changes > 0

    def obter_xml(self, chave: str) -> Optional[str]:
        """Obtém o XML de uma NF-e pela chave, com validação de path traversal."""
        with self._db_connection() as conn:
            row = conn.execute(
                "SELECT file_path FROM downloaded_nfe WHERE chave = ?",
                (chave,),
            ).fetchone()

            if row and row["file_path"]:
                resolved = Path(row["file_path"]).resolve()
                try:
                    resolved.relative_to(self.storage_dir.resolve())
                except ValueError as exc:
                    logger.warning(
                        f"Path traversal bloqueado: {row['file_path']} fora de {self.storage_dir}"
                    )
                    raise PathTraversalError(row["file_path"]) from exc
                try:
                    with open(resolved, "r", encoding="utf-8") as f:
                        return f.read()
                except FileNotFoundError:
                    return None
            return None

    def get_sync_status(self) -> Dict[str, Any]:
        with self._db_connection() as conn:
            control = conn.execute(
                "SELECT * FROM sync_control WHERE cnpj = ?",
                (self.cnpj,),
            ).fetchone()

            counts = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN is_complete = 1 THEN 1 ELSE 0 END) as completos,
                    SUM(CASE WHEN processed = 1 THEN 1 ELSE 0 END) as processados
                FROM downloaded_nfe WHERE cnpj_destinatario = ?
                """,
                (self.cnpj,),
            ).fetchone()

            can_query, wait_seconds = self.can_query_distnsu()

            return {
                "cnpj": self.cnpj,
                "cnpj_masked": mask_cnpj(self.cnpj),
                "ambiente": self.ambiente,
                "ultimo_nsu": control["ultimo_nsu"] if control else "000000000000000",
                "max_nsu": control["max_nsu"] if control else "000000000000000",
                "last_sync": control["last_sync"] if control else None,
                "total_downloaded": counts["total"] if counts else 0,
                "completos": counts["completos"] if counts else 0,
                "processados": counts["processados"] if counts else 0,
                "can_sync": can_query,
                "wait_seconds": wait_seconds,
            }
