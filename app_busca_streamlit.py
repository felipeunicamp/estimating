import streamlit as st
import pandas as pd
from fuzzywuzzy import fuzz, process
import re
import io

# Configuração da página
st.set_page_config(
    page_title="🔍 Buscador de Projetos",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal
st.title("�� Buscador de Projetos")
st.markdown("---")


# Função para limpar descrições
@st.cache_data
def limpar_descricoes(descricoes):
    descrições_limpas = []
    for desc in descricoes:
        desc_limpa = str(desc).lower()
        desc_limpa = re.sub(r'\s+', ' ', desc_limpa).strip()
        descrições_limpas.append(desc_limpa)
    return descrições_limpas


# Função para processar arquivo carregado
@st.cache_data
def processar_arquivo(arquivo_carregado):
    try:
        # Detectar tipo de arquivo
        if arquivo_carregado.name.endswith('.csv'):
            # Tentar diferentes encodings para CSV
            try:
                df = pd.read_csv(arquivo_carregado, encoding='utf-8')
            except UnicodeDecodeError:
                arquivo_carregado.seek(0)  # Reset file pointer
                df = pd.read_csv(arquivo_carregado, encoding='latin-1')
        elif arquivo_carregado.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(arquivo_carregado)
        else:
            st.error("❌ Formato de arquivo não suportado! Use CSV, XLS ou XLSX.")
            return None

        # Verificar se as colunas existem
        colunas_necessarias = ['ID do Projeto', 'Descrição', 'Custo proposto', 'Nome do Projeto']
        colunas_disponiveis = df.columns.tolist()

        # Mapear colunas similares (case insensitive)
        mapeamento_colunas = {}
        for col_necessaria in colunas_necessarias:
            for col_disponivel in colunas_disponiveis:
                if col_necessaria.lower() in col_disponivel.lower() or col_disponivel.lower() in col_necessaria.lower():
                    mapeamento_colunas[col_necessaria] = col_disponivel
                    break

        # Verificar se todas as colunas foram encontradas
        colunas_faltando = [col for col in colunas_necessarias if col not in mapeamento_colunas]

        if colunas_faltando:
            st.error(f"❌ Colunas não encontradas no arquivo: {', '.join(colunas_faltando)}")
            st.info("📋 Colunas disponíveis no arquivo:")
            st.write(colunas_disponiveis)

            # Permitir mapeamento manual
            st.subheader("🔧 Mapeamento Manual de Colunas")
            for col_faltando in colunas_faltando:
                opcao_selecionada = st.selectbox(
                    f"Selecione a coluna para '{col_faltando}':",
                    ["Não mapear"] + colunas_disponiveis,
                    key=f"map_{col_faltando}"
                )
                if opcao_selecionada != "Não mapear":
                    mapeamento_colunas[col_faltando] = opcao_selecionada

            if st.button("🔄 Aplicar Mapeamento"):
                st.rerun()

            return None

        # Renomear colunas conforme mapeamento
        df_processado = df.copy()
        for col_nova, col_antiga in mapeamento_colunas.items():
            if col_antiga in df_processado.columns:
                df_processado = df_processado.rename(columns={col_antiga: col_nova})

        # Selecionar apenas as colunas necessárias e remover valores nulos
        df_processado = df_processado[colunas_necessarias].dropna()

        if df_processado.empty:
            st.error("❌ Nenhum dado válido encontrado após limpeza!")
            return None

        # Limpar descrições
        descrições_limpas = limpar_descricoes(df_processado['Descrição'].tolist())
        df_processado['Descrições_limpas'] = descrições_limpas

        return df_processado

    except Exception as e:
        st.error(f"❌ Erro ao processar arquivo: {str(e)}")
        return None


# Sidebar para configurações e upload
with st.sidebar:
    st.header("📁 Upload de Arquivo")

    # Upload de arquivo
    arquivo_carregado = st.file_uploader(
        "Escolha um arquivo CSV, XLS ou XLSX",
        type=['csv', 'xlsx', 'xls'],
        help="Faça upload do arquivo contendo os dados dos projetos"
    )

    if arquivo_carregado is not None:
        st.success(f"✅ Arquivo carregado: {arquivo_carregado.name}")

        # Mostrar informações do arquivo
        file_details = {
            "Nome": arquivo_carregado.name,
            "Tamanho": f"{arquivo_carregado.size / 1024:.2f} KB",
            "Tipo": arquivo_carregado.type
        }
        st.json(file_details)

    st.markdown("---")

    st.header("⚙️ Configurações")

    # Configurações de busca
    st.subheader("🎯 Parâmetros de Busca")
    precisao = st.slider(
        "Precisão (%)",
        min_value=1,
        max_value=100,
        value=70,
        help="Nível mínimo de similaridade para mostrar resultados"
    )

    limite_resultados = st.selectbox(
        "Máximo de resultados",
        [5, 10, 15, 20],
        index=1,
        help="Número máximo de projetos a serem exibidos"
    )

# Verificar se há arquivo carregado
if arquivo_carregado is not None:
    # Processar arquivo carregado
    with st.spinner("🔄 Processando arquivo carregado..."):
        info_df = processar_arquivo(arquivo_carregado)
else:
    # Mostrar instruções para upload
    st.info("📁 **Faça upload de um arquivo para começar a busca**")

    st.markdown("""
    ### 📋 Instruções:

    1. **📁 Faça upload** de um arquivo CSV, XLS ou XLSX na barra lateral
    2. **📊 Certifique-se** de que o arquivo contém as seguintes colunas:
       - `ID do Projeto` (ou similar)
       - `Nome do Projeto` (ou similar)
       - `Descrição` (ou similar)
       - `Custo proposto` (ou similar)
    3. **🔍 Use a busca** para encontrar projetos similares
    """)

    # Exemplo de dados
    st.subheader("📝 Exemplo de estrutura esperada:")
    exemplo_dados = pd.DataFrame({
        'ID do Projeto': [1, 2, 3],
        'Nome do Projeto': ['Sistema de Gestão', 'Reforma Predial', 'Compra Equipamentos'],
        'Descrição': [
            'Desenvolvimento de sistema de gestão integrada',
            'Reforma completa do prédio administrativo',
            'Aquisição de equipamentos de informática'
        ],
        'Custo proposto': [150000.00, 85000.00, 45000.00]
    })
    st.dataframe(exemplo_dados, use_container_width=True)

    # Botão para download do exemplo
    csv_exemplo = exemplo_dados.to_csv(index=False)
    st.download_button(
        label="📥 Download Exemplo CSV",
        data=csv_exemplo,
        file_name="exemplo_projetos.csv",
        mime="text/csv",
        help="Baixe este arquivo como exemplo de estrutura"
    )

    info_df = None

# Se os dados foram carregados com sucesso
if info_df is not None:
    # Mostrar estatísticas dos dados
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📊 Total de Projetos", len(info_df))

    with col2:
        custo_total = info_df['Custo proposto'].sum()
        st.metric("💰 Custo Total", f"R$ {custo_total:,.2f}")

    with col3:
        custo_medio = info_df['Custo proposto'].mean()
        st.metric("📈 Custo Médio", f"R$ {custo_medio:,.2f}")

    with col4:
        custo_max = info_df['Custo proposto'].max()
        st.metric("🔝 Maior Custo", f"R$ {custo_max:,.2f}")

    st.markdown("---")

    # Interface de busca
    st.subheader("🔍 Buscar Projetos")

    col1, col2 = st.columns([3, 1])

    with col1:
        busca = st.text_input(
            "Digite a descrição do projeto:",
            placeholder="Ex: sistema de gestão, reforma de prédio, compra de equipamentos...",
            help="Digite palavras-chave relacionadas ao projeto que você está procurando"
        )

    with col2:
        buscar_btn = st.button("🔍 Buscar", type="primary", use_container_width=True)

    # Realizar busca
    if (buscar_btn or busca) and busca.strip():
        with st.spinner("🔍 Buscando projetos similares..."):
            # Limpar busca
            busca_limpa = str(busca).lower()
            busca_limpa = re.sub(r'\s+', ' ', busca_limpa).strip()

            # Encontrar matches
            matches = process.extract(
                busca_limpa,
                info_df['Descrições_limpas'].tolist(),
                scorer=fuzz.token_set_ratio,
                limit=limite_resultados
            )

            # Criar DataFrame de resultados
            resultados = []
            for descricao, score in matches:
                if score >= precisao:
                    projeto = info_df[info_df['Descrições_limpas'] == descricao].iloc[0]
                    resultados.append({
                        'ID': projeto['ID do Projeto'],
                        'Nome': projeto['Nome do Projeto'],
                        'Descrição': projeto['Descrição'],
                        'Custo': projeto['Custo proposto'],
                        'Similaridade': score
                    })

            # Mostrar resultados
            if resultados:
                st.success(f"✅ {len(resultados)} projeto(s) encontrado(s) com similaridade ≥ {precisao}%")

                # Tabs para diferentes visualizações
                tab1, tab2, tab3 = st.tabs(["📋 Lista Detalhada", "📊 Tabela", "📈 Gráfico"])

                with tab1:
                    # Mostrar cada resultado em um card
                    for i, resultado in enumerate(resultados):
                        with st.expander(f"🎯 {resultado['Similaridade']:.1f}% - {resultado['Nome']}",
                                         expanded=(i == 0)):
                            # Layout em duas colunas
                            col1, col2 = st.columns([3, 1])

                            with col1:
                                # Informações principais do projeto
                                st.markdown(f"**🆔 ID do Projeto:** {resultado['ID']}")
                                st.markdown(f"**📝 Nome do Projeto:** {resultado['Nome']}")
                                st.markdown(f"**📄 Descrição:**")
                                st.markdown(f"_{resultado['Descrição']}_")
                                st.markdown(f"**💰 Custo Proposto:** R$ {resultado['Custo']:,.2f}")

                            with col2:
                                # Métricas visuais
                                st.metric("🎯 Similaridade", f"{resultado['Similaridade']:.1f}%")

                                # Indicador visual de similaridade
                                if resultado['Similaridade'] >= 90:
                                    st.success("🟢 Excelente match")
                                elif resultado['Similaridade'] >= 80:
                                    st.info("🔵 Bom match")
                                elif resultado['Similaridade'] >= 70:
                                    st.warning("🟡 Match moderado")
                                else:
                                    st.error("🔴 Match baixo")

                            # Separador visual
                            st.markdown("---")

                with tab2:
                    # Tabela formatada
                    df_resultados = pd.DataFrame(resultados)
                    df_resultados_display = df_resultados.copy()
                    df_resultados_display['Custo'] = df_resultados_display['Custo'].apply(lambda x: f"R$ {x:,.2f}")
                    df_resultados_display['Similaridade'] = df_resultados_display['Similaridade'].apply(
                        lambda x: f"{x:.1f}%")

                    st.dataframe(
                        df_resultados_display,
                        use_container_width=True,
                        hide_index=True
                    )

                    # Botão para download
                    csv = df_resultados.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f"busca_projetos_{busca[:20].replace(' ', '_')}.csv",
                        mime="text/csv"
                    )

                with tab3:
                    # Gráfico de similaridade
                    df_grafico = pd.DataFrame(resultados)
                    st.subheader("�� Similaridade dos Projetos")
                    st.bar_chart(
                        data=df_grafico.set_index('Nome')['Similaridade'],
                        height=400
                    )

                    # Gráfico de custos
                    st.subheader("💰 Distribuição de Custos")
                    st.bar_chart(
                        data=df_grafico.set_index('Nome')['Custo'],
                        height=400
                    )

            else:
                st.warning(f"⚠️ Nenhum projeto encontrado com similaridade ≥ {precisao}%")
                st.info("💡 Dicas:")
                st.write("• Tente diminuir o nível de precisão")
                st.write("• Use palavras-chave mais gerais")
                st.write("• Verifique a ortografia")

    # Mostrar preview dos dados
    with st.expander("👀 Preview dos Dados Carregados"):
        st.dataframe(
            info_df[['ID do Projeto', 'Nome do Projeto', 'Custo proposto']].head(10),
            use_container_width=True
        )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        🔍 Buscador de Projetos | Upload de Arquivo | Desenvolvido com Streamlit
    </div>
    """,
    unsafe_allow_html=True
)