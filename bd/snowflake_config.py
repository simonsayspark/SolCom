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
    Upload Excel data to Snowflake with history tracking
    Returns True if successful, False otherwise
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # Don't clear existing data - keep for history
        # Instead, add new data with timestamp
        
        # Clean the dataframe - remove NaN and empty rows
        df_clean = df.copy()
        
        # Remove completely empty rows
        df_clean = df_clean.dropna(how='all')
        
        # Get actual column names from the dataframe
        available_columns = list(df_clean.columns)
        st.info(f"📊 Colunas encontradas: {available_columns}")
        
        # Insert new data - adapting to whatever columns exist
        for idx, row in df_clean.iterrows():
            # Skip if all important values are NaN
            if pd.isna(row).all():
                continue
                
            # Prepare values safely
            values = []
            for col in available_columns[:10]:  # Limit to first 10 columns to match table
                val = row[col] if col in row.index else ''
                
                # Handle different data types safely
                if pd.isna(val) or val == '' or str(val).lower() == 'nan':
                    if col in ['QTD', 'Estoque_Total', 'In_Transit', 'MOQ']:
                        values.append(0)  # Numeric defaults to 0
                    elif col in ['Preco_Unitario', 'Vendas_Medias', 'CBM']:
                        values.append(0.0)  # Float defaults to 0.0
                    else:
                        values.append('')  # String defaults to empty
                else:
                    # Convert based on expected type
                    if col in ['QTD', 'Estoque_Total', 'In_Transit', 'MOQ']:
                        try:
                            values.append(int(float(str(val))))
                        except:
                            values.append(0)
                    elif col in ['Preco_Unitario', 'Vendas_Medias', 'CBM']:
                        try:
                            values.append(float(str(val)))
                        except:
                            values.append(0.0)
                    else:
                        values.append(str(val))
            
            # Ensure we have exactly 11 values (10 data + 1 user)
            while len(values) < 10:
                values.append('')
            values.append(usuario)  # Add user at the end
            
            # Insert with proper parameter binding
            cursor.execute("""
            INSERT INTO ESTOQUE.PRODUTOS 
            (item, modelo, fornecedor, qtd_atual, preco_unitario, estoque_total, 
             in_transit, vendas_medias, cbm, moq, usuario)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, values)
        
        # Log the upload
        cursor.execute("""
        INSERT INTO CONFIG.UPLOAD_LOG 
        (nome_arquivo, linhas_processadas, usuario, status)
        VALUES (?, ?, ?, ?)
        """, (arquivo_nome, len(df_clean), usuario, 'SUCCESS'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        st.success(f"✅ {len(df_clean)} linhas processadas (sem NaN)")
        return True
        
    except Exception as e:
        st.error(f"❄️ Erro ao fazer upload: {str(e)}")
        st.error(f"📊 Detalhes do erro: {type(e).__name__}")
        return False

def analyze_excel_structure(uploaded_file):
    """
    Analyze Excel file structure and suggest best processing approach
    """
    try:
        # Try to read Excel file and detect structure
        xl_file = pd.ExcelFile(uploaded_file)
        sheets = xl_file.sheet_names
        
        st.info(f"📋 Planilhas encontradas: {sheets}")
        
        # Try different starting rows to find headers
        for sheet in sheets[:3]:  # Check first 3 sheets
            st.subheader(f"📊 Análise da planilha: {sheet}")
            
            for header_row in [0, 9, 10]:  # Common header positions
                try:
                    df_sample = pd.read_excel(uploaded_file, sheet_name=sheet, header=header_row, nrows=5)
                    if not df_sample.empty and len(df_sample.columns) > 3:
                        st.success(f"✅ Estrutura detectada em linha {header_row}")
                        st.dataframe(df_sample)
                        
                        # Show column info
                        st.write("**Colunas detectadas:**")
                        for i, col in enumerate(df_sample.columns):
                            st.write(f"{i+1}. `{col}` - Tipo: {df_sample[col].dtype}")
                        
                        return sheet, header_row
                except:
                    continue
        
        return None, 0
                        
    except Exception as e:
        st.error(f"❌ Erro ao analisar Excel: {str(e)}")
        return None, 0

def load_data_with_history(usuario="minipa", limit_days=30):
    """
    Load data from Snowflake with history tracking
    """
    conn = get_snowflake_connection()
    if not conn:
        return None
        
    try:
        query = """
        SELECT item, modelo, fornecedor, qtd_atual as QTD, 
               preco_unitario as "Preco_Unitario", estoque_total as "Estoque_Total",
               in_transit as "In_Transit", vendas_medias as "Vendas_Medias",
               cbm as CBM, moq as MOQ, data_upload,
               ROW_NUMBER() OVER (PARTITION BY item ORDER BY data_upload DESC) as row_num
        FROM ESTOQUE.PRODUTOS 
        WHERE usuario = ? 
        AND data_upload >= DATEADD(day, ?, CURRENT_DATE())
        ORDER BY data_upload DESC
        """
        
        df = pd.read_sql(query, conn, params=(usuario, -limit_days))
        conn.close()
        
        # Show history summary
        if not df.empty:
            latest_df = df[df['row_num'] == 1].drop('row_num', axis=1)
            history_count = len(df[df['row_num'] > 1])
            
            st.info(f"📅 Dados atuais: {len(latest_df)} produtos | 📈 Histórico: {history_count} registros")
            
            return latest_df
        
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