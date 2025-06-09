import streamlit as st
from datetime import datetime
import auth
import sys
import os

# Check authentication first
if not auth.require_auth():
    st.stop()

st.set_page_config(page_title="Dashboard Corporativo", page_icon="🏢", layout="wide")

# Import functions from page files
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def show_dashboard():
    st.title("🏢 DASHBOARD CORPORATIVO")
    st.markdown("### 📊 Central de Gestão e Comunicação")
    
    # Hero section
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        ### 📅 Timeline de Compras
        Visualize e otimize suas compras com base em MOQ e análise de estoque.
        
        **Recursos:**
        - ⏰ Previsão de esgotamento
        - 🎯 Otimização de MOQ 
        - 📈 Gráficos interativos
        - 💰 Análise financeira
        """)
        if st.button("🚀 Acessar Timeline", use_container_width=True, key="nav_timeline"):
            st.session_state.current_page = "timeline"
            st.rerun()

    with col2:
        st.markdown("""
        ### 📢 Central de Anúncios
        Gerencie comunicações corporativas e mantenha todos informados.
        
        **Recursos:**
        - 📝 Criar anúncios
        - 🎯 Filtros por departamento
        - ⚡ Níveis de prioridade
        - 📊 Dashboard analítico
        """)
        if st.button("🚀 Acessar Anúncios", use_container_width=True, key="nav_announcements"):
            st.session_state.current_page = "announcements"
            st.rerun()

    with col3:
        st.markdown("""
        ### 📈 Métricas em Tempo Real
        
        **Status Atual:**
        - 🟢 Sistema: Operacional
        - 📊 Dados: Atualizados
        - 👥 Usuários: Online
        - 🔄 Última atualização: Agora
        """)
        st.success("✅ Todos os sistemas funcionando normalmente")

    st.divider()

    # Quick stats section
    st.subheader("📊 Resumo Executivo")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="⏰ Uptime do Sistema",
            value="99.9%",
            delta="0.1%"
        )

    with col2:
        st.metric(
            label="📈 Eficiência",
            value="94%",
            delta="2%"
        )

    with col3:
        st.metric(
            label="💰 Economia MOQ",
            value="R$ 250K",
            delta="R$ 15K"
        )

    with col4:
        st.metric(
            label="📢 Anúncios Ativos",
            value="12",
            delta="3"
        )

    st.divider()

    # Features grid
    st.subheader("🎯 Funcionalidades Principais")

    features_col1, features_col2 = st.columns(2)

    with features_col1:
        with st.container():
            st.markdown("""
            #### 🔍 Análise Inteligente
            - **Predição de Estoque**: Algoritmos avançados para prever quando produtos vão esgotar
            - **Otimização de MOQ**: Calcula automaticamente as melhores quantidades de compra
            - **Alertas Proativos**: Notificações antes que problemas aconteçam
            """)

    with features_col2:
        with st.container():
            st.markdown("""
            #### 📱 Interface Moderna
            - **Design Responsivo**: Funciona perfeitamente em qualquer dispositivo
            - **Visualizações Interativas**: Gráficos dinâmicos com Plotly
            - **Filtros Inteligentes**: Encontre exatamente o que precisa
            """)

    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>🚀 Desenvolvido com Streamlit | 💡 Otimizado para performance | 🔒 Seguro e confiável</p>
        <p>📞 Suporte: support@empresa.com | 📚 Documentação disponível no GitHub</p>
    </div>
    """, unsafe_allow_html=True)

