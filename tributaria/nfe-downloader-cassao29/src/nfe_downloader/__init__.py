"""
nfe-downloader — Baixa NF-e (compras) da SEFAZ via Distribuição DF-e.

Exemplo de uso como biblioteca:

    from nfe_downloader import SefazClient
    client = SefazClient.from_env()
    client.sync(max_iterations=10)

Para uso via CLI, veja `nfe-downloader --help`.
"""

from .client import SEFAZClient as SefazClient
from .parser import NFeParser, parse_nfe_file, parse_nfe_string

__all__ = ["SefazClient", "NFeParser", "parse_nfe_file", "parse_nfe_string"]
__version__ = "0.1.0"
