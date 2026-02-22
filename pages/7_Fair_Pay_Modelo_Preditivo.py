import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Bibliotecas de Machine Learning
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

# Importações dos utilitários
from utils import renderizar_sidebar_global, formata_brl_int, formata_abrev, create_download_button

st.set_page_config(layout="wide", page_title="Modelo Preditivo (Fair Pay)", page_icon="🤖")

if 'df_completo' not in st.session_state:
    st.warning("⚠️ Por favor, acesse a 'Página Inicial' primeiro para carregar a base de dados.")
    st.stop()

df_original = st.session_state['df_completo']
df = renderizar_sidebar_global(df_original)

if df.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()

st.header("🤖 Modelo Preditivo de Remuneração (IA)")
st.markdown("""
Esta página utiliza um algoritmo de **Machine Learning (Random Forest)** para aprender os padrões salariais do mercado (Setor, Estado, Tamanho da Diretoria, Controle Acionário). 
O modelo estima qual *deveria ser* a remuneração de uma empresa e calcula o **Índice de Desvio**: quem está sobrepagando (Overpaid) ou subpagando (Underpaid) seus executivos em relação ao "Salário Justo" estatístico.
""")

st.markdown("---")

# Filtro de Ano para o Modelo
anos_disponiveis = sorted(df['ANO_REFER'].unique(), reverse=True)
ano_selecionado = st.selectbox("Selecione o Ano para Treinar o Modelo e Analisar:", anos_disponiveis)

# Preparar os dados da Diretoria
df_modelo = df[(df['ANO_REFER'] == ano_selecionado) & 
               (df['ORGAO_ADMINISTRACAO'].str.contains('DIRETORIA', case=False, na=False))].copy()

# Remover valores zerados ou nulos que prejudicam a IA
df_modelo = df_modelo.dropna(subset=['REM_MAXIMA_INDIVIDUAL', 'REM_MEDIA_INDIVIDUAL', 'NUM_MEMBROS_TOTAL', 'SETOR_ATIVIDADE', 'UF_SEDE'])
df_modelo = df_modelo[(df_modelo['REM_MAXIMA_INDIVIDUAL'] > 0) & (df_modelo['REM_MEDIA_INDIVIDUAL'] > 0)]

if len(df_modelo) < 30:
    st.error(f"Dados insuficientes para treinar o modelo de IA no ano de {ano_selecionado}.")
    st.stop()

# ==========================================
# 1. TREINAMENTO DO MODELO (MACHINE LEARNING)
# ==========================================
# Variáveis que a IA vai usar para aprender (Features)
features = ['SETOR_ATIVIDADE', 'UF_SEDE', 'CONTROLE_ACIONARIO', 'NUM_MEMBROS_TOTAL']

X = df_modelo[features]
y_max = df_modelo['REM_MAXIMA_INDIVIDUAL'] # Alvo 1: Maior Salário (CEO)
y_med = df_modelo['REM_MEDIA_INDIVIDUAL']  # Alvo 2: Média da Diretoria

# Pipeline de Transformação (Converte texto em números para a IA entender)
preprocessor = ColumnTransformer(
    transformers=[
        ('cat', OneHotEncoder(handle_unknown='ignore'), ['SETOR_ATIVIDADE', 'UF_SEDE', 'CONTROLE_ACIONARIO'])
    ], remainder='passthrough'
)

# Criando as florestas aleatórias
modelo_max = Pipeline(steps=[('preprocessor', preprocessor), ('regressor', RandomForestRegressor(n_estimators=100, random_state=42))])
modelo_med = Pipeline(steps=[('preprocessor', preprocessor), ('regressor', RandomForestRegressor(n_estimators=100, random_state=42))])

# Treinamento da IA
with st.spinner("Treinando algoritmo de Machine Learning..."):
    modelo_max.fit(X, y_max)
    modelo_med.fit(X, y_med)

# Fazendo as predições para a base atual
df_modelo['Predito_Maxima'] = modelo_max.predict(X)
df_modelo['Predito_Media'] = modelo_med.predict(X)

# Calculando o Índice de Desvio (%)
# Desvio = (Real - Esperado) / Esperado
df_modelo['Desvio_Maxima_Perc'] = ((df_modelo['REM_MAXIMA_INDIVIDUAL'] - df_modelo['Predito_Maxima']) / df_modelo['Predito_Maxima']) * 100
df_modelo['Desvio_Media_Perc'] = ((df_modelo['REM_MEDIA_INDIVIDUAL'] - df_modelo['Predito_Media']) / df_modelo['Predito_Media']) * 100

st.success(f"✅ Modelo treinado com sucesso utilizando dados de {len(df_modelo)} empresas.")

# ==========================================
# 2. VISUALIZAÇÃO: REAL VS. PREDITO
# ==========================================
st.subheader("1. Dispersão de Mercado: Remuneração Real vs. Esperada (CEO)")
st.markdown("A linha tracejada representa o **Salário Justo (Fair Pay)** estimado pela IA. Bolhas **acima da linha** pagam mais que o esperado pelo seu perfil; bolhas **abaixo**, pagam menos.")

