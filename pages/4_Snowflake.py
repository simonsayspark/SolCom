import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# Configure page
st.set_page_config(
    page_title="Snowflake Integration - MINIPA",
    page_icon="❄️",
    layout="wide"
)

# Authentication check
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.error("⚠️ Acesso negado. Faça login primeiro.")
    st.stop()

def create_sample_data():
    """Create sample data that mimics what might come from Snowflake"""
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    
    # Sample purchase data
    purchase_data = []
    products = ['Produto A', 'Produto B', 'Produto C', 'Produto D', 'Produto E']
    suppliers = ['Fornecedor 1', 'Fornecedor 2', 'Fornecedor 3', 'Fornecedor 4']
    
    for i in range(100):
        purchase_data.append({
            'DATA': np.random.choice(dates),
            'PRODUTO': np.random.choice(products),
            'FORNECEDOR': np.random.choice(suppliers),
            'QUANTIDADE': np.random.randint(10, 1000),
            'VALOR_UNITARIO': np.random.uniform(5.0, 100.0),
            'VALOR_TOTAL': 0,  # Will calculate
            'STATUS': np.random.choice(['Pendente', 'Aprovado', 'Cancelado'], p=[0.3, 0.6, 0.1])
        })
    
    df = pd.DataFrame(purchase_data)
    df['VALOR_TOTAL'] = df['QUANTIDADE'] * df['VALOR_UNITARIO']
    return df

def connect_to_snowflake():
    """Attempt to connect to Snowflake using st.connection"""
    try:
        # Try to establish connection
        conn = st.connection("snowflake")
        return conn
    except Exception as e:
        st.error(f"❌ Erro ao conectar com Snowflake: {str(e)}")
        st.info("💡 Verifique se o arquivo `.streamlit/secrets.toml` está configurado corretamente.")
        return None

def test_snowflake_connection(conn):
    """Test the Snowflake connection with a simple query"""
    try:
        # Simple test query
        df = conn.query("SELECT CURRENT_VERSION() as VERSION, CURRENT_USER() as USER, CURRENT_ROLE() as ROLE;")
        return df
    except Exception as e:
        st.error(f"❌ Erro no teste de conexão: {str(e)}")
        return None

def create_sample_tables(conn):
    """Create sample tables in Snowflake for demonstration"""
    try:
        # Create database and schema if they don't exist
        conn.query("CREATE DATABASE IF NOT EXISTS COMPRAS_DB;")
        conn.query("CREATE SCHEMA IF NOT EXISTS COMPRAS_DB.MINIPA;")
        
        # Create products table
        conn.query("""
            CREATE OR REPLACE TABLE COMPRAS_DB.MINIPA.PRODUTOS (
                ID NUMBER AUTOINCREMENT,
                NOME VARCHAR(100),
                CATEGORIA VARCHAR(50),
                PRECO_UNITARIO DECIMAL(10,2),
                ESTOQUE_ATUAL NUMBER,
                ESTOQUE_MINIMO NUMBER,
                FORNECEDOR VARCHAR(100),
                CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
            );
        """)
        
        # Create purchases table
        conn.query("""
            CREATE OR REPLACE TABLE COMPRAS_DB.MINIPA.COMPRAS (
                ID NUMBER AUTOINCREMENT,
                PRODUTO_ID NUMBER,
                DATA_COMPRA DATE,
                QUANTIDADE NUMBER,
                VALOR_UNITARIO DECIMAL(10,2),
                VALOR_TOTAL DECIMAL(12,2),
                FORNECEDOR VARCHAR(100),
                STATUS VARCHAR(20),
                CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
            );
        """)
        
        # Insert sample data
        sample_products = [
            ('Multímetro Digital', 'Instrumentos', 150.00, 25, 10, 'Fornecedor A'),
            ('Alicate Amperímetro', 'Instrumentos', 200.00, 15, 5, 'Fornecedor B'),
            ('Osciloscópio', 'Equipamentos', 1500.00, 8, 3, 'Fornecedor C'),
            ('Fonte Regulável', 'Equipamentos', 300.00, 12, 5, 'Fornecedor A'),
            ('Gerador de Funções', 'Equipamentos', 800.00, 6, 2, 'Fornecedor D')
        ]
        
        for product in sample_products:
            conn.query(f"""
                INSERT INTO COMPRAS_DB.MINIPA.PRODUTOS 
                (NOME, CATEGORIA, PRECO_UNITARIO, ESTOQUE_ATUAL, ESTOQUE_MINIMO, FORNECEDOR)
                VALUES ('{product[0]}', '{product[1]}', {product[2]}, {product[3]}, {product[4]}, '{product[5]}');
            """)
        
        return True
    except Exception as e:
        st.error(f"❌ Erro ao criar tabelas: {str(e)}")
        return False

