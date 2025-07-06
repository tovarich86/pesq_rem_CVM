import streamlit as st
import pandas as pd
import plotly.express as px
import warnings

# Ignorar avisos de depreciação futuros do pandas que podem poluir a saída
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- Configuração da Página ---
# Define o layout da página para ser 'wide' (largo) e dá um título à aba do navegador
st.set_page_config(layout="wide", page_title="Análise de Remuneração CVM")


# --- Carregamento e Preparação dos Dados ---
# A anotação @st.cache_data garante que os dados sejam carregados e processados apenas uma vez,
# melhorando a performance da aplicação.
@st.cache_data
def load_data(url: str) -> pd.DataFrame:
    """
    Carrega os dados de uma URL, limpa, renomeia colunas e calcula novos campos
    para facilitar as análises.

    Args:
        url (str): A URL para o arquivo CSV bruto no GitHub.

    Returns:
        pd.DataFrame: O DataFrame processado e pronto para uso.
    """
    try:
        df = pd.read_csv(url)

        # --- Limpeza e Renomeação de Colunas ---
        # Padroniza os nomes das colunas para facilitar o acesso e a consistência com as funções
        df.rename(columns={
            'DENOM_CIA': 'NOME_COMPANHIA',
            'Ano do Exercício Social': 'ANO_REFER',
            'Orgao_Administracao': 'ORGAO_ADMINISTRACAO',
            'Setor de ativdade': 'SETOR_ATIVIDADE',
            'Valor_Total_Remuneracao_Anual_Orgao': 'TOTAL_REMUNERACAO_ORGAO',
            'Valor_Total_Bonus_Participacao_Resultados_Aprovado': 'BONUS',
            'Quantidade_Total_Membros_Remunerados_Orgao': 'NUM_MEMBROS_REMUNERADOS',
            'Salario_Fixo_Anual_Total': 'REM_FIXA',
            'Remuneracao_Variavel_Anual_Total': 'REM_VARIAVEL',
            'Valor_Total_Remuneracao_Baseada_Acoes_Reconhecida_Resultado_Exercicio': 'REM_ACOES'
        }, inplace=True)

        # --- Tratamento de Tipos e Nulos ---
        # Converte colunas numéricas, preenchendo valores ausentes (NaN) com 0
        numeric_cols = [
            'TOTAL_REMUNERACAO_ORGAO', 'BONUS', 'NUM_MEMBROS_REMUNERADOS',
            'REM_FIXA', 'REM_VARIAVEL', 'REM_ACOES'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Garante que a coluna de ano seja do tipo inteiro
        if 'ANO_REFER' in df.columns:
            df['ANO_REFER'] = pd.to_numeric(df['ANO_REFER'], errors='coerce').dropna().astype(int)
        
        # Limpa espaços em branco extras na coluna de setor
        if 'SETOR_ATIVIDADE' in df.columns:
            df['SETOR_ATIVIDADE'] = df['SETOR_ATIVIDADE'].str.strip()

        return df
    except Exception as e:
        # Se houver um erro no carregamento, exibe uma mensagem de erro na aplicação
        st.error(f"Erro ao carregar ou processar os dados: {e}")
        return pd.DataFrame()


# --- Funções de Plotagem e Análise (Páginas da Aplicação) ---

def page_home():
    """Página inicial da aplicação."""
    st.title("Análise Interativa de Remuneração de Administradores")
    st.markdown("""
    Bem-vindo(a) à ferramenta de análise de remuneração de administradores de companhias abertas brasileiras.
    Os dados são públicos e foram extraídos da CVM (Comissão de Valores Mobiliários).

    **Como usar:**
    1.  **Navegue pelas análises** usando o menu na barra lateral à esquerda.
    2.  **Use os filtros** em cada página para customizar a visualização.
    3.  **Interaja com os gráficos** para obter mais detalhes (passe o mouse sobre os pontos/barras).

    **Fonte dos Dados:** Dados públicos da CVM, compilados para os exercícios de 2022 a 2025 (projeção).
    **Aviso:** Esta é uma ferramenta para fins exploratórios e educacionais. Valide sempre as informações antes de tomar decisões.
    """)
    st.info("Selecione uma opção de análise na barra lateral para começar.")


def page_visao_geral(df: pd.DataFrame):
    """Página para análises gerais e de tendências."""
    st.header("Visão Geral e Tendências de Remuneração")

    # --- Filtros para a página ---
    col1, col2 = st.columns(2)
    with col1:
        orgao = st.selectbox(
            "Selecione o Órgão de Administração",
            df['ORGAO_ADMINISTRACAO'].unique(),
            key='orgao_geral'
        )
    with col2:
        anos = sorted(df['ANO_REFER'].unique())
        ano_selecionado = st.selectbox(
            "Selecione o Ano para o Ranking",
            options=anos,
            index=len(anos)-1, # Padrão para o último ano
            key='ano_geral'
        )

    # --- Análise 1: Tendência da Remuneração ---
    st.subheader(f"Tendência da Remuneração Total Média para: {orgao}")
    
    df_orgao = df[df['ORGAO_ADMINISTRACAO'] == orgao]
    trend_data = df_orgao.groupby('ANO_REFER')['TOTAL_REMUNERACAO_ORGAO'].mean().reset_index()

    if not trend_data.empty:
        fig = px.line(
            trend_data,
            x='ANO_REFER',
            y='TOTAL_REMUNERACAO_ORGAO',
            markers=True,
            title=f"Evolução da Remuneração Média Anual ({orgao})",
            labels={'ANO_REFER': 'Ano', 'TOTAL_REMUNERACAO_ORGAO': 'Remuneração Média (R$)'}
        )
        fig.update_layout(xaxis_type='category')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Não há dados suficientes para exibir a tendência.")

    # --- Análise 2: Top e Bottom Empresas ---
    st.subheader(f"Ranking de Empresas por Remuneração Total em {ano_selecionado}")
    
    df_ano = df[(df['ANO_REFER'] == ano_selecionado) & (df['ORGAO_ADMINISTRACAO'] == orgao)]
    
    # Agrupa por companhia para garantir valores únicos por empresa
    remuneracao_por_cia = df_ano.groupby('NOME_COMPANHIA')['TOTAL_REMUNERACAO_ORGAO'].sum().reset_index()
    remuneracao_por_cia = remuneracao_por_cia[remuneracao_por_cia['TOTAL_REMUNERACAO_ORGAO'] > 0]
    
    col1_rank, col2_rank = st.columns(2)
    
    with col1_rank:
        st.markdown("#### Maiores Remunerações")
        top_5 = remuneracao_por_cia.nlargest(5, 'TOTAL_REMUNERACAO_ORGAO')
        if not top_5.empty:
            fig_top = px.bar(
                top_5, y='NOME_COMPANHIA', x='TOTAL_REMUNERACAO_ORGAO',
                orientation='h', text_auto='.2s',
                labels={'NOME_COMPANHIA': 'Empresa', 'TOTAL_REMUNERACAO_ORGAO': 'Remuneração Total (R$)'}
            )
            fig_top.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_top, use_container_width=True)
        else:
            st.info("Não há dados para exibir o ranking de maiores remunerações.")

    with col2_rank:
        st.markdown("#### Menores Remunerações")
        bottom_5 = remuneracao_por_cia.nsmallest(5, 'TOTAL_REMUNERACAO_ORGAO')
        if not bottom_5.empty:
            fig_bottom = px.bar(
                bottom_5, y='NOME_COMPANHIA', x='TOTAL_REMUNERACAO_ORGAO',
                orientation='h', text_auto='.2s',
                labels={'NOME_COMPANHIA': 'Empresa', 'TOTAL_REMUNERACAO_ORGAO': 'Remuneração Total (R$)'}
            )
            fig_bottom.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_bottom, use_container_width=True)
        else:
            st.info("Não há dados para exibir o ranking de menores remunerações.")

