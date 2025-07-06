import streamlit as st
import pandas as pd
import plotly.express as px
import warnings

# Ignorar avisos de depreciação futuros do pandas que podem poluir a saída
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Análise de Remuneração CVM")


# --- Carregamento e Preparação dos Dados ---
@st.cache_data
def load_data(url: str) -> pd.DataFrame:
    """
    Carrega os dados de uma URL, limpa, e renomeia colunas de forma robusta
    para facilitar as análises, espelhando a estrutura de blocos da CVM.
    """
    try:
        df = pd.read_csv(url, sep=',', encoding='latin-1', engine='python')
        df.columns = df.columns.str.strip()

        # Mapeamento completo e flexível das colunas para nomes padronizados.
        rename_map = {
            # Identificação e Filtros Novos
            'NOME_COMPANHIA': ['DENOM_CIA'],
            'ANO_REFER': ['Ano do Exercício Social'],
            'ORGAO_ADMINISTRACAO': ['Orgao_Administracao'],
            'SETOR_ATIVIDADE': ['SETOR_DE_ATIVDADE', 'Setor de ativdade', 'Setor de Atividade', 'SETOR', 'ATIVIDADE'], # Mapeamento final
            'CONTROLE_ACIONARIO': ['CONTROLE_ACIONARIO'],
            'UF_SEDE': ['UF_SEDE'],
            
            # Bloco 1: Remuneração Baseada em Ações
            'NUM_MEMBROS_ACOES': ['Quantidade_Membros_Remunerados_Com_Acoes_Opcoes'],
            'VALOR_OPCOES_EXERCIDAS': ['Valor_Total_Opcoes_Acoes_Exercidas_Reconhecidas_Resultado_Exercicio'],
            'VALOR_ACOES_RESTRITAS': ['Valor_Total_Acoes_Restritas_Entregues_Reconhecidas_Resultado_Exercicio'],
            'VALOR_OUTROS_PLANOS_ACOES': ['Valor_Total_Outros_Planos_Baseados_Acoes_Reconhecidos_Resultado_Exercicio'],
            'TOTAL_REM_ACOES_BLOCO1': ['Valor_Total_Remuneracao_Baseada_Acoes_Reconhecida_Resultado_Exercicio'],

            # Bloco 2: Remuneração Individual (Máx/Média/Mín)
            'NUM_MEMBROS_INDIVIDUAL': ['Quantidade_Membros_Orgao_Remuneracao_Individual'],
            'REM_MAXIMA_INDIVIDUAL': ['Valor_Maior_Remuneracao_Individual_Reconhecida_Exercicio'],
            'REM_MEDIA_INDIVIDUAL': ['Valor_Medio_Remuneracao_Individual_Reconhecida_Exercicio'],
            'REM_MINIMA_INDIVIDUAL': ['Valor_Menor_Remuneracao_Individual_Reconhecida_Exercicio'],
            'DESVIO_PADRAO_INDIVIDUAL': ['Desvio_Padrao_Remuneracao_Individual_Reconhecida_Exercicio'],

            # Bloco 3: Componentes da Remuneração Total
            'NUM_MEMBROS_TOTAL': ['Quantidade_Total_Membros_Remunerados_Orgao'],
            'REM_FIXA_SALARIO': ['Salario_Fixo_Anual_Total'],
            'REM_FIXA_BENEFICIOS': ['Beneficios_Anual_Total'],
            'REM_FIXA_POS_EMPREGO': ['Beneficios_Pos_Emprego_Anual_Total'],
            'REM_FIXA_RESCISAO': ['Beneficios_Cessacao_Cargo_Anual_Total'],
            'REM_FIXA_OUTROS': ['Outros_Valores_Remuneracao_Fixa_Anual_Total'],
            'TOTAL_REM_FIXA': ['Valor_Total_Remuneracao_Fixa_Anual_Orgao'],
            'REM_VAR_BONUS_PLR': ['Bonus_Participacao_Resultados_Anual_Total'],
            'REM_VAR_ACOES': ['Remuneracao_Baseada_Acoes_Anual_Total'],
            'REM_VAR_OUTROS': ['Outros_Valores_Remuneracao_Variavel_Anual_Total'],
            'TOTAL_REM_VARIAVEL': ['Remuneracao_Variavel_Anual_Total'],
            'TOTAL_REMUNERACAO_ORGAO': ['Valor_Total_Remuneracao_Anual_Orgao'],

            # Bloco 4: Métricas de Bônus e PLR
            'NUM_MEMBROS_BONUS_PLR': ['QTD_MEMBROS_REMUNERADOS_VARIAVEL'],
            'BONUS_MIN': ['BONUS_VALOR_MINIMO'],
            'BONUS_MAX': ['BONUS_VALOR_MAXIMO'],
            'BONUS_ALVO': ['BONUS_VALOR_METAS_ATINGIDAS'],
            'BONUS_PAGO': ['BONUS_VALOR_EFETIVO'],
            'PLR_MIN': ['PARTICIPACAO_VALOR_MINIMO'],
            'PLR_MAX': ['PARTICIPACAO_VALOR_MAXIMO'],
            'PLR_ALVO': ['PARTICIPACAO_VALOR_METAS_ATINGIDAS'],
            'PLR_PAGO': ['PARTICIPACAO_VALOR_EFETIVO'],
        }

        actual_rename_dict = {}
        for new_name, old_names in rename_map.items():
            for old_name in old_names:
                if old_name in df.columns:
                    actual_rename_dict[old_name] = new_name
                    break
        df.rename(columns=actual_rename_dict, inplace=True)
        
        # --- Verificação por Posição (Plano B) ---
        if 'SETOR_ATIVIDADE' not in df.columns and len(df.columns) >= 42:
            target_col_name = df.columns[41] # Posição 42 é índice 41
            df.rename(columns={target_col_name: 'SETOR_ATIVIDADE'}, inplace=True)
            st.sidebar.success(f"Coluna de atividade ('{target_col_name}') encontrada pela posição.")

        # Converte todas as colunas numéricas de uma vez
        all_numeric_cols = list(rename_map.keys())
        for col in all_numeric_cols:
            if 'NUM' in col or 'VALOR' in col or 'TOTAL' in col or 'REM' in col or 'PERC' in col or 'BONUS' in col or 'PLR' in col or 'DESVIO' in col:
                 if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                 else:
                    df[col] = 0

        # Limpeza e Padronização de Dados Categóricos
        categorical_cols = ['NOME_COMPANHIA', 'ORGAO_ADMINISTRACAO', 'SETOR_ATIVIDADE', 'CONTROLE_ACIONARIO', 'UF_SEDE']
        for col in categorical_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.upper().fillna(f'{col.replace("_", " ").title()} Não Informado')
            else:
                st.warning(f"Atenção: A coluna para '{col}' não foi encontrada. Um valor padrão será usado.")
                df[col] = f"{col.replace('_', ' ').title()} Não Informado"

        if 'ANO_REFER' in df.columns:
            df['ANO_REFER'] = pd.to_numeric(df['ANO_REFER'], errors='coerce').dropna().astype(int)
        
        return df
    except Exception as e:
        st.error(f"Erro crítico ao carregar ou processar os dados: {e}")
        return pd.DataFrame()

