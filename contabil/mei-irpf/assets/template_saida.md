# 📊 Mini Relatório: Declaração de IRPF para MEI

Olá! Com base nos dados financeiros fornecidos pela pessoa assessora/contadora, processamos os cálculos tributários do MEI seguindo a legislação contábil oficial brasileira e as diretrizes do Sebrae.

---

## 📈 Resumo Financeiro da Empresa

| Indicador Contábil | Valor do Exercício (R$) | Finalidade / Significado Prático |
| :--- | :---: | :--- |
| **Receita Bruta Anual** | `R$ {{RECEITA_BRUTA}}` | Faturamento bruto total auferido pelo CNPJ no ano-calendário. |
| **Despesas Comprovadas** | `R$ {{DESPESAS}}` | Custos operacionais reais comprovados com nota fiscal ou recibo comercial. |
| **Lucro Líquido Evidenciado** | `R$ {{LUCRO_EVIDENCIADO}}` | Lucro real da empresa (Receita Bruta - Despesas operacionais). |

---

## ⚖️ Divisão das Parcelas para Declaração no IRPF (Pessoa Física)

Os valores abaixo devem ser inseridos diretamente no programa gerador do IRPF da Receita Federal do Brasil (RFB) nas respectivas fichas:

```markdown
┌────────────────────────────────────────────────────────────────────────┐
│  1. RENDIMENTO ISENTO (Lucro Isento Presumido)                          │
├────────────────────────────────────────────────────────────────────────┤
│  Valor: R$ {{LUCRO_ISENTO}}                                             │
│  Ficha no IRPF: "Rendimentos Isentos e Não Tributáveis"                │
│  Código do Tipo: Lucros e dividendos recebidos pelo titular (MEI)      │
│  Fonte Pagadora: Preencher com o CNPJ e Nome da sua própria empresa MEI│
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│  2. PARCELA TRIBUTÁVEL (Rendimento Tributável)                        │
├────────────────────────────────────────────────────────────────────────┤
│  Valor: R$ {{PARCELA_TRIBUTAVEL}}                                       │
│  Ficha no IRPF: "Rendimentos Tributáveis Recebidos de PJ pelo Titular" │
│  Fonte Pagadora: Preencher com o CNPJ e Nome da sua própria empresa MEI│
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚨 Monitoramento do Faturamento do MEI (Aviso para o Contador)

O limite oficial de faturamento do MEI é de **R$ 81.000,00** ao ano. A receita bruta informada consome **`{{PERCENTUAL_TETO}}%`** deste teto.

> [!NOTE]
> **Parecer de Alerta Contábil (Limite de 35 palavras por faixa):**
> 
> *   **Se Faturamento for até 25% do limite:**
>     *"Faturamento inicial seguro. A empresa MEI consome até 25% do teto oficial. Ideal para monitorar o ritmo de crescimento mensal sem alertas imediatos."*
> 
> *   **Se Faturamento for de 25% a 50% do limite:**
>     *"A empresa atingiu metade do faturamento máximo anual do MEI. Situação sob controle, recomendando-se controle regular do caixa para acompanhar a expansão saudável."*
> 
> *   **Se Faturamento for de 50% a 75% do limite:**
>     *"Atenção: faturamento superou 50% do limite anual do MEI. Excelente momento para o contador organizar despesas e começar o planejamento para o encerramento anual fiscal."*
> 
> *   **Se Faturamento for de 75% a 100% do limite:**
>     *"Alerta: faturamento muito próximo ao limite máximo de R$ 81 mil. Acompanhe a receita mês a mês para mitigar riscos de desenquadramento imediato não planejado."*
> 
> *   **Se Faturamento for acima de 100% do limite:**
>     *"Atenção Crítica: faturamento excedeu o limite oficial de R$ 81 mil. A migração para Microempresa (ME) é obrigatória. Inicie imediatamente os trâmites contábeis de desenquadramento."*

---

## 💡 Lista de Despesas Operacionais Sugeridas (Atividade Selecionada)

Para fins de escrituração ou controle do caixa do MEI, estas são as 10 despesas mais dedutíveis e comuns associadas à atividade assinalada (`Opção {{ATIVIDADE_SELECIONADA}}`):

`{{LISTA_DESPESAS}}`

---
*Fonte dos limites e regras: Receita Federal do Brasil e Sebrae Nacional.*
*Este relatório serve como roteiro auxiliar para preenchimento profissional do Imposto de Renda.*