def show_timeline():
    import pandas as pd
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import numpy as np
    from datetime import datetime, timedelta
    
    st.title("📅 TIMELINE INTERATIVA DE COMPRAS")
    st.markdown("### 🎯 Visualização interativa com MOQ otimizado")

    with st.expander("ℹ️ Como usar esta aplicação"):
        st.markdown("""
        **Para usar esta aplicação:**
        1. 📁 **Upload:** Faça upload do seu arquivo Excel na barra lateral
        2. 📊 **Exemplo:** Ou marque a opção "Usar dados de exemplo" para testar
        3. 🎛️ **Configure:** Ajuste os parâmetros na barra lateral
        4. 📈 **Analise:** Visualize os gráficos interativos
        
        **Formato do arquivo Excel:**
        - Deve ter as colunas: Item, Modelo, Fornecedor, QTD, Preço FOB Unitário, Estoque Total, In Transit Shipt, Avg Sales, CBM, MOQ
        - Os dados devem começar na linha 10 (header=9)
        """)

    @st.cache_data
    def carregar_dados(uploaded_file=None):
        try:
            if uploaded_file is not None:
                df = pd.read_excel(uploaded_file, header=9)
            else:
                # No local file in production - user must upload
                return None
            
            df = df.dropna(subset=['Item'])
            df = df[df['Item'] != 'Item']
            
            # Converter colunas numéricas
            colunas_numericas = ['QTD', 'Preço FOB\nUnitário', 'Estoque\nTotal ', 
                               'In Transit\nShipt', 'Avg Sales\n', 'CBM', 'MOQ']
            
            for col in colunas_numericas:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # Renomear colunas
            df = df.rename(columns={
                'Preço FOB\nUnitário': 'Preco_Unitario',
                'Estoque\nTotal ': 'Estoque_Total',
                'In Transit\nShipt': 'In_Transit',
                'Avg Sales\n': 'Vendas_Medias'
            })
            
            return df
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            return None

    def criar_dados_exemplo():
        """Cria dados de exemplo para demonstração"""
        dados_exemplo = {
            'Item': ['ITEM001', 'ITEM002', 'ITEM003', 'ITEM004', 'ITEM005'],
            'Modelo': ['Multímetro DM-1000', 'Osciloscópio OS-200', 'Fonte DC-300', 'Gerador GF-400', 'Analisador AN-500'],
            'Fornecedor': ['Fornecedor A', 'Fornecedor B', 'Fornecedor A', 'Fornecedor C', 'Fornecedor B'],
            'QTD': [100, 50, 75, 30, 25],
            'Preço FOB\nUnitário': [150.00, 800.00, 450.00, 1200.00, 2500.00],
            'Estoque\nTotal ': [45, 12, 23, 8, 5],
            'In Transit\nShipt': [20, 5, 10, 0, 2],
            'Avg Sales\n': [15, 3, 8, 2, 1],
            'CBM': [0.05, 0.15, 0.08, 0.12, 0.20],
            'MOQ': [50, 10, 25, 5, 5]
        }
        return pd.DataFrame(dados_exemplo)

    # Timeline sidebar controls
    st.sidebar.header("📁 Upload de Dados")
    uploaded_file = st.sidebar.file_uploader(
        "Faça upload do seu arquivo Excel:",
        type=['xlsx', 'xls'],
        help="Carregue um arquivo Excel com dados de estoque e vendas"
    )

    usar_dados_exemplo = st.sidebar.checkbox("📊 Usar dados de exemplo", value=False)

    if usar_dados_exemplo:
        df = criar_dados_exemplo()
        st.info("📊 Usando dados de exemplo para demonstração")
    elif uploaded_file is not None:
        df = carregar_dados(uploaded_file)
        st.success("✅ Arquivo carregado com sucesso!")
    else:
        df = carregar_dados()
        if df is None:
            st.warning("📁 Faça upload de um arquivo Excel ou use os dados de exemplo para começar!")
    
    if df is not None:
        st.success("🎯 Timeline carregado com sucesso! Dados prontos para análise.")
        st.dataframe(df.head(), use_container_width=True)
    else:
        st.info("📤 Aguardando upload de dados...")

