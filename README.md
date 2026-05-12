# 🧠 Skills de Contabilidade Inteligente

Este diretório contém o conjunto de **Skills** (habilidades especializadas) utilizadas pelos agentes de IA para processar, extrair e conciliar dados contábeis de forma autônoma.

As skills são projetadas para serem modulares, permitindo que diferentes agentes as utilizem para tarefas específicas dentro do fluxo contábil.

---

## 🛠️ Skills Disponíveis

### 1. [doc-intelligence](./doc-intelligence/)
**Objetivo:** Especialista em Visão Computacional e Extração de Dados.
- **Função:** Transforma documentos desestruturados (PDFs, Imagens, Excel, OFX) em Markdown estruturado.
- **Capacidades:**
  - Extração analítica de Planos de Contas (Grau 5).
  - Mapeamento de Históricos Contábeis e legendas.
  - Normalização de Extratos Bancários para processamento.
  - Leitura de Notas Fiscais (NF-e, NFS-e).
- **Utilitário Principal:** `extract_documents.py` (Script genérico para extração de planilhas).

### 2. [financial-conciliator](./financial-conciliator/)
**Objetivo:** Especialista em Conciliação Bancária e Contábil.
- **Função:** Realiza o cruzamento de dados (3-way match) entre extratos, planilhas financeiras e notas fiscais.
- **Lógica:** Baseado no princípio da **Partida Dobrada**.
- **Capacidades:**
  - Identificação automática de contas (Ativo, Passivo, Despesas, Receitas).
  - Validação em três camadas (Planilha, NF, Histórico).
  - Geração de lançamentos contábeis estruturados em JSON.
  - Cálculo de índice de confiança por transação.

---

## 🚀 Como usar este diretório

Este diretório centraliza as inteligências do projeto. 
- **Instruções Gerais:** Cada pasta de skill possui seu próprio `README.md` com instruções detalhadas de instalação e uso.
- **Portabilidade:** As skills foram projetadas para serem independentes, podendo ser importadas para diferentes agentes ou projetos.

---

## 🛠️ Padrão para Criação de Novas Skills

Para manter a consistência do repositório, novas skills devem seguir esta estrutura:

1.  **Pasta da Skill**: Nome descritivo em `kebab-case`.
2.  **`README.md`**: Instruções de uso, exemplos de comandos e lista de dependências (`pip install`).
3.  **`SKILL.md`**: Definição do sistema para a LLM, regras de negócio e exemplos de *few-shot*.
4.  **Scripts de Suporte**: Arquivos `.py` que executam a lógica pesada ou utilitários necessários.
5.  **Assinatura**: Todo README e arquivo de definição deve conter a autoria do projeto.

---

## 📁 Estrutura de cada Skill

Cada pasta de skill segue o padrão:
- `README.md`: Instruções de instalação, uso e dependências específicas.
- `SKILL.md`: Definição do sistema, instruções de prompt e regras de negócio para a IA.
- `*.py`: Scripts de suporte e utilitários da skill.

---

## 📋 Objetivos do Projeto Original (Contexto)
Estas skills foram desenvolvidas originalmente para automatizar a contabilidade da **Nex2u**, com foco em transformar processos manuais de conciliação em fluxos digitais de alta precisão.

---
**Autor:** Eliezer Henrique (Aluno da Pós UFG)  
**Contato:** [contato@nex2u.ia.br](mailto:contato@nex2u.ia.br)
