"""Tests do parser de NF-e contra um XML sintético mínimo."""

from decimal import Decimal

import pytest

from nfe_downloader.parser import NFeParser, parse_nfe_string


# XML sintético mínimo — não corresponde a nenhuma NF-e real. Os valores
# são fictícios e servem só para exercitar o parser.
NFE_MINIMA = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe>
    <infNFe Id="NFe35231012345678000123550010000012341234567890" versao="4.00">
      <ide>
        <cUF>35</cUF>
        <natOp>Venda de mercadoria</natOp>
        <mod>55</mod>
        <serie>1</serie>
        <nNF>1234</nNF>
        <dhEmi>2026-01-15T10:30:00-03:00</dhEmi>
        <tpNF>1</tpNF>
        <idDest>1</idDest>
        <finNFe>1</finNFe>
        <indFinal>0</indFinal>
        <indPres>1</indPres>
      </ide>
      <emit>
        <CNPJ>12345678000199</CNPJ>
        <xNome>Fornecedor Teste LTDA</xNome>
        <xFant>Fornecedor</xFant>
        <IE>123456789</IE>
        <CRT>3</CRT>
        <enderEmit>
          <xLgr>Rua Teste</xLgr>
          <nro>100</nro>
          <xBairro>Centro</xBairro>
          <cMun>3550308</cMun>
          <xMun>Sao Paulo</xMun>
          <UF>SP</UF>
          <CEP>01000000</CEP>
        </enderEmit>
      </emit>
      <dest>
        <CNPJ>98765432000188</CNPJ>
        <xNome>Comprador Teste LTDA</xNome>
        <IE>987654321</IE>
        <indIEDest>1</indIEDest>
      </dest>
      <det nItem="1">
        <prod>
          <cProd>P001</cProd>
          <cEAN>SEM GTIN</cEAN>
          <xProd>Produto Teste</xProd>
          <NCM>12345678</NCM>
          <CFOP>5102</CFOP>
          <uCom>UN</uCom>
          <qCom>2.0000</qCom>
          <vUnCom>50.0000</vUnCom>
          <vProd>100.00</vProd>
        </prod>
        <imposto>
          <ICMS>
            <ICMS00>
              <orig>0</orig>
              <CST>00</CST>
              <vBC>100.00</vBC>
              <pICMS>18.00</pICMS>
              <vICMS>18.00</vICMS>
            </ICMS00>
          </ICMS>
        </imposto>
      </det>
      <total>
        <ICMSTot>
          <vBC>100.00</vBC>
          <vICMS>18.00</vICMS>
          <vProd>100.00</vProd>
          <vNF>100.00</vNF>
          <vFrete>0.00</vFrete>
        </ICMSTot>
      </total>
    </infNFe>
  </NFe>
  <protNFe versao="4.00">
    <infProt>
      <tpAmb>1</tpAmb>
      <chNFe>35231012345678000123550010000012341234567890</chNFe>
      <dhRecbto>2026-01-15T10:31:00-03:00</dhRecbto>
      <nProt>135230000999999</nProt>
      <digVal>abc123==</digVal>
      <cStat>100</cStat>
      <xMotivo>Autorizado o uso da NF-e</xMotivo>
    </infProt>
  </protNFe>
</nfeProc>"""


def test_parse_identification():
    nfe = parse_nfe_string(NFE_MINIMA)
    assert nfe.chave == "35231012345678000123550010000012341234567890"
    assert nfe.numero == "1234"
    assert nfe.serie == "1"
    assert nfe.modelo == "55"
    assert nfe.tipo_operacao == "1"
    assert nfe.protocolo == "135230000999999"


def test_parse_emitente():
    nfe = parse_nfe_string(NFE_MINIMA)
    assert nfe.emitente.cnpj == "12345678000199"
    assert nfe.emitente.nome == "Fornecedor Teste LTDA"
    assert nfe.emitente.crt == "3"
    assert nfe.emitente.endereco.uf == "SP"
    assert nfe.emitente.endereco.cep == "01000000"


def test_parse_destinatario():
    nfe = parse_nfe_string(NFE_MINIMA)
    assert nfe.destinatario.cnpj == "98765432000188"
    assert nfe.destinatario.nome == "Comprador Teste LTDA"


def test_parse_item():
    nfe = parse_nfe_string(NFE_MINIMA)
    assert len(nfe.itens) == 1
    item = nfe.itens[0]
    assert item.numero == 1
    assert item.codigo == "P001"
    assert item.descricao == "Produto Teste"
    assert item.ncm == "12345678"
    assert item.cfop == "5102"
    assert item.quantidade == Decimal("2.0000")
    assert item.valor_total == Decimal("100.00")


def test_parse_impostos():
    nfe = parse_nfe_string(NFE_MINIMA)
    item = nfe.itens[0]
    assert item.impostos.icms_cst == "00"
    assert item.impostos.icms_base == Decimal("100.00")
    assert item.impostos.icms_aliq == Decimal("18.00")
    assert item.impostos.icms_valor == Decimal("18.00")


def test_parse_totais():
    nfe = parse_nfe_string(NFE_MINIMA)
    assert nfe.totais.valor_nota == Decimal("100.00")
    assert nfe.totais.valor_icms == Decimal("18.00")


def test_to_dict_returns_cents():
    """to_dict converte valores monetários para inteiros em centavos."""
    nfe = parse_nfe_string(NFE_MINIMA)
    parser = NFeParser()
    data = parser.to_dict(nfe)
    assert data["totais"]["valor_nota"] == 10000  # R$ 100,00 → 10000 centavos


def test_parse_invalid_xml_raises():
    """XML inválido lança ValueError."""
    with pytest.raises(ValueError):
        parse_nfe_string("isto nao e xml")
