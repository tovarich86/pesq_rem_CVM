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

st.header("🤖 Modelo Preditivo de Remuneração (Alta Significância)")
st.markdown("""
Este modelo utiliza **Machine Learning (Random Forest Regressor)** rigorosamente parametrizado. 
Aplicamos **Validação Cruzada (K-Fold)** e **Transformação Logarítmica** para garantir que a curva de aprendizagem respeita o comportamento exponencial dos salários corporativos, mitigando a distorção causada por *outliers* extremos.
""")

st.markdown("---")

# Filtro de Ano para o Modelo
anos_disponiveis = sorted(df['ANO_REFER'].unique(), reverse=True)
ano_selecionado = st.selectbox("Selecione o Ano Base para o Treinamento do Modelo:", anos_disponiveis)

df_modelo = df[(df['ANO_REFER'] == ano_selecionado) & 
               (df['ORGAO_ADMINISTRACAO'].str.contains('DIRETORIA', case=False, na=False))].copy()

df_modelo = df_modelo.dropna(subset=['REM_MAXIMA_INDIVIDUAL', 'REM_MEDIA_INDIVIDUAL', 'SETOR_ATIVIDADE'])
df_modelo = df_modelo[(df_modelo['REM_MAXIMA_INDIVIDUAL'] > 0) & (df_modelo['REM_MEDIA_INDIVIDUAL'] > 0)]

if len(df_modelo) < 30:
    st.error(f"Amostra estatística insuficiente (menos de 30 empresas válidas) para o ano de {ano_selecionado}.")
    st.stop()

# ==========================================
# 1. FEATURE ENGINEERING (ENGENHARIA DE DADOS)
# ==========================================

# Risco / Pay Mix
df_modelo['Rem_Fixa_Total'] = df_modelo[['REM_FIXA_SALARIO', 'REM_FIXA_BENEFICIOS', 'REM_FIXA_COMITES', 'REM_FIXA_OUTROS', 'REM_POS_EMPREGO', 'REM_CESSACAO_CARGO']].sum(axis=1)
df_modelo['Rem_Var_Curto_Prazo'] = df_modelo[['REM_VAR_BONUS', 'REM_VAR_PLR', 'REM_VAR_REUNIOES', 'REM_VAR_COMISSOES', 'REM_VAR_OUTROS']].sum(axis=1)
df_modelo['Rem_Var_Longo_Prazo'] = df_modelo['REM_ACOES_BLOCO3'].fillna(0)

df_modelo['Total_Mix'] = df_modelo['Rem_Fixa_Total'] + df_modelo['Rem_Var_Curto_Prazo'] + df_modelo['Rem_Var_Longo_Prazo']
df_modelo['Total_Mix'] = df_modelo['Total_Mix'].replace(0, 1) # Proteção matemática contra divisão por zero

df_modelo['Perc_Fixo'] = df_modelo['Rem_Fixa_Total'] / df_modelo['Total_Mix']
df_modelo['Perc_Var_CP'] = df_modelo['Rem_Var_Curto_Prazo'] / df_modelo['Total_Mix']
df_modelo['Perc_Var_LP'] = df_modelo['Rem_Var_Longo_Prazo'] / df_modelo['Total_Mix']

# Variáveis de Escala (Total_Funcionários e Faturamento obtidos no nosso novo update_data.py)
if 'TOTAL_FUNCIONARIOS' not in df_modelo.columns: df_modelo['TOTAL_FUNCIONARIOS'] = np.nan
if 'FATURAMENTO_BRUTO' not in df_modelo.columns: df_modelo['FATURAMENTO_BRUTO'] = np.nan

# ==========================================
# 2. MACHINE LEARNING (TREINAMENTO DE ALTO NÍVEL)
# ==========================================
features_categoricas = ['SETOR_ATIVIDADE', 'UF_SEDE', 'CONTROLE_ACIONARIO']
features_numericas = ['NUM_MEMBROS_TOTAL', 'TOTAL_FUNCIONARIOS', 'FATURAMENTO_BRUTO', 'Perc_Fixo', 'Perc_Var_CP', 'Perc_Var_LP']

features = features_categoricas + features_numericas
X = df_modelo[features]