# --- PÁGINAS DA APLICAÇÃO ---

def page_home():
    st.title("Análise Interativa de Remuneração de Administradores")
    st.markdown("""
    Bem-vindo(a) à ferramenta de análise de remuneração de companhias abertas brasileiras. Esta aplicação foi estruturada para refletir os blocos de dados do Formulário de Referência da CVM.

    **Como usar:**
    1.  **Use os filtros na barra lateral** para refinar sua análise por UF, Setor ou Controle Acionário. Esses filtros são globais.
    2.  **Navegue pelas seções temáticas** no menu principal para explorar diferentes aspectos da remuneração.
    
    **Seções de Análise:**
    - **Remuneração Individual (Máx/Média/Mín):** Analise a dispersão salarial dentro de um órgão (maior, menor e média remuneração individual).
    - **Componentes da Remuneração Total:** Veja a composição da remuneração total do órgão (salário, bônus, benefícios) e sua evolução.
    - **Remuneração Baseada em Ações:** Foque nos pagamentos via opções e ações.
    - **Bônus e PLR:** Investigue os bônus, participação nos lucros e métricas de desempenho.
    """)

def page_remuneracao_individual(df: pd.DataFrame):
    st.header("Análise da Remuneração Individual (Máxima, Média e Mínima)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        ano = st.selectbox("1. Selecione o Ano", sorted(df['ANO_REFER'].unique(), reverse=True), key='ano_ind')
    df_ano = df[df['ANO_REFER'] == ano]
    with col2:
        orgaos_disponiveis = sorted(df_ano['ORGAO_ADMINISTRACAO'].unique())
        orgao = st.selectbox("2. Selecione o Órgão", orgaos_disponiveis, key='orgao_ind')
    df_orgao = df_ano[df_ano['ORGAO_ADMINISTRACAO'] == orgao]
    with col3:
        empresas_disponiveis = sorted(df_orgao['NOME_COMPANHIA'].unique())
        if not empresas_disponiveis:
            st.warning("Nenhuma empresa encontrada para os filtros selecionados.")
            st.stop()
        empresa = st.selectbox("3. Selecione a Empresa", empresas_disponiveis, key='empresa_ind')

    df_filtered = df_orgao[df_orgao['NOME_COMPANHIA'] == empresa]
    if not df_filtered.empty:
        rem_max = df_filtered['REM_MAXIMA_INDIVIDUAL'].iloc[0]
        rem_med = df_filtered['REM_MEDIA_INDIVIDUAL'].iloc[0]
        rem_min = df_filtered['REM_MINIMA_INDIVIDUAL'].iloc[0]
        if rem_max > 0:
            data_plot = pd.DataFrame({'Métrica': ['Máxima', 'Média', 'Mínima'], 'Valor': [rem_max, rem_med, rem_min]})
            fig = px.bar(data_plot, x='Métrica', y='Valor', text_auto='.2s', title=f"Dispersão da Remuneração Individual em {ano}", labels={'Valor': 'Valor (R$)'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Não há dados de remuneração individual para a seleção atual.")
    else:
        st.warning("Nenhum dado encontrado para a combinação de filtros.")

def page_componentes_remuneracao(df: pd.DataFrame):
    st.header("Análise dos Componentes da Remuneração Total")
    col1, col2 = st.columns(2)
    with col1:
        orgao = st.selectbox("1. Selecione o Órgão", sorted(df['ORGAO_ADMINISTRACAO'].unique()), key='orgao_comp')
    df_orgao = df[df['ORGAO_ADMINISTRACAO'] == orgao]
    with col2:
        empresas_disponiveis = sorted(df_orgao['NOME_COMPANHIA'].unique())
        if not empresas_disponiveis:
            st.warning("Nenhuma empresa encontrada para o órgão selecionado.")
            st.stop()
        empresa = st.selectbox("2. Selecione a Empresa", empresas_disponiveis, key='empresa_comp')

    df_filtered = df_orgao[df_orgao['NOME_COMPANHIA'] == empresa]
    component_cols = {
        'Salário': 'REM_FIXA_SALARIO', 'Benefícios': 'REM_FIXA_BENEFICIOS', 'Pós-Emprego': 'REM_FIXA_POS_EMPREGO',
        'Bônus/PLR': 'REM_VAR_BONUS_PLR', 'Ações (Bloco 2)': 'REM_VAR_ACOES', 'Outros': 'REM_FIXA_OUTROS'
    }
    yearly_data = df_filtered.groupby('ANO_REFER')[[col for col in component_cols.values() if col in df_filtered.columns]].sum().reset_index()
    df_plot = yearly_data.melt(id_vars=['ANO_REFER'], var_name='Componente', value_name='Valor')
    df_plot['Componente'] = df_plot['Componente'].map({v: k for k, v in component_cols.items()})
    if not df_plot.empty and df_plot['Valor'].sum() > 0:
        fig = px.bar(df_plot, x='ANO_REFER', y='Valor', color='Componente', title=f"Evolução dos Componentes da Remuneração para {empresa}", labels={'ANO_REFER': 'Ano', 'Valor': 'Valor Anual (R$)'})
        fig.update_layout(xaxis_type='category', barmode='stack')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Não há dados de remuneração para exibir.")

def page_remuneracao_acoes(df: pd.DataFrame):
    st.header("Análise de Remuneração Baseada em Ações")
    ano = st.selectbox("Selecione o Ano", sorted(df['ANO_REFER'].unique(), reverse=True), key='ano_acoes')
    df_ano = df[df['ANO_REFER'] == ano]
    st.subheader(f"Ranking de Empresas por Remuneração em Ações ({ano})")
    rem_acoes_cia = df_ano.groupby('NOME_COMPANHIA')['TOTAL_REM_ACOES_BLOCO1'].sum().nlargest(10).reset_index()
    if not rem_acoes_cia[rem_acoes_cia['TOTAL_REM_ACOES_BLOCO1'] > 0].empty:
        fig = px.bar(rem_acoes_cia, x='NOME_COMPANHIA', y='TOTAL_REM_ACOES_BLOCO1', text_auto='.2s', title="Top 10 Empresas por Valor Total")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Não há dados de remuneração baseada em ações para o ano.")

def page_bonus_plr(df: pd.DataFrame):
    st.header("Análise Detalhada de Bônus e Participação nos Resultados")
    col1, col2, col3 = st.columns(3)
    with col1:
        ano = st.selectbox("1. Selecione o Ano", sorted(df['ANO_REFER'].unique(), reverse=True), key='ano_bonus_detail')
    df_ano = df[df['ANO_REFER'] == ano]
    with col2:
        orgao = st.selectbox("2. Selecione o Órgão", sorted(df_ano['ORGAO_ADMINISTRACAO'].unique()), key='orgao_bonus_detail')
    df_orgao = df_ano[df_ano['ORGAO_ADMINISTRACAO'] == orgao]
    with col3:
        empresas_disponiveis = sorted(df_orgao['NOME_COMPANHIA'].unique())
        if not empresas_disponiveis:
            st.warning("Nenhuma empresa encontrada para a seleção.")
            st.stop()
        empresa = st.selectbox("3. Selecione a Empresa", empresas_disponiveis, key='empresa_bonus_detail')

    df_selection = df_orgao[df_orgao['NOME_COMPANHIA'] == empresa]
    if not df_selection.empty:
        bonus_alvo = df_selection['BONUS_ALVO'].iloc[0]
        bonus_pago = df_selection['BONUS_PAGO'].iloc[0]
        plr_alvo = df_selection['PLR_ALVO'].iloc[0]
        plr_pago = df_selection['PLR_PAGO'].iloc[0]
        data_to_plot = {
            'Tipo': ['Bônus', 'Bônus', 'Participação nos Resultados', 'Participação nos Resultados'],
            'Métrica': ['Alvo (Metas)', 'Efetivamente Pago', 'Alvo (Metas)', 'Efetivamente Pago'],
            'Valor': [bonus_alvo, bonus_pago, plr_alvo, plr_pago]
        }
        df_plot = pd.DataFrame(data_to_plot)
        df_plot = df_plot[df_plot['Valor'] > 0] 
        if not df_plot.empty:
            fig = px.bar(
                df_plot, x='Tipo', y='Valor', color='Métrica',
                barmode='group', text_auto='.2s',
                title=f"Comparativo Bônus e PLR: Alvo vs. Pago em {ano}",
                labels={'Valor': 'Valor (R$)', 'Tipo': 'Tipo de Remuneração Variável'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Não há dados de Bônus ou PLR (Alvo e Pago) para a seleção atual.")
    else:
        st.warning("Nenhum dado encontrado para a combinação de filtros.")

# --- Função Principal da Aplicação ---
def main():
    github_url = "https://raw.githubusercontent.com/tovarich86/pesq_rem_CVM/main/dados_cvm_mesclados.csv.csv"
    df_original = load_data(github_url)
    if df_original.empty:
        st.error("Falha no carregamento dos dados. O aplicativo não pode continuar.")
        st.stop()

    st.sidebar.title("Painel de Análise")
    st.sidebar.image("https://www.ibgc.org.br/themes/ibgc/dist/images/logo-default.svg", width=150)
    st.sidebar.header("Filtros Globais")
    
    ufs_disponiveis = ["TODAS"] + sorted(df_original['UF_SEDE'].unique())
    uf = st.sidebar.selectbox("UF da Sede", ufs_disponiveis)
    setores_disponiveis = ["TODOS"] + sorted(df_original['SETOR_ATIVIDADE'].unique())
    setor = st.sidebar.selectbox("Setor de Atividade", setores_disponiveis)
    controles_disponiveis = ["TODOS"] + sorted(df_original['CONTROLE_ACIONARIO'].unique())
    controle = st.sidebar.selectbox("Controle Acionário", controles_disponiveis)

    df_filtrado = df_original.copy()
    if uf != "TODAS":
        df_filtrado = df_filtrado[df_filtrado['UF_SEDE'] == uf]
    if setor != "TODOS":
        df_filtrado = df_filtrado[df_filtrado['SETOR_ATIVIDADE'] == setor]
    if controle != "TODOS":
        df_filtrado = df_filtrado[df_filtrado['CONTROLE_ACIONARIO'] == controle]

    pagina_selecionada = st.sidebar.radio(
        "Selecione a Análise:",
        ["Página Inicial", "Remuneração Individual (Máx/Média/Mín)", "Componentes da Remuneração Total", "Remuneração Baseada em Ações", "Bônus e PLR"]
    )
    
    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado para os filtros globais selecionados. Por favor, ajuste os filtros na barra lateral.")
        st.stop()

    if pagina_selecionada == "Página Inicial":
        page_home()
    elif pagina_selecionada == "Remuneração Individual (Máx/Média/Mín)":
        page_remuneracao_individual(df_filtrado)
    elif pagina_selecionada == "Componentes da Remuneração Total":
        page_componentes_remuneracao(df_filtrado)
    elif pagina_selecionada == "Remuneração Baseada em Ações":
        page_remuneracao_acoes(df_filtrado)
    elif pagina_selecionada == "Bônus e PLR":
        page_bonus_plr(df_filtrado)

if __name__ == "__main__":
    main()
