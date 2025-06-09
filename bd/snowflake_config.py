"""
Snowflake Database Configuration
Simple database structure for MINIPA purchasing system
"""

import streamlit as st
import pandas as pd
import snowflake.connector
from snowflake.snowpark import Session
import json
from datetime import datetime

# Recommended database schema structure
DATABASE_SCHEMA = {
    "database": "COMPRAS_MINIPA",
    "schemas": {
        "ESTOQUE": "Inventory and stock data",
        "TIMELINE": "Purchase timeline analysis", 
        "ANALYTICS": "Reports and analytics",
        "CONFIG": "Configuration and metadata"
    }
}

def get_snowflake_connection():
    """
    Get Snowflake connection using Streamlit secrets
    Returns connection object or None if failed
    """
    try:
        # Check if secrets are configured
        if not hasattr(st, 'secrets') or "connections" not in st.secrets or "snowflake" not in st.secrets.connections:
            st.error("❄️ Snowflake não configurado. Configure em .streamlit/secrets.toml")
            st.info("💡 Verifique se o arquivo .streamlit/secrets.toml está configurado corretamente.")
            return None
            
        # Create connection using the same format as st.connection
        snowflake_config = st.secrets.connections.snowflake
        conn = snowflake.connector.connect(
            account=snowflake_config.account,
            user=snowflake_config.user,
            password=snowflake_config.password,
            role=snowflake_config.role,
            warehouse=snowflake_config.warehouse,
            database=snowflake_config.database,
            schema=snowflake_config.schema
        )
        return conn
    except Exception as e:
        st.error(f"❄️ Erro ao conectar com Snowflake: {str(e)}")
        st.info("💡 Verifique se o arquivo .streamlit/secrets.toml está configurado corretamente.")
        return None

def get_snowpark_session():
    """
    Get Snowpark session for advanced operations
    """
    try:
        if "connections" not in st.secrets or "snowflake" not in st.secrets.connections:
            return None
            
        snowflake_config = st.secrets.connections.snowflake
        connection_parameters = {
            "ACCOUNT": snowflake_config.account,
            "USER": snowflake_config.user,
            "PASSWORD": snowflake_config.password,
            "ROLE": snowflake_config.role,
            "WAREHOUSE": snowflake_config.warehouse,
            "DATABASE": snowflake_config.database,
            "SCHEMA": snowflake_config.schema
        }
        
        session = Session.builder.configs(connection_parameters).create()
        return session
    except Exception as e:
        st.error(f"❄️ Erro ao criar sessão Snowpark: {str(e)}")
        return None

