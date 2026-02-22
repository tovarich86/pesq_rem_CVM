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
def main():
    st.title("Análise Interativa de Remuneração de Administradores 2022-2025 FRE")
    
    st.markdown("""
    Esta ferramenta foi desenvolvida para permitir a análise interativa dos dados de remuneração de administradores de companhias abertas brasileiras, utilizando como base o arquivo de dados compilado do Formulário de Referência (FRE) da CVM. 
    
    👈 **Utilize o menu lateral para navegar entre as diferentes análises disponíveis.**
    """)
    
    with st.expander("Clique para ver a Metodologia, Limitações e Fórmulas"):
        st.subheader("Metodologia")
        st.markdown("""
        **1. Fonte e Coleta de Dados:**
        * **Fonte Primária:** Formulário de Referência (FRE).
        * **Estrutura dos Dados:** A análise respeita a estrutura de blocos de dados descrita:
            * Remuneração Individual (Máxima, Média e Mínima) Fonte item 8.15 FRE.
            * Componentes da Remuneração Total (Fixa e Variável). Fonte item 8.2 FRE.
            * Métricas de Bônus e PLR (Alvo, Pago, etc.) Fonte Item 8.3 FRE.

        **2. Fórmulas e Cálculos:**
        * **Média por Membro:** Quando selecionada, o cálculo é: *Média = Valor Total do Componente / Número de Membros Remunerados do Bloco*.
        * **Quartis:** Calculados sobre a série de dados de remuneração para cada setor.
        """)
        st.subheader("Limitações")
        st.markdown("""
        **Aviso: Protótipo e Limitações dos Dados**
        Este aplicativo é um protótipo. Os dados aqui exibidos não devem ser usados para fins profissionais ou tomadas de decisão críticas sem validação.
        * **Qualidade do FRE:** A precisão depende da correção do FRE preenchido pela empresa.
        * **Remuneração via Controladores:** Não inclui valores pagos por controladores ou outras empresas do grupo.
        * **Dados de 2025:** Representam a proposta aprovada, não o valor efetivamente pago.
        """)

    # Carrega os dados e salva na sessão para as outras páginas usarem
    github_url = "https://raw.githubusercontent.com/tovarich86/pesq_rem_CVM/main/dados_cvm_mesclados.csv"
    with st.spinner("Carregando base de dados da CVM..."):
        df_original = load_data(github_url)
        
    if not df_original.empty:
        # Guardando o DataFrame no estado da sessão (Session State)
        st.session_state['df_completo'] = df_original
        st.success("Dados carregados com sucesso! Navegue pelo menu lateral.")
    else:
        st.error("Falha ao carregar os dados.")

if __name__ == "__main__":
    main()
