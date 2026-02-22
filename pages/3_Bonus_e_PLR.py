import streamlit as st
import pandas as pd
import plotly.express as px

# Adicionamos o formata_abrev aqui também
from utils import get_default_index, create_download_button, renderizar_sidebar_global, format_year, formata_abrev

st.set_page_config(layout="wide", page_title="Bônus e PLR", page_icon="🎯")

if 'df_completo' not in st.session_state:
    st.warning("⚠️ Por favor, aceda à 'Página Inicial' (Home) primeiro para carregar a base de dados.")
    st.stop()

df_original = st.session_state['df_completo']
df = renderizar_sidebar_global(df_original)

if df.empty:
    st.warning("Nenhum dado encontrado para os filtros globais selecionados.")
    st.stop()

st.header("Análise Detalhada de Bônus e Participação nos Resultados")
st.subheader("Evolução Comparativa de Bônus e PLR")

col1, col2, col3 = st.columns(3)
with col1:
    empresas = sorted(df['NOME_COMPANHIA'].unique())
    if 'empresa_bonus' not in st.session_state: st.session_state['empresa_bonus'] = empresas[0]
    empresa = st.selectbox("1. Selecione a Empresa", empresas, index=get_default_index(empresas, st.session_state['empresa_bonus']))
    st.session_state['empresa_bonus'] = empresa
    
df_empresa = df[df['NOME_COMPANHIA'] == empresa]

with col2:
    orgaos_disponiveis = sorted(df_empresa['ORGAO_ADMINISTRACAO'].unique())
    if 'orgao_bonus' not in st.session_state: st.session_state['orgao_bonus'] = 'DIRETORIA ESTATUTARIA'
    orgao = st.selectbox("2. Selecione o Órgão", orgaos_disponiveis, index=get_default_index(orgaos_disponiveis, st.session_state['orgao_bonus']))
    st.session_state['orgao_bonus'] = orgao
    
with col3:
    calc_type = st.radio("Calcular por:", ["Total", "Média por Membro"], horizontal=True)

df_filtered = df_empresa[df_empresa['ORGAO_ADMINISTRACAO'] == orgao]
bonus_cols = {'Bônus Mínimo': 'BONUS_MIN', 'Bônus Alvo': 'BONUS_ALVO', 'Bônus Máximo': 'BONUS_MAX', 'Bônus Pago': 'BONUS_PAGO', 'PLR Mínimo': 'PLR_MIN', 'PLR Alvo': 'PLR_ALVO', 'PLR Máximo': 'PLR_MAX', 'PLR Pago': 'PLR_PAGO'}
yearly_data = df_filtered.groupby('ANO_REFER').agg({**{col: 'sum' for col in bonus_cols.values() if col in df.columns}, 'NUM_MEMBROS_BONUS_PLR': 'first'}).reset_index()

if calc_type == "Média por Membro":
    yearly_data = yearly_data[yearly_data['NUM_MEMBROS_BONUS_PLR'] > 0]
    for col in bonus_cols.values():
        if col in yearly_data.columns:
            yearly_data[col] = yearly_data[col] / yearly_data['NUM_MEMBROS_BONUS_PLR']

df_plot = yearly_data.melt(id_vars=['ANO_REFER'], value_vars=[col for col in bonus_cols.values() if col in yearly_data.columns], var_name='Métrica', value_name='Valor')
df_plot = df_plot[df_plot['Valor'] > 0]
df_plot['Tipo'] = df_plot['Métrica'].apply(lambda x: 'Bônus' if 'BONUS' in x else 'PLR')
df_plot['Métrica'] = df_plot['Métrica'].map({v: k for k, v in bonus_cols.items()})

