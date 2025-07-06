import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import warnings
import io

# Ignorar avisos de depreciação futuros do pandas que podem poluir a saída
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Análise de Remuneração CVM")


# --- Funções Auxiliares ---
@st.cache_data
def load_data(url: str) -> pd.DataFrame:
    """
    Carrega os dados de uma URL, limpa, e renomeia colunas de forma robusta
    para facilitar as análises, espelhando a estrutura de blocos da CVM.
    """
    try:
        # CORREÇÃO DE ACENTUAÇÃO: Alterado encoding para utf-8-sig
        df = pd.read_csv(url, sep=',', encoding='utf-8-sig', engine='python')
        df.columns = df.columns.str.strip()

        # Mapeamento completo e flexível das colunas para nomes padronizados.
        rename_map = {
            # Identificação e Filtros Novos
            'NOME_COMPANHIA': ['DENOM_CIA'],
            'ANO_REFER': ['Ano do Exercício Social'],
            'ORGAO_ADMINISTRACAO': ['Orgao_Administracao'],
            'SETOR_ATIVIDADE': ['SETOR_DE_ATIVDADE', 'Setor de ativdade', 'Setor de Atividade', 'SETOR', 'ATIVIDADE'],
            'CONTROLE_ACIONARIO': ['CONTROLE_ACIONARIO'],
            'UF_SEDE': ['UF_SEDE'],
            
            # Bloco 1: Remuneração Individual (Máx/Média/Mín)
            'NUM_MEMBROS_INDIVIDUAL': ['Quantidade_Membros_Orgao_Remuneracao_Individual'],
            'REM_MAXIMA_INDIVIDUAL': ['Valor_Maior_Remuneracao_Individual_Reconhecida_Exercicio', 'Valor_Maior_Remuneracao_Individual', 'REMUNERACAO_MAXIMA', 'VALOR_MAIOR_REMUNERACAO'],
            'REM_MEDIA_INDIVIDUAL': ['Valor_Medio_Remuneracao_Individual_Reconhecida_Exercicio', 'Valor_Medio_Remuneracao_Individual', 'REMUNERACAO_MEDIA', 'VALOR_MEDIO_REMUNERACAO'],
            'REM_MINIMA_INDIVIDUAL': ['Valor_Menor_Remuneracao_Individual_Reconhecida_Exercicio', 'Valor_Menor_Remuneracao_Individual', 'REMUNERACAO_MINIMA', 'VALOR_MENOR_REMUNERACAO'],
            'DESVIO_PADRAO_INDIVIDUAL': ['Desvio_Padrao_Remuneracao_Individual_Reconhecida_Exercicio', 'DESVIO_PADRAO'],

            # Bloco 2: Componentes da Remuneração Total
            'NUM_MEMBROS_TOTAL': ['Quantidade_Total_Membros_Remunerados_Orgao', 'QTD_MEMBROS_REMUNERADOS_TOTAL'],
            'REM_FIXA_SALARIO': ['SALARIO'],
            'REM_FIXA_BENEFICIOS': ['BENEFICIOS_DIRETOS_INDIRETOS'],
            'REM_FIXA_COMITES': ['PARTICIPACOES_COMITES'],
            'REM_FIXA_OUTROS': ['OUTROS_VALORES_FIXOS'],
            'REM_VAR_BONUS': ['BONUS'],
            'REM_VAR_PLR': ['PARTICIPACAO_RESULTADOS'],
            'REM_VAR_REUNIOES': ['PARTICIPACAO_REUNIOES'],
            'REM_VAR_COMISSOES': ['COMISSOES'],
            'REM_VAR_OUTROS': ['OUTROS_VALORES_VARIAVEIS'],
            'REM_POS_EMPREGO': ['POS_EMPREGO'],
            'REM_CESSACAO_CARGO': ['CESSACAO_CARGO'],
            'REM_ACOES_BLOCO3': ['BASEADA_ACOES'],
            'TOTAL_REMUNERACAO_ORGAO': ['TOTAL_REMUNERACAO_ORGAO'],

            # Bloco 3: Métricas de Bônus e PLR
            'NUM_MEMBROS_BONUS_PLR': ['QTD_MEMBROS_REMUNERADOS_VARIAVEL'],
            'BONUS_MIN': ['BONUS_VALOR_MINIMO'],
            'BONUS_MAX': ['BONUS_VALOR_MAXIMO'],
            'BONUS_ALVO': ['BONUS_VALOR_METAS_ATINGIDAS'],
            'BONUS_PAGO': ['BONUS_VALOR_EFETIVO'],
            'PLR_MIN': ['PARTICIPACAO_VALOR_MINIMO'],
            'PLR_MAX': ['PARTICIPACAO_VALOR_MAXIMO'],
            'PLR_ALVO': ['PARTICIPACAO_VALOR_METAS_ATINGIDAS'],
            'PLR_PAGO': ['PARTICIPACAO_VALOR_EFETIVO'],
        }

        actual_rename_dict = {}
        for new_name, old_names in rename_map.items():
            for old_name in old_names:
                if old_name in df.columns:
                    actual_rename_dict[old_name] = new_name
                    break
        df.rename(columns=actual_rename_dict, inplace=True)
        
        # --- Verificação por Posição (Plano B) ---
        if 'SETOR_ATIVIDADE' not in df.columns and len(df.columns) >= 42:
            target_col_name = df.columns[41] # Posição 42 é índice 41
            df.rename(columns={target_col_name: 'SETOR_ATIVIDADE'}, inplace=True)
            st.sidebar.success(f"Coluna de atividade ('{target_col_name}') encontrada pela posição.")

        # Converte todas as colunas numéricas de uma vez
        all_numeric_cols = list(rename_map.keys())
        for col in all_numeric_cols:
            if 'NUM' in col or 'VALOR' in col or 'TOTAL' in col or 'REM' in col or 'PERC' in col or 'BONUS' in col or 'PLR' in col or 'DESVIO' in col:
                 if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                 else:
                    df[col] = 0

        # Limpeza e Padronização de Dados Categóricos
        categorical_cols = ['NOME_COMPANHIA', 'ORGAO_ADMINISTRACAO', 'SETOR_ATIVIDADE', 'CONTROLE_ACIONARIO', 'UF_SEDE']
        for col in categorical_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.upper().fillna(f'{col.replace("_", " ").title()} Não Informado')
            else:
                st.warning(f"Atenção: A coluna para '{col}' não foi encontrada. Um valor padrão será usado.")
                df[col] = f"{col.replace('_', ' ').title()} Não Informado"

        if 'ANO_REFER' in df.columns:
            df['ANO_REFER'] = pd.to_numeric(df['ANO_REFER'], errors='coerce').dropna().astype(int)
        
        return df
    except Exception as e:
        st.error(f"Erro crítico ao carregar ou processar os dados: {e}")
        return pd.DataFrame()

