# 💰 Financial-Conciliator Skill

Habilidade especializada em conciliação bancária automática usando o princípio de Partida Dobrada.

## 🚀 Como usar

Esta skill é projetada para ser consumida por um Agente de IA. O agente deve seguir as instruções contidas no arquivo `SKILL.md` para:

1.  Receber o Plano de Contas e Extratos (preferencialmente em Markdown vindo da `doc-intelligence`).
2.  Identificar as contas de Débito e Crédito.
3.  Validar contra Notas Fiscais e Planilhas Financeiras.

### Exemplo de Fluxo:
```text
Input: Extrato Bancário (MD) + Plano de Contas (MD)
Ação: IA processa via Partida Dobrada
Output: JSON estruturado com os lançamentos conciliados
```

## 📦 Dependências Necessárias

Para rodar o motor de conciliação e as validações, as seguintes bibliotecas são recomendadas:

```bash
pip install pydantic python-dotenv openai google-generativeai
```

- `pydantic`: Essencial para garantir que o output JSON siga exatamente o schema definido no `SKILL.md`.
- `python-dotenv`: Para gerenciar chaves de API com segurança.
- `openai` ou `google-generativeai`: Bibliotecas para interface com as LLMs que executam a lógica de conciliação.

## 🎯 Objetivo
Automatizar o fechamento contábil garantindo que cada entrada e saída no extrato tenha sua contrapartida correta no Plano de Contas, com validação em três camadas (Planilha, NF e Histórico).

---
**Autor:** Eliezer Henrique (Pós UFG)  
**Contato:** [contato@nex2u.ia.br](mailto:contato@nex2u.ia.br)