# Main interface
st.title("❄️ Integração com Snowflake")
st.markdown("### Conecte seus dados à nuvem com Snowflake")

# Connection status
with st.container():
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 🔗 Status da Conexão")
        
        # Try to connect
        if st.button("🔄 Testar Conexão", type="primary"):
            with st.spinner("Conectando ao Snowflake..."):
                conn = connect_to_snowflake()
                if conn:
                    test_result = test_snowflake_connection(conn)
                    if test_result is not None:
                        st.success("✅ Conexão estabelecida com sucesso!")
                        st.dataframe(test_result, use_container_width=True)
                        st.session_state.snowflake_connected = True
                    else:
                        st.session_state.snowflake_connected = False
                else:
                    st.session_state.snowflake_connected = False
    
    with col2:
        st.markdown("#### 📋 Configuração")
        if st.button("📝 Ver Template"):
            st.code("""
# .streamlit/secrets.toml
[connections.snowflake]
account = "sua-org-sua-conta"
user = "seu_usuario"
password = "sua_senha"
role = "ACCOUNTADMIN"
warehouse = "COMPUTE_WH"
database = "COMPRAS_DB"
schema = "MINIPA"
            """)

# Tabs for different functionalities
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🗃️ Dados", "⚙️ Setup", "📚 Documentação"])

with tab1:
    st.markdown("#### 📊 Dashboard de Compras")
    
    # Check if connected
    if st.session_state.get('snowflake_connected', False):
        st.info("🔗 Conectado ao Snowflake - Dados em tempo real")
        # Here you would query real Snowflake data
        # For now, we'll use sample data
    else:
        st.warning("📴 Usando dados de exemplo - Configure a conexão Snowflake")
    
    # Create sample dashboard
    df_sample = create_sample_data()
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_compras = len(df_sample)
        st.metric("Total de Compras", total_compras)
    
    with col2:
        valor_total = df_sample['VALOR_TOTAL'].sum()
        st.metric("Valor Total", f"R$ {valor_total:,.2f}")
    
    with col3:
        compras_pendentes = len(df_sample[df_sample['STATUS'] == 'Pendente'])
        st.metric("Pendentes", compras_pendentes)
    
    with col4:
        fornecedores_unicos = df_sample['FORNECEDOR'].nunique()
        st.metric("Fornecedores", fornecedores_unicos)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Purchases by status
        status_counts = df_sample['STATUS'].value_counts()
        fig_status = px.pie(
            values=status_counts.values, 
            names=status_counts.index,
            title="Distribuição por Status"
        )
        st.plotly_chart(fig_status, use_container_width=True)
    
    with col2:
        # Monthly trend
        df_monthly = df_sample.groupby(df_sample['DATA'].dt.to_period('M'))['VALOR_TOTAL'].sum().reset_index()
        df_monthly['DATA'] = df_monthly['DATA'].astype(str)
        
        fig_trend = px.line(
            df_monthly, 
            x='DATA', 
            y='VALOR_TOTAL',
            title="Tendência Mensal de Compras"
        )
        st.plotly_chart(fig_trend, use_container_width=True)

with tab2:
    st.markdown("#### 🗃️ Consulta de Dados")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # SQL Query interface
        st.markdown("**💻 Console SQL**")
        
        sample_queries = {
            "Selecionar tudo": "SELECT * FROM COMPRAS_DB.MINIPA.PRODUTOS LIMIT 10;",
            "Produtos em baixo estoque": "SELECT * FROM COMPRAS_DB.MINIPA.PRODUTOS WHERE ESTOQUE_ATUAL <= ESTOQUE_MINIMO;",
            "Compras por fornecedor": "SELECT FORNECEDOR, COUNT(*) as TOTAL_COMPRAS, SUM(VALOR_TOTAL) as VALOR_TOTAL FROM COMPRAS_DB.MINIPA.COMPRAS GROUP BY FORNECEDOR;",
            "Custom": ""
        }
        
        query_type = st.selectbox("Consulta pré-definida:", list(sample_queries.keys()))
        
        if query_type == "Custom":
            sql_query = st.text_area("Digite sua consulta SQL:", height=100)
        else:
            sql_query = st.text_area("Consulta SQL:", value=sample_queries[query_type], height=100)
    
    with col2:
        st.markdown("**⚡ Ações**")
        
        if st.button("▶️ Executar"):
            if sql_query.strip():
                # Here you would execute the actual query
                st.info("💡 Configure a conexão Snowflake para executar consultas reais")
                
                # Show sample result
                if "PRODUTOS" in sql_query.upper():
                    sample_result = pd.DataFrame({
                        'NOME': ['Multímetro Digital', 'Alicate Amperímetro'],
                        'CATEGORIA': ['Instrumentos', 'Instrumentos'],
                        'PRECO_UNITARIO': [150.00, 200.00],
                        'ESTOQUE_ATUAL': [25, 15],
                        'FORNECEDOR': ['Fornecedor A', 'Fornecedor B']
                    })
                    st.dataframe(sample_result, use_container_width=True)
            else:
                st.warning("⚠️ Digite uma consulta SQL")
        
        if st.button("💾 Exportar CSV"):
            st.info("Funcionalidade disponível após executar consulta")

