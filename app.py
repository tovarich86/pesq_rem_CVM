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
    Carrega os dados de uma URL, limpa, renomeia colunas e calcula novos campos
    para facilitar as análises.
    """
    try:
        df = pd.read_csv(url, sep=',', encoding='latin-1', engine='python')
        df.columns = df.columns.str.strip()

        # Renomeação de colunas para nomes padronizados
        df.rename(columns={
            'DENOM_CIA': 'NOME_COMPANHIA',
            'Ano do Exercício Social': 'ANO_REFER',
            'Orgao_Administracao': 'ORGAO_ADMINISTRACAO',
            'Setor de ativdade': 'SETOR_ATIVIDADE',
            # Bloco 2: Remuneração Total
            'Valor_Total_Remuneracao_Anual_Orgao': 'TOTAL_REMUNERACAO_ORGAO',
            'Quantidade_Total_Membros_Remunerados_Orgao': 'NUM_MEMBROS_REMUNERADOS',
            'Salario_Fixo_Anual_Total': 'REM_FIXA',
            'Remuneracao_Variavel_Anual_Total': 'REM_VARIAVEL',
            # Bloco 1: Ações
            'Valor_Total_Remuneracao_Baseada_Acoes_Reconhecida_Resultado_Exercicio': 'REM_ACOES',
            # Bloco 3: Bônus
            'Valor_Total_Bonus_Participacao_Resultados_Aprovado': 'BONUS',
        }, inplace=True)

        # Tratamento de Tipos e Nulos
        numeric_cols = [
            'TOTAL_REMUNERACAO_ORGAO', 'BONUS', 'NUM_MEMBROS_REMUNERADOS',
            'REM_FIXA', 'REM_VARIAVEL', 'REM_ACOES'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        if 'ANO_REFER' in df.columns:
            df['ANO_REFER'] = pd.to_numeric(df['ANO_REFER'], errors='coerce').dropna().astype(int)
        
        if 'SETOR_ATIVIDADE' in df.columns:
            df['SETOR_ATIVIDADE'] = df['SETOR_ATIVIDADE'].str.strip()

        return df
    except Exception as e:
        st.error(f"Erro ao carregar ou processar os dados: {e}")
        # Adiciona um debug para mostrar as colunas lidas se houver erro
        try:
            temp_df = pd.read_csv(url, sep=',', encoding='latin-1', engine='python', nrows=5)
            st.info(f"Amostra das colunas lidas do arquivo: {list(temp_df.columns)}")
        except:
            pass
        return pd.DataFrame()


# --- PÁGINAS DA APLICAÇÃO ---

def page_home():
    """Página inicial da aplicação."""
    st.title("Análise Interativa de Remuneração de Administradores")
    st.markdown("""
    Bem-vindo(a) à ferramenta de análise de remuneração de companhias abertas brasileiras, baseada nos dados da CVM.
    Esta versão foi reestruturada para alinhar as análises com os blocos de dados do formulário de referência.

    **Como usar:**
    - **Navegue pelas seções temáticas** no menu à esquerda para explorar diferentes aspectos da remuneração.
    - **Use os filtros** em cada página para customizar a visualização por ano, órgão ou setor.
    
    **Seções de Análise:**
    - **Análise da Remuneração Consolidada:** Explore os valores totais, rankings e a estrutura geral da remuneração (salário, variável, etc.).
    - **Análise de Remuneração Baseada em Ações:** Foque nos pagamentos via opções e ações.
    - **Análise de Bônus e PLR:** Investigue os bônus, participação nos lucros e métricas de desempenho.
    """)
    st.info("Selecione uma opção de análise na barra lateral para começar.")


def page_remuneracao_consolidada(df: pd.DataFrame):
    """Página para análises do Bloco 2: Remuneração Total e Componentes."""
    st.header("Análise da Remuneração Consolidada")

    # --- Filtros ---
    col1, col2 = st.columns(2)
    with col1:
        orgao = st.selectbox("Selecione o Órgão", df['ORGAO_ADMINISTRACAO'].unique(), key='orgao_consolidado')
    with col2:
        anos = sorted(df['ANO_REFER'].unique())
        ano_selecionado = st.selectbox("Selecione o Ano", anos, index=len(anos)-1, key='ano_consolidado')

    # --- Análise 1: Tendência da Remuneração Total ---
    st.subheader(f"Tendência da Remuneração Total Média para: {orgao}")
    df_orgao = df[df['ORGAO_ADMINISTRACAO'] == orgao]
    trend_data = df_orgao.groupby('ANO_REFER')['TOTAL_REMUNERACAO_ORGAO'].mean().reset_index()
    if not trend_data.empty:
        fig = px.line(trend_data, x='ANO_REFER', y='TOTAL_REMUNERACAO_ORGAO', markers=True, title=f"Evolução da Remuneração Média Anual ({orgao})", labels={'ANO_REFER': 'Ano', 'TOTAL_REMUNERACAO_ORGAO': 'Remuneração Média (R$)'})
        fig.update_layout(xaxis_type='category')
        st.plotly_chart(fig, use_container_width=True)

    # --- Análise 2: Ranking de Empresas por Remuneração Total ---
    st.subheader(f"Ranking de Empresas por Remuneração Total em {ano_selecionado}")
    df_ano = df[(df['ANO_REFER'] == ano_selecionado) & (df['ORGAO_ADMINISTRACAO'] == orgao)]
    remuneracao_por_cia = df_ano.groupby('NOME_COMPANHIA')['TOTAL_REMUNERACAO_ORGAO'].sum().reset_index()
    remuneracao_por_cia = remuneracao_por_cia[remuneracao_por_cia['TOTAL_REMUNERACAO_ORGAO'] > 0]
    
    # --- Análise 3: Estrutura da Remuneração por Empresa ---
    st.subheader(f"Estrutura da Remuneração por Empresa em {ano_selecionado}")
    empresa_selecionada = st.selectbox("Selecione uma Empresa para detalhar a estrutura", sorted(df_ano['NOME_COMPANHIA'].unique()))
    
    if empresa_selecionada:
        df_empresa_ano = df_ano[df_ano['NOME_COMPANHIA'] == empresa_selecionada]
        rem_fixa_total = df_empresa_ano['REM_FIXA'].sum()
        rem_variavel_total = df_empresa_ano['REM_VARIAVEL'].sum()
        rem_acoes_total = df_empresa_ano['REM_ACOES'].sum()
        rem_total_calc = rem_fixa_total + rem_variavel_total + rem_acoes_total
        
        if rem_total_calc > 0:
            estrutura_data = pd.DataFrame({'Componente': ['Fixa', 'Variável', 'Ações'], 'Valor': [rem_fixa_total, rem_variavel_total, rem_acoes_total]})
            fig_pie = px.pie(estrutura_data, values='Valor', names='Componente', title=f'Composição da Remuneração para {empresa_selecionada}', hole=.3)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Não há dados detalhados de remuneração para compor o gráfico de estrutura para a empresa e ano selecionados.")


def page_remuneracao_acoes(df: pd.DataFrame):
    """Página para análises do Bloco 1: Remuneração Baseada em Ações."""
    st.header("Análise de Remuneração Baseada em Ações")

    # --- Filtros ---
    anos = sorted(df['ANO_REFER'].unique())
    ano_selecionado = st.selectbox("Selecione o Ano", anos, index=len(anos)-1, key='ano_acoes')
    df_ano = df[df['ANO_REFER'] == ano_selecionado]

    # --- Análise 1: Ranking de Empresas por Remuneração em Ações ---
    st.subheader(f"Top 10 Empresas por Valor de Remuneração em Ações ({ano_selecionado})")
    rem_acoes_cia = df_ano.groupby('NOME_COMPANHIA')['REM_ACOES'].sum().nlargest(10).reset_index()
    rem_acoes_cia = rem_acoes_cia[rem_acoes_cia['REM_ACOES'] > 0]

    if not rem_acoes_cia.empty:
        fig = px.bar(rem_acoes_cia, x='NOME_COMPANHIA', y='REM_ACOES', text_auto='.2s', title="Maiores Valores de Remuneração Baseada em Ações", labels={'NOME_COMPANHIA': 'Empresa', 'REM_ACOES': 'Valor Total (R$)'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Não há dados de remuneração baseada em ações para o ano selecionado.")

    # --- Análise 2: Evolução da Remuneração em Ações por Setor ---
    st.subheader("Evolução da Remuneração em Ações por Setor")
    setores = sorted(df['SETOR_ATIVIDADE'].dropna().unique())
    setor_selecionado = st.selectbox("Selecione um Setor", setores, key='setor_acoes')

    if setor_selecionado:
        df_setor = df[df['SETOR_ATIVIDADE'] == setor_selecionado]
        trend_data = df_setor.groupby('ANO_REFER')['REM_ACOES'].mean().reset_index()
        if not trend_data.empty:
            fig_trend = px.line(trend_data, x='ANO_REFER', y='REM_ACOES', markers=True, title=f"Evolução da Média de Rem. em Ações para o Setor: {setor_selecionado}", labels={'ANO_REFER': 'Ano', 'REM_ACOES': 'Valor Médio (R$)'})
            fig_trend.update_layout(xaxis_type='category')
            st.plotly_chart(fig_trend, use_container_width=True)


def page_bonus_plr(df: pd.DataFrame):
    """Página para análises do Bloco 3: Bônus e PLR."""
    st.header("Análise de Bônus e Participação nos Resultados")

    # --- Filtros ---
    anos = sorted(df['ANO_REFER'].unique())
    ano_selecionado = st.selectbox("Selecione o Ano", anos, index=len(anos)-1, key='ano_bonus')
    df_ano = df[df['ANO_REFER'] == ano_selecionado]

    # --- Análise 1: Faixa de Bônus por Setor ---
    st.subheader(f"Faixa de Bônus por Setor em {ano_selecionado}")
    setores = sorted(df_ano['SETOR_ATIVIDADE'].dropna().unique())
    setor_bonus = st.selectbox("Selecione um Setor para analisar a faixa de bônus", setores)
    
    if setor_bonus:
        df_setor_bonus = df_ano[df_ano['SETOR_ATIVIDADE'] == setor_bonus]
        if not df_setor_bonus.empty and df_setor_bonus['BONUS'].sum() > 0:
            min_b, max_b, mean_b = df_setor_bonus['BONUS'].min(), df_setor_bonus['BONUS'].max(), df_setor_bonus['BONUS'].mean()
            col1, col2, col3 = st.columns(3)
            col1.metric("Bônus Mínimo", f"R$ {min_b:,.2f}")
            col2.metric("Bônus Médio", f"R$ {mean_b:,.2f}")
            col3.metric("Bônus Máximo", f"R$ {max_b:,.2f}")
        else:
            st.info(f"Não há dados de bônus para o setor '{setor_bonus}' no ano selecionado.")

    # --- Análise 2: Correlação Membros vs. Bônus ---
    st.subheader(f"Correlação: Nº de Membros Remunerados vs. Bônus Total ({ano_selecionado})")
    df_corr = df_ano.groupby('NOME_COMPANHIA').agg(Total_Membros=('NUM_MEMBROS_REMUNERADOS', 'sum'), Total_Bonus=('BONUS', 'sum')).reset_index()
    df_corr = df_corr[(df_corr['Total_Membros'] > 0) & (df_corr['Total_Bonus'] > 0)]

    if not df_corr.empty and len(df_corr) > 1:
        correlation = df_corr['Total_Membros'].corr(df_corr['Total_Bonus'])
        st.metric("Coeficiente de Correlação de Pearson", f"{correlation:.2f}")
        fig_corr = px.scatter(df_corr, x='Total_Membros', y='Total_Bonus', title="Nº de Membros Remunerados vs. Bônus Total por Empresa", labels={'Total_Membros': 'Nº Total de Membros Remunerados', 'Total_Bonus': 'Bônus Total (R$)'}, hover_name='NOME_COMPANHIA', trendline="ols", trendline_color_override="red")
        st.plotly_chart(fig_corr, use_container_width=True)
    else:
        st.warning("Não há dados suficientes para calcular a correlação para o ano selecionado.")


# --- Função Principal da Aplicação ---
def main():
    """Função principal que organiza a UI e a navegação."""
    
    github_url = "https://raw.githubusercontent.com/tovarich86/pesq_rem_CVM/main/dados_cvm_mesclados%20(1)%20-%20dados_cvm_mesclados%20(1).csv.csv"
    df = load_data(github_url)

    if df.empty:
        st.stop()

    # --- Barra Lateral de Navegação ---
    st.sidebar.title("Painel de Análise")
    st.sidebar.image("https://www.ibgc.org.br/themes/ibgc/dist/images/logo-default.svg", width=150)
    
    pagina_selecionada = st.sidebar.radio(
        "Selecione a Análise:",
        [
            "Página Inicial",
            "Análise da Remuneração Consolidada",
            "Análise de Remuneração Baseada em Ações",
            "Análise de Bônus e PLR",
        ]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info("Aplicação desenvolvida para análise exploratória de dados da CVM.")

    # --- Roteamento das Páginas ---
    if pagina_selecionada == "Página Inicial":
        page_home()
    elif pagina_selecionada == "Análise da Remuneração Consolidada":
        page_remuneracao_consolidada(df)
    elif pagina_selecionada == "Análise de Remuneração Baseada em Ações":
        page_remuneracao_acoes(df)
    elif pagina_selecionada == "Análise de Bônus e PLR":
        page_bonus_plr(df)


if __name__ == "__main__":
    main()
