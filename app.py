import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import warnings

# Ignorar avisos de depreciação futuros do pandas que podem poluir a saída
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Análise de Remuneração CVM")


# --- Carregamento e Preparação dos Dados ---
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
            
            # Bloco 1: Remuneração Baseada em Ações
            'NUM_MEMBROS_ACOES': ['Quantidade_Membros_Remunerados_Com_Acoes_Opcoes'],
            'VALOR_OPCOES_EXERCIDAS': ['Valor_Total_Opcoes_Acoes_Exercidas_Reconhecidas_Resultado_Exercicio'],
            'VALOR_ACOES_RESTRITAS': ['Valor_Total_Acoes_Restritas_Entregues_Reconhecidas_Resultado_Exercicio'],
            'VALOR_OUTROS_PLANOS_ACOES': ['Valor_Total_Outros_Planos_Baseados_Acoes_Reconhecidos_Resultado_Exercicio'],
            'TOTAL_REM_ACOES_BLOCO1': ['Valor_Total_Remuneracao_Baseada_Acoes_Reconhecida_Resultado_Exercicio'],

            # Bloco 2: Remuneração Individual (Máx/Média/Mín)
            'NUM_MEMBROS_INDIVIDUAL': ['Quantidade_Membros_Orgao_Remuneracao_Individual'],
            'REM_MAXIMA_INDIVIDUAL': ['Valor_Maior_Remuneracao_Individual_Reconhecida_Exercicio', 'Valor_Maior_Remuneracao_Individual', 'REMUNERACAO_MAXIMA', 'VALOR_MAIOR_REMUNERACAO'],
            'REM_MEDIA_INDIVIDUAL': ['Valor_Medio_Remuneracao_Individual_Reconhecida_Exercicio', 'Valor_Medio_Remuneracao_Individual', 'REMUNERACAO_MEDIA', 'VALOR_MEDIO_REMUNERACAO'],
            'REM_MINIMA_INDIVIDUAL': ['Valor_Menor_Remuneracao_Individual_Reconhecida_Exercicio', 'Valor_Menor_Remuneracao_Individual', 'REMUNERACAO_MINIMA', 'VALOR_MENOR_REMUNERACAO'],
            'DESVIO_PADRAO_INDIVIDUAL': ['Desvio_Padrao_Remuneracao_Individual_Reconhecida_Exercicio', 'DESVIO_PADRAO'],

            # Bloco 3: Componentes da Remuneração Total
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

            # Bloco 4: Métricas de Bônus e PLR
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

# --- Funções Auxiliares ---
def get_default_index(options_list, default_value):
    """Retorna o índice de um valor padrão em uma lista, ou 0 se não for encontrado."""
    if default_value in options_list:
        return options_list.index(default_value)
    return 0

# --- PÁGINAS DA APLICAÇÃO ---

def page_home():
    st.title("Análise Interativa de Remuneração de Administradores")
    st.markdown("""
    Bem-vindo(a) à ferramenta de análise de remuneração de companhias abertas brasileiras. Esta aplicação foi estruturada para refletir os blocos de dados do Formulário de Referência da CVM.

    **Como usar:**
    1.  **Use os filtros na barra lateral** para refinar sua análise por UF, Setor ou Controle Acionário. Esses filtros são globais.
    2.  **Navegue pelas seções temáticas** no menu principal para explorar diferentes aspectos da remuneração.
    
    **Seções de Análise:**
    - **Remuneração Individual (Máx/Média/Mín):** Analise a dispersão salarial dentro de um órgão (maior, menor e média remuneração individual).
    - **Componentes da Remuneração Total:** Veja a composição da remuneração total do órgão (salário, bônus, benefícios) e sua evolução.
    - **Bônus e PLR:** Investigue os bônus, participação nos lucros e métricas de desempenho.
    - **Remuneração Baseada em Ações:** Foque nos pagamentos via opções e ações.
    """)