def page_analise_setorial(df: pd.DataFrame):
    """Página para análises por setor de atividade."""
    st.header("Análise por Setor de Atividade")

    # --- Filtros ---
    anos = sorted(df['ANO_REFER'].unique())
    ano_selecionado = st.selectbox(
        "Selecione o Ano",
        options=anos,
        index=len(anos)-1,
        key='ano_setor'
    )
    
    df_ano = df[df['ANO_REFER'] == ano_selecionado].copy()

    # --- Análise 1: Top Setores por Remuneração Média ---
    st.subheader(f"Ranking de Setores por Remuneração Média Total em {ano_selecionado}")
    
    rem_setor = df_ano.groupby('SETOR_ATIVIDADE')['TOTAL_REMUNERACAO_ORGAO'].mean().nlargest(10).reset_index()
    
    if not rem_setor.empty:
        fig = px.bar(
            rem_setor, x='SETOR_ATIVIDADE', y='TOTAL_REMUNERACAO_ORGAO',
            text_auto='.2s', title="Top 10 Setores por Remuneração Média",
            labels={'SETOR_ATIVIDADE': 'Setor', 'TOTAL_REMUNERACAO_ORGAO': 'Remuneração Média (R$)'}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Não há dados para o ranking de setores.")

    # --- Análise 2: Faixa de Bônus por Setor ---
    st.subheader(f"Faixa de Bônus por Setor em {ano_selecionado}")
    setor_bonus = st.selectbox(
        "Selecione um Setor para analisar a faixa de bônus",
        df_ano['SETOR_ATIVIDADE'].dropna().unique()
    )
    
    df_setor_bonus = df_ano[df_ano['SETOR_ATIVIDADE'] == setor_bonus]
    
    if not df_setor_bonus.empty and df_setor_bonus['BONUS'].sum() > 0:
        min_bonus = df_setor_bonus['BONUS'].min()
        max_bonus = df_setor_bonus['BONUS'].max()
        mean_bonus = df_setor_bonus['BONUS'].mean()

        col1, col2, col3 = st.columns(3)
        col1.metric("Bônus Mínimo", f"R$ {min_bonus:,.2f}")
        col2.metric("Bônus Médio", f"R$ {mean_bonus:,.2f}")
        col3.metric("Bônus Máximo", f"R$ {max_bonus:,.2f}")
    else:
        st.info(f"Não há dados de bônus para o setor '{setor_bonus}' no ano selecionado.")


def page_analise_empresa(df: pd.DataFrame):
    """Página para análises focadas em uma única empresa."""
    st.header("Análise Detalhada por Empresa")

    # --- Filtros ---
    empresas = sorted(df['NOME_COMPANHIA'].unique())
    empresa_selecionada = st.selectbox("Selecione a Empresa", empresas)
    
    df_empresa = df[df['NOME_COMPANHIA'] == empresa_selecionada].copy()
    
    anos = sorted(df_empresa['ANO_REFER'].unique())
    ano_selecionado = st.selectbox(
        "Selecione o Ano",
        options=anos,
        index=len(anos)-1 if anos else 0,
        key='ano_empresa'
    )
    
    df_empresa_ano = df_empresa[df_empresa['ANO_REFER'] == ano_selecionado]

    # --- Análise 1: Estrutura da Remuneração ---
    st.subheader(f"Estrutura da Remuneração em {ano_selecionado}")
    
    if not df_empresa_ano.empty:
        # Agrega os valores para todos os órgãos da empresa naquele ano
        rem_fixa_total = df_empresa_ano['REM_FIXA'].sum()
        rem_variavel_total = df_empresa_ano['REM_VARIAVEL'].sum()
        rem_acoes_total = df_empresa_ano['REM_ACOES'].sum()
        rem_total = df_empresa_ano['TOTAL_REMUNERACAO_ORGAO'].sum()

        if rem_total > 0:
            estrutura_data = pd.DataFrame({
                'Componente': ['Fixa', 'Variável', 'Ações', 'Outros'],
                'Valor': [
                    rem_fixa_total,
                    rem_variavel_total,
                    rem_acoes_total,
                    rem_total - (rem_fixa_total + rem_variavel_total + rem_acoes_total)
                ]
            })
            
            fig = px.pie(
                estrutura_data, values='Valor', names='Componente',
                title=f'Composição da Remuneração Total para {empresa_selecionada} ({ano_selecionado})',
                hole=.3
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Não há dados de remuneração para compor o gráfico.")
    else:
        st.warning(f"Não foram encontrados dados para a empresa {empresa_selecionada} no ano {ano_selecionado}.")


def page_analises_correlacao(df: pd.DataFrame):
    """Página para análises de correlação."""
    st.header("Análise de Correlação")

    anos = sorted(df['ANO_REFER'].unique())
    ano_selecionado = st.selectbox(
        "Selecione o Ano para a Análise",
        options=anos,
        index=len(anos)-1,
        key='ano_corr'
    )
    
    df_ano = df[df['ANO_REFER'] == ano_selecionado].copy()
    
    st.subheader(f"Correlação: Nº de Membros Remunerados vs. Bônus Total ({ano_selecionado})")

    # Agrega por empresa para a análise de correlação
    df_corr = df_ano.groupby('NOME_COMPANHIA').agg(
        Total_Membros=('NUM_MEMBROS_REMUNERADOS', 'sum'),
        Total_Bonus=('BONUS', 'sum')
    ).reset_index()

    # Filtra para remover casos que podem distorcer a correlação
    df_corr = df_corr[(df_corr['Total_Membros'] > 0) & (df_corr['Total_Bonus'] > 0)]

    if not df_corr.empty and len(df_corr) > 1:
        correlation = df_corr['Total_Membros'].corr(df_corr['Total_Bonus'])
        
        st.metric("Coeficiente de Correlação de Pearson", f"{correlation:.2f}")
        st.caption("Valores próximos de 1 indicam forte correlação positiva. Próximos de -1, forte correlação negativa. Próximos de 0, baixa correlação.")

        fig = px.scatter(
            df_corr, x='Total_Membros', y='Total_Bonus',
            title="Nº de Membros Remunerados vs. Bônus Total por Empresa",
            labels={'Total_Membros': 'Número Total de Membros Remunerados', 'Total_Bonus': 'Bônus Total (R$)'},
            hover_name='NOME_COMPANHIA',
            trendline="ols", # 'ols' = Ordinary Least Squares (linha de tendência)
            trendline_color_override="red"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Não há dados suficientes para calcular a correlação para o ano selecionado.")


# --- Função Principal da Aplicação ---
def main():
    """Função principal que organiza a UI e a navegação."""
    
    # URL para o seu arquivo CSV no GitHub (substitua pelo seu link)
    # IMPORTANTE: Use o link para o arquivo "raw" (bruto)
    github_url = "https://raw.githubusercontent.com/tovarich86/Remunera-oxReceita/main/dados_cvm_mesclados%20(1)%20-%20dados_cvm_mesclados%20(1).csv.csv"

    df = load_data(github_url)

    if df.empty:
        st.stop() # Interrompe a execução se os dados não puderem ser carregados

    # --- Barra Lateral de Navegação ---
    st.sidebar.title("Painel de Análise")
    st.sidebar.image("https://www.ibgc.org.br/themes/ibgc/dist/images/logo-default.svg", width=150)
    
    pagina_selecionada = st.sidebar.radio(
        "Selecione a Análise:",
        [
            "Página Inicial",
            "Visão Geral e Tendências",
            "Análise por Setor",
            "Análise por Empresa",
            "Análises de Correlação"
        ]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info("Aplicação desenvolvida para análise exploratória de dados da CVM.")

    # --- Roteamento das Páginas ---
    if pagina_selecionada == "Página Inicial":
        page_home()
    elif pagina_selecionada == "Visão Geral e Tendências":
        page_visao_geral(df)
    elif pagina_selecionada == "Análise por Setor":
        page_analise_setorial(df)
    elif pagina_selecionada == "Análise por Empresa":
        page_analise_empresa(df)
    elif pagina_selecionada == "Análises de Correlação":
        page_analises_correlacao(df)


if __name__ == "__main__":
    main()