# Transformação Exponencial para estabilizar a variância (Maior Significância Estatística)
y_max = np.log1p(df_modelo['REM_MAXIMA_INDIVIDUAL']) 
y_med = np.log1p(df_modelo['REM_MEDIA_INDIVIDUAL'])

# Pipeline Robusto
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

# Random Forest Otimizada para evitar Overfitting (min_samples_leaf=2)
modelo_max = Pipeline(steps=[
    ('preprocessor', preprocessor), 
    ('regressor', RandomForestRegressor(n_estimators=200, random_state=42, max_depth=15, min_samples_leaf=2, bootstrap=True))
])

modelo_med = Pipeline(steps=[
    ('preprocessor', preprocessor), 
    ('regressor', RandomForestRegressor(n_estimators=200, random_state=42, max_depth=15, min_samples_leaf=2, bootstrap=True))
])

with st.spinner("Realizando Validação Cruzada (K-Fold) e treinando o Modelo..."):
    # Validação Cruzada para extrair o grau de confiança (R²)
    cv_scores_max = cross_val_score(modelo_max, X, y_max, cv=5, scoring='r2')
    
    # Treino final sobre todos os dados
    modelo_max.fit(X, y_max)
    modelo_med.fit(X, y_med)

# Reverter Log para valores em Reais (R$)
df_modelo['Predito_Maxima'] = np.expm1(modelo_max.predict(X))
df_modelo['Predito_Media'] = np.expm1(modelo_med.predict(X))

# Índice de Desvio: (Real - Predito) / Predito
df_modelo['Desvio_Maxima_Perc'] = ((df_modelo['REM_MAXIMA_INDIVIDUAL'] - df_modelo['Predito_Maxima']) / df_modelo['Predito_Maxima']) * 100

st.success(f"✅ Treinamento concluído. Validação Cruzada R² (Confiança da IA): **{cv_scores_max.mean():.1%}** (Para dados de RH e Finanças, valores acima de 40% já indicam alta significância).")

# ==========================================
# 3. VISUALIZAÇÃO DE RESULTADOS E ANOMALIAS
# ==========================================
st.subheader("1. Dispersão de Mercado (Real vs. Salário Justo Justificado)")
st.markdown("A linha tracejada representa o Salário Justo calculado pelo Modelo. As bolhas com cores mais quentes (amarelo) possuem maior **Prêmio de Risco** (% em Ações).")

fig_scatter = px.scatter(
    df_modelo, x='Predito_Maxima', y='REM_MAXIMA_INDIVIDUAL', color='Perc_Var_LP',
    hover_name='NOME_COMPANHIA',
    hover_data={'Predito_Maxima': ':,.0f', 'REM_MAXIMA_INDIVIDUAL': ':,.0f', 'Desvio_Maxima_Perc': ':.1f', 'Perc_Var_LP': ':.1%'},
    labels={'Predito_Maxima': 'Estimado pela IA (R$)', 'REM_MAXIMA_INDIVIDUAL': 'Real Pago (R$)', 'Perc_Var_LP': '% Ações (Risco)'},
    color_continuous_scale='Turbo',
    opacity=0.8
)

max_limit = max(df_modelo['Predito_Maxima'].max(), df_modelo['REM_MAXIMA_INDIVIDUAL'].max())
fig_scatter.add_trace(go.Scatter(x=[0, max_limit], y=[0, max_limit], mode='lines', name='Linha de Equilíbrio (Fair Pay)', line=dict(dash='dash', color='white')))
fig_scatter.update_layout(height=600, template="plotly_dark")
st.plotly_chart(fig_scatter, use_container_width=True)

st.subheader("2. Deteção de Anomalias (Desvios Mais Acentuados)")
col1, col2 = st.columns(2)
df_overpaid = df_modelo.sort_values(by='Desvio_Maxima_Perc', ascending=False).head(10)
df_underpaid = df_modelo.sort_values(by='Desvio_Maxima_Perc', ascending=True).head(10)

with col1:
    st.markdown("🔴 **Top 10 Maior Pagamento Acima do Padrão (Overpaid)**")
    fig_over = px.bar(df_overpaid, x='Desvio_Maxima_Perc', y='NOME_COMPANHIA', orientation='h', text_auto='.1f', color_discrete_sequence=['#ff4b4b'])
    fig_over.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_over, use_container_width=True)

