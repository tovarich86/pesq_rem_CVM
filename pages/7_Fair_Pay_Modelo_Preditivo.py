import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Bibliotecas de Machine Learning de Alta Significância
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.model_selection import cross_val_score

# Importações dos utilitários
from utils import renderizar_sidebar_global, formata_brl_int, formata_abrev, create_download_button

st.set_page_config(layout="wide", page_title="Modelo Preditivo (Fair Pay)", page_icon="🤖")

if 'df_completo' not in st.session_state:
    st.warning("⚠️ Por favor, aceda à 'Página Inicial' primeiro para carregar a base de dados.")
    st.stop()

df_original = st.session_state['df_completo']
df = renderizar_sidebar_global(df_original)

if df.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()

st.header("🤖 Inteligência Artificial (Explainable AI & Fair Pay)")
st.markdown("""
Este modelo avançado ajusta-se automaticamente ao tamanho da amostra filtrada. Escolha a métrica que deseja prever e a IA abrirá a sua "caixa negra", mostrando o peso matemático de cada variável na definição da Remuneração Justa.
""")

st.markdown("---")

# ==========================================
# SELETORES GLOBAIS DA IA
# ==========================================
col_filtros1, col_filtros2 = st.columns(2)

with col_filtros1:
    anos_disponiveis = sorted(df['ANO_REFER'].unique(), reverse=True)
    ano_selecionado = st.selectbox("Selecione o Ano Base para o Treinamento:", anos_disponiveis)

with col_filtros2:
    alvo_selecionado = st.selectbox(
        "Selecione a Métrica Alvo para a IA prever:",
        ["Maior Remuneração (CEO)", "Remuneração Média da Diretoria", "Total da Diretoria"]
    )

dict_alvos = {
    "Maior Remuneração (CEO)": "REM_MAXIMA_INDIVIDUAL",
    "Remuneração Média da Diretoria": "REM_MEDIA_INDIVIDUAL",
    "Total da Diretoria": "TOTAL_REMUNERACAO_ORGAO"
}
coluna_alvo = dict_alvos[alvo_selecionado]

# Filtra apenas a Diretoria e o ano
df_modelo = df[(df['ANO_REFER'] == ano_selecionado) & 
               (df['ORGAO_ADMINISTRACAO'].str.contains('DIRETORIA', case=False, na=False))].copy()

# Remove Nulos do Alvo
df_modelo = df_modelo.dropna(subset=[coluna_alvo, 'SETOR_ATIVIDADE'])
df_modelo = df_modelo[df_modelo[coluna_alvo] > 0]

# --- AJUSTE ELÁSTICO DE AMOSTRA ---
n_amostras = len(df_modelo)
if n_amostras < 10:
    st.error(f"⚠️ Amostra excessivamente pequena ({n_amostras} empresas). A IA exige um mínimo de 10 empresas para encontrar padrões. Se está a usar um filtro de setor, tente limpá-lo na barra lateral.")
    st.stop()
