import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Importações dos utilitários
from utils import get_default_index, renderizar_sidebar_global, formata_brl_int, formata_abrev, create_download_button

st.set_page_config(layout="wide", page_title="Governança e Risco", page_icon="⚖️")

if 'df_completo' not in st.session_state:
    st.warning("⚠️ Por favor, aceda à 'Página Inicial' (Home) primeiro para carregar a base de dados.")
    st.stop()

df_original = st.session_state['df_completo']
df = renderizar_sidebar_global(df_original)

if df.empty:
    st.warning("Nenhum dado encontrado para os filtros globais selecionados.")
    st.stop()

st.header("⚖️ Governança e Risco (Raio-X)")
st.markdown("""
Este painel aplica métricas avançadas de Governança Corporativa para identificar riscos de agência, concentração de poder e anomalias de rescisão.
""")

# --- Filtro Global da Página ---
anos_disponiveis = sorted(df['ANO_REFER'].unique(), reverse=True)
ano_selecionado = st.selectbox("Selecione o Ano de Referência para a Análise de Risco:", anos_disponiveis)

st.markdown("---")

# ==========================================
# 1. CEO PAY SLICE (Dispersão Salarial)
# ==========================================
st.subheader("1. CEO Pay Slice (Fosso Salarial da Diretoria)")
st.markdown("""
O **Múltiplo de Dispersão** divide a Maior Remuneração pela Média da Diretoria. Valores muito altos indicam uma concentração excessiva de orçamento no CEO (Key Person Risk) e uma estrutura menos colaborativa.
""")

df_diretoria = df[(df['ANO_REFER'] == ano_selecionado) & (df['ORGAO_ADMINISTRACAO'] == 'DIRETORIA ESTATUTARIA')].copy()

# Cálculo do CEO Pay Slice
df_diretoria['CEO_Pay_Slice'] = 0.0
mascara_validos = (df_diretoria['REM_MEDIA_INDIVIDUAL'] > 0) & (df_diretoria['REM_MAXIMA_INDIVIDUAL'] > 0)
df_diretoria.loc[mascara_validos, 'CEO_Pay_Slice'] = df_diretoria.loc[mascara_validos, 'REM_MAXIMA_INDIVIDUAL'] / df_diretoria.loc[mascara_validos, 'REM_MEDIA_INDIVIDUAL']

df_cps = df_diretoria[df_diretoria['CEO_Pay_Slice'] > 0].sort_values(by='CEO_Pay_Slice', ascending=False)

col1_cps, col2_cps = st.columns([2, 1])

with col1_cps:
    # Mostra o Top 15 empresas com maior dispersão
    fig_cps = px.bar(
        df_cps.head(15), 
        x='CEO_Pay_Slice', 
        y='NOME_COMPANHIA', 
        orientation='h',
        title=f"Top 15 Maiores Dispersões Salariais (Diretoria) - {ano_selecionado}",
        labels={'CEO_Pay_Slice': 'Múltiplo (Maior vs Média)', 'NOME_COMPANHIA': 'Empresa'},
        text_auto='.1f',
        color='CEO_Pay_Slice',
        color_continuous_scale='Reds'
    )
    fig_cps.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig_cps, width='stretch')

with col2_cps:
    st.info("**Estatísticas do Mercado (Filtro Atual)**")
    media_mercado = df_cps['CEO_Pay_Slice'].mean()
    mediana_mercado = df_cps['CEO_Pay_Slice'].median()
    maximo_mercado = df_cps['CEO_Pay_Slice'].max()
    
    st.metric("Média de Dispersão", f"{media_mercado:.1f}x")
    st.metric("Mediana de Dispersão", f"{mediana_mercado:.1f}x")
    st.metric("Pico do Mercado (Máximo)", f"{maximo_mercado:.1f}x")
    
    st.write("*(Exemplo: 3.0x significa que a maior remuneração é o triplo da média da própria diretoria).*")

st.markdown("---")

# ==========================================
# 2. EQUILÍBRIO DE PODER (Conselho vs Diretoria)
# ==========================================
st.subheader("2. Assimetria de Incentivos (Conselho vs. Diretoria)")
st.markdown("""
Analisa se o Conselho de Administração é bem remunerado o suficiente para fiscalizar uma diretoria milionária. Gráfico exibe a Remuneração Total de cada órgão.
""")

df_ano = df[df['ANO_REFER'] == ano_selecionado].copy()

# Agregar total por empresa e por órgão
df_gov = df_ano[df_ano['ORGAO_ADMINISTRACAO'].isin(['DIRETORIA ESTATUTARIA', 'CONSELHO DE ADMINISTRACAO'])]
df_gov_pivot = df_gov.pivot_table(
    index='NOME_COMPANHIA', 
    columns='ORGAO_ADMINISTRACAO', 
    values='TOTAL_REMUNERACAO_ORGAO', 
    aggfunc='sum'
).fillna(0).reset_index()