with col2:
    st.markdown("🔵 **Top 10 Maior Pagamento Abaixo do Padrão (Underpaid)**")
    fig_under = px.bar(df_underpaid, x='Desvio_Maxima_Perc', y='NOME_COMPANHIA', orientation='h', text_auto='.1f', color_discrete_sequence=['#4b8bff'])
    fig_under.update_layout(yaxis={'categoryorder':'total descending'})
    st.plotly_chart(fig_under, use_container_width=True)

# ==========================================
# 4. SIMULADOR ESTRATÉGICO
# ==========================================
st.markdown("---")
st.subheader("🧪 3. Simulador de Salário Justo (Machine Learning)")

with st.form("form_simulador"):
    st.markdown("**A. Complexidade e Escala (Scale Effect)**")
    col_s1, col_s2, col_s3 = st.columns(3)
    sim_setor = col_s1.selectbox("Setor Econômico:", df_modelo['SETOR_ATIVIDADE'].unique())
    sim_uf = col_s2.selectbox("Sede (UF):", df_modelo['UF_SEDE'].unique())
    sim_membros = col_s3.number_input("Tamanho da Diretoria:", min_value=1, max_value=30, value=5)
    
    col_s4, col_s5 = st.columns(2)
    sim_func = col_s4.number_input("Total de Funcionários:", min_value=1, value=int(df_modelo['TOTAL_FUNCIONARIOS'].median() if pd.notna(df_modelo['TOTAL_FUNCIONARIOS'].median()) else 1000))
    sim_fat = col_s5.number_input("Faturamento Bruto Anual (R$):", min_value=1.0, value=float(df_modelo['FATURAMENTO_BRUTO'].median() if pd.notna(df_modelo['FATURAMENTO_BRUTO'].median()) else 500000000.0), step=50000000.0)

    st.markdown("**B. Estrutura de Incentivos e Risco (Risk Premium)**")
    col_r1, col_r2, col_r3 = st.columns(3)
    sim_p_fixo = col_r1.slider("% Fixo (Salário Base)", 0, 100, 30)
    sim_p_cp = col_r2.slider("% Variável Curto Prazo (Bônus/PLR)", 0, 100, 40)
    sim_p_lp = col_r3.slider("% Variável Longo Prazo (Ações)", 0, 100, 30)
    
    submit = st.form_submit_button("Processar Estimativa de Remuneração")

if submit:
    if (sim_p_fixo + sim_p_cp + sim_p_lp) != 100:
        st.error("⚠️ Erro Matemático: A soma dos percentuais da estrutura de incentivos deve ser exatamente 100%.")
    else:
        novo_dado = pd.DataFrame({
            'SETOR_ATIVIDADE': [sim_setor], 'UF_SEDE': [sim_uf], 'CONTROLE_ACIONARIO': ['PRIVADO'], 
            'NUM_MEMBROS_TOTAL': [sim_membros], 'TOTAL_FUNCIONARIOS': [sim_func], 'FATURAMENTO_BRUTO': [sim_fat],
            'Perc_Fixo': [sim_p_fixo/100], 'Perc_Var_CP': [sim_p_cp/100], 'Perc_Var_LP': [sim_p_lp/100]
        })
        
        est_max = np.expm1(modelo_max.predict(novo_dado)[0])
        est_med = np.expm1(modelo_med.predict(novo_dado)[0])
        
        st.info(f"💡 **Predição Estatística Concluída (Base {ano_selecionado})**")
        col_res1, col_res2 = st.columns(2)
        col_res1.metric("Máxima Recomendada (CEO)", f"R$ {est_max:,.2f}")
        col_res2.metric("Média da Diretoria Recomendada", f"R$ {est_med:,.2f}")

st.markdown("---")
st.write("**Exportação para Auditoria do Modelo:**")
df_export = df_modelo[['NOME_COMPANHIA', 'SETOR_ATIVIDADE', 'REM_MAXIMA_INDIVIDUAL', 'Predito_Maxima', 'Desvio_Maxima_Perc']]
create_download_button(df_export, f"auditoria_desvios_ia_{ano_selecionado}")