def get_default_index(options_list, default_value):
    """Retorna o índice de um valor padrão em uma lista, ou 0 se não for encontrado."""
    try:
        return options_list.index(default_value)
    except (ValueError, AttributeError):
        return 0

def create_download_button(df, filename):
    """Cria um botão de download para um DataFrame em formato Excel."""
    output = io.BytesIO()
    # CORREÇÃO DO ERRO DE DOWNLOAD: Alterado engine para 'openpyxl'
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    processed_data = output.getvalue()
    st.download_button(
        label="📥 Download dos dados do gráfico (Excel)",
        data=processed_data,
        file_name=f"{filename}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def format_year(year):
    """Adiciona '(projeção)' ao ano de 2025."""
    return f"{year} (projeção)" if year == 2025 else str(year)

# --- PÁGINAS DA APLICAÇÃO ---

def page_home():
    st.title("Análise Interativa de Remuneração de Administradores")
    
    # --- IMAGEM HARMONIZADA PARA DESKTOP E CELULAR ---
    # A URL foi atualizada para uma imagem com tema similar e proporção de banner.
    # use_container_width=True garante que a imagem se ajuste à largura da tela,
    # funcionando bem em qualquer dispositivo.
    st.image(
        "https://raw.githubusercontent.com/tovarich86/pesq_rem_CVM/main/Gemini_Generated_Image_k75a3hk75a3hk75a.png")    
    st.markdown("""
    Esta ferramenta foi desenvolvida para permitir a análise interativa dos dados de remuneração de administradores de companhias abertas brasileiras, utilizando como base o arquivo de dados compilado e disponibilizado. A metodologia empregada busca replicar e expandir as análises apresentadas em pesquisas de mercado, como a do IBGC.
    """)
    with st.expander("Clique para ver a Metodologia, Limitações e Fórmulas"):
        st.subheader("Metodologia")
        st.markdown("""
        **1. Fonte e Coleta de Dados:**
        * **Fonte Primária:** Os dados são carregados diretamente do arquivo `dados_cvm_mesclados.csv.csv` hospedado no repositório GitHub `tovarich86/pesq_rem_CVM`. A aplicação assume que este arquivo é uma compilação de diferentes formulários da CVM (Comissão de Valores Mobiliários), como o Formulário de Referência (FRE).
        * **Estrutura dos Dados:** A análise respeita a estrutura de blocos de dados descrita:
            * Remuneração Individual (Máxima, Média e Mínima).
            * Componentes da Remuneração Total (Fixa e Variável).
            * Métricas de Bônus e PLR (Alvo, Pago, etc.).

        **2. Tratamento e Limpeza dos Dados:**
        * **Padronização de Nomes:** Ao carregar, o aplicativo renomeia as colunas do arquivo para um formato padronizado, garantindo a resiliência do código a pequenas variações nos nomes das colunas.
        * **Limpeza de Dados Categóricos:** Colunas de texto como `NOME_COMPANHIA`, `SETOR_ATIVIDADE` e `ORGAO_ADMINISTRACAO` são automaticamente convertidas para maiúsculas e têm espaços em branco removidos, evitando que entradas como "Ambev" e "AMBEV " sejam tratadas como categorias diferentes.
        * **Tratamento de Nulos:** Valores numéricos ausentes ou não preenchidos no arquivo original são convertidos para `0` para evitar erros de cálculo.

        **3. Fórmulas e Cálculos:**
        * **Média por Membro:** Quando a opção "Média por Membro" é selecionada, o cálculo é realizado da seguinte forma:
            > *Média = Valor Total do Componente / Número de Membros Remunerados do Bloco*
        * **Quartis:** Na página de "Análise Estatística", os quartis são calculados utilizando a função `.describe()` da biblioteca Pandas sobre a série de dados de remuneração para cada setor.
        """)
        st.subheader("Limitações")
        st.markdown("""
        É fundamental que o usuário esteja ciente das seguintes limitações, inerentes à fonte dos dados e à natureza desta análise:

        1.  **Qualidade dos Dados de Origem:** A precisão das análises depende inteiramente da qualidade e da correção do preenchimento do Formulário de Referência (FRE) pelas companhias. São comuns inconsistências como número de membros incorreto, valores de remuneração zerados ou ausentes, o que pode levar a distorções.
        2.  **Remuneração via Controladores:** Esta análise considera apenas os valores pagos diretamente pela companhia. Remunerações pagas por controladores, holdings ou outras empresas do grupo não são capturadas, o que pode subestimar o valor total recebido por alguns administradores.
        3.  **Dados de 2025 são Projeções:** Os valores referentes ao ano de 2025 representam a **proposta de remuneração aprovada**, e não necessariamente o valor que será efetivamente pago.
        4.  **Arquivo CSV como Única Fonte:** O aplicativo depende exclusivamente do arquivo CSV fornecido. Quaisquer erros de compilação, extração ou tratamento prévio neste arquivo serão refletidos diretamente nas análises.
        """)



def page_remuneracao_individual(df: pd.DataFrame):
    st.header("Análise da Remuneração Individual")
    
    st.subheader("Evolução Comparativa por Empresa (2022-2024)")
    col1, col2 = st.columns(2)
    with col1:
        orgaos_disponiveis = sorted(df['ORGAO_ADMINISTRACAO'].unique())
        default_index = get_default_index(orgaos_disponiveis, 'DIRETORIA ESTATUTARIA')
        orgao = st.selectbox("1. Selecione o Órgão", orgaos_disponiveis, index=default_index, key='orgao_ind')
    df_orgao = df[df['ORGAO_ADMINISTRACAO'] == orgao]
    with col2:
        empresas_disponiveis = sorted(df_orgao['NOME_COMPANHIA'].unique())
        if not empresas_disponiveis:
            st.warning("Nenhuma empresa encontrada para o órgão selecionado.")
            st.stop()
        empresa = st.selectbox("2. Selecione a Empresa", empresas_disponiveis, key='empresa_ind')

    df_filtered = df_orgao[(df_orgao['NOME_COMPANHIA'] == empresa) & (df_orgao['ANO_REFER'].isin([2022, 2023, 2024]))]
    if not df_filtered.empty:
        df_analysis = df_filtered[['ANO_REFER', 'REM_MAXIMA_INDIVIDUAL', 'REM_MEDIA_INDIVIDUAL', 'REM_MINIMA_INDIVIDUAL']]
        df_plot = df_analysis.melt(id_vars=['ANO_REFER'], value_vars=['REM_MAXIMA_INDIVIDUAL', 'REM_MEDIA_INDIVIDUAL', 'REM_MINIMA_INDIVIDUAL'], var_name='Métrica', value_name='Valor')
        metric_names = {'REM_MAXIMA_INDIVIDUAL': 'Máxima', 'REM_MEDIA_INDIVIDUAL': 'Média', 'REM_MINIMA_INDIVIDUAL': 'Mínima'}
        df_plot['Métrica'] = df_plot['Métrica'].map(metric_names)
        df_plot = df_plot[df_plot['Valor'] > 0]
        if not df_plot.empty:
            fig = px.bar(df_plot, x='ANO_REFER', y='Valor', color='Métrica', barmode='group', text_auto='.2s', title=f"Evolução Comparativa da Remuneração Individual para {empresa}", labels={'ANO_REFER': 'Ano', 'Valor': 'Valor (R$)', 'Métrica': 'Tipo de Remuneração'})
            fig.update_layout(xaxis_type='category')
            st.plotly_chart(fig, use_container_width=True)
            create_download_button(df_plot, f"evolucao_rem_individual_{empresa}")
        else:
            st.info("Não há dados de remuneração individual para exibir no período de 2022-2024 para esta seleção.")
    else:
        st.warning("Nenhum dado encontrado para a combinação de filtros no período de 2022-2024.")

    st.markdown("---")
    st.subheader("Ranking de Empresas por Remuneração Individual")
    col_bar1, col_bar2 = st.columns(2)
    with col_bar1:
        ano_bar = st.selectbox("Selecione o Ano para o Ranking", sorted(df['ANO_REFER'].unique(), reverse=True), key='ano_bar')
    with col_bar2:
        metric_options = {'Máxima': 'REM_MAXIMA_INDIVIDUAL', 'Média': 'REM_MEDIA_INDIVIDUAL', 'Mínima': 'REM_MINIMA_INDIVIDUAL'}
        metrica_selecionada = st.selectbox("Selecione a Métrica", list(metric_options.keys()), key='metrica_bar')
    df_bar = df[(df['ANO_REFER'] == ano_bar) & (df['ORGAO_ADMINISTRACAO'] == orgao)]
    coluna_metrica = metric_options[metrica_selecionada]
    df_bar = df_bar[df_bar[coluna_metrica] > 0]
    df_top_companies = df_bar.nlargest(15, coluna_metrica)
    if not df_top_companies.empty:
        fig_bar = px.bar(df_top_companies.sort_values(by=coluna_metrica), x=coluna_metrica, y='NOME_COMPANHIA', orientation='h', text_auto='.2s', title=f"Top 15 Empresas por Remuneração {metrica_selecionada} ({orgao}, {format_year(ano_bar)})", labels={coluna_metrica: f"Remuneração {metrica_selecionada} (R$)", 'NOME_COMPANHIA': 'Empresa'})
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
        create_download_button(df_top_companies[['NOME_COMPANHIA', coluna_metrica]], f"ranking_rem_individual_{ano_bar}")
    else:
        st.warning(f"Não há dados de Remuneração {metrica_selecionada} para exibir para os filtros selecionados.")

def page_componentes_remuneracao(df: pd.DataFrame):
    st.header("Análise dos Componentes da Remuneração Total")
    analysis_type = st.selectbox("Escolha o tipo de análise:", ["Composição por Empresa (Ano Único)", "Evolução Anual Comparativa (por Empresa)", "Ranking de Empresas (Top 15)"], key="component_analysis_type")
    component_cols = {'Salário': 'REM_FIXA_SALARIO', 'Benefícios': 'REM_FIXA_BENEFICIOS', 'Comitês': 'REM_FIXA_COMITES', 'Bônus': 'REM_VAR_BONUS', 'PLR': 'REM_VAR_PLR', 'Comissões': 'REM_VAR_COMISSOES', 'Pós-Emprego': 'REM_POS_EMPREGO', 'Cessação': 'REM_CESSACAO_CARGO', 'Ações': 'REM_ACOES_BLOCO3', 'Outros': 'REM_FIXA_OUTROS'}

    if analysis_type == "Composição por Empresa (Ano Único)":
        st.subheader("Composição da Remuneração por Órgão")
        col1, col2 = st.columns(2)
        with col1:
            empresa = st.selectbox("1. Selecione a Empresa", sorted(df['NOME_COMPANHIA'].unique()), key='empresa_comp_1')
        df_empresa = df[df['NOME_COMPANHIA'] == empresa]
        with col2:
            ano = st.selectbox("2. Selecione o Ano", sorted(df_empresa['ANO_REFER'].unique(), reverse=True), key='ano_comp_1')
        df_filtered = df_empresa[df_empresa['ANO_REFER'] == ano]
        df_grouped = df_filtered.groupby('ORGAO_ADMINISTRACAO')[[col for col in component_cols.values() if col in df_filtered.columns]].sum()
        df_grouped['Total'] = df_grouped.sum(axis=1)
        df_grouped = df_grouped[df_grouped['Total'] > 0]
        if not df_grouped.empty:
            df_plot = df_grouped.drop(columns='Total').reset_index().melt(id_vars='ORGAO_ADMINISTRACAO', var_name='Componente', value_name='Valor')
            df_plot = df_plot[df_plot['Valor'] > 0]
            df_plot['Componente'] = df_plot['Componente'].map({v: k for k, v in component_cols.items()})
            fig = px.bar(df_plot, x='ORGAO_ADMINISTRACAO', y='Valor', color='Componente', title=f"Composição da Remuneração por Órgão para {empresa} em {format_year(ano)}", labels={'ORGAO_ADMINISTRACAO': 'Órgão', 'Valor': 'Valor (R$)'})
            fig.update_layout(barmode='stack')
            totals = df_grouped['Total']
            fig.add_trace(go.Scatter(x=totals.index, y=totals, text=[f"<b>R$ {val:,.0f}</b>" for val in totals], mode='text', textposition='top center', showlegend=False))
            st.plotly_chart(fig, use_container_width=True)
            create_download_button(df_grouped.reset_index(), f"composicao_orgaos_{empresa}_{ano}")
        else:
            st.info("Não há dados de componentes para exibir para a seleção atual.")

    elif analysis_type == "Evolução Anual Comparativa (por Empresa)":
        st.subheader("Evolução Anual dos Componentes")
        col1, col2, col3 = st.columns(3)
        with col1:
            empresa = st.selectbox("1. Selecione a Empresa", sorted(df['NOME_COMPANHIA'].unique()), key='empresa_comp_2')
        df_empresa = df[df['NOME_COMPANHIA'] == empresa]
        with col2:
            orgaos_disponiveis = sorted(df_empresa['ORGAO_ADMINISTRACAO'].unique())
            default_index = get_default_index(orgaos_disponiveis, 'DIRETORIA ESTATUTARIA')
            orgao = st.selectbox("2. Selecione o Órgão", orgaos_disponiveis, index=default_index, key='orgao_comp_2')
        with col3:
            calc_type = st.radio("Calcular por:", ["Total", "Média por Membro"], key='calc_type_2', horizontal=True)
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
            fig = px.bar(df_plot, x='ANO_REFER_FORMATTED', y='Valor', color='Componente', title=f"Evolução dos Componentes para {empresa} ({orgao})", labels={'ANO_REFER_FORMATTED': 'Ano', 'Valor': f'Valor {calc_type} (R$)'})
            fig.update_layout(xaxis_type='category', barmode='stack')
            totals = yearly_data.set_index('ANO_REFER_FORMATTED')['Total']
            if calc_type == "Média por Membro":
                membros = yearly_data.set_index('ANO_REFER_FORMATTED')['NUM_MEMBROS_TOTAL']
                labels = [f"<b>R$ {total:,.0f}</b><br>({membro:.0f} membros)" for total, membro in zip(totals, membros)]
            else:
                labels = [f"<b>R$ {val:,.0f}</b>" for val in totals]
            fig.add_trace(go.Scatter(x=totals.index, y=totals, text=labels, mode='text', textposition='top center', showlegend=False))
            st.plotly_chart(fig, use_container_width=True)
            create_download_button(yearly_data, f"evolucao_componentes_{empresa}_{orgao}")
        else:
            st.info("Não há dados para exibir para a seleção atual.")
            
    elif analysis_type == "Ranking de Empresas (Top 15)":
        st.subheader("Ranking de Empresas por Componente de Remuneração")
        col1, col2, col3 = st.columns(3)
        with col1:
            ano = st.selectbox("1. Selecione o Ano", sorted(df['ANO_REFER'].unique(), reverse=True), key='ano_comp_3')
        with col2:
            orgaos_disponiveis = sorted(df['ORGAO_ADMINISTRACAO'].unique())
            default_index = get_default_index(orgaos_disponiveis, 'DIRETORIA ESTATUTARIA')
            orgao = st.selectbox("2. Selecione o Órgão", orgaos_disponiveis, index=default_index, key='orgao_comp_3')
        rank_options = {'Remuneração Total': 'TOTAL_REMUNERACAO_ORGAO', **component_cols}
        with col3:
            rank_metric_name = st.selectbox("3. Rankear por:", list(rank_options.keys()), key='rank_metric_3')
        col_rank = rank_options[rank_metric_name]
        calc_type = st.radio("Calcular por:", ["Total", "Média por Membro"], key='calc_type_3', horizontal=True)
        df_filtered = df[(df['ANO_REFER'] == ano) & (df['ORGAO_ADMINISTRACAO'] == orgao)]
        if calc_type == "Total":
            df_rank = df_filtered.groupby('NOME_COMPANHIA')[col_rank].sum().nlargest(15).reset_index()
        else: # Média por Membro
            df_agg = df_filtered.groupby('NOME_COMPANHIA').agg(Valor=(col_rank, 'sum'), Membros=('NUM_MEMBROS_TOTAL', 'first')).reset_index()
            df_agg = df_agg[df_agg['Membros'] > 0]
            df_agg[col_rank] = df_agg['Valor'] / df_agg['Membros']
            df_rank = df_agg.nlargest(15, col_rank)
        if not df_rank.empty and df_rank[col_rank].sum() > 0:
            fig = px.bar(df_rank.sort_values(by=col_rank), x=col_rank, y='NOME_COMPANHIA', orientation='h', text_auto='.2s', title=f"Top 15 Empresas por {rank_metric_name} ({calc_type}) em {format_year(ano)}")
            fig.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title=f"Valor {calc_type} (R$)", yaxis_title="Empresa")
            st.plotly_chart(fig, use_container_width=True)
            create_download_button(df_rank, f"ranking_componentes_{ano}_{orgao}")
        else:
            st.info("Não há dados para gerar o ranking para a seleção atual.")

