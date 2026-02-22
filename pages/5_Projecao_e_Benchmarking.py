import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Importações dos utilitários
from utils import get_default_index, renderizar_sidebar_global, formata_brl_int, create_download_button

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
4. **Compare** com um grupo de pares projetado através de um fator de ajuste de mercado.
""")

# Dicionário de componentes para análise
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
    # Opções de pares excluem a empresa base
    opcoes_pares = [e for e in empresas_disponiveis if e != empresa_base]
    pares = st.multiselect("Selecione as Empresas Pares (Benchmarking):", opcoes_pares)
    fator_ajuste = st.number_input("Ajuste Mercado 2026 para os Pares (%):", min_value=-50.0, max_value=100.0, value=5.0, step=1.0)

st.markdown("---")
st.subheader("2. Edição de Dados da Empresa Base")
st.info("💡 Clique nas células das colunas **2025** e **2026** para alterar os valores. Os anos anteriores estão bloqueados para manter o histórico fiel ao FRE.")

# --- PREPARAÇÃO DOS DADOS DA EMPRESA BASE ---
df_base = df[(df['NOME_COMPANHIA'] == empresa_base) & (df['ORGAO_ADMINISTRACAO'] == orgao)]

# Estrutura para o Editor de Dados
anos_historicos = [2022, 2023, 2024, 2025]
dados_editor = {ano: {comp: 0.0 for comp in component_cols.keys()} for ano in anos_historicos}

# Preenche os dados históricos reais
for ano in anos_historicos:
    df_ano = df_base[df_base['ANO_REFER'] == ano]
    if not df_ano.empty:
        for comp_nome, col_db in component_cols.items():
            dados_editor[ano][comp_nome] = float(df_ano[col_db].sum())

# Converte para DataFrame do Pandas para ir para o Streamlit Data Editor
df_editor_pd = pd.DataFrame(dados_editor)

# Sugere 2026 começando igual a 2025 para facilitar
df_editor_pd[2026] = df_editor_pd[2025]

# Formata as colunas para string para melhor apresentação no dataframe, mas o editor lida com números
config_colunas = {
    2022: st.column_config.NumberColumn("2022 (Histórico)", format="R$ %d", disabled=True),
    2023: st.column_config.NumberColumn("2023 (Histórico)", format="R$ %d", disabled=True),
    2024: st.column_config.NumberColumn("2024 (Histórico)", format="R$ %d", disabled=True),
    2025: st.column_config.NumberColumn("2025 (Editável)", format="R$ %d"),
    2026: st.column_config.NumberColumn("2026 (Projeção)", format="R$ %d")
}

# Renderiza a tabela editável
edited_df = st.data_editor(
    df_editor_pd,
    column_config=config_colunas,
    use_container_width=True
)

st.markdown("---")
st.subheader("3. Resultados e Comparação de Benchmarking")

if not pares:
    st.warning("Selecione pelo menos uma empresa par no filtro acima para visualizar a comparação de Benchmarking.")
else:
    # --- CÁLCULO DA EMPRESA BASE (PÓS-EDIÇÃO) ---
    # Totaliza os valores editados por ano
    totais_base = edited_df.sum()
    df_plot_base = pd.DataFrame({
        'Ano': totais_base.index.astype(int),
        'Remuneração Total': totais_base.values,
        'Tipo': f'{empresa_base} (Sua Projeção)'
    })

    # --- CÁLCULO DO BENCHMARKING (MÉDIA DOS PARES) ---
    df_pares = df[(df['NOME_COMPANHIA'].isin(pares)) & (df['ORGAO_ADMINISTRACAO'] == orgao)]
    
    # Agrupa por Ano e por Empresa para saber o total de cada par
    df_pares_grouped = df_pares.groupby(['ANO_REFER', 'NOME_COMPANHIA'])[[col for col in component_cols.values()]].sum()
    df_pares_grouped['Total_Par'] = df_pares_grouped.sum(axis=1)
    
    # Calcula a média do mercado (pares) por ano histórico
    media_pares_ano = df_pares_grouped.groupby('ANO_REFER')['Total_Par'].mean().to_dict()
    
    # Prepara os dados de plotagem para os pares
    dados_pares_plot = []
    for ano in [2022, 2023, 2024, 2025]:
        valor_medio = media_pares_ano.get(ano, 0.0)
        dados_pares_plot.append({'Ano': ano, 'Remuneração Total': valor_medio, 'Tipo': 'Média dos Pares'})
    
    # Projeta 2026 aplicando o Fator de Ajuste sobre 2025
    valor_2025_pares = media_pares_ano.get(2025, 0.0)
    valor_2026_pares = valor_2025_pares * (1 + (fator_ajuste / 100))
    dados_pares_plot.append({'Ano': 2026, 'Remuneração Total': valor_2026_pares, 'Tipo': 'Média dos Pares'})

    df_plot_pares = pd.DataFrame(dados_pares_plot)

    # --- MESCLAR E PLOTAR ---
    df_final_plot = pd.concat([df_plot_base, df_plot_pares])
    
    # Converter Anos para string para o Plotly tratá-los como categorias (não linha contínua)
    df_final_plot['Ano'] = df_final_plot['Ano'].astype(str)

    fig = px.bar(
        df_final_plot, 
        x='Ano', 
        y='Remuneração Total', 
        color='Tipo', 
        barmode='group',
        title=f"Comparativo de Remuneração Total: {empresa_base} vs Pares Selecionados ({orgao})",
        labels={'Ano': 'Ano de Referência', 'Remuneração Total': 'Remuneração Total (R$)'},
        color_discrete_map={f'{empresa_base} (Sua Projeção)': '#1f77b4', 'Média dos Pares': '#ff7f0e'}
    )
    
    # Adicionando rótulos formatados em cima das barras
    fig.update_traces(
        texttemplate='%{y:,.0f}', 
        textposition='outside',
        textfont_size=12
    )
    
    # Ajustando layout para usar padrão brasileiro e afastar o teto do gráfico para o texto não cortar
    fig.update_layout(
        separators=",.",
        yaxis=dict(title='Remuneração (R$)', tickformat=",.0f"),
        margin=dict(t=50, b=50),
        legend_title_text=''
    )
    fig.update_yaxes(range=[0, df_final_plot['Remuneração Total'].max() * 1.15]) # Dá um respiro de 15% acima da maior barra

    st.plotly_chart(fig, use_container_width=True)

    # Botões de Download dos Cenários
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.write("**Dados Projetados (Sua Empresa):**")
        create_download_button(edited_df.reset_index(names='Componente'), f"projecao_interna_{empresa_base}_2026")
    with col_d2:
        st.write("**Dados Comparativos (Mercado/Pares):**")
        create_download_button(df_final_plot, f"comparativo_pares_{empresa_base}_2026")