def page_remuneracao_individual(df: pd.DataFrame):
    st.header("Análise da Remuneração Individual")
    
    st.subheader("Evolução Comparativa por Empresa (2022-2024)")
    # Filtros para selecionar órgão e empresa
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

    # Filtra para a empresa e órgão selecionados, e apenas para os anos com dados reais (2022-2024)
    df_filtered = df_orgao[(df_orgao['NOME_COMPANHIA'] == empresa) & (df_orgao['ANO_REFER'].isin([2022, 2023, 2024]))]
    
    if not df_filtered.empty:
        df_analysis = df_filtered[['ANO_REFER', 'REM_MAXIMA_INDIVIDUAL', 'REM_MEDIA_INDIVIDUAL', 'REM_MINIMA_INDIVIDUAL']]
        df_plot = df_analysis.melt(id_vars=['ANO_REFER'], 
                                   value_vars=['REM_MAXIMA_INDIVIDUAL', 'REM_MEDIA_INDIVIDUAL', 'REM_MINIMA_INDIVIDUAL'],
                                   var_name='Métrica', 
                                   value_name='Valor')
        
        metric_names = {'REM_MAXIMA_INDIVIDUAL': 'Máxima', 'REM_MEDIA_INDIVIDUAL': 'Média', 'REM_MINIMA_INDIVIDUAL': 'Mínima'}
        df_plot['Métrica'] = df_plot['Métrica'].map(metric_names)
        df_plot = df_plot[df_plot['Valor'] > 0]

        if not df_plot.empty:
            fig = px.bar(
                df_plot, x='ANO_REFER', y='Valor', color='Métrica', barmode='group',
                text_auto='.2s', title=f"Evolução Comparativa da Remuneração Individual para {empresa}",
                labels={'ANO_REFER': 'Ano', 'Valor': 'Valor (R$)', 'Métrica': 'Tipo de Remuneração'}
            )
            fig.update_layout(xaxis_type='category')
            st.plotly_chart(fig, use_container_width=True)
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
        fig_bar = px.bar(
            df_top_companies.sort_values(by=coluna_metrica),
            x=coluna_metrica, y='NOME_COMPANHIA', orientation='h', text_auto='.2s',
            title=f"Top 15 Empresas por Remuneração {metrica_selecionada} ({orgao}, {ano_bar})",
            labels={coluna_metrica: f"Remuneração {metrica_selecionada} (R$)", 'NOME_COMPANHIA': 'Empresa'}
        )
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.warning(f"Não há dados de Remuneração {metrica_selecionada} para exibir para os filtros selecionados.")

def page_componentes_remuneracao(df: pd.DataFrame):
    st.header("Análise dos Componentes da Remuneração Total")

    analysis_type = st.selectbox(
        "Escolha o tipo de análise:",
        ["Composição por Empresa (Ano Único)", "Evolução Anual Comparativa (por Empresa)", "Ranking de Empresas (Top 15)"],
        key="component_analysis_type"
    )

    component_cols = {
        'Salário': 'REM_FIXA_SALARIO', 'Benefícios': 'REM_FIXA_BENEFICIOS', 'Comitês': 'REM_FIXA_COMITES',
        'Bônus': 'REM_VAR_BONUS', 'PLR': 'REM_VAR_PLR', 'Comissões': 'REM_VAR_COMISSOES',
        'Pós-Emprego': 'REM_POS_EMPREGO', 'Cessação': 'REM_CESSACAO_CARGO',
        'Ações': 'REM_ACOES_BLOCO3', 'Outros': 'REM_FIXA_OUTROS'
    }

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
            fig = px.bar(df_plot, x='ORGAO_ADMINISTRACAO', y='Valor', color='Componente', title=f"Composição da Remuneração por Órgão para {empresa} em {ano}", labels={'ORGAO_ADMINISTRACAO': 'Órgão', 'Valor': 'Valor (R$)'})
            fig.update_layout(barmode='stack')
            totals = df_grouped['Total']
            fig.add_trace(go.Scatter(x=totals.index, y=totals, text=[f"<b>R$ {val:,.0f}</b>" for val in totals], mode='text', textposition='top center', showlegend=False))
            st.plotly_chart(fig, use_container_width=True)
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
            fig = px.bar(df_plot, x='ANO_REFER', y='Valor', color='Componente', title=f"Evolução dos Componentes para {empresa} ({orgao})", labels={'ANO_REFER': 'Ano', 'Valor': f'Valor {calc_type} (R$)'})
            fig.update_layout(xaxis_type='category', barmode='stack')
            
            # Adiciona o totalizador com o número de membros (se aplicável)
            totals = yearly_data.set_index('ANO_REFER')['Total']
            if calc_type == "Média por Membro":
                membros = yearly_data.set_index('ANO_REFER')['NUM_MEMBROS_TOTAL']
                labels = [f"<b>R$ {total:,.0f}</b><br>({membro:.0f} membros)" for total, membro in zip(totals, membros)]
            else:
                labels = [f"<b>R$ {val:,.0f}</b>" for val in totals]
            
            fig.add_trace(go.Scatter(x=totals.index, y=totals, text=labels, mode='text', textposition='top center', showlegend=False))
            st.plotly_chart(fig, use_container_width=True)
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
            fig = px.bar(df_rank.sort_values(by=col_rank), x=col_rank, y='NOME_COMPANHIA', orientation='h', text_auto='.2s', title=f"Top 15 Empresas por {rank_metric_name} ({calc_type})")
            fig.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title=f"Valor {calc_type} (R$)", yaxis_title="Empresa")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Não há dados para gerar o ranking para a seleção atual.")