# Gráfico de Dispersão (Scatter Plot)
fig_scatter = px.scatter(
    df_modelo, 
    x='Predito_Maxima', 
    y='REM_MAXIMA_INDIVIDUAL',
    color='SETOR_ATIVIDADE',
    hover_name='NOME_COMPANHIA',
    hover_data={
        'Predito_Maxima': ':,.0f', 
        'REM_MAXIMA_INDIVIDUAL': ':,.0f', 
        'Desvio_Maxima_Perc': ':.1f'
    },
    labels={
        'Predito_Maxima': 'Remuneração Estimada pela IA (R$)',
        'REM_MAXIMA_INDIVIDUAL': 'Remuneração Real Paga (R$)',
        'SETOR_ATIVIDADE': 'Setor',
        'Desvio_Maxima_Perc': 'Desvio (%)'
    },
    title="Análise de Anomalias de Remuneração Máxima"
)

# Adiciona a linha de 45 graus (Linha de Preço Justo)
max_limit = max(df_modelo['Predito_Maxima'].max(), df_modelo['REM_MAXIMA_INDIVIDUAL'].max())
fig_scatter.add_trace(go.Scatter(
    x=[0, max_limit], y=[0, max_limit], 
    mode='lines', name='Linha Justa (IA)', 
    line=dict(dash='dash', color='black')
))

fig_scatter.update_layout(height=600)
st.plotly_chart(fig_scatter, use_container_width=True)

# ==========================================
# 3. RANKING DE DESVIOS (ANOMALIAS)
# ==========================================
st.subheader("2. Ranking de Anomalias (Overpaid vs Underpaid)")
col1, col2 = st.columns(2)

df_overpaid = df_modelo.sort_values(by='Desvio_Maxima_Perc', ascending=False).head(10)
df_underpaid = df_modelo.sort_values(by='Desvio_Maxima_Perc', ascending=True).head(10)

with col1:
    st.markdown("🔴 **Top 10 Maior Desvio Positivo (Pagam ACIMA do esperado)**")
    fig_over = px.bar(
        df_overpaid, x='Desvio_Maxima_Perc', y='NOME_COMPANHIA', orientation='h',
        text_auto='.1f', color_discrete_sequence=['#EF553B'],
        labels={'Desvio_Maxima_Perc': 'Desvio (%)', 'NOME_COMPANHIA': ''}
    )
    fig_over.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_over, use_container_width=True)

with col2:
    st.markdown("🔵 **Top 10 Maior Desvio Negativo (Pagam ABAIXO do esperado)**")
    fig_under = px.bar(
        df_underpaid, x='Desvio_Maxima_Perc', y='NOME_COMPANHIA', orientation='h',
        text_auto='.1f', color_discrete_sequence=['#636EFA'],
        labels={'Desvio_Maxima_Perc': 'Desvio (%)', 'NOME_COMPANHIA': ''}
    )
    fig_under.update_layout(yaxis={'categoryorder':'total descending'})
    st.plotly_chart(fig_under, use_container_width=True)

# ==========================================
# 4. SIMULADOR DE MERCADO (O SEU PRÓPRIO CENÁRIO)
# ==========================================
st.markdown("---")
st.subheader("🧪 3. Simulador de Inteligência Artificial")
st.markdown("Preencha as características de uma empresa fictícia ou da sua empresa para ver qual deveria ser o salário de mercado segundo a IA.")

with st.form("form_simulador"):
    col_sim1, col_sim2, col_sim3, col_sim4 = st.columns(4)
    with col_sim1:
        sim_setor = st.selectbox("Setor:", df_modelo['SETOR_ATIVIDADE'].unique())
    with col_sim2:
        sim_uf = st.selectbox("UF:", df_modelo['UF_SEDE'].unique())
    with col_sim3:
        sim_controle = st.selectbox("Controle:", df_modelo['CONTROLE_ACIONARIO'].unique())
    with col_sim4:
        sim_membros = st.number_input("Tamanho da Diretoria:", min_value=1, max_value=30, value=5)
    
    submit = st.form_submit_button("Estimar Remuneração Justa")

if submit:
    # Criar um DataFrame com a entrada do usuário
    novo_dado = pd.DataFrame({
        'SETOR_ATIVIDADE': [sim_setor],
        'UF_SEDE': [sim_uf],
        'CONTROLE_ACIONARIO': [sim_controle],
        'NUM_MEMBROS_TOTAL': [sim_membros]
    })
    
    # Fazer a predição
    est_max = modelo_max.predict(novo_dado)[0]
    est_med = modelo_med.predict(novo_dado)[0]
    
    st.info(f"💡 **Resultado da IA para uma empresa com este perfil em {ano_selecionado}:**")
    col_res1, col_res2 = st.columns(2)
    col_res1.metric("Maior Remuneração Estimada (CEO)", f"R$ {est_max:,.2f}")
    col_res2.metric("Remuneração Média Estimada", f"R$ {est_med:,.2f}")

st.markdown("---")
st.write("**Exportar Base de Desvios para Auditoria**")
df_export = df_modelo[['NOME_COMPANHIA', 'SETOR_ATIVIDADE', 'REM_MAXIMA_INDIVIDUAL', 'Predito_Maxima', 'Desvio_Maxima_Perc', 'REM_MEDIA_INDIVIDUAL', 'Predito_Media', 'Desvio_Media_Perc']]
create_download_button(df_export, f"auditoria_desvios_ia_{ano_selecionado}")