def page_bonus_plr(df: pd.DataFrame):
    st.header("Análise Detalhada de Bônus e Participação nos Resultados")
    st.subheader("Evolução Comparativa de Bônus e PLR")
    col1, col2, col3 = st.columns(3)
    with col1:
        empresa = st.selectbox("1. Selecione a Empresa", sorted(df['NOME_COMPANHIA'].unique()), key='empresa_bonus_1')
    df_empresa = df[df['NOME_COMPANHIA'] == empresa]
    with col2:
        orgaos_disponiveis = sorted(df_empresa['ORGAO_ADMINISTRACAO'].unique())
        default_index = get_default_index(orgaos_disponiveis, 'DIRETORIA ESTATUTARIA')
        orgao = st.selectbox("2. Selecione o Órgão", orgaos_disponiveis, index=default_index, key='orgao_bonus_1')
    with col3:
        calc_type = st.radio("Calcular por:", ["Total", "Média por Membro"], key='calc_type_bonus_1', horizontal=True)
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
        fig = px.bar(df_plot, x='ANO_REFER_FORMATTED', y='Valor', color='Métrica', barmode='group', facet_col='Tipo', title=f"Evolução de Bônus e PLR para {empresa} ({orgao})", labels={'ANO_REFER_FORMATTED': 'Ano', 'Valor': f'Valor {calc_type} (R$)'})
        fig.update_xaxes(type='category')
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
        ano_rank = st.selectbox("1. Selecione o Ano", sorted(df['ANO_REFER'].unique(), reverse=True), key='ano_bonus_rank')
    with col_rank2:
        rank_metric_name = st.selectbox("2. Rankear por:", list(bonus_cols.keys()), key='metric_bonus_rank')
    with col_rank3:
        calc_type_rank = st.radio("Calcular por:", ["Total", "Média por Membro"], key='calc_type_bonus_rank', horizontal=True)
    col_rank = bonus_cols[rank_metric_name]
    df_rank_filtered = df[df['ANO_REFER'] == ano_rank]
    if calc_type_rank == "Total":
        df_rank = df_rank_filtered.groupby('NOME_COMPANHIA')[col_rank].sum().nlargest(15).reset_index()
    else: # Média
        df_agg = df_rank_filtered.groupby('NOME_COMPANHIA').agg(Valor=(col_rank, 'sum'), Membros=('NUM_MEMBROS_BONUS_PLR', 'first')).reset_index()
        df_agg = df_agg[df_agg['Membros'] > 0]
        df_agg[col_rank] = df_agg['Valor'] / df_agg['Membros']
        df_rank = df_agg.nlargest(15, col_rank)
    if not df_rank.empty and df_rank[col_rank].sum() > 0:
        fig_rank = px.bar(df_rank.sort_values(by=col_rank), x=col_rank, y='NOME_COMPANHIA', orientation='h', text_auto='.2s', title=f"Top 15 Empresas por {rank_metric_name} ({calc_type_rank}) em {format_year(ano_rank)}")
        fig_rank.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title=f"Valor {calc_type_rank} (R$)", yaxis_title="Empresa")
        st.plotly_chart(fig_rank, use_container_width=True)
        create_download_button(df_rank, f"ranking_bonus_plr_{ano_rank}")
    else:
        st.info("Não há dados para gerar o ranking para a seleção atual.")

