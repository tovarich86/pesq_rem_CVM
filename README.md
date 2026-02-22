# Painel Analítico de Remuneração de Administradores (CVM/FRE)

## Visão Geral
Este repositório contém uma aplicação analítica desenvolvida em **Python** e **Streamlit**, projetada para a extração, consolidação e visualização de dados de remuneração de executivos de companhias abertas no Brasil. 

A ferramenta automatiza o acesso à base de dados abertos da Comissão de Valores Mobiliários (CVM), especificamente o Formulário de Referência (FRE), transformando dados brutos em inteligência de mercado estruturada para áreas de *Compensation*, *People Analytics* e Governança Corporativa.

🔗 **[Acesso ao Painel Interativo] (inserir link do deploy)**

---

## Funcionalidades Principais

A aplicação é modularizada para atender a diferentes escopos de análise e planejamento:

* **Decomposição da Remuneração Total:** Análise detalhada da estrutura de pacotes de remuneração (Salário, Benefícios, Bônus, Ações e Pós-Emprego), permitindo a visualização da evolução histórica por órgão de administração.
* **Avaliação de Performance (Bônus e PLR):** Rastreamento da remuneração variável, com métricas de atingimento (Valor Alvo vs. Valor Efetivamente Pago) e potencial máximo aprovado.
* **Análise de Competitividade e Estatística:** Posicionamento de mercado através do cálculo automatizado de quartis, medianas e desvios-padrão segmentados por setor de atividade econômica.
* **Modelagem e Benchmarking (Projeções):** Módulo de simulação que permite a inserção de dados projetados (ex: orçamento do próximo ciclo) e a comparação direta, via gráficos empilhados, contra a média de um *peer group* (empresas pares) selecionado de forma dinâmica.

## Arquitetura e Engenharia de Dados

O projeto é sustentado por um pipeline de dados (ETL) automatizado:
1. **Extração:** Conexão com o Portal de Dados Abertos da CVM (`update_data.py`).
2. **Transformação:** Limpeza de dados, tratamento de nomenclaturas e deduplicação de registros de órgãos administrativos (garantindo a integridade relacional entre as tabelas do FRE).
3. **Carga:** Consolidação em um arquivo estruturado (`dados_cvm_mesclados.csv`) otimizado para a camada de visualização em memória (Streamlit/Pandas).

## Instalação e Execução Local

Para executar o painel em um ambiente local, siga as diretrizes abaixo:

1. Clone o repositório:
   ```bash
   git clone [https://github.com/seu-usuario/pesq_rem_CVM.git](https://github.com/seu-usuario/pesq_rem_CVM.git)
   cd pesq_rem_CVM
Configure o ambiente virtual e instale as dependências listadas:

Bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
Inicialize a aplicação web:

Bash
streamlit run Home.py
Conformidade e Aviso Legal
Esta aplicação utiliza exclusivamente dados públicos disponibilizados pelas próprias companhias abertas via CVM.

Integridade dos Dados: Eventuais inconsistências ou valores atípicos apresentados nos gráficos refletem o preenchimento original do Formulário de Referência (FRE) pelas respectivas empresas emissoras.

Uso da Ferramenta: Este software é fornecido "no estado em que se encontra" (as is). Os cálculos e projeções aqui realizados não constituem aconselhamento financeiro, legal ou recomendação oficial de estruturação de remuneração. Recomenda-se a validação das informações cruzando-as com os documentos oficiais arquivados na CVM antes de qualquer tomada de decisão corporativa.

Privacidade: A ferramenta opera analiticamente no cliente (navegador) e não armazena ou coleta dados sensíveis inseridos durante as simulações de projeção.
