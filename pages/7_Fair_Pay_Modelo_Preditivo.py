import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.model_selection import cross_val_score

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
st.markdown("Este modelo aprende os padrões salariais de centenas de empresas e cria uma **matemática do Salário Justo** baseada no tamanho, setor e risco do pacote de remuneração.")

# --- GUIA EDUCATIVO GERAL ---
with st.expander("📖 Como interpretar os resultados desta Inteligência Artificial? (Clique para ler)"):
    st.markdown("""
    **1. O que é a Linha de Equilíbrio (Fair Pay)?** A Inteligência Artificial calculou qual *deveria ser* o salário de uma empresa olhando para os seus concorrentes de mesmo tamanho e perfil. Se uma empresa está acima da linha (Overpaid), paga mais do que a matemática de mercado exige. Se está abaixo (Underpaid), paga menos.

    **2. O que é o "Prêmio de Risco"?** A teoria financeira prova que executivos preferem o "dinheiro certo" (salário fixo). Se uma empresa decide pagar o CEO majoritariamente em **Ações** ou **Bônus de Metas Difíceis** (alto risco de ele não receber nada), ela precisa prometer um pacote total *muito maior* para compensar esse risco. A IA sabe disso e aumenta a linha de "Salário Justo" automaticamente para empresas que usam muitas ações.

    **3. O que é a Significância (R²)?** É a nota de confiança da IA (de 0% a 100%). Um R² de 40%, por exemplo, significa que 40% da variação gigantesca de salários no mercado pode ser explicada matematicamente por este nosso modelo. Em dados humanos (RH), qualquer R² acima de 30% já é considerado excelente para prever tendências!
    """)

st.markdown("---")

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

df_modelo = df[(df['ANO_REFER'] == ano_selecionado) & 
               (df['ORGAO_ADMINISTRACAO'].str.contains('DIRETORIA', case=False, na=False))].copy()

df_modelo = df_modelo.dropna(subset=[coluna_alvo, 'SETOR_ATIVIDADE'])
df_modelo = df_modelo[df_modelo[coluna_alvo] > 0]

# ==========================================
# MOTOR ELÁSTICO (AJUSTE À AMOSTRA)
# ==========================================
n_amostras = len(df_modelo)
if n_amostras < 10:
    st.error(f"⚠️ Amostra excessivamente pequena ({n_amostras} empresas). A IA exige um mínimo de 10 empresas. Limpe alguns filtros na barra lateral.")
    st.stop()
elif n_amostras < 30:
    st.warning(f"⚠️ Amostra pequena ({n_amostras} empresas). A IA ativou o modo **Baixa Complexidade**: Variáveis geográficas e setoriais foram desativadas para evitar o colapso estatístico (Overfitting).")
    cv_folds = min(3, n_amostras // 4)
    min_leaf = 3
    max_depth = 3
    usar_categoricas = False 
else:
    cv_folds = 5
    min_leaf = 2
    max_depth = 10
    usar_categoricas = True

# Engenharia de Dados (Risco)
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
# MACHINE LEARNING PIPELINE
# ==========================================
features_numericas = ['NUM_MEMBROS_TOTAL', 'TOTAL_FUNCIONARIOS', 'FATURAMENTO_BRUTO', 'Perc_Fixo', 'Perc_Var_CP', 'Perc_Var_LP']
features_categoricas = ['SETOR_ATIVIDADE', 'UF_SEDE', 'CONTROLE_ACIONARIO'] if usar_categoricas else []

features = features_categoricas + features_numericas
X = df_modelo[features]
y = np.log1p(df_modelo[coluna_alvo])

numeric_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])

transformers_list = [('num', numeric_transformer, features_numericas)]

if usar_categoricas:
    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])
    transformers_list.append(('cat', categorical_transformer, features_categoricas))

preprocessor = ColumnTransformer(transformers=transformers_list)

modelo = Pipeline(steps=[
    ('preprocessor', preprocessor), 
    ('regressor', RandomForestRegressor(n_estimators=150, random_state=42, max_depth=max_depth, min_samples_leaf=min_leaf, bootstrap=True))
])

with st.spinner(f"Treinando IA e calculando Variância (R²)..."):
    if cv_folds >= 2:
        cv_scores = cross_val_score(modelo, X, y, cv=cv_folds, scoring='r2')
        confianca = cv_scores.mean()
    else:
        confianca = None
        
    modelo.fit(X, y)

df_modelo['Predito'] = np.expm1(modelo.predict(X))
df_modelo['Desvio_Perc'] = ((df_modelo[coluna_alvo] - df_modelo['Predito']) / df_modelo['Predito']) * 100

