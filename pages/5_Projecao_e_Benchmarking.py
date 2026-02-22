import streamlit as st
import pandas as pd
import plotly.express as px

# Adicionamos a importação do formata_abrev
from utils import get_default_index, renderizar_sidebar_global, formata_abrev, create_download_button

st.set_page_config(layout="wide", page_title="Projeção e Benchmarking", page_icon="🚀")

if 'df_completo' not in st.session_state:
    st.warning("⚠️ Por favor, aceda à 'Página Inicial' (Home) primeiro para carregar a base de dados.")
    st.stop()

df_original = st.session_state['df_completo']
df = renderizar_sidebar_global(df_original)

if df.empty:
    st.warning("Nenhum dado encontrado para os filtros globais selecionados.")
    st.stop()

st.header("🚀 Projeção e Benchmarking de Remuneração")
st.markdown("""
Utilize esta ferramenta para planear o próximo ciclo. 
1. **Verifique** o seu histórico (2022-2024).
2. **Atualize** os dados reais/finais de 2025 da sua empresa.
3. **Projete** o ano de 2026.
4. **Compare** os componentes com pares de mercado selecionados.
""")

component_cols = {
    'Salário': 'REM_FIXA_SALARIO', 
    'Benefícios': 'REM_FIXA_BENEFICIOS', 
    'Bônus': 'REM_VAR_BONUS', 
    'PLR': 'REM_VAR_PLR', 
    'Ações': 'REM_ACOES_BLOCO3', 
    'Outros': 'REM_FIXA_OUTROS'
}

st.markdown("---")
st.subheader("1. Configuração do Cenário")

col1, col2, col3 = st.columns(3)
empresas_disponiveis = sorted(df['NOME_COMPANHIA'].unique())
orgaos_disponiveis = sorted(df['ORGAO_ADMINISTRACAO'].unique())

with col1:
    if 'empresa_proj' not in st.session_state: st.session_state['empresa_proj'] = empresas_disponiveis[0]
    empresa_base = st.selectbox("Sua Empresa (Base):", empresas_disponiveis, index=get_default_index(empresas_disponiveis, st.session_state['empresa_proj']))
    st.session_state['empresa_proj'] = empresa_base

with col2:
    if 'orgao_proj' not in st.session_state: st.session_state['orgao_proj'] = 'DIRETORIA ESTATUTARIA'
    orgao = st.selectbox("Órgão Administrativo:", orgaos_disponiveis, index=get_default_index(orgaos_disponiveis, st.session_state['orgao_proj']))
    st.session_state['orgao_proj'] = orgao

with col3:
    opcoes_pares = [e for e in empresas_disponiveis if e != empresa_base]
    pares = st.multiselect("Selecione Empresas Pares (Opcional):", opcoes_pares)
    fator_ajuste = st.number_input("Ajuste Mercado 2026 para os Pares (%):", min_value=-50.0, max_value=100.0, value=5.0, step=1.0)

st.markdown("---")
st.subheader("2. Edição de Dados da Empresa Base")
st.info("💡 Clique nas células das colunas **2025** e **2026** para alterar os valores.")

# --- PREPARAÇÃO DOS DADOS DA EMPRESA BASE ---
df_base = df[(df['NOME_COMPANHIA'] == empresa_base) & (df['ORGAO_ADMINISTRACAO'] == orgao)]
anos_historicos = [2022, 2023, 2024, 2025]
dados_editor = {ano: {comp: 0.0 for comp in component_cols.keys()} for ano in anos_historicos}

for ano in anos_historicos:
    df_ano = df_base[df_base['ANO_REFER'] == ano]
    if not df_ano.empty:
        for comp_nome, col_db in component_cols.items():
            dados_editor[ano][comp_nome] = float(df_ano[col_db].sum())

df_editor_pd = pd.DataFrame(dados_editor)
df_editor_pd[2026] = df_editor_pd[2025] # Sugere 2026 = 2025

config_colunas = {
    2022: st.column_config.NumberColumn("2022 (Histórico)", format="R$ %d", disabled=True),
    2023: st.column_config.NumberColumn("2023 (Histórico)", format="R$ %d", disabled=True),
    2024: st.column_config.NumberColumn("2024 (Histórico)", format="R$ %d", disabled=True),
    2025: st.column_config.NumberColumn("2025 (Editável)", format="R$ %d"),
    2026: st.column_config.NumberColumn("2026 (Projeção)", format="R$ %d")
}

edited_df = st.data_editor(
    df_editor_pd,
    column_config=config_colunas,
    width='stretch' # Atualizado para corrigir o warning do Streamlit
)

st.markdown("---")
st.subheader("3. Resultados e Comparação")

# --- NOVO FILTRO DE ANOS ---
anos_opcoes = [2022, 2023, 2024, 2025, 2026]
intervalo_anos = st.slider(
    "Selecione o intervalo de anos para visualizar no gráfico:",
    min_value=min(anos_opcoes),
    max_value=max(anos_opcoes),
    value=(2022, 2026)
)