def show_announcements():
    st.title("📢 DASHBOARD DE ANÚNCIOS")
    st.markdown("### 🏢 Central de Comunicação Corporativa")
    
    # Get current user for role checking
    current_user = auth.get_current_user()
    
    st.sidebar.header("🎛️ Controles")
    
    # Admin only features
    if auth.is_admin(current_user):
        st.sidebar.success("🔑 Modo Administrador")
        
        # Sample data button
        if st.sidebar.button("📊 Carregar Dados de Exemplo"):
            sample_data = [
                {
                    "id": 1,
                    "title": "🎉 Nova Política de Home Office",
                    "content": "A partir de segunda-feira, implementaremos nossa nova política de trabalho híbrido.",
                    "type": "Política",
                    "priority": "Alta",
                    "department": "Todos",
                    "author": "Recursos Humanos",
                    "date": "2024-01-15",
                    "active": True
                }
            ]
            st.success("✅ Dados de exemplo carregados!")
        
        # Create announcement form
        with st.sidebar.expander("➕ Criar Novo Anúncio"):
            with st.form("new_announcement"):
                title = st.text_input("Título")
                content = st.text_area("Conteúdo", height=100)
                
                col1, col2 = st.columns(2)
                with col1:
                    announcement_type = st.selectbox(
                        "Tipo",
                        ["Geral", "Política", "Resultado", "Segurança", "Evento", "Sistema", "Urgente"]
                    )
                    priority = st.selectbox("Prioridade", ["Baixa", "Média", "Alta", "Crítica"])
                
                with col2:
                    department = st.selectbox(
                        "Departamento",
                        ["Todos", "TI", "Compras", "Vendas", "RH", "Financeiro", "Produção"]
                    )
                    author = st.text_input("Autor", value=current_user['name'])
                
                if st.form_submit_button("📝 Criar Anúncio"):
                    if title and content:
                        st.success("✅ Anúncio criado com sucesso!")
                    else:
                        st.error("⚠️ Preencha título e conteúdo")
    else:
        st.sidebar.info("👁️ Modo Visualização")
    
    # Main content area
    st.subheader("📋 Central de Anúncios")
    
    # Sample metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📢 Total de Anúncios", "5")
    with col2:
        st.metric("🚨 Críticos", "1")
    with col3:
        st.metric("📅 Hoje", "2")
    with col4:
        st.metric("⏰ Expirando", "1")
    
    # Sample announcement
    with st.container():
        st.markdown("### 🎉 Nova Política de Home Office")
        
        info_col1, info_col2, info_col3, info_col4 = st.columns(4)
        with info_col1:
            st.write("**Tipo:** Política")
        with info_col2:
            st.write("**Prioridade:** Alta")
        with info_col3:
            st.write("**Departamento:** Todos")
        with info_col4:
            st.write("**Autor:** Recursos Humanos")
        
        st.write("A partir de segunda-feira, implementaremos nossa nova política de trabalho híbrido. Funcionários podem trabalhar remotamente 2 dias por semana.")
        
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            st.caption("📅 Criado em: 15/01/2024")
        with date_col2:
            st.caption("📅 Expira em: 15/02/2024")
    
    st.info("🔄 Sistema de anúncios funcionando em modo demonstração")

# Main app logic
# Show user info in sidebar
auth.show_user_info()

# Add manual navigation
st.sidebar.markdown("---")
st.sidebar.markdown("### 🧭 Navegação")

# Initialize session state for page navigation
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"

# Navigation buttons
if st.sidebar.button("🏠 Dashboard", use_container_width=True):
    st.session_state.current_page = "home"
    st.rerun()

if st.sidebar.button("📅 Timeline de Compras", use_container_width=True):
    st.session_state.current_page = "timeline"
    st.rerun()

if st.sidebar.button("📢 Anúncios", use_container_width=True):
    st.session_state.current_page = "announcements"
    st.rerun()

# Show different pages based on navigation
if st.session_state.current_page == "home":
    show_dashboard()
elif st.session_state.current_page == "timeline":
    show_timeline()
elif st.session_state.current_page == "announcements":
    show_announcements()

 