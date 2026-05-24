"""Mascaramento de identificadores sensíveis em logs e relatórios."""


def mask_chave(chave: str) -> str:
    """Mascara chave de acesso de NF-e (44 dígitos) para uso em logs.

    Exemplo: 35231012345678000123550010000012341234567890 → 3523...7890
    """
    value = str(chave or "")
    if len(value) <= 8:
        return "****" if value else ""
    return f"{value[:4]}...{value[-4:]}"


def mask_cnpj(cnpj: str) -> str:
    """Mascara CNPJ para uso em logs."""
    return "XX.XXX.XXX/XXXX-XX" if cnpj else ""