def page_bonus_plr(df: pd.DataFrame):
    st.header("Análise Detalhada de Bônus e Participação nos Resultados")

    # --- Análise 1: Evolução Comparativa por Empresa ---
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

    bonus_cols = {'Bônus Mínimo': 'BONUS_MIN', 'Bônus Alvo': 'BONUS_ALVO', 'Bônus Máximo': 'BONUS_MAX', 'Bônus Pago': 'BONUS_PAGO',
                  'PLR Mínimo': 'PLR_MIN', 'PLR Alvo': 'PLR_ALVO', 'PLR Máximo': 'PLR_MAX', 'PLR Pago': 'PLR_PAGO'}
    
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
        fig = px.bar(df_plot, x='ANO_REFER', y='Valor', color='Métrica', barmode='group', facet_col='Tipo',
                     title=f"Evolução de Bônus e PLR para {empresa} ({orgao})",
                     labels={'ANO_REFER': 'Ano', 'Valor': f'Valor {calc_type} (R$)'})
        fig.update_xaxes(type='category')
        st.plotly_chart(fig, use_container_width=True)

        # Análise de Performance (% do Alvo)
        st.subheader("Performance: % do Alvo Efetivamente Pago")
        perf_cols = st.columns(len(yearly_data))
        for i, row in yearly_data.iterrows():
            with perf_cols[i]:
                st.write(f"**{row['ANO_REFER']}**")
                if row['BONUS_ALVO'] > 0:
                    perc_bonus = (row['BONUS_PAGO'] / row['BONUS_ALVO']) * 100
                    st.metric(label="Bônus", value=f"{perc_bonus:.1f}%")
                if row['PLR_ALVO'] > 0:
                    perc_plr = (row['PLR_PAGO'] / row['PLR_ALVO']) * 100
                    st.metric(label="PLR", value=f"{perc_plr:.1f}%")
    else:
        st.info("Não há dados de Bônus ou PLR para exibir para a seleção atual.")

    # --- Análise 2: Ranking de Empresas ---
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
        fig_rank = px.bar(df_rank.sort_values(by=col_rank), x=col_rank, y='NOME_COMPANHIA', orientation='h', text_auto='.2s', title=f"Top 15 Empresas por {rank_metric_name} ({calc_type_rank})")
        fig_rank.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title=f"Valor {calc_type_rank} (R$)", yaxis_title="Empresa")
        st.plotly_chart(fig_rank, use_container_width=True)
    else:
        st.info("Não há dados para gerar o ranking para a seleção atual.")


def page_remuneracao_acoes(df: pd.DataFrame):
    st.header("Análise de Remuneração Baseada em Ações")
    ano = st.selectbox("Selecione o Ano", sorted(df['ANO_REFER'].unique(), reverse=True), key='ano_acoes')
    df_ano = df[df['ANO_REFER'] == ano]
    st.subheader(f"Ranking de Empresas por Remuneração em Ações ({ano})")
    rem_acoes_cia = df_ano.groupby('NOME_COMPANHIA')['TOTAL_REM_ACOES_BLOCO1'].sum().nlargest(10).reset_index()
    if not rem_acoes_cia[rem_acoes_cia['TOTAL_REM_ACOES_BLOCO1'] > 0].empty:
        fig = px.bar(rem_acoes_cia, x='NOME_COMPANHIA', y='TOTAL_REM_ACOES_BLOCO1', text_auto='.2s', title="Top 10 Empresas por Valor Total")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Não há dados de remuneração baseada em ações para o ano.")

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
        ["Página Inicial", "Remuneração Individual (Máx/Média/Mín)", "Componentes da Remuneração Total", "Bônus e PLR", "Remuneração Baseada em Ações"]
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
    elif pagina_selecionada == "Remuneração Baseada em Ações":
        page_remuneracao_acoes(df_filtrado)


if __name__ == "__main__":
    main()
