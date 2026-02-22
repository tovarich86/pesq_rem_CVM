import streamlit as st
import pandas as pd

from utils import get_default_index, create_download_button, renderizar_sidebar_global, format_year, formata_brl

st.set_page_config(layout="wide", page_title="Análise Estatística", page_icon="📈")

if 'df_completo' not in st.session_state:
    st.warning("⚠️ Por favor, aceda à 'Página Inicial' (Home) primeiro para carregar a base de dados.")
    st.stop()

df_original = st.session_state['df_completo']
df = renderizar_sidebar_global(df_original)

if df.empty:
    st.warning("Nenhum dado encontrado para os filtros globais selecionados.")
    st.stop()

st.header("Análise Estatística por Quartis")
metric_options = {
    'Remuneração Máxima': 'REM_MAXIMA_INDIVIDUAL', 'Remuneração Média': 'REM_MEDIA_INDIVIDUAL', 'Remuneração Mínima': 'REM_MINIMA_INDIVIDUAL',
    'Remuneração Total do Órgão': 'TOTAL_REMUNERACAO_ORGAO', 'Salário': 'REM_FIXA_SALARIO', 'Bônus Pago': 'BONUS_PAGO'
}

col1, col2, col3 = st.columns(3)
with col1:
    ano = st.selectbox("1. Selecione o Ano", sorted(df['ANO_REFER'].unique(), reverse=True))
with col2:
    orgaos_disponiveis = sorted(df['ORGAO_ADMINISTRACAO'].unique())
    orgao = st.selectbox("2. Selecione o Órgão", orgaos_disponiveis, index=get_default_index(orgaos_disponiveis, 'DIRETORIA ESTATUTARIA'))
with col3:
    metrica = st.selectbox("3. Selecione a Métrica", list(metric_options.keys()))

calc_type = st.radio("Calcular por:", ["Total", "Média por Membro"], horizontal=True)

col_metrica = metric_options[metrica]
df_filtered = df[(df['ANO_REFER'] == ano) & (df['ORGAO_ADMINISTRACAO'] == orgao)]

if metrica in ['Bônus Pago']:
    membros_col = 'NUM_MEMBROS_BONUS_PLR'
elif metrica in ['Remuneração Máxima', 'Remuneração Média', 'Remuneração Mínima']:
    membros_col = 'NUM_MEMBROS_INDIVIDUAL'
else:
    membros_col = 'NUM_MEMBROS_TOTAL'
    
if calc_type == "Média por Membro":
    df_filtered = df_filtered[df_filtered[membros_col] > 0].copy()
    df_filtered.loc[:, col_metrica] = df_filtered[col_metrica] / df_filtered[membros_col]

df_filtered = df_filtered[df_filtered[col_metrica] > 0]

if not df_filtered.empty:
    format_dict = {
        'Nº de Companhias': lambda x: f"{x:_.0f}".replace('_', '.'),
        'Média': formata_brl,
        'Desvio Padrão': formata_brl,
        'Mínimo': formata_brl,
        '1º Quartil': formata_brl,
        'Mediana (2º Q)': formata_brl,
        '3º Quartil': formata_brl,
        'Máximo': formata_brl
    }

    st.subheader(f"Estatísticas por Setor de Atividade ({format_year(ano)})")
    df_stats_sector = df_filtered.groupby('SETOR_ATIVIDADE')[col_metrica].describe().reset_index()
    df_stats_sector = df_stats_sector.rename(columns={'count': 'Nº de Companhias', 'mean': 'Média', 'std': 'Desvio Padrão', 'min': 'Mínimo', '25%': '1º Quartil', '50%': 'Mediana (2º Q)', '75%': '3º Quartil', 'max': 'Máximo'})
    st.dataframe(df_stats_sector.style.format(format_dict))
    create_download_button(df_stats_sector, f"estatisticas_setor_{ano}_{orgao}")

    st.subheader(f"Estatísticas para a Amostra Total Filtrada ({format_year(ano)})")
    df_stats_total = df_filtered[col_metrica].describe().to_frame().T
    df_stats_total = df_stats_total.rename(columns={'count': 'Nº de Companhias', 'mean': 'Média', 'std': 'Desvio Padrão', 'min': 'Mínimo', '25%': '1º Quartil', '50%': 'Mediana (2º Q)', '75%': '3º Quartil', 'max': 'Máximo'})
    st.dataframe(df_stats_total.style.format(format_dict))
    create_download_button(df_stats_total, f"estatisticas_total_{ano}_{orgao}")
else:
    st.warning("Não há dados para gerar a tabela de quartis para a seleção atual.")
