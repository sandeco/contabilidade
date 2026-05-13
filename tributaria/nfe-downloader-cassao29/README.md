# 🤖 NF-e Downloader — SEFAZ via Distribuição DF-e

## 📌 Visão Geral

Baixa automaticamente as NF-e de **compra** (em que sua empresa é destinatária) diretamente da SEFAZ, usando o serviço oficial **Distribuição DF-e**.
Substitui a tarefa manual de logar no portal SEFAZ e baixar XMLs um a um — útil para escritórios contábeis que precisam coletar centenas de notas por cliente todo mês.

## ⚙️ Como funciona

- [x] **Entrada**: CNPJ da empresa + certificado digital A1 (.pfx).
- [x] **Processamento**: consulta SOAP ao endpoint `NFeDistribuicaoDFe` da SEFAZ, paginando por NSU (Número Sequencial Único) e descompactando GZIP. A autenticação do canal usa mTLS via certificado A1 (PKCS12); a verificação criptográfica da assinatura do XML em si não é feita por este utilitário — a confiança vem do canal mTLS direto com a SEFAZ.
- [x] **Saída**: XMLs organizados em `nfe_storage/<CNPJ>/{completos,resumos,eventos}/`, com NSU persistido para sync incremental.

```text
SEFAZ ── DistDFe SOAP ──> client.py ──> parser.py ──> nfe_storage/
                                                      ├── completos/   (NF-e XML inteiro)
                                                      ├── resumos/     (resNFe — quando não autorizada a baixar completo)
                                                      └── eventos/     (CC-e, cancelamento, ciência)
```

## 🛠️ Tecnologias

- **Python 3.10+**
- `requests` + `requests-pkcs12` (autenticação mTLS via certificado A1)
- `lxml` + `defusedxml` (parsing de XML, hardening contra XXE/billion-laughs)
- `cryptography` (leitura do PKCS12 / e-CNPJ A1)
- API: [NFeDistribuicaoDFe](https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=Mfx5/2EFvf0=) (Ambiente Nacional)

## ▶️ Como Executar

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar credenciais (NUNCA commite o .env real)
cp .env.example .env
$EDITOR .env   # preencha SEFAZ_CNPJ, SEFAZ_CERT_PATH, SEFAZ_CERT_PASSWORD, SEFAZ_UF

# 3. Validar a configuração
python -m nfe_downloader.cli info
python -m nfe_downloader.cli status     # testa conexão e mostra último NSU

# 4. Baixar NF-e pendentes
python -m nfe_downloader.cli sync
```

Comandos principais:

| Comando | O que faz |
| :--- | :--- |
| `info` | Lê o `.env` e mostra a configuração ativa (com mascaramento de dados sensíveis). |
| `status` | Testa a conexão SOAP e exibe o último NSU consumido. |
| `sync` | Baixa todas as NF-e pendentes desde o último NSU. |
| `list` | Lista as NF-e já baixadas localmente. |
| `get <chave>` | Mostra dados parseados de uma NF-e baixada (chave de 44 dígitos). |
| `download <chave>` | Solicita o XML completo de uma NF-e específica. |

> [!IMPORTANT]
> O `.env.example` já vem com `SEFAZ_AMBIENTE=homologacao` (sandbox da SEFAZ). Só mude para `producao` quando estiver confiante — produção tem rate limit e cota real.

## 🔒 Segurança

- **Nunca** comite o `.env` real ou o `.pfx` — ambos estão no `.gitignore`.
- O certificado A1 deve ter `chmod 600`.
- Os XMLs baixados contêm dados fiscais sensíveis (LGPD): trate o diretório `nfe_storage/` como sigiloso.
- Logs mascaram chave NF-e, CNPJ e CPF por padrão (`masking.py`).
- Path traversal validado: chaves NF-e fora do formato 44 dígitos numéricos são rejeitadas antes do `Path.join`.

## 🧪 Testes

```bash
pip install pytest
pytest tests/ -v
```

Cobertura: parser (caminhos felizes + XML malformado), security (path traversal, masking), smoke (import + CLI `--help`).

## 👤 Autor

Desenvolvido por **Cássio (cassao29)**

- GitHub: [@cassao29](https://github.com/cassao29)
- Inspiração: comunidade Grupo Sandeco IA Contabilidade — em especial Leal, que apontou a oportunidade do nicho de download em massa de NF-e para escritórios contábeis.

## 📜 Licença

MIT — veja `LICENSE`.