def create_tables():
    """
    Create the basic table structure for MINIPA system
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # Create main inventory table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ESTOQUE.PRODUTOS (
            id INTEGER AUTOINCREMENT PRIMARY KEY,
            item VARCHAR(50),
            modelo VARCHAR(100),
            fornecedor VARCHAR(100),
            qtd_atual INTEGER,
            preco_unitario DECIMAL(10,2),
            estoque_total INTEGER,
            in_transit INTEGER,
            vendas_medias DECIMAL(10,2),
            cbm DECIMAL(8,4),
            moq INTEGER,
            data_upload TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
            usuario VARCHAR(50)
        )
        """)
        
        # Create timeline analysis table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS TIMELINE.ANALISES (
            id INTEGER AUTOINCREMENT PRIMARY KEY,
            produto_id INTEGER,
            dias_restantes INTEGER,
            urgencia VARCHAR(20),
            qtd_comprar INTEGER,
            valor_pedido DECIMAL(12,2),
            data_analise TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
            meta_meses INTEGER
        )
        """)
        
        # Create file upload log
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS CONFIG.UPLOAD_LOG (
            id INTEGER AUTOINCREMENT PRIMARY KEY,
            nome_arquivo VARCHAR(255),
            tamanho_arquivo INTEGER,
            linhas_processadas INTEGER,
            data_upload TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
            usuario VARCHAR(50),
            status VARCHAR(20)
        )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"❄️ Erro ao criar tabelas: {str(e)}")
        return False

def upload_excel_to_snowflake(df, arquivo_nome, usuario="minipa"):
    """
    Upload Excel data to Snowflake
    Returns True if successful, False otherwise
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # Debug: Show dataframe info
        st.info(f"🔍 Debug: DataFrame shape: {df.shape}")
        st.info(f"🔍 Debug: Columns: {list(df.columns)}")
        
        # Check if required columns exist
        required_columns = ['Item', 'Modelo', 'Fornecedor', 'QTD', 'Preco_Unitario', 
                          'Estoque_Total', 'In_Transit', 'Vendas_Medias', 'CBM', 'MOQ']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"❌ Colunas obrigatórias não encontradas: {missing_columns}")
            st.info("💡 Certifique-se de que o arquivo Excel foi processado corretamente")
            return False
        
        # Clear existing data (for this demo - in production you might want versioning)
        cursor.execute("DELETE FROM ESTOQUE.PRODUTOS WHERE usuario = ?", (usuario,))
        
        # Insert new data with better error handling
        success_count = 0
        for idx, row in df.iterrows():
            try:
                # Convert and validate data
                item = str(row.get('Item', ''))[:50]  # Limit to 50 chars
                modelo = str(row.get('Modelo', ''))[:100]  # Limit to 100 chars
                fornecedor = str(row.get('Fornecedor', ''))[:100]  # Limit to 100 chars
                
                # Handle numeric conversions safely
                qtd_atual = int(float(row.get('QTD', 0))) if pd.notna(row.get('QTD')) else 0
                preco_unitario = float(row.get('Preco_Unitario', 0)) if pd.notna(row.get('Preco_Unitario')) else 0.0
                estoque_total = int(float(row.get('Estoque_Total', 0))) if pd.notna(row.get('Estoque_Total')) else 0
                in_transit = int(float(row.get('In_Transit', 0))) if pd.notna(row.get('In_Transit')) else 0
                vendas_medias = float(row.get('Vendas_Medias', 0)) if pd.notna(row.get('Vendas_Medias')) else 0.0
                cbm = float(row.get('CBM', 0)) if pd.notna(row.get('CBM')) else 0.0
                moq = int(float(row.get('MOQ', 0))) if pd.notna(row.get('MOQ')) else 0
                
                cursor.execute("""
                INSERT INTO ESTOQUE.PRODUTOS 
                (item, modelo, fornecedor, qtd_atual, preco_unitario, estoque_total, 
                 in_transit, vendas_medias, cbm, moq, usuario)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item, modelo, fornecedor, qtd_atual, preco_unitario, 
                    estoque_total, in_transit, vendas_medias, cbm, moq, usuario
                ))
                success_count += 1
                
            except Exception as row_error:
                st.warning(f"⚠️ Erro na linha {idx}: {str(row_error)}")
                continue
        
        # Log the upload
        cursor.execute("""
        INSERT INTO CONFIG.UPLOAD_LOG 
        (nome_arquivo, linhas_processadas, usuario, status)
        VALUES (?, ?, ?, ?)
        """, (arquivo_nome, success_count, usuario, 'SUCCESS'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        if success_count > 0:
            st.success(f"✅ {success_count} registros inseridos com sucesso!")
            return True
        else:
            st.error("❌ Nenhum registro foi inserido")
            return False
        
    except Exception as e:
        st.error(f"❄️ Erro ao fazer upload: {str(e)}")
        st.error(f"🔍 Tipo do erro: {type(e).__name__}")
        return False

def load_data_from_snowflake(usuario="minipa"):
    """
    Load data from Snowflake
    Returns DataFrame or None if failed
    """
    conn = get_snowflake_connection()
    if not conn:
        return None
        
    try:
        query = """
        SELECT item, modelo, fornecedor, qtd_atual as QTD, 
               preco_unitario as "Preco_Unitario", estoque_total as "Estoque_Total",
               in_transit as "In_Transit", vendas_medias as "Vendas_Medias",
               cbm as CBM, moq as MOQ, data_upload
        FROM ESTOQUE.PRODUTOS 
        WHERE usuario = ?
        ORDER BY data_upload DESC
        """
        
        df = pd.read_sql(query, conn, params=(usuario,))
        conn.close()
        return df
        
    except Exception as e:
        st.error(f"❄️ Erro ao carregar dados: {str(e)}")
        return None

def test_connection():
    """
    Test Snowflake connection
    Returns True if successful
    """
    conn = get_snowflake_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT CURRENT_VERSION()")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            st.success(f"✅ Conectado ao Snowflake! Versão: {version}")
            return True
        except Exception as e:
            st.error(f"❄️ Erro no teste: {str(e)}")
            return False
    return False 