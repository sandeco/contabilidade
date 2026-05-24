"""Testes de hardening de segurança — defense-in-depth.

Cobrem caminhos defensivos que não dependem de rede:
- HIGH-1: path traversal em _save_documento
- MEDIUM-2: validação de chave SEFAZ
- MEDIUM-3: validação amigável de SEFAZ_UF
- LOW-2: warning ao sobrescrever XML
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from nfe_downloader.client import (
    NFeSummary,
    PathTraversalError,
    SEFAZClient,
    _money_to_cents,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def fake_cert(tmp_path):
    """Cria um arquivo PFX inválido só para satisfazer cert_path existir.

    Não dá pra carregar (cryptography vai falhar), então os testes que
    instanciam SEFAZClient precisam mockar _load_certificate.
    """
    p = tmp_path / "fake.pfx"
    p.write_bytes(b"NOT_A_REAL_CERT")
    return str(p)


@pytest.fixture
def client_no_cert(tmp_path, fake_cert):
    """Cria SEFAZClient bypassando o carregamento real do certificado."""
    with patch.object(SEFAZClient, "_load_certificate"), patch.object(
        SEFAZClient, "_create_session"
    ):
        return SEFAZClient(
            cnpj="12345678000123",
            cert_path=fake_cert,
            cert_password="x",
            ambiente="homologacao",
            storage_dir=str(tmp_path / "storage"),
        )


# ============================================================
# HIGH-1: path traversal em _save_documento
# ============================================================


def test_save_documento_rejects_path_traversal_in_chave(client_no_cert):
    """Chave com '../' (path traversal) deve ser rejeitada."""
    doc = NFeSummary(
        nsu="000000000000001",
        schema="procNFe_v4.00.xsd",
        chave="../../etc/passwd-attempt",
        is_complete=True,
        xml_content="<x/>",
    )
    with pytest.raises(PathTraversalError):
        client_no_cert._save_documento(doc)


def test_save_documento_rejects_short_chave(client_no_cert):
    """Chave muito curta (não 44 dígitos) é rejeitada."""
    doc = NFeSummary(
        nsu="000000000000001",
        schema="procNFe_v4.00.xsd",
        chave="12345",  # 5 dígitos, não 44
        is_complete=True,
        xml_content="<x/>",
    )
    with pytest.raises(PathTraversalError):
        client_no_cert._save_documento(doc)


def test_save_documento_rejects_non_numeric_chave(client_no_cert):
    """Chave de 44 chars mas não-numérica é rejeitada."""
    doc = NFeSummary(
        nsu="000000000000001",
        schema="procNFe_v4.00.xsd",
        chave="a" * 44,
        is_complete=True,
        xml_content="<x/>",
    )
    with pytest.raises(PathTraversalError):
        client_no_cert._save_documento(doc)


def test_save_documento_rejects_non_numeric_nsu(client_no_cert):
    """NSU não-numérico (caso chave esteja vazia) é rejeitado."""
    doc = NFeSummary(
        nsu="../etc",
        schema="resNFe_v1.01.xsd",
        chave=None,
        is_complete=False,
        xml_content="<x/>",
    )
    with pytest.raises(PathTraversalError):
        client_no_cert._save_documento(doc)


def test_save_documento_aceita_chave_valida(client_no_cert):
    """Caminho feliz: chave válida de 44 dígitos é aceita."""
    doc = NFeSummary(
        nsu="000000000000001",
        schema="procNFe_v4.00.xsd",
        chave="3" * 44,
        is_complete=True,
        xml_content="<x/>",
    )
    # Não deve lançar
    path = client_no_cert._save_documento(doc)
    assert Path(path).exists()
    assert Path(path).name == ("3" * 44) + ".xml"


# ============================================================
# MEDIUM-2: validação de chave em consultar_por_chave
# ============================================================


def test_consultar_por_chave_rejeita_nao_numerica(client_no_cert):
    """Chave com letras é rejeitada antes de qualquer rede."""
    # Não chega a fazer rate-limit lock; rejeita antes
    result = client_no_cert.consultar_por_chave("a" * 44, _skip_rate_check=True)
    assert result.status == "error"
    assert result.codigo == "996"
    assert "numéricos" in result.motivo


def test_consultar_por_chave_rejeita_tamanho_errado(client_no_cert):
    """Chave de 43 dígitos é rejeitada."""
    result = client_no_cert.consultar_por_chave("1" * 43, _skip_rate_check=True)
    assert result.status == "error"
    assert result.codigo == "996"


# ============================================================
# MEDIUM-3: validação amigável de SEFAZ_UF
# ============================================================


def test_from_env_uf_invalida_mensagem_amigavel(tmp_path, monkeypatch):
    """SEFAZ_UF='SP' (sigla) deve dar erro com dica clara."""
    monkeypatch.setenv("SEFAZ_CNPJ", "12345678000123")
    monkeypatch.setenv("SEFAZ_CERT_PATH", str(tmp_path / "cert.pfx"))
    monkeypatch.setenv("SEFAZ_CERT_PASSWORD", "x")
    monkeypatch.setenv("SEFAZ_UF", "SP")  # sigla em vez de código IBGE

    # Garante que load_dotenv não vai puxar outro .env
    monkeypatch.delenv("CONTAB_ENV_FILE", raising=False)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="SEFAZ_UF deve ser código IBGE"):
        SEFAZClient.from_env()


# ============================================================
# MEDIUM-4: _money_to_cents loga warning em valor inválido
# ============================================================


def test_money_to_cents_loga_warning_em_invalido(caplog):
    """Valor não-parseável retorna 0 mas loga warning (não silencioso)."""
    import logging

    with caplog.at_level(logging.WARNING):
        result = _money_to_cents("nao-eh-numero")
    assert result == 0
    assert any("inválido" in r.message.lower() for r in caplog.records)


def test_money_to_cents_aceita_valor_valido():
    """Valor numérico válido converte corretamente para centavos."""
    assert _money_to_cents("100.00") == 10000
    assert _money_to_cents("99.99") == 9999
    assert _money_to_cents("0") == 0
    assert _money_to_cents("") == 0


# ============================================================
# LOW-2: warning ao sobrescrever XML
# ============================================================


def test_save_documento_avisa_ao_sobrescrever(client_no_cert, caplog):
    """Re-baixar o mesmo XML deve logar warning de sobrescrita."""
    import logging

    doc = NFeSummary(
        nsu="000000000000001",
        schema="procNFe_v4.00.xsd",
        chave="4" * 44,
        is_complete=True,
        xml_content="<x/>",
    )
    client_no_cert._save_documento(doc)

    with caplog.at_level(logging.WARNING):
        client_no_cert._save_documento(doc)

    assert any("Sobrescrevendo" in r.message for r in caplog.records)
