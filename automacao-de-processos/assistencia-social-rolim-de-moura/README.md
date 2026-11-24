# IA e automação para o Administrativo da Secretaria Municipal de Assistência Social, Rolim de Moura (RO)

> Levantamento feito em novembro de 2026 no GitHub, no Hugging Face e em experiências públicas de outras prefeituras e de outros países.
> Objetivo: reduzir a carga do setor administrativo da SEMAS/SMAS sem reinventar o que o governo federal já fornece de graça.

---

## 1. Resumo

1. **Use primeiro o que é gratuito e obrigatório.** Desde 19/12/2025 o MDS opera o **Prontuário Eletrônico do SUAS** nacional (Resolução CIT nº 29/2025). Não vale a pena criar outro prontuário. O ganho está em tudo o que fica em volta dele: ofícios, controles em planilha, relatórios, atendimento por WhatsApp e consolidação de dados.
2. **Há quatro frentes com retorno rápido**, e todas podem ser montadas só com software livre:
   - **A. Assistente de documentos** (ofícios, memorandos, pareceres, atas do CMAS, termos de referência): um LLM com os modelos de documentos da própria secretaria.
   - **B. Atendimento e agendamento por WhatsApp** (CadÚnico, Bolsa Família, benefícios eventuais), com triagem automática e passagem para um atendente humano.
   - **C. Digitalização e busca no acervo** (OCR e busca por significado em processos, leis, resoluções e portarias).
   - **D. Painel de vigilância socioassistencial** com os dados do CECAD/CadÚnico, nos moldes de **Vale do Paraíso/RO** e Hortolândia/SP.
3. **A experiência internacional mais forte é a transcrição e o resumo de atendimentos.** No Reino Unido, o *Magic Notes* reduziu de 46% a 63% o tempo de registro em pilotos de várias prefeituras (números informados pelas próprias prefeituras, sem avaliação independente). Dá para montar algo equivalente com **Whisper** e um LLM local, mas sempre com revisão do técnico.
4. **A LGPD vem antes de tudo.** Dados da assistência social são sensíveis (art. 11 da LGPD). Dados pessoais de usuários só devem ser processados em servidor próprio ou em nuvem com contrato e DPA. A decisão sobre qualquer benefício deve ser sempre de um servidor.

---

## 2. Onde está a carga do administrativo

| Demanda típica | Dor | Frente que ajuda |
|---|---|---|
| Ofícios, memorandos, despachos, CI, respostas ao MP, Conselho Tutelar e Judiciário | Redação repetitiva, retrabalho | **A** |
| Atas e resoluções do CMAS e de outros conselhos | Transcrever reunião, formatar | **A** e transcrição |
| Benefícios eventuais (cesta, auxílio-natalidade, funeral, aluguel social) | Controle em papel ou planilha, conferência de critérios, relatório mensal | Sistema simples, **D** |
| Fila do CadÚnico e do Bolsa Família (agendar, dúvidas, documentos) | Telefone e balcão lotados | **B** |
| RMA, Censo SUAS, Demonstrativo do SUASweb, prestação de contas do cofinanciamento (federal e estadual, SEAS/RO) | Coletar dados espalhados entre CRAS, CREAS e equipes | **D** e planilhas automatizadas |
| Termos de referência, ETP, processos de compra (Lei 14.133) | Texto técnico longo | **A** e busca no acervo (**C**) |
| Arquivo físico de processos | Achar documentos antigos | **C** |
| Encaminhamentos para a rede (saúde, educação, Conselho Tutelar) | Repassar fichas, acompanhar retorno | **B**, mais adiante um fluxo de trabalho |

---

## 3. Sistemas do governo que já existem (usar e integrar, não copiar)

| Sistema | Para que serve | Observação |
|---|---|---|
| **Prontuário Eletrônico do SUAS** (MDS) | Registro do atendimento no CRAS e no CREAS | Nacional desde dez/2025, diretrizes na Resolução CIT 29/2025 |
| **CECAD** | Extração e tabulação do CadÚnico do município | Fonte de dados da frente **D** |
| **SUASweb / CadSUAS / Censo SUAS / RMA** | Gestão, cofinanciamento e indicadores | Hoje o preenchimento é manual; dá para automatizar o preparo das planilhas |
| **VIS Data / SAGI (MDS)** | Indicadores prontos por município | Bom para relatórios ao CMAS e à Câmara |
| **Canal de WhatsApp do MDS e Disque Social 121** | Atendimento federal | Encaminhar dúvidas federais para lá |
| **Serpro Gestão Social** | Plataforma paga de gestão de benefícios integrada ao CadÚnico | Alternativa contratável, porque o Serpro é empresa pública. Pedir proposta para comparar com o software livre |

