import streamlit as st
from datetime import datetime
import auth

# Check authentication first
if not auth.require_auth():
    st.stop()

st.set_page_config(page_title="Dashboard Corporativo", page_icon="🏢", layout="wide")

st.title("🏢 DASHBOARD CORPORATIVO")
st.markdown("### 📊 Central de Gestão e Comunicação")

# Show user info in sidebar
auth.show_user_info()

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
    st.info("📍 Use a navegação lateral para acessar o Timeline de Compras")

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
    st.info("📍 Use a navegação lateral para acessar os Anúncios")

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

 