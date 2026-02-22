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
st.markdown("Este modelo aprende os padrões salariais de centenas de empresas com base no histórico consolidado e cria uma **matemática do Salário Justo**. *Nota: Projeções de 2025 foram removidas para garantir que a IA treine apenas com pagamentos reais e auditados.*")

# --- GUIA EDUCATIVO GERAL (EXPLAINABLE AI) ---
with st.expander("📖 Transparência do Modelo: Como a IA pensa e o que significa cada variável?"):
    st.markdown("""
    ### Como funciona o algoritmo de predição?
    Utilizamos um modelo de **Random Forest (Floresta Aleatória)**. Em vez de olhar para uma única regra, a IA constrói centenas de "árvores de decisão" diferentes baseadas nos dados das empresas. Ela cruza milhares de cenários (ex: "Se a empresa é de Varejo E fatura mais de 1 Bilhão E paga muito em ações...") para descobrir qual é o padrão salarial exato do mercado para aquele perfil. O resultado final é a média da inteligência de todas essas árvores.
    
    ### O que significam os Componentes da Equação?
    * **Efeito Escala (Faturamento e Funcionários):** A complexidade de gerir uma empresa. A teoria económica dita que o salário de um executivo deve crescer exponencialmente conforme o tamanho da receita e a quantidade de pessoas que ele lidera.
    * **Prêmio de Risco (% do Pacote em Bônus ou Ações):** Executivos preferem a segurança do Salário Fixo. Se o Conselho de Administração quer atrelar 60% do pagamento do CEO a Ações de Longo Prazo (que ele pode acabar por nunca receber se a empresa for mal), o Conselho tem que prometer um pacote total *muito maior* para ele aceitar o cargo. A IA sabe ler este risco e aumenta a estimativa de "Salário Justo".
    * **Efeito Setorial:** Ajusta a agressividade padrão de diferentes indústrias (ex: Startups de Tecnologia pagam diferente de Indústrias Pesadas).
    * **Tamanho da Diretoria:** Mede a fragmentação do poder. Um orçamento de diretoria dividido por 2 pessoas gera fatias maiores do que o mesmo orçamento dividido por 15 diretores.
    """)

st.markdown("---")

col_filtros1, col_filtros2 = st.columns(2)
with col_filtros1:
    # FILTRO: Apenas anos com dados reais (2024 para trás)
    anos_reais = [ano for ano in df['ANO_REFER'].unique() if ano <= 2024]
    if not anos_reais:
        st.error("Não há dados de anos anteriores a 2025 para treinar o modelo de forma segura.")
        st.stop()
    anos_disponiveis = sorted(anos_reais, reverse=True)
    ano_selecionado = st.selectbox("Selecione o Ano Base (Histórico Auditado):", anos_disponiveis)

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
    st.warning(f"⚠️ Amostra pequena ({n_amostras} empresas). A IA ativou o modo **Baixa Complexidade**: Variáveis setoriais foram desativadas para evitar o colapso estatístico (Overfitting).")
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
# UF removida das features categóricas
features_categoricas = ['SETOR_ATIVIDADE', 'CONTROLE_ACIONARIO'] if usar_categoricas else []

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
        st.warning(f"📊 **Confiança da IA (R²): {confianca:.1%}** | Confiança Moderada. A IA encontrou tendências, mas existem muitos casos 'fora da curva' nesta amostra.")
    else:
        st.success(f"✅ **Confiança da IA (R²): {confianca:.1%}** | Alta Precisão! A IA mapeou com clareza a regra de pagamento deste grupo de {n_amostras} empresas.")

# ==========================================
# EXPLAINABLE AI (IMPORTÂNCIA DAS VARIÁVEIS)
# ==========================================
st.markdown("---")
st.subheader("1. O que mais pesou na decisão da Inteligência Artificial? (Poder Preditivo)")
st.info("💡 **Dica de Leitura:** Se a barra 'Prêmio Risco: % Ações Longo Prazo' possuir **40%**, isso indica que 40% das diferenças salariais entre as empresas desta amostra são explicadas exclusivamente pela quantidade de ações que elas oferecem. Variáveis no topo da lista são os principais 'motores' que ditam a remuneração neste ano.")

todas_features = list(features_numericas)
if usar_categoricas:
    cat_encoder = preprocessor.named_transformers_['cat'].named_steps['onehot']
    cat_features = cat_encoder.get_feature_names_out(features_categoricas)
    todas_features += list(cat_features)

importancias = modelo.named_steps['regressor'].feature_importances_
df_imp = pd.DataFrame({'Feature': todas_features, 'Importancia': importancias})

def agrupar_feature(nome):
    if 'SETOR_ATIVIDADE' in nome: return 'Efeito Setorial'
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
st.write("Cada ponto representa uma empresa. A posição horizontal é o que a matemática diz que ela deveria pagar. A vertical é o que ela realmente pagou na prática.")

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


