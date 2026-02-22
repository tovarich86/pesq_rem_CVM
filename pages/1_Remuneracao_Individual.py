import streamlit as st
import plotly.express as px

# Importa as nossas funções partilhadas do utils.py
from utils import get_default_index, create_download_button, renderizar_sidebar_global, format_year

st.set_page_config(layout="wide", page_title="Remuneração Individual", page_icon="💰")

# Verifica se os dados já foram carregados na Home. Se não, avisa o utilizador.
if 'df_completo' not in st.session_state:
    st.warning("⚠️ Por favor, aceda à 'Página Inicial' (Home) primeiro para carregar a base de dados.")
    st.stop()

# Recupera os dados e desenha a barra lateral global
df_original = st.session_state['df_completo']
df = renderizar_sidebar_global(df_original)

if df.empty:
    st.warning("Nenhum dado encontrado para os filtros globais selecionados.")
    st.stop()

st.header("Análise da Remuneração Individual")
st.subheader("Evolução Comparativa por Empresa (2022-2024)")

col1, col2 = st.columns(2)

with col1:
    orgaos_disponiveis = sorted(df['ORGAO_ADMINISTRACAO'].unique())
    # Guarda o órgão no estado da sessão para não perder a seleção ao mudar de página
    if 'orgao_ind_selecionado' not in st.session_state: st.session_state['orgao_ind_selecionado'] = 'DIRETORIA ESTATUTARIA'
    idx_orgao = get_default_index(orgaos_disponiveis, st.session_state['orgao_ind_selecionado'])
    
    orgao = st.selectbox("1. Selecione o Órgão", orgaos_disponiveis, index=idx_orgao, key='orgao_ind')
    st.session_state['orgao_ind_selecionado'] = orgao

df_orgao = df[df['ORGAO_ADMINISTRACAO'] == orgao]

with col2:
    empresas_disponiveis = sorted(df_orgao['NOME_COMPANHIA'].unique())
    if not empresas_disponiveis:
        st.warning("Nenhuma empresa encontrada para o órgão selecionado.")
        st.stop()
        
    if 'empresa_ind_selecionada' not in st.session_state: st.session_state['empresa_ind_selecionada'] = empresas_disponiveis[0]
    idx_emp = get_default_index(empresas_disponiveis, st.session_state['empresa_ind_selecionada'])
    
    empresa = st.selectbox("2. Selecione a Empresa", empresas_disponiveis, index=idx_emp, key='empresa_ind_sel')
    st.session_state['empresa_ind_selecionada'] = empresa

# --- Gráfico de Evolução ---
df_filtered = df_orgao[(df_orgao['NOME_COMPANHIA'] == empresa) & (df_orgao['ANO_REFER'].isin([2022, 2023, 2024]))]

if not df_filtered.empty:
    df_analysis = df_filtered[['ANO_REFER', 'REM_MAXIMA_INDIVIDUAL', 'REM_MEDIA_INDIVIDUAL', 'REM_MINIMA_INDIVIDUAL']]
    df_plot = df_analysis.melt(id_vars=['ANO_REFER'], value_vars=['REM_MAXIMA_INDIVIDUAL', 'REM_MEDIA_INDIVIDUAL', 'REM_MINIMA_INDIVIDUAL'], var_name='Métrica', value_name='Valor')
    
    metric_names = {'REM_MAXIMA_INDIVIDUAL': 'Máxima', 'REM_MEDIA_INDIVIDUAL': 'Média', 'REM_MINIMA_INDIVIDUAL': 'Mínima'}
    df_plot['Métrica'] = df_plot['Métrica'].map(metric_names)
    df_plot = df_plot[df_plot['Valor'] > 0]
    
    if not df_plot.empty:
        fig = px.bar(df_plot, x='ANO_REFER', y='Valor', color='Métrica', barmode='group', text_auto='.2s', 
                     title=f"Evolução Comparativa da Remuneração Individual para {empresa}", 
                     labels={'ANO_REFER': 'Ano', 'Valor': 'Valor (R$)', 'Métrica': 'Tipo de Remuneração'})
        fig.update_layout(xaxis_type='category', separators=",.")
        st.plotly_chart(fig, use_container_width=True)
        create_download_button(df_plot, f"evolucao_rem_individual_{empresa}")
    else:
        st.info("Não há dados de remuneração individual para exibir no período de 2022-2024 para esta seleção.")
else:
    st.warning("Nenhum dado encontrado para a combinação de filtros no período de 2022-2024.")

st.markdown("---")
st.subheader("Ranking de Empresas por Remuneração Individual")

col_bar1, col_bar2 = st.columns(2)
with col_bar1:
    ano_bar = st.selectbox("Selecione o Ano para o Ranking", sorted(df['ANO_REFER'].unique(), reverse=True), key='ano_bar')
with col_bar2:
    metric_options = {'Máxima': 'REM_MAXIMA_INDIVIDUAL', 'Média': 'REM_MEDIA_INDIVIDUAL', 'Mínima': 'REM_MINIMA_INDIVIDUAL'}
    metrica_selecionada = st.selectbox("Selecione a Métrica", list(metric_options.keys()), key='metrica_bar')

df_bar = df[(df['ANO_REFER'] == ano_bar) & (df['ORGAO_ADMINISTRACAO'] == orgao)]
coluna_metrica = metric_options[metrica_selecionada]
df_bar = df_bar[df_bar[coluna_metrica] > 0]
df_top_companies = df_bar.nlargest(15, coluna_metrica)

if not df_top_companies.empty:
    fig_bar = px.bar(df_top_companies.sort_values(by=coluna_metrica), x=coluna_metrica, y='NOME_COMPANHIA', 
                     orientation='h', text_auto='.2s', 
                     title=f"Top 15 Empresas por Remuneração {metrica_selecionada} ({orgao}, {format_year(ano_bar)})", 
                     labels={coluna_metrica: f"Remuneração {metrica_selecionada} (R$)", 'NOME_COMPANHIA': 'Empresa'})
    fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, separators=",.")
    st.plotly_chart(fig_bar, use_container_width=True)
    create_download_button(df_top_companies[['NOME_COMPANHIA', coluna_metrica]], f"ranking_rem_individual_{ano_bar}")
else:
    st.warning(f"Não há dados de Remuneração {metrica_selecionada} para exibir para os filtros selecionados.")