elif n_amostras < 30:
    st.warning(f"⚠️ Amostra pequena ({n_amostras} empresas). A IA ativou o modo de Baixa Complexidade. O nível de significância será reduzido para evitar *overfitting*.")
    cv_folds = min(3, n_amostras // 3)
    min_leaf = 1
else:
    cv_folds = 5
    min_leaf = 2

# ==========================================
# 1. FEATURE ENGINEERING (ENGENHARIA DE DADOS)
# ==========================================
# Risco / Pay Mix
df_modelo['Rem_Fixa_Total'] = df_modelo[['REM_FIXA_SALARIO', 'REM_FIXA_BENEFICIOS', 'REM_FIXA_COMITES', 'REM_FIXA_OUTROS', 'REM_POS_EMPREGO', 'REM_CESSACAO_CARGO']].sum(axis=1)
df_modelo['Rem_Var_Curto_Prazo'] = df_modelo[['REM_VAR_BONUS', 'REM_VAR_PLR', 'REM_VAR_REUNIOES', 'REM_VAR_COMISSOES', 'REM_VAR_OUTROS']].sum(axis=1)
df_modelo['Rem_Var_Longo_Prazo'] = df_modelo['REM_ACOES_BLOCO3'].fillna(0)

df_modelo['Total_Mix'] = df_modelo['Rem_Fixa_Total'] + df_modelo['Rem_Var_Curto_Prazo'] + df_modelo['Rem_Var_Longo_Prazo']
df_modelo['Total_Mix'] = df_modelo['Total_Mix'].replace(0, 1)

df_modelo['Perc_Fixo'] = df_modelo['Rem_Fixa_Total'] / df_modelo['Total_Mix']
df_modelo['Perc_Var_CP'] = df_modelo['Rem_Var_Curto_Prazo'] / df_modelo['Total_Mix']
df_modelo['Perc_Var_LP'] = df_modelo['Rem_Var_Longo_Prazo'] / df_modelo['Total_Mix']

if 'TOTAL_FUNCIONARIOS' not in df_modelo.columns: df_modelo['TOTAL_FUNCIONARIOS'] = np.nan
if 'FATURAMENTO_BRUTO' not in df_modelo.columns: df_modelo['FATURAMENTO_BRUTO'] = np.nan

# ==========================================
# 2. MACHINE LEARNING (TREINAMENTO DINÂMICO)
# ==========================================
features_categoricas = ['SETOR_ATIVIDADE', 'UF_SEDE', 'CONTROLE_ACIONARIO']
features_numericas = ['NUM_MEMBROS_TOTAL', 'TOTAL_FUNCIONARIOS', 'FATURAMENTO_BRUTO', 'Perc_Fixo', 'Perc_Var_CP', 'Perc_Var_LP']

features = features_categoricas + features_numericas
X = df_modelo[features]
y = np.log1p(df_modelo[coluna_alvo])

numeric_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])

categorical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='most_frequent')),
    ('onehot', OneHotEncoder(handle_unknown='ignore'))
])

preprocessor = ColumnTransformer(
    transformers=[
        ('num', numeric_transformer, features_numericas),
        ('cat', categorical_transformer, features_categoricas)
    ])

modelo = Pipeline(steps=[
    ('preprocessor', preprocessor), 
    ('regressor', RandomForestRegressor(n_estimators=150, random_state=42, max_depth=10, min_samples_leaf=min_leaf, bootstrap=True))
])

with st.spinner(f"Treinando IA para {alvo_selecionado}..."):
    if cv_folds >= 2:
        cv_scores = cross_val_score(modelo, X, y, cv=cv_folds, scoring='r2')
        confianca = cv_scores.mean()
    else:
        confianca = "N/A (Amostra Mínima)"
        
    modelo.fit(X, y)

df_modelo['Predito'] = np.expm1(modelo.predict(X))
df_modelo['Desvio_Perc'] = ((df_modelo[coluna_alvo] - df_modelo['Predito']) / df_modelo['Predito']) * 100

st.success(f"✅ Modelo ajustado em **{n_amostras} empresas**. Significância Estatística (R² da Validação Cruzada): **{confianca if isinstance(confianca, str) else f'{confianca:.1%}'}**.")

# ==========================================
# 3. EXPLAINABLE AI (IMPORTÂNCIA DAS VARIÁVEIS)
# ==========================================
st.subheader("1. O que impacta a Equação da Remuneração? (Feature Importance)")
st.markdown("A Inteligência Artificial abre a sua lógica para explicar **quais as variáveis que têm maior poder preditivo** sobre a remuneração escolhida, contribuindo para a variância (R²).")

# Extraindo pesos da IA
cat_encoder = preprocessor.named_transformers_['cat'].named_steps['onehot']
cat_features = cat_encoder.get_feature_names_out(features_categoricas)
todas_features = list(features_numericas) + list(cat_features)
importancias = modelo.named_steps['regressor'].feature_importances_

df_imp = pd.DataFrame({'Feature': todas_features, 'Importancia': importancias})