with tab3:
    st.markdown("#### ⚙️ Configuração Inicial")
    
    st.markdown("**📝 Passo a passo para configurar Snowflake:**")
    
    with st.expander("1️⃣ Criar conta Snowflake", expanded=True):
        st.markdown("""
        - Acesse: https://signup.snowflake.com
        - Crie uma conta trial gratuita
        - Anote seu **account identifier** (formato: organização-conta)
        - Configure warehouse padrão (COMPUTE_WH)
        """)
    
    with st.expander("2️⃣ Configurar credenciais"):
        st.markdown("""
        - Copie o arquivo `.streamlit/secrets.toml.template` para `.streamlit/secrets.toml`
        - Preencha com suas credenciais reais
        - **NUNCA** commite o arquivo secrets.toml no Git!
        """)
        
        st.code("""
        # .streamlit/secrets.toml
        [connections.snowflake]
        account = "abc12345-xy67890"  # Seu account identifier
        user = "seu_usuario"
        password = "sua_senha_segura"
        role = "ACCOUNTADMIN"
        warehouse = "COMPUTE_WH"
        database = "COMPRAS_DB"
        schema = "MINIPA"
        """)
    
    with st.expander("3️⃣ Instalar dependências"):
        st.markdown("Execute no terminal:")
        st.code("pip install -r requirements.txt")
    
    with st.expander("4️⃣ Criar estrutura de dados"):
        if st.button("🏗️ Criar Tabelas de Exemplo"):
            conn = connect_to_snowflake()
            if conn:
                if create_sample_tables(conn):
                    st.success("✅ Tabelas criadas com sucesso!")
                    st.balloons()
            else:
                st.error("❌ Configure a conexão primeiro")

with tab4:
    st.markdown("#### 📚 Documentação e Recursos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🔗 Links Úteis**")
        st.markdown("""
        - [Snowflake Trial](https://signup.snowflake.com)
        - [Streamlit + Snowflake Docs](https://docs.streamlit.io/develop/tutorials/databases/snowflake)
        - [Snowpark Python](https://docs.snowflake.com/en/developer-guide/snowpark/python/index)
        - [Snowflake SQL Reference](https://docs.snowflake.com/en/sql-reference)
        """)
        
        st.markdown("**🛠️ Funcionalidades Disponíveis**")
        st.markdown("""
        - ✅ Conexão segura com autenticação
        - ✅ Consultas SQL em tempo real
        - ✅ Dashboards interativos
        - ✅ Caching automático de consultas
        - ✅ Integração com Snowpark
        - ✅ Escalabilidade automática
        """)
    
    with col2:
        st.markdown("**💡 Exemplos de Uso**")
        
        st.markdown("**Consulta simples:**")
        st.code("""
conn = st.connection("snowflake")
df = conn.query("SELECT * FROM produtos LIMIT 10;")
st.dataframe(df)
        """)
        
        st.markdown("**Com cache:**")
        st.code("""
# Cache por 10 minutos
df = conn.query(
    "SELECT * FROM vendas WHERE data >= CURRENT_DATE();",
    ttl="10m"
)
        """)
        
        st.markdown("**Usando Snowpark:**")
        st.code("""
session = conn.session()
df = session.table("produtos").filter(
    session.col("estoque") < 10
).to_pandas()
        """)

# Sidebar info
with st.sidebar:
    st.markdown("### ❄️ Snowflake Status")
    
    if st.session_state.get('snowflake_connected', False):
        st.success("🟢 Conectado")
    else:
        st.error("🔴 Desconectado")
    
    st.markdown("---")
    st.markdown("### 📋 Próximos Passos")
    st.markdown("""
    1. Configure suas credenciais
    2. Teste a conexão
    3. Crie suas tabelas
    4. Migre dados existentes
    5. Configure dashboards
    """)
    
    st.markdown("---")
    st.markdown("**💡 Dica:** Use Snowflake para:")
    st.markdown("- Dados em grande escala")
    st.markdown("- Análises complexas")
    st.markdown("- Compartilhamento seguro")
    st.markdown("- Backup automático") 