# --- ENGENHARIA DE DADOS PARA O GRÁFICO (MELT) ---
# 1. Dados da Empresa Base
df_base_plot = edited_df.reset_index().rename(columns={'index': 'Componente'})
df_base_plot = df_base_plot.melt(id_vars='Componente', var_name='Ano', value_name='Valor')
nome_tipo_base = f'{empresa_base} (Sua Projeção)'
df_base_plot['Tipo'] = nome_tipo_base

# 2. Dados dos Pares e Média (se selecionados)
dados_pares_plot = []
if pares:
    df_pares = df[(df['NOME_COMPANHIA'].isin(pares)) & (df['ORGAO_ADMINISTRACAO'] == orgao)]
    for par in pares:
        df_par = df_pares[df_pares['NOME_COMPANHIA'] == par]
        # Puxa dados de 2022 a 2025
        for ano in anos_historicos:
            df_ano = df_par[df_par['ANO_REFER'] == ano]
            for comp_nome, col_db in component_cols.items():
                valor = float(df_ano[col_db].sum()) if not df_ano.empty else 0.0
                dados_pares_plot.append({'Componente': comp_nome, 'Ano': ano, 'Valor': valor, 'Tipo': par})
    
    df_pares_plot_df = pd.DataFrame(dados_pares_plot)
    
    # Projeta 2026 para os Pares individualmente
    df_2025_pares = df_pares_plot_df[df_pares_plot_df['Ano'] == 2025].copy()
    df_2026_pares = df_2025_pares.copy()
    df_2026_pares['Ano'] = 2026
    df_2026_pares['Valor'] = df_2026_pares['Valor'] * (1 + (fator_ajuste / 100))
    df_pares_plot_df = pd.concat([df_pares_plot_df, df_2026_pares], ignore_index=True)
    
    # Calcula a Média dos Pares (Mercado)
    df_media = df_pares_plot_df.groupby(['Ano', 'Componente'])['Valor'].mean().reset_index()
    df_media['Tipo'] = 'Média dos Pares'
    
    df_final_plot = pd.concat([df_base_plot, df_pares_plot_df, df_media], ignore_index=True)
else:
    # Se nenhum par foi selecionado, mostra apenas a empresa base
    df_final_plot = df_base_plot

# --- APLICAR FILTRO DE ANO ---
# 1. Primeiro garantimos que a coluna 'Ano' é um número inteiro para a matemática funcionar
df_final_plot['Ano'] = df_final_plot['Ano'].astype(int)

# 2. Aplicamos o filtro do Slider
df_final_plot = df_final_plot[(df_final_plot['Ano'] >= intervalo_anos[0]) & (df_final_plot['Ano'] <= intervalo_anos[1])]

if df_final_plot.empty:
    st.info("Não há dados para exibir no intervalo de anos selecionado.")
else:
    # Cálculo de Porcentagem para não poluir barras muito pequenas com texto
    totais_ano_tipo = df_final_plot.groupby(['Ano', 'Tipo'])['Valor'].transform('sum')
    df_final_plot['Perc'] = (df_final_plot['Valor'] / totais_ano_tipo) * 100
    df_final_plot['Texto'] = df_final_plot.apply(lambda row: formata_abrev(row['Valor']) if row['Perc'] >= 5 else "", axis=1)
    
    # 3. DEPOIS do filtro, voltamos a converter 'Ano' para string para o Plotly não somar os anos no eixo X
    df_final_plot['Ano'] = df_final_plot['Ano'].astype(str)

    # Construção do Gráfico Facetado (Subplots automáticos por Tipo de Empresa)
    fig = px.bar(
        df_final_plot, 
        x='Ano', 
        y='Valor', 
        color='Componente', 
        facet_col='Tipo', 
        facet_col_wrap=3, # Se houver muitos pares, quebra a linha a cada 3 gráficos
        barmode='stack',
        text='Texto',
        title=f"Evolução e Benchmarking Empilhado ({orgao})",
        labels={'Ano': '', 'Valor': 'Remuneração (R$)'},
        category_orders={'Tipo': ordem_tipos}
    )
    
    # Ajustes estéticos
    fig.update_traces(textposition='inside', insidetextanchor='middle', textfont_size=11)
    fig.update_layout(
        separators=",.",
        margin=dict(t=60, b=40),
        legend_title_text='Componentes',
        hovermode='x unified'
    )
    
    # Remove a palavra "Tipo=" do título de cada subplot para ficar mais limpo
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))

    st.plotly_chart(fig, width='stretch')

    # Botões de Download
    st.markdown("---")
    st.write("**Exportar Dados da Visualização**")
    create_download_button(df_final_plot.drop(columns=['Texto', 'Perc']), f"dados_projecao_{empresa_base}_{intervalo_anos[0]}_{intervalo_anos[1]}")
