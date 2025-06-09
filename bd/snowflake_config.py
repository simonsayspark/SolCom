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
        if not hasattr(st, 'secrets') or "snowflake" not in st.secrets:
            st.error("❄️ Snowflake não configurado. Configure em .streamlit/secrets.toml")
            st.info("💡 Verifique se o arquivo .streamlit/secrets.toml está configurado corretamente.")
            return None
            
        # Create connection
        conn = snowflake.connector.connect(
            account=st.secrets.snowflake.account,
            user=st.secrets.snowflake.user,
            password=st.secrets.snowflake.password,
            role=st.secrets.snowflake.role,
            warehouse=st.secrets.snowflake.warehouse,
            database=st.secrets.snowflake.database,
            schema=st.secrets.snowflake.schema
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
        if "snowflake" not in st.secrets:
            return None
            
        connection_parameters = {
            "ACCOUNT": st.secrets.snowflake.account,
            "USER": st.secrets.snowflake.user,
            "PASSWORD": st.secrets.snowflake.password,
            "ROLE": st.secrets.snowflake.role,
            "WAREHOUSE": st.secrets.snowflake.warehouse,
            "DATABASE": st.secrets.snowflake.database,
            "SCHEMA": st.secrets.snowflake.schema
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
        
        # Clear existing data (for this demo - in production you might want versioning)
        cursor.execute("DELETE FROM ESTOQUE.PRODUTOS WHERE usuario = %s", (usuario,))
        
        # Insert new data
        for idx, row in df.iterrows():
            cursor.execute("""
            INSERT INTO ESTOQUE.PRODUTOS 
            (item, modelo, fornecedor, qtd_atual, preco_unitario, estoque_total, 
             in_transit, vendas_medias, cbm, moq, usuario)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                str(row.get('Item', '')),
                str(row.get('Modelo', '')),
                str(row.get('Fornecedor', '')),
                int(row.get('QTD', 0)),
                float(row.get('Preco_Unitario', 0)),
                int(row.get('Estoque_Total', 0)),
                int(row.get('In_Transit', 0)),
                float(row.get('Vendas_Medias', 0)),
                float(row.get('CBM', 0)),
                int(row.get('MOQ', 0)),
                usuario
            ))
        
        # Log the upload
        cursor.execute("""
        INSERT INTO CONFIG.UPLOAD_LOG 
        (nome_arquivo, linhas_processadas, usuario, status)
        VALUES (%s, %s, %s, %s)
        """, (arquivo_nome, len(df), usuario, 'SUCCESS'))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"❄️ Erro ao fazer upload: {str(e)}")
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
        WHERE usuario = %s
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