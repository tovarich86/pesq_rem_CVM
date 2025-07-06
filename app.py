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
        # O engine 'python' é mais flexível para ler arquivos com possíveis inconsistências.
        df = pd.read_csv(url, sep=',', encoding='latin-1', engine='python')
        df.columns = df.columns.str.strip()

        # Mapeamento completo e flexível das colunas para nomes padronizados.
        rename_map = {
            # Identificação
            'NOME_COMPANHIA': ['DENOM_CIA'],
            'ANO_REFER': ['Ano do Exercício Social'],
            'ORGAO_ADMINISTRACAO': ['Orgao_Administracao'],
            'SETOR_ATIVIDADE': ['Setor de ativdade', 'Setor de Atividade'],
            
            # Bloco 1: Remuneração Baseada em Ações (Colunas F-J)
            'NUM_MEMBROS_ACOES': ['Quantidade_Membros_Remunerados_Com_Acoes_Opcoes'],
            'VALOR_OPCOES_EXERCIDAS': ['Valor_Total_Opcoes_Acoes_Exercidas_Reconhecidas_Resultado_Exercicio'],
            'VALOR_ACOES_RESTRITAS': ['Valor_Total_Acoes_Restritas_Entregues_Reconhecidas_Resultado_Exercicio'],
            'VALOR_OUTROS_PLANOS_ACOES': ['Valor_Total_Outros_Planos_Baseados_Acoes_Reconhecidos_Resultado_Exercicio'],
            'TOTAL_REM_ACOES_BLOCO1': ['Valor_Total_Remuneracao_Baseada_Acoes_Reconhecida_Resultado_Exercicio'],

            # Bloco 2: Remuneração Total e Componentes (Colunas K-AF)
            'NUM_MEMBROS_TOTAL': ['Quantidade_Total_Membros_Remunerados_Orgao'],
            'REM_FIXA_SALARIO': ['Salario_Fixo_Anual_Total'],
            'REM_FIXA_BENEFICIOS': ['Beneficios_Anual_Total'],
            'REM_FIXA_POS_EMPREGO': ['Beneficios_Pos_Emprego_Anual_Total'],
            'REM_FIXA_RESCISAO': ['Beneficios_Cessacao_Cargo_Anual_Total'],
            'REM_FIXA_OUTROS': ['Outros_Valores_Remuneracao_Fixa_Anual_Total'],
            'REM_VAR_BONUS_PLR': ['Bonus_Participacao_Resultados_Anual_Total'],
            'REM_VAR_ACOES': ['Remuneracao_Baseada_Acoes_Anual_Total'],
            'REM_VAR_OUTROS': ['Outros_Valores_Remuneracao_Variavel_Anual_Total'],
            'TOTAL_REMUNERACAO_ORGAO': ['Valor_Total_Remuneracao_Anual_Orgao'],

            # Bloco 3: Métricas de Bônus e PLR (Colunas AG-AO)
            'NUM_MEMBROS_BONUS': ['Quantidade_Membros_Com_Direito_Bonus_Participacao_Resultados'],
            'VALOR_BONUS_APROVADO': ['Valor_Total_Bonus_Participacao_Resultados_Aprovado'],
            'PERC_LUCRO_PAGO': ['Percentual_Lucro_Liquido_Destinado_Remuneracao'],
        }

        actual_rename_dict = {}
        for new_name, old_names in rename_map.items():
            for old_name in old_names:
                if old_name in df.columns:
                    actual_rename_dict[old_name] = new_name
                    break
        
        df.rename(columns=actual_rename_dict, inplace=True)

        # Converte todas as colunas numéricas de uma vez
        all_renamed_cols = list(rename_map.keys())
        for col in all_renamed_cols:
            if col in df.columns:
                 if 'NUM' in col or 'VALOR' in col or 'TOTAL' in col or 'REM' in col or 'PERC' in col:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # --- CORREÇÃO ROBUSTA: Cálculo dos Totais ---
        # Calcula os totais somando os componentes para garantir que as colunas existam,
        # resolvendo o KeyError de forma definitiva.
        fixed_rem_components = ['REM_FIXA_SALARIO', 'REM_FIXA_BENEFICIOS', 'REM_FIXA_POS_EMPREGO', 'REM_FIXA_RESCISAO', 'REM_FIXA_OUTROS']
        variable_rem_components = ['REM_VAR_BONUS_PLR', 'REM_VAR_ACOES', 'REM_VAR_OUTROS']
        
        # Garante que as colunas de componentes existam antes de somar
        for component_col in fixed_rem_components + variable_rem_components:
            if component_col not in df.columns:
                df[component_col] = 0 # Cria a coluna com zeros se não existir

        df['TOTAL_REM_FIXA'] = df[fixed_rem_components].sum(axis=1)
        df['TOTAL_REM_VARIAVEL'] = df[variable_rem_components].sum(axis=1)

        if 'ANO_REFER' in df.columns:
            df['ANO_REFER'] = pd.to_numeric(df['ANO_REFER'], errors='coerce').dropna().astype(int)
        
        if 'SETOR_ATIVIDADE' in df.columns:
            df['SETOR_ATIVIDADE'] = df['SETOR_ATIVIDADE'].str.strip()

        return df
    except Exception as e:
        st.error(f"Erro crítico ao carregar ou processar os dados: {e}")
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
    - **Remuneração Consolidada:** Explore os valores totais, rankings e a estrutura geral da remuneração (salário, variável, etc.).
    - **Remuneração Baseada em Ações:** Foque nos pagamentos via opções e ações.
    - **Bônus e PLR:** Investigue os bônus, participação nos lucros e métricas de desempenho.
    """)
    st.info("Selecione uma opção de análise na barra lateral para começar.")


def page_remuneracao_consolidada(df: pd.DataFrame):
    """Página para análises do Bloco 2: Remuneração Total e Componentes."""
    st.header("Análise da Remuneração Consolidada")

    st.subheader("Evolução da Estrutura da Remuneração")
    
    # --- Filtros aprimorados ---
    col1, col2, col3 = st.columns(3)
    with col1:
        setor = st.selectbox("Selecione o Setor", sorted(df['SETOR_ATIVIDADE'].dropna().unique()), key='setor_consolidado')
    
    df_setor = df[df['SETOR_ATIVIDADE'] == setor]
    
    with col2:
        orgao = st.selectbox("Selecione o Órgão", sorted(df_setor['ORGAO_ADMINISTRACAO'].unique()), key='orgao_consolidado')
    
    df_orgao = df_setor[df_setor['ORGAO_ADMINISTRACAO'] == orgao]

    with col3:
        empresa = st.selectbox("Selecione a Empresa", sorted(df_orgao['NOME_COMPANHIA'].unique()), key='empresa_consolidado')

    # --- Preparação dos dados para o gráfico de barras empilhadas ---
    df_empresa_filtrada = df_orgao[df_orgao['NOME_COMPANHIA'] == empresa]

    # Componentes detalhados da remuneração
    component_cols = {
        'Salário': 'REM_FIXA_SALARIO',
        'Benefícios': 'REM_FIXA_BENEFICIOS',
        'Pós-Emprego': 'REM_FIXA_POS_EMPREGO',
        'Bônus/PLR': 'REM_VAR_BONUS_PLR',
        'Ações (do Bloco 2)': 'REM_VAR_ACOES',
        'Outros (Fixo)': 'REM_FIXA_OUTROS',
        'Outros (Variável)': 'REM_VAR_OUTROS',
    }

    # Garante que todas as colunas de componentes existam
    for col in component_cols.values():
        if col not in df_empresa_filtrada.columns:
            df_empresa_filtrada[col] = 0

    # Agrupa por ano e soma os componentes
    yearly_data = df_empresa_filtrada.groupby('ANO_REFER')[[col for col in component_cols.values()]].sum().reset_index()

    # Transforma os dados do formato 'largo' para 'longo' para o Plotly
    df_plot = yearly_data.melt(id_vars=['ANO_REFER'], var_name='Componente', value_name='Valor')
    
    # Mapeia os nomes técnicos para nomes amigáveis para a legenda
    friendly_names = {v: k for k, v in component_cols.items()}
    df_plot['Componente'] = df_plot['Componente'].map(friendly_names)

    if not df_plot.empty and df_plot['Valor'].sum() > 0:
        fig = px.bar(
            df_plot,
            x='ANO_REFER',
            y='Valor',
            color='Componente',
            title=f"Evolução dos Componentes da Remuneração para {empresa}<br><sub>Órgão: {orgao}</sub>",
            labels={
                'ANO_REFER': 'Ano do Exercício Social',
                'Valor': 'Valor Total Anual (R$)',
                'Componente': 'Componente da Remuneração'
            },
            text_auto='.2s'
        )
        fig.update_layout(xaxis_type='category', barmode='stack')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Não há dados de remuneração para exibir para a seleção atual.")


def page_remuneracao_acoes(df: pd.DataFrame):
    """Página para análises do Bloco 1: Remuneração Baseada em Ações."""
    st.header("Análise de Remuneração Baseada em Ações")

    anos = sorted(df['ANO_REFER'].unique())
    ano_selecionado = st.selectbox("Selecione o Ano", anos, index=len(anos)-1, key='ano_acoes')
    df_ano = df[df['ANO_REFER'] == ano_selecionado]

    st.subheader(f"Ranking de Empresas por Remuneração em Ações ({ano_selecionado})")
    rem_acoes_cia = df_ano.groupby('NOME_COMPANHIA')['TOTAL_REM_ACOES_BLOCO1'].sum().nlargest(10).reset_index()
    rem_acoes_cia = rem_acoes_cia[rem_acoes_cia['TOTAL_REM_ACOES_BLOCO1'] > 0]

    if not rem_acoes_cia.empty:
        fig = px.bar(rem_acoes_cia, x='NOME_COMPANHIA', y='TOTAL_REM_ACOES_BLOCO1', text_auto='.2s', title="Top 10 Empresas por Valor Total de Remuneração Baseada em Ações", labels={'NOME_COMPANHIA': 'Empresa', 'TOTAL_REM_ACOES_BLOCO1': 'Valor Total (R$)'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Não há dados de remuneração baseada em ações para o ano selecionado.")

    st.subheader(f"Composição da Remuneração por Ações ({ano_selecionado})")
    empresa_selecionada_acoes = st.selectbox("Selecione uma Empresa para detalhar", sorted(df_ano['NOME_COMPANHIA'].unique()), key='empresa_acoes')
    
    if empresa_selecionada_acoes:
        df_empresa = df_ano[df_ano['NOME_COMPANHIA'] == empresa_selecionada_acoes]
        opcoes = df_empresa['VALOR_OPCOES_EXERCIDAS'].sum()
        restritas = df_empresa['VALOR_ACOES_RESTRITAS'].sum()
        outros = df_empresa['VALOR_OUTROS_PLANOS_ACOES'].sum()

        if opcoes + restritas + outros > 0:
            comp_data = pd.DataFrame({'Componente': ['Opções Exercidas', 'Ações Restritas', 'Outros Planos'], 'Valor': [opcoes, restritas, outros]})
            fig_comp = px.bar(comp_data, x='Componente', y='Valor', title=f'Composição da Remuneração por Ações para {empresa_selecionada_acoes}', labels={'Componente': 'Tipo de Plano', 'Valor': 'Valor (R$)'}, text_auto='.2s')
            st.plotly_chart(fig_comp, use_container_width=True)
        else:
            st.info("Não há dados detalhados sobre os tipos de planos baseados em ações.")


def page_bonus_plr(df: pd.DataFrame):
    """Página para análises do Bloco 3: Bônus e PLR."""
    st.header("Análise de Bônus e Participação nos Resultados")

    anos = sorted(df['ANO_REFER'].unique())
    ano_selecionado = st.selectbox("Selecione o Ano", anos, index=len(anos)-1, key='ano_bonus')
    df_ano = df[df['ANO_REFER'] == ano_selecionado]

    st.subheader(f"Ranking de Empresas por Valor de Bônus Aprovado ({ano_selecionado})")
    bonus_cia = df_ano.groupby('NOME_COMPANHIA')['VALOR_BONUS_APROVADO'].sum().nlargest(10).reset_index()
    bonus_cia = bonus_cia[bonus_cia['VALOR_BONUS_APROVADO'] > 0]
    if not bonus_cia.empty:
        fig_bonus = px.bar(bonus_cia, x='NOME_COMPANHIA', y='VALOR_BONUS_APROVADO', text_auto='.2s', title="Top 10 Empresas por Valor de Bônus/PLR Aprovado", labels={'NOME_COMPANHIA': 'Empresa', 'VALOR_BONUS_APROVADO': 'Valor Total (R$)'})
        st.plotly_chart(fig_bonus, use_container_width=True)
    else:
        st.info("Não há dados de bônus/PLR para o ano selecionado.")

    st.subheader(f"Correlação: Nº de Membros vs. Bônus Aprovado ({ano_selecionado})")
    df_corr = df_ano.groupby('NOME_COMPANHIA').agg(Total_Membros=('NUM_MEMBROS_BONUS', 'sum'), Total_Bonus=('VALOR_BONUS_APROVADO', 'sum')).reset_index()
    df_corr = df_corr[(df_corr['Total_Membros'] > 0) & (df_corr['Total_Bonus'] > 0)]

    if not df_corr.empty and len(df_corr) > 1:
        correlation = df_corr['Total_Membros'].corr(df_corr['Total_Bonus'])
        st.metric("Coeficiente de Correlação de Pearson", f"{correlation:.2f}")
        fig_corr = px.scatter(df_corr, x='Total_Membros', y='Total_Bonus', title="Nº de Membros com Direito a Bônus vs. Valor Aprovado", labels={'Total_Membros': 'Nº de Membros com Direito a Bônus', 'Total_Bonus': 'Bônus Total Aprovado (R$)'}, hover_name='NOME_COMPANHIA', trendline="ols", trendline_color_override="red")
        st.plotly_chart(fig_corr, use_container_width=True)
    else:
        st.warning("Não há dados suficientes para calcular a correlação.")


# --- Função Principal da Aplicação ---
def main():
    """Função principal que organiza a UI e a navegação."""
    
    # --- CORREÇÃO DA URL ---
    # A URL foi corrigida para apontar para o arquivo "raw" (bruto) e não para a página de visualização do GitHub.
    github_url = "https://raw.githubusercontent.com/tovarich86/pesq_rem_CVM/main/dados_cvm_mesclados.csv.csv"
    df = load_data(github_url)

    if df.empty:
        st.error("Falha no carregamento dos dados. O aplicativo não pode continuar.")
        st.stop()

    st.sidebar.title("Painel de Análise")
    st.sidebar.image("https://www.ibgc.org.br/themes/ibgc/dist/images/logo-default.svg", width=150)
    
    pagina_selecionada = st.sidebar.radio(
        "Selecione a Análise:",
        [
            "Página Inicial",
            "Remuneração Consolidada",
            "Remuneração Baseada em Ações",
            "Bônus e PLR",
        ]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info("Aplicação desenvolvida para análise exploratória de dados da CVM.")

    if pagina_selecionada == "Página Inicial":
        page_home()
    elif pagina_selecionada == "Remuneração Consolidada":
        page_remuneracao_consolidada(df)
    elif pagina_selecionada == "Remuneração Baseada em Ações":
        page_remuneracao_acoes(df)
    elif pagina_selecionada == "Bônus e PLR":
        page_bonus_plr(df)


if __name__ == "__main__":
    main()
