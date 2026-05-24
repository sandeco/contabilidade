class CalculadoraMEI:
    """Classe responsável por gerenciar e calcular o IRPF do Microempreendedor Individual (MEI).
    
    Adota princípios de Alta Coesão e Baixo Acoplamento, encapsulando
    a lógica tributária e as sugestões operacionais de despesas.
    """
    
    # Limite oficial anual de faturamento do MEI (Fonte: Gov.br)
    LIMITE_MEI_ANUAL = 81000.00

    def __init__(self):
        # Propriedades de estado inicializadas com valores padrão
        self.atividade_mei = 0
        self.receita_bruta = 0.0
        self.despesas = 0.0
        self.lucro_evidenciado = 0.0
        self.lucro_isento = 0.0
        self.parcela_tributavel = 0.0
        self.proporcao_limite = 0.0

    def _limpar_valor(self, valor_str):
        """Converte uma string monetária com vírgula ou ponto em float com segurança.
        
        Args:
            valor_str (str): Valor digitado pelo usuário.
            
        Returns:
            float: Valor numérico convertido.
        """
        try:
            # Remove espaços extras e ajusta os delimitadores de milhar/decimal
            valor_limpo = valor_str.strip().replace('.', '').replace(',', '.')
            return float(valor_limpo)
        except ValueError:
            # Caso a conversão falhe, retorna zero para evitar quebras no programa
            return 0.0

    def obter_sugestoes_despesas(self):
        """Retorna uma lista de até 10 despesas dedutíveis comuns conforme a atividade do MEI.
        
        Returns:
            list: Lista de strings contendo as despesas sugeridas.
        """
        sugestoes = {
            1: [
                "1. Compra de mercadorias para revenda",
                "2. Compra de matérias-primas e insumos para produção",
                "3. Embalagens para envio ou armazenamento",
                "4. Fretes sobre compras e entregas de mercadorias",
                "5. Aluguel de ponto comercial, galpão ou depósito",
                "6. Energia elétrica e água do estabelecimento comercial/industrial",
                "7. Telefone e internet do ambiente de trabalho",
                "8. Manutenção de máquinas, ferramentas e equipamentos de fabricação",
                "9. Combustível e manutenção de veículos de transporte de carga",
                "10. Tarifas de maquininhas de cartão sobre vendas"
            ],
            2: [
                "1. Combustível (gasolina, etanol, diesel, GNV)",
                "2. Manutenção preventiva e corretiva (freios, óleo, suspensão)",
                "3. Pneus, alinhamento e balanceamento do veículo",
                "4. Seguros veiculares (DPVAT e seguro de responsabilidade civil)",
                "5. Lavagem, higienização e conservação do veículo",
                "6. Aluguel de veículos ou parcelas de leasing operacional",
                "7. Tarifas de pedágio e estacionamento em trânsito",
                "8. Taxas de licenciamento anual e IPVA proporcional",
                "9. Internet móvel e suporte para celular/GPS",
                "10. Taxas de intermediação de aplicativos de transporte"
            ],
            3: [
                "1. Aluguel de escritório ou mensalidade de espaço Coworking",
                "2. Assinatura de softwares, sistemas de gestão e licenças de TI",
                "3. Serviços de telefonia e internet fixa/móvel profissional",
                "4. Energia elétrica, água e condomínio da sala comercial",
                "5. Materiais de escritório, papelaria e impressões",
                "6. Anúncios e marketing digital (Google Ads, Meta Ads)",
                "7. Cursos de capacitação, mentorias e treinamentos profissionais",
                "8. Hospedagem de site, domínio e e-mail profissional",
                "9. Limpeza e conservação do ambiente de trabalho",
                "10. Deslocamentos rápidos para reuniões com clientes (combustível ou apps)"
            ]
        }
        return sugestoes.get(self.atividade_mei, [])

    def obter_disclaimer_faturamento(self):
        """Gera um disclaimer contábil conciso de até 35 palavras com base no faturamento atingido.
        
        Returns:
            str: Aviso instrucional para o contador assessorar o MEI.
        """
        percentual = self.proporcao_limite * 100
        
        if percentual <= 25.0:
            return "Faturamento inicial seguro. A empresa MEI consome até 25% do teto oficial. Ideal para monitorar o ritmo de crescimento mensal sem alertas imediatos."
        elif percentual <= 50.0:
            return "A empresa atingiu metade do faturamento máximo anual do MEI. Situação sob controle, recomendando-se controle regular do caixa para acompanhar a expansão saudável."
        elif percentual <= 75.0:
            return "Atenção: faturamento superou 50% do limite anual do MEI. Excelente momento para o contador organizar despesas e começar o planejamento para o encerramento anual fiscal."
        elif percentual <= 100.0:
            return "Alerta: faturamento muito próximo ao limite máximo de R$ 81 mil. Acompanhe a receita mês a mês para mitigar riscos de desenquadramento imediato não planejado."
        else:
            return "Atenção Crítica: faturamento excedeu o limite oficial de R$ 81 mil. A migração para Microempresa (ME) é obrigatória. Inicie imediatamente os trâmites contábeis de desenquadramento."

    def coletar_dados(self):
        """Executa a interface de entrada de dados via console CLI, seguindo o novo fluxo lógico."""
        print("=== INICIALIZANDO CALCULADORA MEI PARA IRPF ===\n")
        
        # 1. Solicita a atividade do MEI primeiro
        while True:
            try:
                opcao = input("""Escolha o número correspondente à atividade principal do seu MEI:
1 - Comércio, Indústria e Transporte de Carga (8% de isenção)
2 - Transporte de Passageiros (16% de isenção)
3 - Serviços em geral (32% de isenção)
Sua opção: """)
                self.atividade_mei = int(opcao)
                if self.atividade_mei in [1, 2, 3]:
                    break
                print("Opção inválida. Digite 1, 2 ou 3.\n")
            except ValueError:
                print("Entrada inválida. Digite um número inteiro (1, 2 ou 3).\n")

        # 2. Exibe as despesas recomendadas de acordo com a atividade selecionada
        print(f"\n--- DESPESAS DEDUTÍVEIS MAIS COMUNS PARA SUA ATIVIDADE MEI ---")
        print("Somente declare despesas comerciais reais comprovadas com nota fiscal ou recibo:")
        for despesa in self.obter_sugestoes_despesas():
            print(f" -> {despesa}")
        print("-----------------------------------------------------------------\n")

        # 3. Solicita os valores financeiros de Receita Bruta e Despesas
        self.receita_bruta = self._limpar_valor(input("Informe o total da sua Receita Bruta Anual (Exemplo: 50250,50): "))
        self.despesas = self._limpar_valor(input("Informe o total de Despesas Comprovadas da empresa (Exemplo: 12500,00): "))

    def calcular(self):
        """Realiza todos os cálculos tributários com base nas regras da Receita Federal e do Sebrae."""
        # Lucro líquido evidenciado da empresa (Receita Bruta - Despesas)
        self.lucro_evidenciado = self.receita_bruta - self.despesas
        
        # Mapeamento do percentual de isenção fiscal por atividade do MEI
        percentuais_isencao = {1: 0.08, 2: 0.16, 3: 0.32}
        percentual = percentuais_isencao.get(self.atividade_mei, 0.0)
        
        # Cálculo da parcela de lucro isento de imposto
        self.lucro_isento = self.receita_bruta * percentual
        
        # Parcela tributável declarável no IRPF (Lucro Líquido - Parcela Isenta)
        # Observação: Se der negativo, a parcela tributável é considerada R$ 0,00
        self.parcela_tributavel = max(0.0, self.lucro_evidenciado - self.lucro_isento)
        
        # Calcula a proporção do faturamento com relação ao teto do MEI
        self.proporcao_limite = self.receita_bruta / self.LIMITE_MEI_ANUAL

    def exibir_relatorio(self):
        """Imprime no terminal o relatório final para o contador de forma clara e estruturada."""
        percentual_teto = self.proporcao_limite * 100
        
        print("\n==================================================")
        print("         RELATÓRIO DE IRPF PARA MEI             ")
        print("==================================================")
        print(f"Atividade MEI Selecionada: Opção {self.atividade_mei}")
        print(f"Receita Bruta Total:       R$ {self.receita_bruta:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        print(f"Despesas Comprovadas:      R$ {self.despesas:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        print(f"Lucro Líquido Evidenciado: R$ {self.lucro_evidenciado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        print("--------------------------------------------------")
        print(f"RENDIMENTO ISENTO:         R$ {self.lucro_isento:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        print("👉 Declarar na Ficha: 'Rendimentos Isentos e Não Tributáveis'")
        print("👉 Tipo de Rendimento: Selecionar a opção correspondente a lucros e dividendos recebidos pelo titular")
        print("--------------------------------------------------")
        print(f"PARCELA TRIBUTÁVEL:        R$ {self.parcela_tributavel:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        print("👉 Declarar na Ficha: 'Rendimentos Tributáveis Recebidos de PJ pelo Titular'")
        print("👉 Preencher o CNPJ do próprio MEI como fonte pagadora")
        print("--------------------------------------------------")
        print(f"Consumo do Limite MEI:     {percentual_teto:.2f}% (Teto de R$ 81.000,00)")
        print("\n--- AVISO PARA O CONTADOR (DISCLAIMER) ---")
        print(self.obter_disclaimer_faturamento())
        print("==================================================")
        print("Fonte de limites: https://www.gov.br/empresas-e-negocios")
        print("Guia de apoio: https://sebrae.com.br")
        print("==================================================")


# Execução automática caso o script seja rodado diretamente
if __name__ == "__main__":
    calculadora = CalculadoraMEI()
    calculadora.coletar_dados()
    calculadora.calcular()
    calculadora.exibir_relatorio()