---

## 4. Software livre no GitHub que pode ser reaproveitado

### 4.1 Feitos para a assistência social no Brasil (servem de referência ou base)

| Repositório | O que é | Uso aqui |
|---|---|---|
| [vigilanciasocioassistencialvp/vale-do-paraiso-dashboard](https://github.com/vigilanciasocioassistencialvp/vale-do-paraiso-dashboard) | Painel offline do CadÚnico da Vigilância Socioassistencial de **Vale do Paraíso/RO** | **Município vizinho, no mesmo estado.** Modelo direto para a frente D |
| [vigilanciasocioassistencialvp/conselho-tutelar-dashboard](https://github.com/vigilanciasocioassistencialvp/conselho-tutelar-dashboard) | Painel do Conselho Tutelar, do mesmo município | Mesmo uso |
| [ailtonfv/Atlas-Social-de-Hortolandia](https://github.com/ailtonfv/Atlas-Social-de-Hortolandia) (38★) | Estrutura analítica do CadÚnico municipal, sem dados pessoais | Base para a frente D |
| [victorijsn/AppLeituraCadastroUnico](https://github.com/victorijsn/AppLeituraCadastroUnico) | Leitura e tratamento da base do CECAD | Importar o CadÚnico |
| [victorijsn/Script-IDF](https://github.com/victorijsn/Script-IDF) | Cálculo do Índice de Desenvolvimento da Família | Priorizar a busca ativa |
| [EL-BID/analise-cadunico](https://github.com/EL-BID/analise-cadunico) | Análise do CadÚnico (BID) | Referência metodológica |
| [lucaswarwar/assistencia_social](https://github.com/lucaswarwar/assistencia_social) | Geolocalização de todos os CRAS do Brasil | Mapas |
| [PaulusXavier/Projeto-Argo-SUAS](https://github.com/PaulusXavier/Projeto-Argo-SUAS) | Aplicativos web offline (PWA) para o trabalho técnico do CRAS | Ideias para visitas domiciliares sem internet |
| [JonasLimaDev/registro-benficios-eventuais](https://github.com/JonasLimaDev/registro-benficios-eventuais) | Sistema em Django para registrar a entrega de benefícios eventuais | **Base para substituir a planilha de cestas e auxílios** |
| [vigilanciasocioassistencialjp-maker/sistema-beneficios-semasf](https://github.com/vigilanciasocioassistencialjp-maker/sistema-beneficios-semasf) | Controle de benefícios eventuais de uma SEMASF | Mesmo uso |
| [RobertoTaveiraDev/ampara-social](https://github.com/RobertoTaveiraDev/ampara-social) | Encaminhamento entre CRAS, CREAS e CAPS (Laravel) | Referência para encaminhamentos na rede |
| [CRASTecnus/Registro-Mensal-de-Atendimento-RMA-](https://github.com/CRASTecnus/Registro-Mensal-de-Atendimento-RMA-) | Coleta do RMA em Python | Automatizar o RMA |
| [eulisonmonteiro-rgb/ficha-busca-ativa](https://github.com/eulisonmonteiro-rgb/ficha-busca-ativa) | Ficha de busca ativa e escuta qualificada (Oriximiná/PA) | Formulário digital |
| [littleisa/conselho-tutelar](https://github.com/littleisa/conselho-tutelar) | Gestão de ocorrências do Conselho Tutelar (Django e Docker) | Integração com o Conselho Tutelar |

> Atenção: quase todos são projetos pequenos (0 a 40 estrelas). Sirvam-se deles como **ponto de partida**, não como produto pronto. Antes de usar qualquer um, revise o código e a licença.

### 4.2 Plataformas internacionais de proteção social (o que outros países usam)

| Projeto | O que é | Lição para Rolim de Moura |
|---|---|---|
| [OpenSPP](https://github.com/OpenSPP/openspp-modules) (LGPL-3.0) | Plataforma livre de proteção social (cadastro, elegibilidade, pagamentos) sobre o Odoo | Módulos de elegibilidade e entrega de benefícios. Estrutura pesada para um município sozinho, mas serve de modelo |
| OpenG2P | Registro e pagamento *government-to-person* | Mesmo conceito |
| [openIMIS](https://github.com/openimis/openimis-dist_dkr) | Gestão de seguros e benefícios sociais | Referência de fluxo |
| Primero (UNICEF) | Gestão de casos de proteção de crianças e violência de gênero | Inspiração para o CREAS e a rede de proteção |
| [CommCare](https://github.com/dimagi/commcare-hq) (527★) e KoboToolbox / ODK | Formulários de campo offline | **Visitas domiciliares e busca ativa sem internet**, com dados enviados ao voltar |

### 4.3 Ferramentas genéricas maduras para montar a solução

| Ferramenta | ★ | Papel |
|---|---|---|
| [open-webui/open-webui](https://github.com/open-webui/open-webui) | 159 mil | Interface tipo "ChatGPT interno" para os servidores (frente A) |
| [ollama](https://ollama.com) | — | Roda LLMs no servidor da prefeitura |
| [Mintplex-Labs/anything-llm](https://github.com/Mintplex-Labs/anything-llm) | 68 mil | Alternativa mais simples: chat com os documentos da secretaria |
| [infiniflow/ragflow](https://github.com/infiniflow/ragflow) | 94 mil | Busca inteligente em grandes acervos (frente C) |
| [docling-project/docling](https://github.com/docling-project/docling) | 70 mil | Converte PDF e DOCX em texto estruturado para a IA |
| [paperless-ngx/paperless-ngx](https://github.com/paperless-ngx/paperless-ngx) | 48 mil | Arquivo digital com OCR, etiquetas e busca (frente C) |
| [ocrmypdf/OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) | 35 mil | OCR em PDFs digitalizados |
| [Stirling-Tools/Stirling-PDF](https://github.com/Stirling-Tools/Stirling-PDF) | 97 mil | Juntar, dividir, assinar e comprimir PDFs (uso diário do administrativo) |
| [evolution-foundation/evolution-api](https://github.com/evolution-foundation/evolution-api) | 10 mil | Conexão com o WhatsApp (frente B) |
| [chatwoot/chatwoot](https://github.com/chatwoot/chatwoot) | 40 mil | Central de atendimento multiatendente: o bot passa a conversa para o humano (frente B) |
| [n8n](https://n8n.io) | — | Automação de fluxos que liga WhatsApp, planilhas, e-mail e IA |
| [metabase/metabase](https://github.com/metabase/metabase) | 50 mil | Painéis e indicadores (frente D) |
| [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 27 mil | Transcrição de áudio de reuniões e atendimentos |

---

## 5. Modelos de IA no Hugging Face (para rodar localmente, sem enviar dados para fora)

| Tarefa | Modelo recomendado | Licença | Observação |
|---|---|---|---|
| Redação e resumo (LLM geral, bom em português) | [Qwen/Qwen3-8B](https://hf.co/Qwen/Qwen3-8B) ou [Qwen/Qwen3-14B](https://hf.co/Qwen/Qwen3-14B) | Apache-2.0 | Bom equilíbrio entre qualidade e custo. O 8B roda em GPU de 12 a 16 GB |
| LLM mais forte (se houver GPU maior) | [Qwen/Qwen3.8-27B](https://hf.co/Qwen/Qwen3.8-27B) | Apache-2.0 | Também lê imagens (documentos fotografados) |
| Alternativa | [google/gemma-3-12b-it](https://hf.co/google/gemma-3-12b-it) | Gemma | Lê imagens |
| LLM pequeno nativo em português | [TucanoBR/Tucano-2b4-Instruct](https://hf.co/TucanoBR/Tucano-2b4-Instruct) | Apache-2.0 | Brasileiro, leve, bom para classificar e fazer triagem em máquina modesta |
| Transcrição de voz | [openai/whisper-large-v3-turbo](https://hf.co/openai/whisper-large-v3-turbo) | MIT | Atas do CMAS, áudios recebidos pelo WhatsApp, atendimentos (com consentimento) |
| Busca por significado (embeddings) | [BAAI/bge-m3](https://hf.co/BAAI/bge-m3) ou [Qwen/Qwen3-Embedding-0.6B](https://hf.co/Qwen/Qwen3-Embedding-0.6B) | MIT / Apache-2.0 | Base da frente C |
| Classificação e extração em português | [neuralmind/bert-base-portuguese-cased](https://hf.co/neuralmind/bert-base-portuguese-cased) (BERTimbau) | MIT | Classificar a demanda de cada mensagem (CadÚnico, BPC, cesta…) |
| Textos jurídicos | [ulysses-camara/legal-bert-pt-br](https://hf.co/ulysses-camara/legal-bert-pt-br) | MIT | Busca em leis e resoluções |

> No Hugging Face **não existe hoje nenhum modelo ou dataset específico de assistência social brasileira**. A especialização deve vir dos **documentos da própria secretaria** (modelos de ofício, PNAS, Tipificação Nacional, NOB-SUAS, leis municipais de benefícios eventuais), usados por busca (RAG), sem treinar um modelo novo.

**Opção em nuvem:** para textos **sem dados pessoais** (ofícios genéricos, TRs, minutas de lei), um LLM comercial em nuvem (Claude, por exemplo) dá qualidade superior sem custo de servidor. Se dados de usuários entrarem, é necessário contrato com cláusulas de LGPD.

---

## 6. Experiências que valem copiar

| Onde | O que fizeram | Como adaptar |
|---|---|---|
| **Recife/PE (2025)** | Atualização cadastral do CadÚnico via WhatsApp, com mensagens automáticas aos beneficiários | Avisar famílias com cadastro a vencer e agendar o atendimento |
| **Porto Alegre/RS (2026)** | IA no WhatsApp do 156 para dúvidas, protocolos e agendamentos; casos complexos vão para um atendente | Mesmo modelo: o bot responde o básico e passa o resto para o humano |
| **Rio de Janeiro/RJ (2026)** | IA e integração de bases (saúde, educação, assistência) para a primeira infância | Futuramente, cruzar CadÚnico com a vacinação e a frequência escolar (condicionalidades do PBF) |
| **Vale do Paraíso/RO** | Painel offline do CadÚnico e do Conselho Tutelar, publicado no GitHub | **Copiar quase direto**, porque a realidade é a mesma |
| **Hortolândia/SP** | Atlas Social do CadÚnico | Mapa de vulnerabilidade por bairro e setor rural |
| **Reino Unido (Kingston, Swindon, Somerset e outros)** | *Magic Notes*: grava o atendimento e gera o registro e o resumo. Pilotos relatam de 46% a 63% menos tempo de burocracia | Whisper + LLM local, **com consentimento do usuário e revisão obrigatória do técnico** |
| **Países que usam OpenSPP, OpenG2P ou Primero** | Cadastro único, elegibilidade e gestão de casos em software livre | Modelos de regras de elegibilidade para benefícios eventuais |

---

## 7. Proposta de arquitetura (tudo em um servidor da prefeitura)

```
            ┌──────────────── Servidor local (Linux + GPU 12–16 GB) ─────────────────┐
 Servidores │  Open WebUI  ──►  Ollama (Qwen3-8B / Tucano)  ◄── RAG (bge-m3 + docs)   │
 da SEMAS ──┤                                                                        │
            │  Paperless-ngx (OCR do arquivo)   Stirling-PDF   faster-whisper (atas)  │
            │                                                                        │
 Cidadão ───┤  WhatsApp ─► Evolution API ─► n8n (triagem/FAQ/agenda) ─► Chatwoot     │
 (WhatsApp) │                                                     └► atendente humano│
            │                                                                        │
 CECAD ─────┤  Import CSV ─► Banco (PostgreSQL) ─► Metabase / painel estilo Vale do   │
 (CadÚnico) │                                     Paraíso (sem nomes/CPF nos painéis)│
            └────────────────────────────────────────────────────────────────────────┘
```

**Custo aproximado:** todo o software é gratuito. O gasto principal é uma máquina com GPU de 12 a 16 GB de VRAM, ou um servidor alugado, mais o número de WhatsApp. Peça orçamento local; o valor muda conforme o mercado.

---

## 8. Plano em etapas

**Primeiros 30 dias (sem dados pessoais, risco baixo)**
1. Juntar 30 a 50 modelos de documentos da secretaria (ofícios, memorandos, pareceres, atas, TRs) e as leis municipais de benefícios eventuais.
2. Instalar Open WebUI + Ollama + Qwen3-8B (ou AnythingLLM) e carregar esses documentos.
3. Instalar Stirling-PDF para o uso diário.
4. Medir o tempo gasto por tipo de documento antes e depois.

**De 30 a 60 dias**
5. Paperless-ngx para digitalizar e organizar o arquivo.
6. Transcrição de reuniões do CMAS com faster-whisper e geração de minuta de ata.
7. Painel do CadÚnico a partir do CECAD, copiando o modelo de Vale do Paraíso/RO.
8. Sistema de benefícios eventuais (adaptar o repositório Django citado) para substituir planilhas.

**De 60 a 90 dias**
9. WhatsApp com FAQ e agendamento do CadÚnico (Evolution API + n8n + Chatwoot), **sem decisão automática**.
10. Relatório de impacto para o CMAS e o gabinete, e plano de expansão para os CRAS e o CREAS.

---

## 9. Cuidados obrigatórios

- **LGPD:** dados de assistência social são sensíveis. Fazer o Relatório de Impacto (RIPD), indicar o encarregado (DPO) do município e registrar a base legal (execução de política pública, art. 7º, III e art. 11, II, "b").
- **Sigilo profissional:** gravação de atendimento só com consentimento expresso. O Prontuário SUAS segue a política nacional de privacidade do MDS (Resolução CIT 29/2025).
- **Humano no controle:** a IA **redige e sugere**; quem decide benefício, encaminhamento e parecer é o servidor. Isso também protege contra a reprodução de vieses.
- **Painéis sem nomes, CPF ou NIS.** Use apenas dados agregados por bairro ou território.
- **Contratação:** se algo for contratado (Serpro, empresas), exigir cláusulas de LGPD, servidores no Brasil e portabilidade dos dados.

---

## 10. Fontes consultadas

- GitHub (busca pública) e Hugging Face Hub, novembro de 2026: repositórios e modelos listados nas tabelas acima.
- [Resolução CIT nº 29/2025: diretrizes do Prontuário SUAS Eletrônico](https://social.campos.rj.gov.br/wp-content/uploads/2025/12/RESOLUCAO-CIT-No-29-DE-6-DE-OUTUBRO-DE-2025-Diretrizes-para-a-Prontuario-Suas-Eletronico.pdf)
- [Folha BV: novo prontuário eletrônico do SUAS em operação](https://www.folhabv.com.br/?p=71434)
- [Serpro Gestão Social](https://www.serpro.gov.br/menu/noticias/noticias-2025/serpro-gestao-social-solucao-digital-assistencia-social)
- [Recife: atualização do CadÚnico por WhatsApp](https://www.diariodepernambuco.com.br/noticia/vidaurbana/2025/03/prefeitura-do-recife-usa-whatsapp-para-garantir-atualizacao-do-cadunic.html)
- [Porto Alegre: IA na Central 156](https://prefeitura.poa.br/smtc/noticias/porto-alegre-prepara-implantacao-de-ia-na-central-do-cidadao-156)
- [Rio de Janeiro: IA para a primeira infância](https://www.portaltela.com/noticias/politica/2026/05/26/prefeitura-do-rio-usa-ia-para-ampliar-protecao-a-primeira-infancia/)
- [Bot no WhatsApp para o CadÚnico (Mobile Time)](https://www.mobiletime.com.br/noticias/12/04/2024/bot-no-whatsapp-ajuda-pessoas-vulneraveis-a-se-cadastrarem-no-cadunico/)
- [Kingston Council: IA na assistência social de adultos (LGA)](https://www.local.gov.uk/node/8277441)
- [Swindon: piloto do Magic Notes](https://socitm.net/resource-hub/case-studies/ai-in-adult-social-care-swindon-borough-council/)
- [Somerset: Magic Notes](https://www.somerset.gov.uk/news/somerset-social-workers-save-time-on-admin-thanks-to-ai-tool-magic-notes/)
- [Newcastle: registro de transparência algorítmica do Magic Notes](https://www.gov.uk/algorithmic-transparency-records/newcastle-city-council-magic-notes)
- [Carta de Serviços da SEAS/RO 2025](https://rondonia.ro.gov.br/wp-content/uploads/2026/02/Carta-de-Servicos-SEAS_14x20-2025-Atualizada.pdf)