# Filtra empresas que têm as duas informações
if 'DIRETORIA ESTATUTARIA' in df_gov_pivot.columns and 'CONSELHO DE ADMINISTRACAO' in df_gov_pivot.columns:
    df_gov_pivot = df_gov_pivot[(df_gov_pivot['DIRETORIA ESTATUTARIA'] > 0) & (df_gov_pivot['CONSELHO DE ADMINISTRACAO'] > 0)]
    
    # Calcular Rácio (Diretoria / Conselho)
    df_gov_pivot['Racio_Poder'] = df_gov_pivot['DIRETORIA ESTATUTARIA'] / df_gov_pivot['CONSELHO DE ADMINISTRACAO']
    
    # Adicionar formatações para o hover do gráfico
    df_gov_pivot['Diretoria_Formatado'] = df_gov_pivot['DIRETORIA ESTATUTARIA'].apply(formata_brl_int)
    df_gov_pivot['Conselho_Formatado'] = df_gov_pivot['CONSELHO DE ADMINISTRACAO'].apply(formata_brl_int)
    
    fig_gov = px.scatter(
        df_gov_pivot, 
        x='CONSELHO DE ADMINISTRACAO', 
        y='DIRETORIA ESTATUTARIA', 
        hover_name='NOME_COMPANHIA',
        hover_data={'CONSELHO DE ADMINISTRACAO': False, 'DIRETORIA ESTATUTARIA': False, 'Racio_Poder': ':.1f', 'Conselho_Formatado': True, 'Diretoria_Formatado': True},
        title="Remuneração: Conselho de Administração vs. Diretoria Estatutária",
        labels={'CONSELHO DE ADMINISTRACAO': 'Total Conselho (R$)', 'DIRETORIA ESTATUTARIA': 'Total Diretoria (R$)', 'Racio_Poder': 'Diretoria ganha X vezes mais', 'Conselho_Formatado': 'Conselho', 'Diretoria_Formatado': 'Diretoria'},
        opacity=0.7,
        size='Racio_Poder',
        size_max=30,
        color='Racio_Poder',
        color_continuous_scale='Turbo'
    )
    
    # Adicionar uma linha de igualdade (1:1) teórica (apenas visual, embora raro)
    max_val = max(df_gov_pivot['CONSELHO DE ADMINISTRACAO'].max(), df_gov_pivot['DIRETORIA ESTATUTARIA'].max())
    fig_gov.add_trace(go.Scatter(x=[0, max_val], y=[0, max_val], mode='lines', name='Equilíbrio 1:1', line=dict(dash='dash', color='gray')))
    
    st.plotly_chart(fig_gov, width='stretch')
else:
    st.info("Não há dados suficientes para comparar Conselho e Diretoria neste ano.")

st.markdown("---")

# ==========================================
# 3. GOLDEN PARACHUTES (Cessação e Pós-Emprego)
# ==========================================
st.subheader("3. Radar de Rescisões ('Golden Parachutes')")
st.markdown("""
Identifica empresas onde os pagamentos por rescisão (Cessação de Cargo e Pós-Emprego) representam uma parcela alarmante da remuneração total do órgão, um indicativo de alto risco moral para os investidores.
""")

df_ano['Rescisao_Total'] = df_ano['REM_CESSACAO_CARGO'].fillna(0) + df_ano['REM_POS_EMPREGO'].fillna(0)
df_ano['Perc_Rescisao'] = 0.0

mascara_rescisao = df_ano['TOTAL_REMUNERACAO_ORGAO'] > 0
df_ano.loc[mascara_rescisao, 'Perc_Rescisao'] = (df_ano.loc[mascara_rescisao, 'Rescisao_Total'] / df_ano.loc[mascara_rescisao, 'TOTAL_REMUNERACAO_ORGAO']) * 100

# Filtra apenas empresas com algum valor de rescisão relevante (ex: > 1%)
df_resc = df_ano[df_ano['Perc_Rescisao'] > 1.0].sort_values(by='Perc_Rescisao', ascending=False)

if not df_resc.empty:
    fig_resc = px.bar(
        df_resc.head(15),
        x='NOME_COMPANHIA',
        y='Perc_Rescisao',
        color='ORGAO_ADMINISTRACAO',
        title=f"Maior Peso de Rescisões na Remuneração Total (%) - Top 15 em {ano_selecionado}",
        labels={'NOME_COMPANHIA': 'Empresa', 'Perc_Rescisao': '% da Remuneração em Rescisões', 'ORGAO_ADMINISTRACAO': 'Órgão'},
        text_auto='.1f'
    )
    fig_resc.update_layout(yaxis_ticksuffix="%", margin=dict(t=40))
    st.plotly_chart(fig_resc, width='stretch')
    
    st.write("**Dados de Anomalias de Rescisão para Exportação:**")
    df_export_resc = df_resc[['NOME_COMPANHIA', 'ORGAO_ADMINISTRACAO', 'SETOR_ATIVIDADE', 'TOTAL_REMUNERACAO_ORGAO', 'Rescisao_Total', 'Perc_Rescisao']].copy()
    df_export_resc['TOTAL_REMUNERACAO_ORGAO'] = df_export_resc['TOTAL_REMUNERACAO_ORGAO'].apply(formata_brl_int)
    df_export_resc['Rescisao_Total'] = df_export_resc['Rescisao_Total'].apply(formata_brl_int)
    df_export_resc['Perc_Rescisao'] = df_export_resc['Perc_Rescisao'].round(2).astype(str) + '%'
    
    st.dataframe(df_export_resc, use_container_width=True)
    create_download_button(df_resc, f"golden_parachutes_{ano_selecionado}")
else:
    st.success("Não foram identificados pagamentos de rescisão significativos (>1% do total) para o filtro selecionado.")