def page_estatisticas_quartis(df: pd.DataFrame):
    st.header("Análise Estatística por Quartis")
    metric_options = {
        'Remuneração Máxima': 'REM_MAXIMA_INDIVIDUAL', 'Remuneração Média': 'REM_MEDIA_INDIVIDUAL', 'Remuneração Mínima': 'REM_MINIMA_INDIVIDUAL',
        'Remuneração Total do Órgão': 'TOTAL_REMUNERACAO_ORGAO', 'Salário': 'REM_FIXA_SALARIO', 'Bônus Pago': 'BONUS_PAGO'
    }
    col1, col2, col3 = st.columns(3)
    with col1:
        ano = st.selectbox("1. Selecione o Ano", sorted(df['ANO_REFER'].unique(), reverse=True), key='ano_quartil')
    with col2:
        orgaos_disponiveis = sorted(df['ORGAO_ADMINISTRACAO'].unique())
        default_index = get_default_index(orgaos_disponiveis, 'DIRETORIA ESTATUTARIA')
        orgao = st.selectbox("2. Selecione o Órgão", orgaos_disponiveis, index=default_index, key='orgao_quartil')
    with col3:
        metrica = st.selectbox("3. Selecione a Métrica", list(metric_options.keys()), key='metrica_quartil')
    
    calc_type = st.radio("Calcular por:", ["Total", "Média por Membro"], key='calc_type_quartil', horizontal=True)
    
    col_metrica = metric_options[metrica]
    df_filtered = df[(df['ANO_REFER'] == ano) & (df['ORGAO_ADMINISTRACAO'] == orgao)]
    
    # Define a coluna de membros correta para o cálculo da média
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
        st.subheader(f"Estatísticas por Setor de Atividade ({format_year(ano)})")
        df_stats_sector = df_filtered.groupby('SETOR_ATIVIDADE')[col_metrica].describe().reset_index()
        df_stats_sector = df_stats_sector.rename(columns={'count': 'Nº de Companhias', 'mean': 'Média', 'std': 'Desvio Padrão', 'min': 'Mínimo', '25%': '1º Quartil', '50%': 'Mediana (2º Q)', '75%': '3º Quartil', 'max': 'Máximo'})
        st.dataframe(df_stats_sector.style.format({'Nº de Companhias': '{:,.0f}', 'Média': 'R$ {:,.2f}', 'Desvio Padrão': 'R$ {:,.2f}', 'Mínimo': 'R$ {:,.2f}', '1º Quartil': 'R$ {:,.2f}', 'Mediana (2º Q)': 'R$ {:,.2f}', '3º Quartil': 'R$ {:,.2f}', 'Máximo': 'R$ {:,.2f}'}))
        create_download_button(df_stats_sector, f"estatisticas_setor_{ano}_{orgao}")

        st.subheader(f"Estatísticas para a Amostra Total Filtrada ({format_year(ano)})")
        df_stats_total = df_filtered[col_metrica].describe().to_frame().T
        df_stats_total = df_stats_total.rename(columns={'count': 'Nº de Companhias', 'mean': 'Média', 'std': 'Desvio Padrão', 'min': 'Mínimo', '25%': '1º Quartil', '50%': 'Mediana (2º Q)', '75%': '3º Quartil', 'max': 'Máximo'})
        st.dataframe(df_stats_total.style.format({'Nº de Companhias': '{:,.0f}', 'Média': 'R$ {:,.2f}', 'Desvio Padrão': 'R$ {:,.2f}', 'Mínimo': 'R$ {:,.2f}', '1º Quartil': 'R$ {:,.2f}', 'Mediana (2º Q)': 'R$ {:,.2f}', '3º Quartil': 'R$ {:,.2f}', 'Máximo': 'R$ {:,.2f}'}))
        create_download_button(df_stats_total, f"estatisticas_total_{ano}_{orgao}")
    else:
        st.warning("Não há dados para gerar a tabela de quartis para a seleção atual.")

