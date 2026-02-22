import streamlit as st
import pandas as pd
import io
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

# --- Configuração da Página ---
# Esta configuração deve ser a primeira linha executada no Streamlit
st.set_page_config(layout="wide", page_title="Análise CVM", page_icon="📊")

# --- Funções Compartilhadas e Carregamento ---
@st.cache_data
def load_data(url: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(url, sep=',', encoding='utf-8-sig', engine='python')
        df.columns = df.columns.str.strip()

        colunas_numericas = [col for col in df.columns if 'NUM' in col or 'VALOR' in col or 'TOTAL' in col or 'REM' in col or 'PERC' in col or 'BONUS' in col or 'PLR' in col or 'DESVIO' in col]
        for col in colunas_numericas:
             df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        categorical_cols = ['NOME_COMPANHIA', 'ORGAO_ADMINISTRACAO', 'SETOR_ATIVIDADE', 'CONTROLE_ACIONARIO', 'UF_SEDE']
        for col in categorical_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.upper().fillna(f'{col.replace("_", " ").title()} Não Informado')

        if 'ANO_REFER' in df.columns:
            df['ANO_REFER'] = pd.to_numeric(df['ANO_REFER'], errors='coerce').dropna().astype(int)
        
        return df
    except Exception as e:
        st.error(f"Erro crítico ao carregar ou processar os dados: {e}")
        return pd.DataFrame()

# --- Página Inicial (Home) ---
# --- Página Inicial (Home) ---
def main():
    st.title("Análise Interativa de Remuneração de Administradores (FRE/CVM)")
    
    st.markdown("""
    Bem-vindo! Esta ferramenta foi desenvolvida para democratizar e facilitar a análise visual dos dados de remuneração de administradores de companhias abertas brasileiras. Toda a base de dados é compilada automaticamente a partir dos **Formulários de Referência (FRE)** públicos disponibilizados pela CVM.
    
     **Utilize o menu lateral para navegar pelas seguintes funcionalidades:**
    
    * ** 1. Componentes da Remuneração:** Composição detalhada da remuneração total (Salário, Benefícios, Bônus, Ações, Pós-Emprego, etc.) por empresa e sua evolução anual.
    * ** 2. Bônus e PLR:** Análise aprofundada da remuneração variável, medindo a performance entre as metas (alvo) e os valores efetivamente pagos.
    * ** 3. Remuneração Individual:** Histórico e ranking comparativo dos valores Máximos, Médios e Mínimos pagos aos membros de cada órgão administrativo.
    * ** 4. Análise Estatística:** Estatísticas de mercado (Quartis, Medianas, Desvio Padrão e Extremos) segmentadas por setor de atuação.
    * ** 5. Projeção e Benchmarking:** Um ambiente interativo de simulação onde você pode editar os dados da sua empresa, projetar o próximo ciclo e comparar diretamente com a média de um grupo de pares (concorrentes).

    ---
    ### ⚠️ Avisos Legais e Privacidade
    
    * **Isenção de Responsabilidade:** O autor desta ferramenta **não se responsabiliza** por quaisquer tomadas de decisão, planejamentos financeiros ou usos profissionais baseados nestes painéis. 
    * **Verifique os Dados:** A precisão dos gráficos depende unicamente da qualidade do FRE preenchido pela própria empresa. **É comum existirem erros de digitação, inconsistências ou omissões nos arquivos oficiais da CVM.** Utilize este painel como um direcional e valide sempre a informação na fonte oficial antes de qualquer uso crítico.
    * **Privacidade Total:** Esta aplicação é executada inteiramente em tempo real e **não realiza nenhuma coleta de dados**. Quaisquer filtros selecionados ou números digitados na aba de Projeção existem apenas temporariamente no seu navegador e são apagados ao fechar a página.
    * **Código Aberto:** O código-fonte deste projeto e os robôs de extração de dados são 100% públicos e transparentes. Você pode auditar o código ou contribuir através do nosso repositório no GitHub.
    """)
    
    with st.expander("📚 Clique para ver a Metodologia, Fórmulas e Limitações Técnicas"):
        st.subheader("Metodologia")
        st.markdown("""
        **1. Fonte e Coleta de Dados:**
        * **Fonte Primária:** Formulário de Referência (FRE) - Portal de Dados Abertos CVM.
        * **Estrutura de Extração:** * Remuneração Individual (Máxima, Média e Mínima) extraída do item 8.15 do FRE.
            * Componentes da Remuneração Total (Fixa e Variável) extraídos do item 8.2 do FRE.
            * Métricas de Bônus e PLR (Alvo, Pago, Mínimo, Máximo) extraídas do Item 8.3 do FRE.

        **2. Fórmulas e Cálculos:**
        * **Média por Membro:** Calculada de forma linear: `Valor Total do Componente / Número de Membros Remunerados do Bloco`.
        * **Quartis e Estatísticas:** Calculados utilizando a biblioteca Pandas sobre a série histórica filtrada de cada setor.
        """)
        
        st.subheader("Limitações dos Dados")
        st.markdown("""
        * **Remuneração via Controladores:** Os dados refletem apenas o que é pago diretamente pela companhia emissora. Não estão incluídos valores pagos por empresas controladoras ou outras entidades do mesmo grupo econômico.
        * **Projeções do Ano Corrente (ex: 2025):** Os valores do ano vigente representam a *proposta aprovada* em Assembleia, e não necessariamente o valor que será *efetivamente pago* ao final do exercício fiscal.
        """)

    st.markdown("---")

    # Carrega os dados e salva na sessão para as outras páginas usarem
    github_url = "https://raw.githubusercontent.com/tovarich86/pesq_rem_CVM/main/dados_cvm_mesclados.csv"
    with st.spinner("Conectando ao repositório e carregando a base de dados da CVM..."):
        df_original = load_data(github_url)
        
    if not df_original.empty:
        st.session_state['df_completo'] = df_original
        st.success("✅ Dados carregados com sucesso! Utilize o menu lateral esquerdo para começar sua análise.")
    else:
        st.error("Falha ao carregar os dados do GitHub. Tente atualizar a página.")

if __name__ == "__main__":
    main()
