import streamlit as st
import pandas as pd
from fuzzywuzzy import fuzz, process
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Configuração da página
st.set_page_config(
    page_title="Busca de Projetos",
    page_icon="��",
    layout="wide"
)

# Título da aplicação
st.title("🔍 Sistema de Busca de Projetos")
st.markdown("---")


# Download dos recursos do NLTK (com cache para evitar downloads repetidos)
@st.cache_resource
def download_nltk_resources():
    try:
        nltk.download('stopwords', quiet=True)
        nltk.download('punkt', quiet=True)
        return True
    except Exception as e:
        st.error(f"Erro ao baixar recursos do NLTK: {e}")
        return False


# Função para validar e processar o arquivo carregado
def processar_arquivo(uploaded_file):
    try:
        # Ler o arquivo Excel
        info = pd.read_excel(uploaded_file)
        info_df = pd.DataFrame(info)

        # Verificar se as colunas necessárias existem
        colunas_necessarias = ['ID do Projeto', 'Descrição', 'Custo proposto', 'Nome do Projeto']
        colunas_faltantes = [col for col in colunas_necessarias if col not in info_df.columns]

        if colunas_faltantes:
            st.error(f"❌ As seguintes colunas são obrigatórias e não foram encontradas: {', '.join(colunas_faltantes)}")
            st.info("💡 **Colunas necessárias:** ID do Projeto, Descrição, Custo proposto, Nome do Projeto")
            return None

        # Filtrar apenas as colunas necessárias e remover linhas vazias
        info_df = info_df[colunas_necessarias].dropna()

        if info_df.empty:
            st.error("❌ O arquivo não contém dados válidos após a limpeza.")
            return None

        return info_df

    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo: {e}")
        return None


# Função para limpar texto
def limpar_texto(texto):
    stop_words = set(stopwords.words('portuguese'))
    stop_words.update(['sobre', 'para', 'com', 'sem', 'por', 'em', 'na', 'no', 'da', 'do', 'das', 'dos', 'projeto'])

    texto_limpo = str(texto).lower()
    texto_limpo = re.sub(r'\s+', ' ', texto_limpo).strip()
    tokens = word_tokenize(texto_limpo, language='portuguese')
    tokens_sem_stopwords = []
    for token in tokens:
        if token not in stop_words and token.isalpha():
            tokens_sem_stopwords.append(token)
    return ' '.join(tokens_sem_stopwords)


# Função principal de busca
def buscar_projetos(info_df, busca, precisao):
    # Limpar descrições e nomes (com cache)
    if 'Descrições_limpas' not in info_df.columns:
        info_df['Descrições_limpas'] = [limpar_texto(desc) for desc in info_df['Descrição'].tolist()]

    if 'Nomes_limpos' not in info_df.columns:
        info_df['Nomes_limpos'] = [limpar_texto(nome) for nome in info_df['Nome do Projeto'].tolist()]

    # Limpar busca
    busca_limpa = limpar_texto(busca)

    # Buscar em descrições
    matches_desc = []
    match1_desc = process.extract(busca_limpa, info_df['Descrições_limpas'].tolist(), scorer=fuzz.token_set_ratio,
                                  limit=10)
    match2_desc = process.extract(busca_limpa, info_df['Descrições_limpas'].tolist(),
                                  scorer=fuzz.partial_token_set_ratio, limit=10)
    matches_desc.extend(match1_desc)
    matches_desc.extend(match2_desc)

    # Buscar em nomes
    matches_nome = []
    match1_nome = process.extract(busca_limpa, info_df['Nomes_limpos'].tolist(), scorer=fuzz.token_set_ratio, limit=10)
    match2_nome = process.extract(busca_limpa, info_df['Nomes_limpos'].tolist(), scorer=fuzz.partial_token_set_ratio,
                                  limit=10)
    matches_nome.extend(match1_nome)
    matches_nome.extend(match2_nome)

    # Criar DataFrame resultado
    df_resultado = pd.DataFrame(
        columns=['ID_Projeto', 'Nome_Projeto', 'Descrição', 'Custo', 'Similaridade', 'Campo_Encontrado'])

    # Processar matches de descrição
    for descricao, score in matches_desc:
        if score > precisao:
            projeto = info_df[info_df['Descrições_limpas'] == descricao]
            if not projeto.empty:
                df_resultado.loc[len(df_resultado)] = [
                    projeto['ID do Projeto'].iloc[0],
                    projeto['Nome do Projeto'].iloc[0],
                    projeto['Descrição'].iloc[0],
                    projeto['Custo proposto'].iloc[0],
                    score,
                    'Descrição'
                ]

    # Processar matches de nome
    for nome, score in matches_nome:
        if score > precisao:
            projeto = info_df[info_df['Nomes_limpos'] == nome]
            if not projeto.empty:
                # Verificar se já não existe no resultado (evitar duplicatas)
                if not any(df_resultado['ID_Projeto'] == projeto['ID do Projeto'].iloc[0]):
                    df_resultado.loc[len(df_resultado)] = [
                        projeto['ID do Projeto'].iloc[0],
                        projeto['Nome do Projeto'].iloc[0],
                        projeto['Descrição'].iloc[0],
                        projeto['Custo proposto'].iloc[0],
                        score,
                        'Nome'
                    ]

    # Ordenar por similaridade
    df_resultado = df_resultado.sort_values('Similaridade', ascending=False).reset_index(drop=True)

    return df_resultado