# --- Função Principal da Aplicação ---
def main():
    github_url = "https://raw.githubusercontent.com/tovarich86/pesq_rem_CVM/main/dados_cvm_mesclados.csv.csv"
    df_original = load_data(github_url)
    if df_original.empty:
        st.error("Falha no carregamento dos dados. O aplicativo não pode continuar.")
        st.stop()

    st.sidebar.title("Painel de Análise")
    st.sidebar.image("https://www.ibgc.org.br/themes/ibgc/dist/images/logo-default.svg", width=150)
    st.sidebar.header("Filtros Globais")
    
    ufs_disponiveis = ["TODAS"] + sorted(df_original['UF_SEDE'].unique())
    uf = st.sidebar.selectbox("UF da Sede", ufs_disponiveis)
    setores_disponiveis = ["TODOS"] + sorted(df_original['SETOR_ATIVIDADE'].unique())
    setor = st.sidebar.selectbox("Setor de Atividade", setores_disponiveis)
    controles_disponiveis = ["TODOS"] + sorted(df_original['CONTROLE_ACIONARIO'].unique())
    controle = st.sidebar.selectbox("Controle Acionário", controles_disponiveis)

    df_filtrado = df_original.copy()
    if uf != "TODAS":
        df_filtrado = df_filtrado[df_filtrado['UF_SEDE'] == uf]
    if setor != "TODOS":
        df_filtrado = df_filtrado[df_filtrado['SETOR_ATIVIDADE'] == setor]
    if controle != "TODOS":
        df_filtrado = df_filtrado[df_filtrado['CONTROLE_ACIONARIO'] == controle]

    pagina_selecionada = st.sidebar.radio(
        "Selecione a Análise:",
        ["Página Inicial", "Remuneração Individual (Máx/Média/Mín)", "Componentes da Remuneração Total", "Bônus e PLR", "Análise Estatística (Quartis)"]
    )
    
    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado para os filtros globais selecionados. Por favor, ajuste os filtros na barra lateral.")
        st.stop()

    if pagina_selecionada == "Página Inicial":
        page_home()
    elif pagina_selecionada == "Remuneração Individual (Máx/Média/Mín)":
        page_remuneracao_individual(df_filtrado)
    elif pagina_selecionada == "Componentes da Remuneração Total":
        page_componentes_remuneracao(df_filtrado)
    elif pagina_selecionada == "Bônus e PLR":
        page_bonus_plr(df_filtrado)
    elif pagina_selecionada == "Análise Estatística (Quartis)":
        page_estatisticas_quartis(df_filtrado)


if __name__ == "__main__":
    main()
