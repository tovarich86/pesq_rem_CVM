import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Atualizamos o import para trazer o formata_abrev
from utils import get_default_index, create_download_button, renderizar_sidebar_global, format_year, formata_brl_int, formata_abrev

st.set_page_config(layout="wide", page_title="Componentes da Remuneração", page_icon="🧩")

if 'df_completo' not in st.session_state:
    st.warning("⚠️ Por favor, aceda à 'Página Inicial' (Home) primeiro para carregar a base de dados.")
    st.stop()

df_original = st.session_state['df_completo']
df = renderizar_sidebar_global(df_original)

if df.empty:
    st.warning("Nenhum dado encontrado para os filtros globais selecionados.")
    st.stop()

st.header("Análise dos Componentes da Remuneração Total")

tipos_analise = ["Composição por Empresa (Ano Único)", "Evolução Anual Comparativa (por Empresa)", "Ranking de Empresas (Top 15)"]
if 'comp_analysis_type' not in st.session_state: st.session_state['comp_analysis_type'] = tipos_analise[0]
idx_analise = get_default_index(tipos_analise, st.session_state['comp_analysis_type'])

analysis_type = st.selectbox("Escolha o tipo de análise:", tipos_analise, index=idx_analise)
st.session_state['comp_analysis_type'] = analysis_type

component_cols = {'Salário': 'REM_FIXA_SALARIO', 'Benefícios': 'REM_FIXA_BENEFICIOS', 'Comitês': 'REM_FIXA_COMITES', 'Bônus': 'REM_VAR_BONUS', 'PLR': 'REM_VAR_PLR', 'Comissões': 'REM_VAR_COMISSOES', 'Pós-Emprego': 'REM_POS_EMPREGO', 'Cessação': 'REM_CESSACAO_CARGO', 'Ações': 'REM_ACOES_BLOCO3', 'Outros': 'REM_FIXA_OUTROS'}

if analysis_type == "Composição por Empresa (Ano Único)":
    st.subheader("Composição da Remuneração por Órgão")
    col1, col2 = st.columns(2)
    with col1:
        empresas = sorted(df['NOME_COMPANHIA'].unique())
        if 'empresa_comp_1' not in st.session_state: st.session_state['empresa_comp_1'] = empresas[0]
        empresa = st.selectbox("1. Selecione a Empresa", empresas, index=get_default_index(empresas, st.session_state['empresa_comp_1']))
        st.session_state['empresa_comp_1'] = empresa
        
    df_empresa = df[df['NOME_COMPANHIA'] == empresa]
    with col2:
        anos = sorted(df_empresa['ANO_REFER'].unique(), reverse=True)
        ano = st.selectbox("2. Selecione o Ano", anos)

    df_filtered = df_empresa[df_empresa['ANO_REFER'] == ano]
    df_grouped = df_filtered.groupby('ORGAO_ADMINISTRACAO')[[col for col in component_cols.values() if col in df_filtered.columns]].sum()
    df_grouped['Total'] = df_grouped.sum(axis=1)
    df_grouped = df_grouped[df_grouped['Total'] > 0]
    
    if not df_grouped.empty:
        df_plot = df_grouped.drop(columns='Total').reset_index().melt(id_vars='ORGAO_ADMINISTRACAO', var_name='Componente', value_name='Valor')
        df_plot = df_plot[df_plot['Valor'] > 0]
        df_plot['Componente'] = df_plot['Componente'].map({v: k for k, v in component_cols.items()})
        
        # --- NOVIDADE: Cálculo de Porcentagem e Rótulos ---
        totals_df = df_grouped[['Total']].reset_index()
        df_plot = df_plot.merge(totals_df, on='ORGAO_ADMINISTRACAO')
        df_plot['Perc'] = (df_plot['Valor'] / df_plot['Total']) * 100
        # Só exibe o texto se a fatia for maior que 4% para evitar sobreposição
        df_plot['Texto'] = df_plot.apply(lambda row: f"{formata_abrev(row['Valor'])}<br>({row['Perc']:.1f}%)" if row['Perc'] >= 4 else "", axis=1)

        # Adicionamos text='Texto' no px.bar
        fig = px.bar(df_plot, x='ORGAO_ADMINISTRACAO', y='Valor', color='Componente', text='Texto', 
                     title=f"Composição da Remuneração por Órgão para {empresa} em {format_year(ano)}", labels={'ORGAO_ADMINISTRACAO': 'Órgão', 'Valor': 'Valor (R$)'})
        
        # Forçamos o texto a ficar no meio da barra e configuramos o separador
        fig.update_traces(textposition='inside', insidetextanchor='middle')
        fig.update_layout(barmode='stack', separators=",.")
        
        totals = df_grouped['Total']
        fig.add_trace(go.Scatter(x=totals.index, y=totals, text=[f"<b>{formata_brl_int(val)}</b>" for val in totals], mode='text', textposition='top center', showlegend=False))
        st.plotly_chart(fig, use_container_width=True)
        create_download_button(df_grouped.reset_index(), f"composicao_orgaos_{empresa}_{ano}")
    else:
        st.info("Não há dados de componentes para exibir para a seleção atual.")

