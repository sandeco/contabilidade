"""Smoke tests — verificam que o pacote importa e a CLI responde."""

import subprocess
import sys


def test_import_package():
    """Pacote nfe_downloader importa sem erros."""
    import nfe_downloader

    assert hasattr(nfe_downloader, "SefazClient")
    assert hasattr(nfe_downloader, "NFeParser")
    assert nfe_downloader.__version__


def test_import_submodules():
    """Submódulos importam sem erros (cobre dependências indiretas)."""
    from nfe_downloader import client, parser, cli, masking  # noqa: F401


def test_masking():
    """Funções de mascaramento."""
    from nfe_downloader.masking import mask_chave, mask_cnpj

    assert mask_chave("35231012345678000123550010000012341234567890") == "3523...7890"
    assert mask_chave("") == ""
    assert mask_chave("short") == "****"
    assert mask_cnpj("12345678000123") == "XX.XXX.XXX/XXXX-XX"
    assert mask_cnpj("") == ""


def test_cli_help():
    """CLI responde a --help sem crashar."""
    result = subprocess.run(
        [sys.executable, "-m", "nfe_downloader.cli", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "nfe-downloader" in result.stdout
    assert "sync" in result.stdout
    assert "status" in result.stdout


def test_cli_version():
    """CLI responde a --version."""
    result = subprocess.run(
        [sys.executable, "-m", "nfe_downloader.cli", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "nfe-downloader" in result.stdout
