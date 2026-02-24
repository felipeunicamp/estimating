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

# Função para processar dados do arquivo carregado
@st.cache_data
def processar_dados(uploaded_file):
    try:
        info = pd.read_excel(uploaded_file)
        info_df = pd.DataFrame(info)
        
        # Verificar se as colunas necessárias existem
        required_columns = ['ID do Projeto', 'Descrição', 'Custo proposto', 'Nome do Projeto']
        missing_columns = [col for col in required_columns if col not in info_df.columns]
        
        if missing_columns:
            st.error(f"❌ Colunas obrigatórias não encontradas: {', '.join(missing_columns)}")
            st.info("📋 O arquivo deve conter as seguintes colunas: ID do Projeto, Descrição, Custo proposto, Nome do Projeto")
            return None
            
        info_df = info_df[required_columns].dropna()
        
        if info_df.empty:
            st.error("❌ Nenhum dado válido encontrado no arquivo após remover linhas vazias.")
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

    # Seção de upload obrigatório
    st.markdown("### 📁 Upload do Arquivo")
    st.info("📋 **Instruções:** Faça upload de um arquivo Excel (.xlsx ou .xls) contendo as colunas: 'ID do Projeto', 'Descrição', 'Custo proposto', 'Nome do Projeto'")
    
    uploaded_file = st.file_uploader(
        "Escolha o arquivo Excel com os dados dos projetos",
        type=['xlsx', 'xls'],
        help="O arquivo deve conter as colunas obrigatórias: ID do Projeto, Descrição, Custo proposto, Nome do Projeto"
    )

    # Verificar se arquivo foi carregado
    if uploaded_file is None:
        st.warning("⚠️ **Por favor, faça upload do arquivo Excel para continuar.**")
        
        # Mostrar exemplo de estrutura esperada
        st.markdown("### 📋 Estrutura Esperada do Arquivo")
        exemplo_df = pd.DataFrame({
            'ID do Projeto': [1, 2, 3],
            'Nome do Projeto': ['Projeto A', 'Projeto B', 'Projeto C'],
            'Descrição': ['Descrição do projeto A', 'Descrição do projeto B', 'Descrição do projeto C'],
            'Custo proposto': [10000.00, 25000.50, 15500.75]
        })
        st.dataframe(exemplo_df, use_container_width=True)
        st.stop()

    # Processar dados do arquivo carregado
    with st.spinner("📊 Processando arquivo..."):
        info_df = processar_dados(uploaded_file)
    
    if info_df is None:
        st.stop()

    # Mostrar sucesso e informações do dataset
    st.success("✅ Arquivo carregado e processado com sucesso!")
    
    # Sidebar com informações do dataset
    st.sidebar.header("📊 Informações do Dataset")
    st.sidebar.metric("Total de Projetos", len(info_df))
    st.sidebar.metric("Custo Total", f"R\$ {info_df['Custo proposto'].sum():,.2f}")
    
    # Mostrar estatísticas básicas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Total de Projetos", len(info_df))
    with col2:
        st.metric("💰 Custo Total", f"R\$ {info_df['Custo proposto'].sum():,.2f}")
    with col3:
        st.metric("💸 Custo Médio", f"R\$ {info_df['Custo proposto'].mean():,.2f}")

    st.markdown("---")

    # Interface de busca
    st.markdown("### 🔍 Busca de Projetos")
    
    col1, col2 = st.columns([3, 1])

    with col1:
        busca = st.text_input(
            "**Descrição do projeto:**",
            placeholder="Digite palavras-chave para buscar projetos...",
            help="Digite uma descrição ou palavras-chave relacionadas ao projeto que você está procurando"
        )

    with col2:
        precisao = st.slider(
            "**Precisão (%):**",
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

    # Mostrar amostra dos dados
    if st.checkbox("�� Visualizar amostra dos dados"):
        st.markdown("### 📊 Amostra do Dataset")
        st.dataframe(info_df.head(10), use_container_width=True)

if __name__ == "__main__":
    main()