elif analysis_type == "Evolução Anual Comparativa (por Empresa)":
    st.subheader("Evolução Anual dos Componentes")
    col1, col2, col3 = st.columns(3)
    with col1:
        empresas = sorted(df['NOME_COMPANHIA'].unique())
        if 'empresa_comp_2' not in st.session_state: st.session_state['empresa_comp_2'] = empresas[0]
        empresa = st.selectbox("1. Selecione a Empresa", empresas, index=get_default_index(empresas, st.session_state['empresa_comp_2']))
        st.session_state['empresa_comp_2'] = empresa
        
    df_empresa = df[df['NOME_COMPANHIA'] == empresa]
    with col2:
        orgaos_disponiveis = sorted(df_empresa['ORGAO_ADMINISTRACAO'].unique())
        if 'orgao_comp_2' not in st.session_state: st.session_state['orgao_comp_2'] = 'DIRETORIA ESTATUTARIA'
        orgao = st.selectbox("2. Selecione o Órgão", orgaos_disponiveis, index=get_default_index(orgaos_disponiveis, st.session_state['orgao_comp_2']))
        st.session_state['orgao_comp_2'] = orgao
    with col3:
        calc_type = st.radio("Calcular por:", ["Total", "Média por Membro"], horizontal=True)

    df_filtered = df_empresa[df_empresa['ORGAO_ADMINISTRACAO'] == orgao]
    yearly_data = df_filtered.groupby('ANO_REFER').agg({**{col: 'sum' for col in component_cols.values() if col in df.columns}, 'NUM_MEMBROS_TOTAL': 'first'}).reset_index()
    yearly_data['Total'] = yearly_data[[col for col in component_cols.values() if col in yearly_data.columns]].sum(axis=1)
    
    if calc_type == "Média por Membro":
        yearly_data = yearly_data[yearly_data['NUM_MEMBROS_TOTAL'] > 0]
        for col in component_cols.values():
            if col in yearly_data.columns:
                yearly_data[col] = yearly_data[col] / yearly_data['NUM_MEMBROS_TOTAL']
        yearly_data['Total'] = yearly_data['Total'] / yearly_data['NUM_MEMBROS_TOTAL']
        
    df_plot = yearly_data.melt(id_vars=['ANO_REFER'], value_vars=[col for col in component_cols.values() if col in yearly_data.columns], var_name='Componente', value_name='Valor')
    df_plot = df_plot[df_plot['Valor'] > 0]
    df_plot['Componente'] = df_plot['Componente'].map({v: k for k, v in component_cols.items()})
    
    if not df_plot.empty:
        yearly_data['ANO_REFER_FORMATTED'] = yearly_data['ANO_REFER'].apply(format_year)
        df_plot = pd.merge(df_plot, yearly_data[['ANO_REFER', 'ANO_REFER_FORMATTED']], on='ANO_REFER')
        
        # --- NOVIDADE: Cálculo de Porcentagem e Rótulos ---
        totals_df = yearly_data[['ANO_REFER_FORMATTED', 'Total']]
        df_plot = pd.merge(df_plot, totals_df, on='ANO_REFER_FORMATTED')
        df_plot['Perc'] = (df_plot['Valor'] / df_plot['Total']) * 100
        df_plot['Texto'] = df_plot.apply(lambda row: f"{formata_abrev(row['Valor'])}<br>({row['Perc']:.1f}%)" if row['Perc'] >= 4 else "", axis=1)

        # Adicionamos text='Texto' no px.bar
        fig = px.bar(df_plot, x='ANO_REFER_FORMATTED', y='Valor', color='Componente', text='Texto',
                     title=f"Evolução dos Componentes para {empresa} ({orgao})", labels={'ANO_REFER_FORMATTED': 'Ano', 'Valor': f'Valor {calc_type} (R$)'})
        
        fig.update_traces(textposition='inside', insidetextanchor='middle')
        fig.update_layout(xaxis_type='category', barmode='stack', separators=",.")
        
        totals = yearly_data.set_index('ANO_REFER_FORMATTED')['Total']
        if calc_type == "Média por Membro":
            membros = yearly_data.set_index('ANO_REFER_FORMATTED')['NUM_MEMBROS_TOTAL']
            labels = [f"<b>{formata_brl_int(total)}</b><br>({membro:.0f} membros)" for total, membro in zip(totals, membros)]
        else:
            labels = [f"<b>{formata_brl_int(val)}</b>" for val in totals]
        fig.add_trace(go.Scatter(x=totals.index, y=totals, text=labels, mode='text', textposition='top center', showlegend=False))
        st.plotly_chart(fig, use_container_width=True)
        create_download_button(yearly_data, f"evolucao_componentes_{empresa}_{orgao}")
    else:
        st.info("Não há dados para exibir para a seleção atual.")
        