if confianca is not None:
    if confianca < 0:
        st.error(f"📉 **Confiança da IA (R²): {confianca:.1%}** | O mercado selecionado é caótico. As empresas pagam valores tão discrepantes que a IA não conseguiu encontrar uma regra matemática óbvia.")
    elif confianca < 0.3:
        st.warning(f"📊 **Confiança da IA (R²): {confianca:.1%}** | Confiança Moderada. A IA encontrou tendências, mas existem muitos casos "fora da curva" nesta amostra.")
    else:
        st.success(f"✅ **Confiança da IA (R²): {confianca:.1%}** | Alta Precisão! A IA mapeou com clareza a regra de pagamento deste grupo de {n_amostras} empresas.")

# ==========================================
# EXPLAINABLE AI (IMPORTÂNCIA DAS VARIÁVEIS)
# ==========================================
st.markdown("---")
st.subheader("1. O que mais pesou na decisão da Inteligência Artificial? (Poder Preditivo)")

# --- TEXTO EDUCATIVO DO GRÁFICO DE IMPORTÂNCIA ---
st.info("""
**Como ler este gráfico?** Se a barra 'Prêmio Risco: % Ações' tiver **40%**, isso significa que, na hora de decidir o Salário Justo de um executivo, a IA baseou 40% da sua decisão apenas olhando para a quantidade de ações que ele recebe. As variáveis no topo são as que mais justificam as diferenças salariais entre as empresas.
""")

todas_features = list(features_numericas)
if usar_categoricas:
    cat_encoder = preprocessor.named_transformers_['cat'].named_steps['onehot']
    cat_features = cat_encoder.get_feature_names_out(features_categoricas)
    todas_features += list(cat_features)

importancias = modelo.named_steps['regressor'].feature_importances_
df_imp = pd.DataFrame({'Feature': todas_features, 'Importancia': importancias})

def agrupar_feature(nome):
    if 'SETOR_ATIVIDADE' in nome: return 'Efeito Setorial'
    if 'UF_SEDE' in nome: return 'Custo de Região (UF)'
    if 'CONTROLE_ACIONARIO' in nome: return 'Controle (Estatizada vs Privada)'
    if nome == 'NUM_MEMBROS_TOTAL': return 'Tamanho da Diretoria'
    if nome == 'TOTAL_FUNCIONARIOS': return 'Efeito Escala: Nº de Funcionários'
    if nome == 'FATURAMENTO_BRUTO': return 'Efeito Escala: Faturamento Bruto'
    if nome == 'Perc_Fixo': return 'Prêmio Risco: % Salário Fixo'
    if nome == 'Perc_Var_CP': return 'Prêmio Risco: % Bônus Curto Prazo'
    if nome == 'Perc_Var_LP': return 'Prêmio Risco: % Ações Longo Prazo'
    return nome

df_imp['Grupo'] = df_imp['Feature'].apply(agrupar_feature)
df_imp_group = df_imp.groupby('Grupo')['Importancia'].sum().reset_index().sort_values(by='Importancia', ascending=True)

fig_imp = px.bar(
    df_imp_group, x='Importancia', y='Grupo', orientation='h', 
    text_auto='.1%', color='Importancia', color_continuous_scale='Mint'
)
fig_imp.update_layout(xaxis_tickformat='.0%', xaxis_title="Poder Preditivo na Decisão da IA (%)", yaxis_title="")
st.plotly_chart(fig_imp, use_container_width=True)

# ==========================================
# DISPERSÃO E ANOMALIAS
# ==========================================
st.markdown("---")
st.subheader(f"2. Dispersão de Mercado: {alvo_selecionado}")
st.write("Cada ponto representa uma empresa. A posição horizontal é o que a IA diz que ela deveria pagar. A vertical é o que ela realmente pagou.")

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
    fig_over.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="% Acima da Linha de Equilíbrio", yaxis_title="")
    st.plotly_chart(fig_over, use_container_width=True)

with col2:
    st.markdown("🔵 **Top 10 Maior Pagamento Abaixo do Padrão (Underpaid)**")
    fig_under = px.bar(df_underpaid, x='Desvio_Perc', y='NOME_COMPANHIA', orientation='h', text_auto='.1f', color_discrete_sequence=['#4b8bff'])
    fig_under.update_layout(yaxis={'categoryorder':'total descending'}, xaxis_title="% Abaixo da Linha de Equilíbrio", yaxis_title="")
    st.plotly_chart(fig_under, use_container_width=True)

st.markdown("---")
st.write("**Exportação para Auditoria:**")
df_export = df_modelo[['NOME_COMPANHIA', 'SETOR_ATIVIDADE', coluna_alvo, 'Predito', 'Desvio_Perc']]
create_download_button(df_export, f"auditoria_desvios_ia_{ano_selecionado}")
