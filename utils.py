import streamlit as st
import pandas as pd
import io

# --- FORMATADORES DE TEXTO E MOEDA ---
def formata_brl(valor):
    """Formata número para moeda BR (ex: R$ 1.234.567,89)"""
    return f"R$ {valor:_.2f}".replace('.', ',').replace('_', '.')

def formata_brl_int(valor):
    """Formata número inteiro para moeda BR (ex: R$ 1.234.567)"""
    return f"R$ {valor:_.0f}".replace('_', '.')

def format_year(year):
    """Adiciona '(projeção)' ao ano de 2025."""
    return f"{year} (projeção)" if year == 2025 else str(year)

def formata_abrev(valor):
    """Formata números grandes para K ou M (ex: 1,2M, 500k) limitando os caracteres."""
    if valor >= 1_000_000:
        return f"{valor/1_000_000:.1f}M".replace('.', ',')
    elif valor >= 1_000:
        return f"{valor/1_000:.0f}k"
    else:
        return str(int(valor))


# --- FUNÇÕES AUXILIARES ---
def get_default_index(options_list, default_value):
    """Retorna o índice de um valor padrão numa lista, ou 0 se não for encontrado."""
    try:
        return options_list.index(default_value)
    except (ValueError, AttributeError):
        return 0

def create_download_button(df, filename):
    """Cria um botão de download para um DataFrame em formato Excel."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    processed_data = output.getvalue()
    st.download_button(
        label="📥 Download dos dados (Excel)",
        data=processed_data,
        file_name=f"{filename}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# --- BARRA LATERAL GLOBAL COMPARTILHADA ---
def renderizar_sidebar_global(df_original):
    """Cria a barra lateral de filtros e aplica o st.session_state para guardar as escolhas."""
    st.sidebar.title("Filtros Globais")

    # Inicializa as variáveis no Session State se elas não existirem
    if 'uf_selecionada' not in st.session_state: st.session_state['uf_selecionada'] = "TODAS"
    if 'setor_selecionado' not in st.session_state: st.session_state['setor_selecionado'] = "TODOS"
    if 'controle_selecionado' not in st.session_state: st.session_state['controle_selecionado'] = "TODOS"

    # Filtro de UF
    ufs_disponiveis = ["TODAS"] + sorted(df_original['UF_SEDE'].unique())
    idx_uf = get_default_index(ufs_disponiveis, st.session_state['uf_selecionada'])
    uf = st.sidebar.selectbox("UF da Sede", ufs_disponiveis, index=idx_uf)
    st.session_state['uf_selecionada'] = uf # Guarda a escolha

    # Filtro de Setor
    setores_disponiveis = ["TODOS"] + sorted(df_original['SETOR_ATIVIDADE'].unique())
    idx_setor = get_default_index(setores_disponiveis, st.session_state['setor_selecionado'])
    setor = st.sidebar.selectbox("Setor de Atividade", setores_disponiveis, index=idx_setor)
    st.session_state['setor_selecionado'] = setor

    # Filtro de Controle Acionário
    controles_disponiveis = ["TODOS"] + sorted(df_original['CONTROLE_ACIONARIO'].unique())
    idx_controle = get_default_index(controles_disponiveis, st.session_state['controle_selecionado'])
    controle = st.sidebar.selectbox("Controle Acionário", controles_disponiveis, index=idx_controle)
    st.session_state['controle_selecionado'] = controle

    # Aplica os filtros ao DataFrame
    df_filtrado = df_original.copy()
    if uf != "TODAS":
        df_filtrado = df_filtrado[df_filtrado['UF_SEDE'] == uf]
    if setor != "TODOS":
        df_filtrado = df_filtrado[df_filtrado['SETOR_ATIVIDADE'] == setor]
    if controle != "TODOS":
        df_filtrado = df_filtrado[df_filtrado['CONTROLE_ACIONARIO'] == controle]

    return df_filtrado