# Interface principal
def main():
    # Download dos recursos NLTK
    if not download_nltk_resources():
        st.stop()

    # Seção de upload de arquivo
    st.header("📁 Upload do Arquivo de Dados")

    # Informações sobre o formato esperado
    with st.expander("ℹ️ Formato do Arquivo Esperado", expanded=False):
        st.markdown("""
        **O arquivo Excel deve conter as seguintes colunas:**
        - `ID do Projeto`: Identificador único do projeto
        - `Nome do Projeto`: Nome/título do projeto
        - `Descrição`: Descrição detalhada do projeto
        - `Custo proposto`: Valor monetário do projeto

        **Formatos aceitos:** .xlsx, .xls
        """)

    uploaded_file = st.file_uploader(
        "Escolha o arquivo Excel com os dados dos projetos",
        type=['xlsx', 'xls'],
        help="Faça upload de um arquivo Excel contendo os dados dos projetos"
    )

    # Verificar se arquivo foi carregado
    if uploaded_file is None:
        st.info("👆 **Por favor, faça upload do arquivo Excel para começar a busca.**")
        st.markdown("---")

        # Mostrar exemplo de estrutura de dados
        st.subheader("📋 Exemplo de Estrutura de Dados")
        exemplo_df = pd.DataFrame({
            'ID do Projeto': [1, 2, 3],
            'Nome do Projeto': ['Sistema de Gestão', 'App Mobile', 'Website Corporativo'],
            'Descrição': ['Sistema para gestão de projetos internos', 'Aplicativo mobile para vendas',
                          'Website institucional da empresa'],
            'Custo proposto': [50000.00, 25000.00, 15000.00]
        })
        st.dataframe(exemplo_df, use_container_width=True)
        return

    # Processar arquivo carregado
    info_df = processar_arquivo(uploaded_file)
    if info_df is None:
        return

    # Mostrar sucesso no carregamento
    st.success("✅ Arquivo carregado com sucesso!")

    # Sidebar com informações do dataset
    st.sidebar.header("📊 Informações do Dataset")
    st.sidebar.metric("Total de Projetos", len(info_df))
    st.sidebar.metric("Custo Total", f"R\$ {info_df['Custo proposto'].sum():,.2f}")

    # Mostrar prévia dos dados
    with st.expander("👀 Visualizar dados carregados", expanded=False):
        st.dataframe(info_df.head(10), use_container_width=True)

    st.markdown("---")

    # Interface de busca
    st.header("🔍 Busca de Projetos")

    col1, col2 = st.columns([3, 1])

    with col1:
        busca = st.text_input(
            "**Descrição do projeto:**",
            placeholder="Digite palavras-chave para buscar projetos...",
            help="Digite uma descrição ou palavras-chave relacionadas ao projeto que você está procurando"
        )

    with col2:
        precisao = st.slider(
            "🎯 **Precisão (%):**",
            min_value=1,
            max_value=100,
            value=70,
            help="Ajuste o nível de precisão da busca. Valores mais altos retornam resultados mais específicos."
        )

    # Botão de busca
    if st.button("🔍 Buscar Projetos", type="primary", use_container_width=True):
        if busca.strip():
            with st.spinner("🔄 Buscando projetos..."):
                df_resultado = buscar_projetos(info_df, busca, precisao)

            if not df_resultado.empty:
                st.success(f"✅ Encontrados {len(df_resultado)} projeto(s) com similaridade acima de {precisao}%")

                # Mostrar resultados
                st.markdown("### 📋 Resultados da Busca")

                # Configurar exibição das colunas
                df_display = df_resultado.copy()
                df_display['Custo'] = df_display['Custo'].apply(lambda x: f"R\$ {x:,.2f}")
                df_display['Similaridade'] = df_display['Similaridade'].apply(lambda x: f"{x:.1f}%")

                # Exibir tabela
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "ID_Projeto": st.column_config.NumberColumn("ID", width="small"),
                        "Nome_Projeto": st.column_config.TextColumn("Nome do Projeto", width="medium"),
                        "Descrição": st.column_config.TextColumn("Descrição", width="large"),
                        "Custo": st.column_config.TextColumn("Custo", width="small"),
                        "Similaridade": st.column_config.TextColumn("Similaridade", width="small"),
                        "Campo_Encontrado": st.column_config.TextColumn("Campo", width="small")
                    }
                )

                # Estatísticas dos resultados
                st.markdown("### 📈 Estatísticas dos Resultados")
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Total de Projetos", len(df_resultado))

                with col2:
                    custo_total = df_resultado['Custo'].sum()
                    st.metric("Custo Total", f"R\$ {custo_total:,.2f}")

                with col3:
                    similaridade_media = df_resultado['Similaridade'].mean()
                    st.metric("Similaridade Média", f"{similaridade_media:.1f}%")

                with col4:
                    melhor_match = df_resultado['Similaridade'].max()
                    st.metric("Melhor Match", f"{melhor_match:.1f}%")

                # Opção de download
                csv = df_resultado.to_csv(index=False)
                st.download_button(
                    label="📥 Baixar Resultados (CSV)",
                    data=csv,
                    file_name=f"resultados_busca_{busca[:20]}.csv",
                    mime="text/csv"
                )

            else:
                st.warning(
                    f"⚠️ Nenhum projeto encontrado com similaridade acima de {precisao}%. Tente diminuir a precisão ou usar outras palavras-chave.")
        else:
            st.error("❌ Por favor, insira uma descrição para buscar.")


if __name__ == "__main__":
    main()
