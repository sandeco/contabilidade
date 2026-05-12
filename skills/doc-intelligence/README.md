# 📄 Doc-Intelligence Skill

Habilidade especializada em extração de inteligência de documentos financeiros e contábeis.

## 🚀 Como usar

Esta skill fornece um utilitário para extrair dados de planilhas e converter para um formato Markdown amigável para LLMs.

```bash
python extract_documents.py <caminho_da_planilha> [opções]
```

### Exemplos:
- **Extração básica:** `python extract_documents.py dados.xlsx`
- **Moeda customizada:** `python extract_documents.py dados.xlsx --currency "$"`
- **Saída em JSON:** `python extract_documents.py dados.xlsx --output json`
- **Colunas específicas:** `python extract_documents.py dados.xlsx --cols "data,valor,descricao"`

## 📦 Dependências Necessárias

Para o funcionamento completo da skill (incluindo extração de PDFs complexos sugerida no `SKILL.md`), instale:

```bash
pip install pandas openpyxl docling markitdown argparse
```

- `pandas` & `openpyxl`: Para processamento de planilhas Excel.
- `docling` / `markitdown`: Para conversão inteligente de PDFs e documentos desestruturados.
- `argparse`: Para interface de linha de comando.

## 🎯 Objetivo
Transformar documentos "sujos" ou desestruturados em dados limpos que seguem as regras de contabilidade (como extração de Planos de Contas de 11 dígitos).

---
**Autor:** Eliezer Henrique (Pós UFG)  
**Contato:** [contato@nex2u.ia.br](mailto:contato@nex2u.ia.br)