# Agrupando as sub-categorias One-Hot de volta aos grupos originais
def agrupar_feature(nome):
    if 'SETOR_ATIVIDADE' in nome: return 'Efeito Setorial'
    if 'UF_SEDE' in nome: return 'Custo de Região (UF)'
    if 'CONTROLE_ACIONARIO' in nome: return 'Controle (Estatizada vs Privada)'
    if nome == 'NUM_MEMBROS_TOTAL': return 'Tamanho da Diretoria'
    if nome == 'TOTAL_FUNCIONARIOS': return 'Escala: Nº de Funcionários'
    if nome == 'FATURAMENTO_BRUTO': return 'Escala: Faturamento Bruto'
    if nome == 'Perc_Fixo': return 'Prêmio Risco: % Fixo'
    if nome == 'Perc_Var_CP': return 'Prêmio Risco: % Bônus'
    if nome == 'Perc_Var_LP': return 'Prêmio Risco: % Ações'
    return nome

df_imp['Grupo'] = df_imp['Feature'].apply(agrupar_feature)
df_imp_group = df_imp.groupby('Grupo')['Importancia'].sum().reset_index().sort_values(by='Importancia', ascending=True)

fig_imp = px.bar(
    df_imp_group, x='Importancia', y='Grupo', orientation='h', 
    text_auto='.1%', color='Importancia', color_continuous_scale='Mint'
)
fig_imp.update_layout(xaxis_tickformat='.0%', xaxis_title="Peso da Variável na Decisão do Modelo (%)", yaxis_title="")
st.plotly_chart(fig_imp, use_container_width=True)

# ==========================================
# 4. DISPERSÃO E ANOMALIAS
# ==========================================
st.markdown("---")
st.subheader(f"2. Dispersão de Mercado: {alvo_selecionado}")

fig_scatter = px.scatter(
    df_modelo, x='Predito', y=coluna_alvo, color='Perc_Var_LP',
    hover_name='NOME_COMPANHIA',
    hover_data={'Predito': ':,.0f', coluna_alvo: ':,.0f', 'Desvio_Perc': ':.1f', 'Perc_Var_LP': ':.1%'},
    labels={'Predito': 'Salário Justo da IA (R$)', coluna_alvo: 'Real Pago (R$)', 'Perc_Var_LP': '% Ações (Risco)'},
    color_continuous_scale='Turbo', opacity=0.8
)

max_limit = max(df_modelo['Predito'].max(), df_modelo[coluna_alvo].max())
fig_scatter.add_trace(go.Scatter(x=[0, max_limit], y=[0, max_limit], mode='lines', name='Linha de Equilíbrio', line=dict(dash='dash', color='white')))
fig_scatter.update_layout(height=600, template="plotly_dark")
st.plotly_chart(fig_scatter, use_container_width=True)

col1, col2 = st.columns(2)
df_overpaid = df_modelo.sort_values(by='Desvio_Perc', ascending=False).head(10)
df_underpaid = df_modelo.sort_values(by='Desvio_Perc', ascending=True).head(10)

with col1:
    st.markdown("🔴 **Top 10 Maior Pagamento Acima do Padrão (Overpaid)**")
    fig_over = px.bar(df_overpaid, x='Desvio_Perc', y='NOME_COMPANHIA', orientation='h', text_auto='.1f', color_discrete_sequence=['#ff4b4b'])
    fig_over.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_over, use_container_width=True)

with col2:
    st.markdown("🔵 **Top 10 Maior Pagamento Abaixo do Padrão (Underpaid)**")
    fig_under = px.bar(df_underpaid, x='Desvio_Perc', y='NOME_COMPANHIA', orientation='h', text_auto='.1f', color_discrete_sequence=['#4b8bff'])
    fig_under.update_layout(yaxis={'categoryorder':'total descending'})
    st.plotly_chart(fig_under, use_container_width=True)

st.markdown("---")
st.write("**Exportação para Auditoria:**")
df_export = df_modelo[['NOME_COMPANHIA', 'SETOR_ATIVIDADE', coluna_alvo, 'Predito', 'Desvio_Perc']]
create_download_button(df_export, f"auditoria_desvios_ia_{ano_selecionado}")
