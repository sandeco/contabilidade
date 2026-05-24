"""
Parser detalhado de XML de NF-e para extração de dados completos.

Converte o XML da NF-e em estruturas de dados Python (dataclasses) que podem
ser facilmente serializadas em JSON ou integradas a qualquer sistema.

Aderência ao Manual de Orientação do Contribuinte (Nota Técnica SEFAZ) — os
nomes dos campos seguem os elementos XML do schema NF-e v4.00.
"""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import List, Optional, Dict, Any
from lxml import etree
from datetime import datetime


def _decimal_to_cents(value: Decimal) -> int:
    """Converte Decimal monetário para inteiro em centavos.

    Evita perda de precisão de float em valores fiscais.
    """
    return int((value * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _is_money_key(key: str) -> bool:
    return (
        key == "valor"
        or key.startswith("valor_")
        or key.startswith("base_")
        or key.endswith("_valor")
        or key.endswith("_base")
        or key.endswith("_base_st")
    )


@dataclass
class Endereco:
    """Endereço (usado tanto para emitente quanto destinatário)."""

    logradouro: str = ""
    numero: str = ""
    complemento: str = ""
    bairro: str = ""
    cod_municipio: str = ""
    municipio: str = ""
    uf: str = ""
    cep: str = ""
    cod_pais: str = "1058"
    pais: str = "Brasil"
    telefone: str = ""


@dataclass
class Emitente:
    """Dados do emitente da NF-e (fornecedor que vendeu)."""

    cnpj: str = ""
    cpf: str = ""
    nome: str = ""
    nome_fantasia: str = ""
    ie: str = ""
    ie_st: str = ""
    im: str = ""
    cnae: str = ""
    # CRT: 1=Simples Nacional, 2=SN Excesso, 3=Regime Normal
    crt: str = ""
    endereco: Endereco = field(default_factory=Endereco)


@dataclass
class Destinatario:
    """Dados do destinatário da NF-e (no nosso caso, o próprio CNPJ)."""

    cnpj: str = ""
    cpf: str = ""
    nome: str = ""
    ie: str = ""
    email: str = ""
    # 1=Contribuinte, 2=Isento, 9=Não Contribuinte
    ind_ie_dest: str = ""
    endereco: Endereco = field(default_factory=Endereco)


@dataclass
class Transportadora:
    """Dados do transportador."""

    cnpj: str = ""
    cpf: str = ""
    nome: str = ""
    ie: str = ""
    endereco_completo: str = ""
    municipio: str = ""
    uf: str = ""
    # 0=Emitente, 1=Destinatário, 2=Terceiros, 9=Sem frete
    mod_frete: str = ""


@dataclass
class ImpostosItem:
    """Impostos de um item da NF-e."""

    # ICMS
    icms_cst: str = ""
    icms_orig: str = ""
    icms_base: Decimal = Decimal("0")
    icms_aliq: Decimal = Decimal("0")
    icms_valor: Decimal = Decimal("0")
    icms_base_st: Decimal = Decimal("0")
    icms_aliq_st: Decimal = Decimal("0")
    icms_valor_st: Decimal = Decimal("0")

    # IPI
    ipi_cst: str = ""
    ipi_base: Decimal = Decimal("0")
    ipi_aliq: Decimal = Decimal("0")
    ipi_valor: Decimal = Decimal("0")

    # PIS
    pis_cst: str = ""
    pis_base: Decimal = Decimal("0")
    pis_aliq: Decimal = Decimal("0")
    pis_valor: Decimal = Decimal("0")

    # COFINS
    cofins_cst: str = ""
    cofins_base: Decimal = Decimal("0")
    cofins_aliq: Decimal = Decimal("0")
    cofins_valor: Decimal = Decimal("0")


@dataclass
class ItemNFe:
    """Item da NF-e."""

    numero: int = 0
    codigo: str = ""
    codigo_barras: str = ""
    descricao: str = ""
    ncm: str = ""
    cest: str = ""
    cfop: str = ""
    unidade: str = ""
    quantidade: Decimal = Decimal("0")
    valor_unitario: Decimal = Decimal("0")
    valor_total: Decimal = Decimal("0")
    valor_desconto: Decimal = Decimal("0")
    valor_frete: Decimal = Decimal("0")
    valor_seguro: Decimal = Decimal("0")
    valor_outras: Decimal = Decimal("0")
    info_adicional: str = ""
    impostos: ImpostosItem = field(default_factory=ImpostosItem)


@dataclass
class TotaisNFe:
    """Totais da NF-e."""

    base_icms: Decimal = Decimal("0")
    valor_icms: Decimal = Decimal("0")
    valor_icms_deson: Decimal = Decimal("0")
    base_icms_st: Decimal = Decimal("0")
    valor_icms_st: Decimal = Decimal("0")
    valor_produtos: Decimal = Decimal("0")
    valor_frete: Decimal = Decimal("0")
    valor_seguro: Decimal = Decimal("0")
    valor_desconto: Decimal = Decimal("0")
    valor_ii: Decimal = Decimal("0")
    valor_ipi: Decimal = Decimal("0")
    valor_pis: Decimal = Decimal("0")
    valor_cofins: Decimal = Decimal("0")
    valor_outros: Decimal = Decimal("0")
    valor_nota: Decimal = Decimal("0")


@dataclass
class Cobranca:
    """Dados de cobrança da NF-e."""

    numero_fatura: str = ""
    valor_original: Decimal = Decimal("0")
    valor_desconto: Decimal = Decimal("0")
    valor_liquido: Decimal = Decimal("0")
    duplicatas: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Pagamento:
    """Forma de pagamento."""

    # 01=Dinheiro, 02=Cheque, 03=Cartão Crédito, 04=Cartão Débito, ...
    forma: str = ""
    valor: Decimal = Decimal("0")
    bandeira: str = ""
    autorizacao: str = ""


@dataclass
class NFe:
    """Estrutura completa da NF-e parseada."""

    # Identificação
    chave: str = ""
    numero: str = ""
    serie: str = ""
    modelo: str = "55"
    data_emissao: Optional[datetime] = None
    data_saida_entrada: Optional[datetime] = None
    # 0=Entrada, 1=Saída
    tipo_operacao: str = ""
    natureza_operacao: str = ""
    # 1=Normal, 2=Complementar, 3=Ajuste, 4=Devolução
    finalidade: str = ""
    # 0=Normal, 1=Consumidor Final
    ind_consumidor_final: str = ""
    # 0=NA, 1=Presencial, 2=Internet, etc
    ind_presenca: str = ""
    # 1=Interna, 2=Interestadual, 3=Exterior
    indicador_destino: str = ""

    # Protocolo de autorização
    protocolo: str = ""
    data_autorizacao: Optional[datetime] = None
    digest_value: str = ""

    # Participantes
    emitente: Emitente = field(default_factory=Emitente)
    destinatario: Destinatario = field(default_factory=Destinatario)
    transportadora: Transportadora = field(default_factory=Transportadora)

    # Itens
    itens: List[ItemNFe] = field(default_factory=list)

    # Totais
    totais: TotaisNFe = field(default_factory=TotaisNFe)

    # Cobrança e Pagamento
    cobranca: Cobranca = field(default_factory=Cobranca)
    pagamentos: List[Pagamento] = field(default_factory=list)

    # Informações adicionais
    info_complementar: str = ""
    info_fisco: str = ""

    # XML original (para auditoria)
    xml_original: str = ""


class NFeParser:
    """Parser de XML de NF-e."""

    def __init__(self):
        self.ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

    def _find_text(self, element, path: str, default: str = "") -> str:
        if element is None:
            return default

        result = element.find(f".//nfe:{path}", self.ns)
        if result is not None and result.text:
            return result.text.strip()

        result = element.find(f".//{path}")
        if result is not None and result.text:
            return result.text.strip()

        result = element.find(path)
        if result is not None and result.text:
            return result.text.strip()

        return default

    def _find_element(self, element, path: str):
        if element is None:
            return None

        result = element.find(f".//nfe:{path}", self.ns)
        if result is not None:
            return result

        result = element.find(f"nfe:{path}", self.ns)
        if result is not None:
            return result

        result = element.find(f".//{path}")
        if result is not None:
            return result

        return element.find(path)

    def _findall_elements(self, element, path: str):
        if element is None:
            return []

        result = element.findall(f".//nfe:{path}", self.ns)
        if result:
            return result

        result = element.findall(f"nfe:{path}", self.ns)
        if result:
            return result

        result = element.findall(f".//{path}")
        if result:
            return result

        return element.findall(path)

    def _find_decimal(
        self, element, path: str, default: Decimal = Decimal("0")
    ) -> Decimal:
        text = self._find_text(element, path, "")
        if text:
            try:
                return Decimal(text)
            except (InvalidOperation, ValueError, TypeError):
                return default
        return default

    def _parse_datetime(self, value: str) -> Optional[datetime]:
        if not value:
            return None

        value = value.strip()
        if value.endswith("Z"):
            value = f"{value[:-1]}+00:00"

        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass

        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            pass

        return None

    def _parse_endereco(self, elem) -> Endereco:
        if elem is None:
            return Endereco()

        return Endereco(
            logradouro=self._find_text(elem, "xLgr"),
            numero=self._find_text(elem, "nro"),
            complemento=self._find_text(elem, "xCpl"),
            bairro=self._find_text(elem, "xBairro"),
            cod_municipio=self._find_text(elem, "cMun"),
            municipio=self._find_text(elem, "xMun"),
            uf=self._find_text(elem, "UF"),
            cep=self._find_text(elem, "CEP"),
            cod_pais=self._find_text(elem, "cPais", "1058"),
            pais=self._find_text(elem, "xPais", "Brasil"),
            telefone=self._find_text(elem, "fone"),
        )

    def _parse_emitente(self, emit) -> Emitente:
        if emit is None:
            return Emitente()

        ender = self._find_element(emit, "enderEmit")

        return Emitente(
            cnpj=self._find_text(emit, "CNPJ"),
            cpf=self._find_text(emit, "CPF"),
            nome=self._find_text(emit, "xNome"),
            nome_fantasia=self._find_text(emit, "xFant"),
            ie=self._find_text(emit, "IE"),
            ie_st=self._find_text(emit, "IEST"),
            im=self._find_text(emit, "IM"),
            cnae=self._find_text(emit, "CNAE"),
            crt=self._find_text(emit, "CRT"),
            endereco=self._parse_endereco(ender),
        )

    def _parse_destinatario(self, dest) -> Destinatario:
        if dest is None:
            return Destinatario()

        ender = self._find_element(dest, "enderDest")

        return Destinatario(
            cnpj=self._find_text(dest, "CNPJ"),
            cpf=self._find_text(dest, "CPF"),
            nome=self._find_text(dest, "xNome"),
            ie=self._find_text(dest, "IE"),
            email=self._find_text(dest, "email"),
            ind_ie_dest=self._find_text(dest, "indIEDest"),
            endereco=self._parse_endereco(ender),
        )

    def _parse_transportadora(self, transp) -> Transportadora:
        if transp is None:
            return Transportadora()

        transporta = self._find_element(transp, "transporta")

        result = Transportadora(mod_frete=self._find_text(transp, "modFrete"))

        if transporta is not None:
            result.cnpj = self._find_text(transporta, "CNPJ")
            result.cpf = self._find_text(transporta, "CPF")
            result.nome = self._find_text(transporta, "xNome")
            result.ie = self._find_text(transporta, "IE")
            result.endereco_completo = self._find_text(transporta, "xEnder")
            result.municipio = self._find_text(transporta, "xMun")
            result.uf = self._find_text(transporta, "UF")

        return result

    def _parse_impostos_item(self, imposto) -> ImpostosItem:
        result = ImpostosItem()

        if imposto is None:
            return result

        # ICMS pode estar em vários grupos (ICMS00, ICMS10, ICMS20, etc) ou
        # ser CSOSN (Simples Nacional) — varremos os filhos para encontrar.
        icms = self._find_element(imposto, "ICMS")
        if icms is not None:
            for child in icms:
                if child.tag.startswith("ICMS") or "ICMS" in child.tag:
                    result.icms_orig = self._find_text(child, "orig")
                    result.icms_cst = self._find_text(child, "CST") or self._find_text(
                        child, "CSOSN"
                    )
                    result.icms_base = self._find_decimal(child, "vBC")
                    result.icms_aliq = self._find_decimal(child, "pICMS")
                    result.icms_valor = self._find_decimal(child, "vICMS")
                    result.icms_base_st = self._find_decimal(child, "vBCST")
                    result.icms_aliq_st = self._find_decimal(child, "pICMSST")
                    result.icms_valor_st = self._find_decimal(child, "vICMSST")
                    break

        ipi = self._find_element(imposto, "IPI")
        if ipi is not None:
            result.ipi_cst = self._find_text(ipi, "CST")
            result.ipi_base = self._find_decimal(ipi, "vBC")
            result.ipi_aliq = self._find_decimal(ipi, "pIPI")
            result.ipi_valor = self._find_decimal(ipi, "vIPI")

        pis = self._find_element(imposto, "PIS")
        if pis is not None:
            for child in pis:
                if "PIS" in child.tag:
                    result.pis_cst = self._find_text(child, "CST")
                    result.pis_base = self._find_decimal(child, "vBC")
                    result.pis_aliq = self._find_decimal(child, "pPIS")
                    result.pis_valor = self._find_decimal(child, "vPIS")
                    break

        cofins = self._find_element(imposto, "COFINS")
        if cofins is not None:
            for child in cofins:
                if "COFINS" in child.tag:
                    result.cofins_cst = self._find_text(child, "CST")
                    result.cofins_base = self._find_decimal(child, "vBC")
                    result.cofins_aliq = self._find_decimal(child, "pCOFINS")
                    result.cofins_valor = self._find_decimal(child, "vCOFINS")
                    break

        return result

    def _parse_item(self, det) -> ItemNFe:
        item = ItemNFe()
        item.numero = int(det.get("nItem", "0"))

        prod = self._find_element(det, "prod")
        if prod is not None:
            item.codigo = self._find_text(prod, "cProd")
            item.codigo_barras = self._find_text(prod, "cEAN")
            item.descricao = self._find_text(prod, "xProd")
            item.ncm = self._find_text(prod, "NCM")
            item.cest = self._find_text(prod, "CEST")
            item.cfop = self._find_text(prod, "CFOP")
            item.unidade = self._find_text(prod, "uCom")
            item.quantidade = self._find_decimal(prod, "qCom")
            item.valor_unitario = self._find_decimal(prod, "vUnCom")
            item.valor_total = self._find_decimal(prod, "vProd")
            item.valor_desconto = self._find_decimal(prod, "vDesc")
            item.valor_frete = self._find_decimal(prod, "vFrete")
            item.valor_seguro = self._find_decimal(prod, "vSeg")
            item.valor_outras = self._find_decimal(prod, "vOutro")

        imposto = self._find_element(det, "imposto")
        item.impostos = self._parse_impostos_item(imposto)

        item.info_adicional = self._find_text(det, "infAdProd")

        return item

    def _parse_totais(self, total) -> TotaisNFe:
        if total is None:
            return TotaisNFe()

        icms_tot = self._find_element(total, "ICMSTot")
        if icms_tot is None:
            return TotaisNFe()

        return TotaisNFe(
            base_icms=self._find_decimal(icms_tot, "vBC"),
            valor_icms=self._find_decimal(icms_tot, "vICMS"),
            valor_icms_deson=self._find_decimal(icms_tot, "vICMSDeson"),
            base_icms_st=self._find_decimal(icms_tot, "vBCST"),
            valor_icms_st=self._find_decimal(icms_tot, "vST"),
            valor_produtos=self._find_decimal(icms_tot, "vProd"),
            valor_frete=self._find_decimal(icms_tot, "vFrete"),
            valor_seguro=self._find_decimal(icms_tot, "vSeg"),
            valor_desconto=self._find_decimal(icms_tot, "vDesc"),
            valor_ii=self._find_decimal(icms_tot, "vII"),
            valor_ipi=self._find_decimal(icms_tot, "vIPI"),
            valor_pis=self._find_decimal(icms_tot, "vPIS"),
            valor_cofins=self._find_decimal(icms_tot, "vCOFINS"),
            valor_outros=self._find_decimal(icms_tot, "vOutro"),
            valor_nota=self._find_decimal(icms_tot, "vNF"),
        )

    def _parse_cobranca(self, cobr) -> Cobranca:
        result = Cobranca()

        if cobr is None:
            return result

        fat = self._find_element(cobr, "fat")
        if fat is not None:
            result.numero_fatura = self._find_text(fat, "nFat")
            result.valor_original = self._find_decimal(fat, "vOrig")
            result.valor_desconto = self._find_decimal(fat, "vDesc")
            result.valor_liquido = self._find_decimal(fat, "vLiq")

        for dup in self._findall_elements(cobr, "dup"):
            result.duplicatas.append(
                {
                    "numero": self._find_text(dup, "nDup"),
                    "vencimento": self._find_text(dup, "dVenc"),
                    "valor": _decimal_to_cents(self._find_decimal(dup, "vDup")),
                }
            )

        return result

    def _parse_pagamentos(self, pag) -> List[Pagamento]:
        result = []

        if pag is None:
            return result

        for det_pag in self._findall_elements(pag, "detPag"):
            pagamento = Pagamento(
                forma=self._find_text(det_pag, "tPag"),
                valor=self._find_decimal(det_pag, "vPag"),
            )

            card = self._find_element(det_pag, "card")
            if card is not None:
                pagamento.bandeira = self._find_text(card, "tBand")
                pagamento.autorizacao = self._find_text(card, "cAut")

            result.append(pagamento)

        return result

    def parse(self, xml_content: str) -> NFe:
        """Faz o parse completo de um XML de NF-e (procNFe ou nfeProc)."""
        nfe = NFe()
        nfe.xml_original = xml_content

        try:
            # Desabilita resolução de entidades externas (proteção XXE)
            parser = etree.XMLParser(resolve_entities=False, no_network=True)
            xml_to_parse = xml_content.lstrip()
            if xml_to_parse.startswith("<?xml"):
                declaration_end = xml_to_parse.find("?>")
                if declaration_end != -1:
                    xml_to_parse = xml_to_parse[declaration_end + 2:]
            root = etree.fromstring(xml_to_parse.encode("utf-8"), parser=parser)
        except (etree.XMLSyntaxError, ValueError, TypeError) as e:
            raise ValueError(f"XML inválido: {e}")

        prot = self._find_element(root, "protNFe")
        if prot is not None:
            inf_prot = self._find_element(prot, "infProt")
            if inf_prot is not None:
                nfe.chave = self._find_text(inf_prot, "chNFe")
                nfe.protocolo = self._find_text(inf_prot, "nProt")
                nfe.digest_value = self._find_text(inf_prot, "digVal")
                nfe.data_autorizacao = self._parse_datetime(
                    self._find_text(inf_prot, "dhRecbto")
                )

        inf_nfe = self._find_element(root, "infNFe")
        if inf_nfe is not None:
            if not nfe.chave:
                nfe_id = inf_nfe.get("Id", "")
                nfe.chave = nfe_id.replace("NFe", "")

            ide = self._find_element(inf_nfe, "ide")
            if ide is not None:
                nfe.numero = self._find_text(ide, "nNF")
                nfe.serie = self._find_text(ide, "serie")
                nfe.modelo = self._find_text(ide, "mod", "55")
                nfe.natureza_operacao = self._find_text(ide, "natOp")
                nfe.tipo_operacao = self._find_text(ide, "tpNF")
                nfe.finalidade = self._find_text(ide, "finNFe")
                nfe.ind_consumidor_final = self._find_text(ide, "indFinal")
                nfe.ind_presenca = self._find_text(ide, "indPres")
                nfe.indicador_destino = self._find_text(ide, "idDest")

                nfe.data_emissao = self._parse_datetime(self._find_text(ide, "dhEmi"))
                nfe.data_saida_entrada = self._parse_datetime(
                    self._find_text(ide, "dhSaiEnt")
                )

            emit = self._find_element(inf_nfe, "emit")
            if emit is not None:
                nfe.emitente = self._parse_emitente(emit)

            dest = self._find_element(inf_nfe, "dest")
            if dest is not None:
                nfe.destinatario = self._parse_destinatario(dest)

            for det in self._findall_elements(inf_nfe, "det"):
                item = self._parse_item(det)
                nfe.itens.append(item)

            total = self._find_element(inf_nfe, "total")
            if total is not None:
                nfe.totais = self._parse_totais(total)

            transp = self._find_element(inf_nfe, "transp")
            if transp is not None:
                nfe.transportadora = self._parse_transportadora(transp)

            cobr = self._find_element(inf_nfe, "cobr")
            nfe.cobranca = self._parse_cobranca(cobr)

            pag = self._find_element(inf_nfe, "pag")
            nfe.pagamentos = self._parse_pagamentos(pag)

            inf_adic = self._find_element(inf_nfe, "infAdic")
            if inf_adic is not None:
                nfe.info_complementar = self._find_text(inf_adic, "infCpl")
                nfe.info_fisco = self._find_text(inf_adic, "infAdFisco")

        return nfe

    def to_dict(self, nfe: NFe) -> Dict[str, Any]:
        """Converte NFe para dicionário (compatível com JSON)."""

        def decimal_to_json(obj, key: str = ""):
            if isinstance(obj, Decimal):
                if _is_money_key(key):
                    return _decimal_to_cents(obj)
                return float(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            if hasattr(obj, "__dataclass_fields__"):
                return {k: decimal_to_json(v, k) for k, v in obj.__dict__.items()}
            if isinstance(obj, list):
                return [decimal_to_json(i, key) for i in obj]
            if isinstance(obj, dict):
                return {k: decimal_to_json(v, k) for k, v in obj.items()}
            return obj

        return decimal_to_json(nfe)


def parse_nfe_file(file_path: str) -> NFe:
    """Parse de arquivo XML com fallback de encoding (UTF-8 → latin-1)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="latin-1") as f:
            content = f.read()
    parser = NFeParser()
    return parser.parse(content)


def parse_nfe_string(xml_content: str) -> NFe:
    """Parse de string XML."""
    parser = NFeParser()
    return parser.parse(xml_content)