# ==========================================
# SIMULADOR ESTRATÉGICO
# ==========================================
st.markdown("---")
st.subheader("🧪 3. Simulador de Salário Justo")
st.markdown("Utilize a inteligência do modelo treinado acima para testar o pacote de remuneração da sua própria organização.")

with st.form("form_simulador"):
    st.markdown("**A. Complexidade e Escala (Scale Effect)**")
    col_s1, col_s2 = st.columns(2)
    sim_setor = col_s1.selectbox("Setor Econômico:", df_modelo['SETOR_ATIVIDADE'].unique())
    sim_membros = col_s2.number_input("Tamanho da Diretoria:", min_value=1, max_value=30, value=5)
    
    col_s4, col_s5 = st.columns(2)
    val_med_func = int(df_modelo['TOTAL_FUNCIONARIOS'].median()) if pd.notna(df_modelo['TOTAL_FUNCIONARIOS'].median()) else 1000
    
    # Lógica de conversão para Bilhões
    val_med_fat_bruto = float(df_modelo['FATURAMENTO_BRUTO'].median()) if pd.notna(df_modelo['FATURAMENTO_BRUTO'].median()) else 500000000.0
    val_med_fat_bilhoes = val_med_fat_bruto / 1_000_000_000
    
    sim_func = col_s4.number_input("Total de Funcionários:", min_value=1, value=val_med_func)
    sim_fat_bilhoes = col_s5.number_input("Faturamento Bruto Anual (em Bilhões de R$):", min_value=0.01, value=val_med_fat_bilhoes, step=0.1)
    
    # Reverte o valor simulado para o formato que a IA entende
    sim_fat = sim_fat_bilhoes * 1_000_000_000

    st.markdown("**B. Estrutura de Incentivos e Risco (Risk Premium)**")
    col_r1, col_r2, col_r3 = st.columns(3)
    sim_p_fixo = col_r1.slider("% Fixo (Salário Base)", 0, 100, 30)
    sim_p_cp = col_r2.slider("% Variável Curto Prazo (Bônus/PLR)", 0, 100, 40)
    sim_p_lp = col_r3.slider("% Variável Longo Prazo (Ações)", 0, 100, 30)
    
    submit = st.form_submit_button("Processar Estimativa com IA")

if submit:
    if (sim_p_fixo + sim_p_cp + sim_p_lp) != 100:
        st.error("⚠️ Erro: A soma dos percentuais da estrutura de incentivos deve ser exatamente 100%.")
    else:
        novo_dado = pd.DataFrame({
            'SETOR_ATIVIDADE': [sim_setor], 'CONTROLE_ACIONARIO': ['PRIVADO'], 
            'NUM_MEMBROS_TOTAL': [sim_membros], 'TOTAL_FUNCIONARIOS': [sim_func], 'FATURAMENTO_BRUTO': [sim_fat],
            'Perc_Fixo': [sim_p_fixo/100], 'Perc_Var_CP': [sim_p_cp/100], 'Perc_Var_LP': [sim_p_lp/100]
        })
        
        est_alvo = np.expm1(modelo.predict(novo_dado)[0])
        
        st.info(f"💡 **Predição Estatística Concluída (Base {ano_selecionado})**")
        st.metric(f"{alvo_selecionado} Recomendado pela IA", f"R$ {est_alvo:,.2f}")


# ==========================================
# EXPORTAÇÃO PARA AUDITORIA (DEEP-DIVE)
# ==========================================
st.markdown("---")
st.write("**📥 Baixar Relatório de Auditoria do Modelo:**")
st.markdown("O Excel gerado contém o desvio calculado e **todas as variáveis exatas** de cada empresa, permitindo que a auditoria rastreie como a IA chegou à conclusão.")

# UF_SEDE removida também do relatório de exportação para evitar confusão de variáveis
colunas_auditoria = [
    'NOME_COMPANHIA', 'SETOR_ATIVIDADE', 'CONTROLE_ACIONARIO', 
    'TOTAL_FUNCIONARIOS', 'FATURAMENTO_BRUTO', 'NUM_MEMBROS_TOTAL',
    'Perc_Fixo', 'Perc_Var_CP', 'Perc_Var_LP',
    coluna_alvo, 'Predito', 'Desvio_Perc'
]

df_export = df_modelo[colunas_auditoria].copy()
df_export['Perc_Fixo'] = (df_export['Perc_Fixo'] * 100).round(2).astype(str) + '%'
df_export['Perc_Var_CP'] = (df_export['Perc_Var_CP'] * 100).round(2).astype(str) + '%'
df_export['Perc_Var_LP'] = (df_export['Perc_Var_LP'] * 100).round(2).astype(str) + '%'
df_export['Desvio_Perc'] = df_export['Desvio_Perc'].round(2).astype(str) + '%'

create_download_button(df_export, f"auditoria_completa_fair_pay_IA_{ano_selecionado}")