if not df_plot.empty:
    df_plot['ANO_REFER_FORMATTED'] = df_plot['ANO_REFER'].apply(format_year)
    
    # --- NOVIDADE: Adicionando Rótulos ao Gráfico ---
    # Aplica a nossa função de formatação para criar uma coluna de texto
    df_plot['Texto'] = df_plot['Valor'].apply(formata_abrev)
    
    fig = px.bar(df_plot, x='ANO_REFER_FORMATTED', y='Valor', color='Métrica', 
                 barmode='group', facet_col='Tipo', text='Texto',
                 title=f"Evolução de Bônus e PLR para {empresa} ({orgao})", 
                 labels={'ANO_REFER_FORMATTED': 'Ano', 'Valor': f'Valor {calc_type} (R$)'},
                 template="streamlit")
    
    # Coloca os textos imediatamente acima de cada barra do grupo
    fig.update_traces(textposition='outside')
    fig.update_xaxes(type='category')
    fig.update_layout(separators=",.")
    st.plotly_chart(fig, use_container_width=True)
    create_download_button(df_plot, f"evolucao_bonus_plr_{empresa}_{orgao}")

    st.subheader("Performance: % do Alvo Efetivamente Pago")
    perf_cols = st.columns(len(yearly_data))
    for i, row in yearly_data.iterrows():
        with perf_cols[i]:
            st.write(f"**{format_year(row['ANO_REFER'])}**")
            if row.get('BONUS_ALVO', 0) > 0:
                perc_bonus = (row.get('BONUS_PAGO', 0) / row['BONUS_ALVO']) * 100
                st.metric(label="Bônus", value=f"{perc_bonus:.1f}%")
            if row.get('PLR_ALVO', 0) > 0:
                perc_plr = (row.get('PLR_PAGO', 0) / row['PLR_ALVO']) * 100
                st.metric(label="PLR", value=f"{perc_plr:.1f}%")

    st.subheader("Potencial Máximo: % do Alvo")
    perf_max_cols = st.columns(len(yearly_data))
    for i, row in yearly_data.iterrows():
        with perf_max_cols[i]:
            st.write(f"**{format_year(row['ANO_REFER'])}**")
            if row.get('BONUS_ALVO', 0) > 0:
                perc_bonus_max = (row.get('BONUS_MAX', 0) / row['BONUS_ALVO']) * 100
                st.metric(label="Bônus (Máximo vs Alvo)", value=f"{perc_bonus_max:.1f}%")
            if row.get('PLR_ALVO', 0) > 0:
                perc_plr_max = (row.get('PLR_MAX', 0) / row['PLR_ALVO']) * 100
                st.metric(label="PLR (Máximo vs Alvo)", value=f"{perc_plr_max:.1f}%")
else:
    st.info("Não há dados de Bônus ou PLR para exibir para a seleção atual.")

st.markdown("---")
st.subheader("Ranking de Empresas por Bônus/PLR")
col_rank1, col_rank2, col_rank3 = st.columns(3)
with col_rank1:
    ano_rank = st.selectbox("1. Selecione o Ano", sorted(df['ANO_REFER'].unique(), reverse=True))
with col_rank2:
    rank_metric_name = st.selectbox("2. Rankear por:", list(bonus_cols.keys()))
with col_rank3:
    calc_type_rank = st.radio("Calcular Ranking por:", ["Total", "Média por Membro"], horizontal=True)

col_rank = bonus_cols[rank_metric_name]
df_rank_filtered = df[df['ANO_REFER'] == ano_rank]

if calc_type_rank == "Total":
    df_rank = df_rank_filtered.groupby('NOME_COMPANHIA')[col_rank].sum().nlargest(15).reset_index()
else:
    df_agg = df_rank_filtered.groupby('NOME_COMPANHIA').agg(Valor=(col_rank, 'sum'), Membros=('NUM_MEMBROS_BONUS_PLR', 'first')).reset_index()
    df_agg = df_agg[df_agg['Membros'] > 0]
    df_agg[col_rank] = df_agg['Valor'] / df_agg['Membros']
    df_rank = df_agg.nlargest(15, col_rank)
    
if not df_rank.empty and df_rank[col_rank].sum() > 0:
    fig_rank = px.bar(df_rank.sort_values(by=col_rank), x=col_rank, y='NOME_COMPANHIA', orientation='h', text_auto='.2s', 
                      title=f"Top 15 Empresas por {rank_metric_name} ({calc_type_rank}) em {format_year(ano_rank)}", template="streamlit") 
    fig_rank.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title=f"Valor {calc_type_rank} (R$)", yaxis_title="Empresa", separators=",.")
    st.plotly_chart(fig_rank, use_container_width=True)
    create_download_button(df_rank, f"ranking_bonus_plr_{ano_rank}")
else:
    st.info("Não há dados para gerar o ranking para a seleção atual.")