elif analysis_type == "Ranking de Empresas (Top 15)":
    # Aqui o ranking já possui o text_auto='.2s' (que faz um formato parecido), mas o mantemos limpo.
    st.subheader("Ranking de Empresas por Componente de Remuneração")
    col1, col2, col3 = st.columns(3)
    with col1:
        ano = st.selectbox("1. Selecione o Ano", sorted(df['ANO_REFER'].unique(), reverse=True))
    with col2:
        orgaos_disponiveis = sorted(df['ORGAO_ADMINISTRACAO'].unique())
        orgao = st.selectbox("2. Selecione o Órgão", orgaos_disponiveis, index=get_default_index(orgaos_disponiveis, 'DIRETORIA ESTATUTARIA'))
    rank_options = {'Remuneração Total': 'TOTAL_REMUNERACAO_ORGAO', **component_cols}
    with col3:
        rank_metric_name = st.selectbox("3. Rankear por:", list(rank_options.keys()))
        
    col_rank = rank_options[rank_metric_name]
    calc_type = st.radio("Calcular por:", ["Total", "Média por Membro"], horizontal=True)
    df_filtered = df[(df['ANO_REFER'] == ano) & (df['ORGAO_ADMINISTRACAO'] == orgao)]
    
    if calc_type == "Total":
        df_rank = df_filtered.groupby('NOME_COMPANHIA')[col_rank].sum().nlargest(15).reset_index()
    else: 
        df_agg = df_filtered.groupby('NOME_COMPANHIA').agg(Valor=(col_rank, 'sum'), Membros=('NUM_MEMBROS_TOTAL', 'first')).reset_index()
        df_agg = df_agg[df_agg['Membros'] > 0]
        df_agg[col_rank] = df_agg['Valor'] / df_agg['Membros']
        df_rank = df_agg.nlargest(15, col_rank)
        
    if not df_rank.empty and df_rank[col_rank].sum() > 0:
        fig = px.bar(df_rank.sort_values(by=col_rank), x=col_rank, y='NOME_COMPANHIA', orientation='h', text_auto='.2s', title=f"Top 15 Empresas por {rank_metric_name} ({calc_type}) em {format_year(ano)}")
        fig.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title=f"Valor {calc_type} (R$)", yaxis_title="Empresa", separators=",.")
        st.plotly_chart(fig, use_container_width=True)
        create_download_button(df_rank, f"ranking_componentes_{ano}_{orgao}")
    else:
        st.info("Não há dados para gerar o ranking para a seleção atual.")
