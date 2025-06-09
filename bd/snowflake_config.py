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

def upload_excel_to_snowflake(df, arquivo_nome, usuario="minipa", table_type="TIMELINE"):
    """
    Upload Excel data to Snowflake with history tracking
    Returns True if successful, False otherwise
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # First, ensure tables exist - create them if they don't
        st.info(f"🔧 Verificando/criando tabelas para {table_type}...")
        try:
            if table_type == "TIMELINE":
                # Check for timeline table
                cursor.execute("SHOW TABLES LIKE 'PRODUTOS' IN SCHEMA ESTOQUE")
                result = cursor.fetchall()
                
                if not result:
                    st.info("📋 Criando tabela PRODUTOS (Timeline)...")
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ESTOQUE.PRODUTOS (
                        id INTEGER AUTOINCREMENT PRIMARY KEY,
                        item VARCHAR(100),
                        modelo VARCHAR(200),
                        fornecedor VARCHAR(200),
                        qtd_atual INTEGER,
                        preco_unitario DECIMAL(10,2),
                        estoque_total INTEGER,
                        in_transit INTEGER,
                        vendas_medias DECIMAL(10,2),
                        cbm DECIMAL(8,4),
                        moq INTEGER,
                        data_upload TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
                        usuario VARCHAR(50),
                        table_type VARCHAR(20) DEFAULT 'TIMELINE'
                    )
                    """)
                else:
                    # Table exists, check if table_type column exists and add if not
                    try:
                        cursor.execute("SELECT table_type FROM ESTOQUE.PRODUTOS LIMIT 1")
                    except:
                        # table_type column doesn't exist, add it
                        st.info("🔄 Adicionando coluna table_type à tabela existente...")
                        try:
                            cursor.execute("ALTER TABLE ESTOQUE.PRODUTOS ADD COLUMN table_type VARCHAR(20) DEFAULT 'TIMELINE'")
                            conn.commit()
                            st.success("✅ Coluna table_type adicionada!")
                        except Exception as alter_error:
                            st.warning(f"⚠️ Erro ao adicionar coluna: {str(alter_error)}")
                            # Continue without table_type for backwards compatibility
            
            else:  # ANALYTICS
                # Check for analytics table
                cursor.execute("SHOW TABLES LIKE 'ANALYTICS_DATA' IN SCHEMA ESTOQUE")
                result = cursor.fetchall()
                
                if not result:
                    st.info("📊 Criando tabela ANALYTICS_DATA...")
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ESTOQUE.ANALYTICS_DATA (
                        id INTEGER AUTOINCREMENT PRIMARY KEY,
                        produto VARCHAR(200),
                        estoque INTEGER,
                        consumo_6_meses DECIMAL(10,2),
                        media_6_meses DECIMAL(10,2),
                        estoque_cobertura DECIMAL(8,2),
                        data_upload TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
                        usuario VARCHAR(50),
                        table_type VARCHAR(20) DEFAULT 'ANALYTICS'
                    )
                    """)
            
            # Create log table if it doesn't exist
            cursor.execute("SHOW TABLES LIKE 'UPLOAD_LOG' IN SCHEMA CONFIG")
            log_result = cursor.fetchall()
            
            if not log_result:
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS CONFIG.UPLOAD_LOG (
                    id INTEGER AUTOINCREMENT PRIMARY KEY,
                    nome_arquivo VARCHAR(255),
                    tamanho_arquivo INTEGER,
                    linhas_processadas INTEGER,
                    data_upload TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
                    usuario VARCHAR(50),
                    status VARCHAR(20),
                    table_type VARCHAR(20)
                )
                """)
            
            conn.commit()
            st.success(f"✅ Tabelas para {table_type} verificadas/criadas!")
            
        except Exception as table_error:
            st.warning(f"⚠️ Erro ao verificar/criar tabelas: {str(table_error)}")
            # Continue anyway - maybe tables exist but show command failed
        
        # Clean the dataframe - remove NaN and empty rows
        df_clean = df.copy()
        df_clean = df_clean.dropna(how='all')
        
        # Get actual column names from the dataframe
        available_columns = list(df_clean.columns)
        st.info(f"📊 Colunas encontradas: {available_columns}")
        
        success_count = 0
        
        # Insert new data row by row based on table type
        if table_type == "TIMELINE":
            # Timeline data insertion
            for idx, row in df_clean.iterrows():
                try:
                    # Extract values for timeline table
                    item = str(row.get('Item', '')) if 'Item' in row.index else ''
                    modelo = str(row.get('Modelo', '')) if 'Modelo' in row.index else ''
                    fornecedor = str(row.get('Fornecedor', '')) if 'Fornecedor' in row.index else ''
                    
                    # Handle numeric values safely
                    def safe_numeric(val, default=0):
                        if pd.isna(val) or val == '' or str(val).lower() == 'nan':
                            return default
                        try:
                            return int(float(str(val)))
                        except:
                            return default
                    
                    def safe_float(val, default=0.0):
                        if pd.isna(val) or val == '' or str(val).lower() == 'nan':
                            return default
                        try:
                            return float(val)
                        except:
                            return default
                    
                    qtd_atual = safe_numeric(row.get('QTD', 0))
                    preco_unitario = safe_float(row.get('Preco_Unitario', 0.0))
                    estoque_total = safe_numeric(row.get('Estoque_Total', 0)) 
                    in_transit = safe_numeric(row.get('In_Transit', 0))
                    vendas_medias = safe_float(row.get('Vendas_Medias', 0.0))
                    cbm = safe_float(row.get('CBM', 0.0))
                    moq = safe_numeric(row.get('MOQ', 0))
                    
                    # Skip completely empty rows
                    if not any([item, modelo, fornecedor]) and all(v == 0 for v in [qtd_atual, estoque_total]):
                        continue
                    
                    # Insert timeline data
                    try:
                        # Try with table_type column first
                        cursor.execute("""
                        INSERT INTO ESTOQUE.PRODUTOS 
                        (item, modelo, fornecedor, qtd_atual, preco_unitario, estoque_total, 
                         in_transit, vendas_medias, cbm, moq, usuario, table_type)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (item, modelo, fornecedor, qtd_atual, preco_unitario, estoque_total, 
                              in_transit, vendas_medias, cbm, moq, usuario, table_type))
                    except Exception:
                        # If table_type column doesn't exist, insert without it
                        cursor.execute("""
                        INSERT INTO ESTOQUE.PRODUTOS 
                        (item, modelo, fornecedor, qtd_atual, preco_unitario, estoque_total, 
                         in_transit, vendas_medias, cbm, moq, usuario)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (item, modelo, fornecedor, qtd_atual, preco_unitario, estoque_total, 
                              in_transit, vendas_medias, cbm, moq, usuario))
                    
                    success_count += 1
                    
                except Exception as row_error:
                    st.warning(f"⚠️ Erro na linha {idx + 1}: {str(row_error)}")
                    continue
                    
        else:  # ANALYTICS
            # Analytics data insertion
            for idx, row in df_clean.iterrows():
                try:
                    # Extract values for analytics table - look for common analytics column names
                    produto = str(row.get('Produto', ''))
                    if not produto:  # Try alternative column names
                        produto = str(row.get('Item', '') or row.get('Modelo', ''))
                    
                    def safe_numeric(val, default=0):
                        if pd.isna(val) or val == '' or str(val).lower() == 'nan':
                            return default
                        try:
                            return int(float(str(val)))
                        except:
                            return default
                    
                    def safe_float(val, default=0.0):
                        if pd.isna(val) or val == '' or str(val).lower() == 'nan':
                            return default
                        try:
                            return float(val)
                        except:
                            return default
                    
                    estoque = safe_numeric(row.get('Estoque', 0))
                    consumo_6_meses = safe_float(row.get('Consumo 6 Meses', 0.0))
                    media_6_meses = safe_float(row.get('Média 6 Meses', 0.0))
                    estoque_cobertura = safe_float(row.get('Estoque Cobertura', 0.0))
                    
                    # Skip completely empty rows
                    if not produto and all(v == 0 for v in [estoque, consumo_6_meses, media_6_meses]):
                        continue
                    
                    # Insert analytics data
                    cursor.execute("""
                    INSERT INTO ESTOQUE.ANALYTICS_DATA 
                    (produto, estoque, consumo_6_meses, media_6_meses, estoque_cobertura, usuario, table_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (produto, estoque, consumo_6_meses, media_6_meses, estoque_cobertura, usuario, table_type))
                    
                    success_count += 1
                    
                except Exception as row_error:
                    st.warning(f"⚠️ Erro na linha {idx + 1}: {str(row_error)}")
                    continue
        
        # Log the upload (only if CONFIG schema and table exist)
        try:
            # Try with table_type column first
            cursor.execute("""
            INSERT INTO CONFIG.UPLOAD_LOG 
            (nome_arquivo, linhas_processadas, usuario, status, table_type)
            VALUES (%s, %s, %s, %s, %s)
            """, (arquivo_nome, success_count, usuario, 'SUCCESS', table_type))
        except Exception:
            # If table_type column doesn't exist or table doesn't exist, try without it
            try:
                cursor.execute("""
                INSERT INTO CONFIG.UPLOAD_LOG 
                (nome_arquivo, linhas_processadas, usuario, status)
                VALUES (%s, %s, %s, %s)
                """, (arquivo_nome, success_count, usuario, 'SUCCESS'))
            except:
                # If log table doesn't exist, continue without logging
                pass
        
        conn.commit()
        cursor.close()
        conn.close()
        
        st.success(f"✅ {success_count} linhas processadas com sucesso!")
        return True
        
    except Exception as e:
        st.error(f"❄️ Erro ao fazer upload: {str(e)}")
        st.error(f"📊 Detalhes do erro: {type(e).__name__}")
        
        # Show more helpful error message
        error_str = str(e)
        if "does not exist" in error_str:
            st.error("🔧 **Problema**: As tabelas não existem no Snowflake")
            st.info("💡 **Solução**: Vá para a página 'Snowflake' e clique em 'Criar Tabelas'")
        
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
        
        # Try different starting rows to find headers - expanded range
        for sheet in sheets[:5]:  # Check first 5 sheets
            st.subheader(f"📊 Análise da planilha: {sheet}")
            
            # Try more header positions, especially around row 8-9 where the user's data is
            for header_row in [0, 8, 9, 10, 7, 6, 11, 12]:
                try:
                    df_sample = pd.read_excel(uploaded_file, sheet_name=sheet, header=header_row, nrows=5)
                    
                    # Check if we found real headers (not None or Unnamed)
                    valid_columns = 0
                    real_headers = []
                    
                    for col in df_sample.columns:
                        col_str = str(col).strip()
                        if (col_str != 'None' and 
                            not col_str.startswith('Unnamed') and 
                            col_str != 'nan' and
                            len(col_str) > 0):
                            valid_columns += 1
                            real_headers.append(col_str)
                    
                    # We need at least 3 valid columns with meaningful names
                    if valid_columns >= 3 and len(df_sample) > 0:
                        # Check if we have data in the rows (not all None)
                        data_found = False
                        for _, row in df_sample.iterrows():
                            non_null_values = row.count()
                            if non_null_values >= 3:
                                data_found = True
                                break
                        
                        if data_found:
                            st.success(f"✅ Estrutura detectada em linha {header_row + 1}")
                            st.info(f"🔍 Colunas válidas encontradas: {real_headers}")
                            st.dataframe(df_sample)
                            
                            # Show column info
                            st.write("**Mapeamento de colunas:**")
                            for i, col in enumerate(df_sample.columns):
                                col_type = df_sample[col].dtype
                                sample_val = df_sample[col].iloc[0] if len(df_sample) > 0 else "N/A"
                                st.write(f"{i+1}. `{col}` - Tipo: {col_type} - Exemplo: {sample_val}")
                            
                            return sheet, header_row
                except Exception as e:
                    continue
        
        # If no automatic detection worked, show manual options
        st.warning("⚠️ Detecção automática não funcionou. Mostrando opções manuais...")
        
        # Show raw data for manual inspection
        for sheet in sheets[:2]:
            st.write(f"**Dados brutos da planilha '{sheet}':**")
            try:
                df_raw = pd.read_excel(uploaded_file, sheet_name=sheet, header=None, nrows=15)
                st.dataframe(df_raw)
                
                # Suggest header row based on where we see most text
                for row_idx in range(min(15, len(df_raw))):
                    row_data = df_raw.iloc[row_idx]
                    text_count = sum(1 for val in row_data if isinstance(val, str) and len(str(val)) > 2)
                    if text_count >= 3:
                        st.info(f"💡 Possível cabeçalho na linha {row_idx + 1}: {list(row_data[:5])}")
                        return sheet, row_idx
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
        # First, check if the table exists and has data
        cursor = conn.cursor()
        
        # Simple check if table exists
        try:
            # First try with table_type column
            cursor.execute("SELECT COUNT(*) FROM ESTOQUE.PRODUTOS WHERE usuario = %s AND table_type = 'TIMELINE'", [usuario])
            total_records = cursor.fetchone()[0]
            use_table_type = True
            
        except Exception:
            # If table_type column doesn't exist, try without it (backwards compatibility)
            try:
                cursor.execute("SELECT COUNT(*) FROM ESTOQUE.PRODUTOS WHERE usuario = %s", [usuario])
                total_records = cursor.fetchone()[0]
                use_table_type = False
                st.info("🔄 Usando tabela sem filtro de tipo (compatibilidade)")
            except Exception as table_error:
                st.warning(f"⚠️ Tabela pode não existir ainda: {str(table_error)}")
                cursor.close()
                conn.close()
                return None
        
        if total_records == 0:
            st.info("💡 Nenhum dado de timeline encontrado na tabela. Faça um upload de dados de timeline primeiro.")
            cursor.close()
            conn.close()
            return None
        
        # If we have data, execute the full query with proper column mapping
        if use_table_type:
            # Use query with table_type filter
            query = """
            SELECT item as "Item", 
                   modelo as "Modelo", 
                   fornecedor as "Fornecedor", 
                   qtd_atual as "QTD", 
                   preco_unitario as "Preco_Unitario", 
                   estoque_total as "Estoque_Total",
                   in_transit as "In_Transit", 
                   vendas_medias as "Vendas_Medias",
                   cbm as "CBM", 
                   moq as "MOQ", 
                   data_upload,
                   ROW_NUMBER() OVER (PARTITION BY item ORDER BY data_upload DESC) as row_num
            FROM ESTOQUE.PRODUTOS 
            WHERE usuario = %s 
            AND table_type = 'TIMELINE'
            AND data_upload >= DATEADD(day, %s, CURRENT_DATE())
            ORDER BY data_upload DESC
            """
        else:
            # Use query without table_type filter (backwards compatibility)
            query = """
            SELECT item as "Item", 
                   modelo as "Modelo", 
                   fornecedor as "Fornecedor", 
                   qtd_atual as "QTD", 
                   preco_unitario as "Preco_Unitario", 
                   estoque_total as "Estoque_Total",
                   in_transit as "In_Transit", 
                   vendas_medias as "Vendas_Medias",
                   cbm as "CBM", 
                   moq as "MOQ", 
                   data_upload,
                   ROW_NUMBER() OVER (PARTITION BY item ORDER BY data_upload DESC) as row_num
            FROM ESTOQUE.PRODUTOS 
            WHERE usuario = %s 
            AND data_upload >= DATEADD(day, %s, CURRENT_DATE())
            ORDER BY data_upload DESC
            """
        
        cursor.close()  # Close the cursor before pandas read_sql
        
        df = pd.read_sql(query, conn, params=[usuario, -limit_days])
        conn.close()
        
        # Check if we got any data
        if df.empty:
            st.info(f"💡 Nenhum dado encontrado nos últimos {limit_days} dias.")
            return None
        
        # Check if row_num column exists before trying to use it
        if 'row_num' not in df.columns:
            st.warning("⚠️ Estrutura de dados inesperada. Retornando dados sem filtro de histórico.")
            return df
        
        # Show history summary and filter for latest records
        try:
            latest_df = df[df['row_num'] == 1].drop('row_num', axis=1)
            history_count = len(df[df['row_num'] > 1])
            
            st.info(f"📅 Dados atuais: {len(latest_df)} produtos | 📈 Histórico: {history_count} registros")
            
            return latest_df
            
        except Exception as filter_error:
            st.warning(f"⚠️ Erro ao filtrar histórico: {str(filter_error)}. Retornando todos os dados.")
            # Remove only row_num column if it exists, keep everything else including data_upload
            if 'row_num' in df.columns:
                df = df.drop('row_num', axis=1)
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

def load_analytics_data(usuario="minipa", limit_days=30):
    """
    Load analytics data from Snowflake for análise de estoque
    """
    conn = get_snowflake_connection()
    if not conn:
        return None
        
    try:
        # First, check if the analytics table exists and has data
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM ESTOQUE.ANALYTICS_DATA WHERE usuario = %s", [usuario])
            total_records = cursor.fetchone()[0]
            
            if total_records == 0:
                st.info("💡 Nenhum dado de análise encontrado. Faça upload de um arquivo de análise primeiro.")
                cursor.close()
                conn.close()
                return None
                
        except Exception as table_error:
            # Table doesn't exist yet
            st.warning(f"⚠️ Tabela de análise não existe ainda: {str(table_error)}")
            st.info("💡 A tabela será criada automaticamente no primeiro upload de análise.")
            cursor.close()
            conn.close()
            return None
        
        # Load analytics data
        query = """
        SELECT produto as "Produto", 
               estoque as "Estoque", 
               consumo_6_meses as "Consumo 6 Meses",
               media_6_meses as "Média 6 Meses", 
               estoque_cobertura as "Estoque Cobertura",
               data_upload,
               ROW_NUMBER() OVER (PARTITION BY produto ORDER BY data_upload DESC) as row_num
        FROM ESTOQUE.ANALYTICS_DATA 
        WHERE usuario = %s 
        AND data_upload >= DATEADD(day, %s, CURRENT_DATE())
        ORDER BY data_upload DESC
        """
        
        cursor.close()
        
        df = pd.read_sql(query, conn, params=[usuario, -limit_days])
        conn.close()
        
        # Check if we got any data
        if df.empty:
            st.info(f"💡 Nenhum dado de análise encontrado nos últimos {limit_days} dias.")
            return None
        
        # Filter for latest records only
        if 'row_num' in df.columns:
            try:
                latest_df = df[df['row_num'] == 1].drop('row_num', axis=1)
                history_count = len(df[df['row_num'] > 1])
                
                st.info(f"📊 Dados de análise: {len(latest_df)} produtos | 📈 Histórico: {history_count} registros")
                
                return latest_df
                
            except Exception as filter_error:
                st.warning(f"⚠️ Erro ao filtrar histórico: {str(filter_error)}. Retornando todos os dados.")
                if 'row_num' in df.columns:
                    df = df.drop('row_num', axis=1)
                return df
        
        return df
        
    except Exception as e:
        st.error(f"❄️ Erro ao carregar dados de análise: {str(e)}")
        return None

def migrate_existing_tables():
    """
    Migrate existing tables to new structure with table_type column
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        st.info("🔄 Verificando e atualizando estrutura das tabelas...")
        
        # Check and update PRODUTOS table
        try:
            cursor.execute("SELECT table_type FROM ESTOQUE.PRODUTOS LIMIT 1")
            st.success("✅ Tabela PRODUTOS já tem coluna table_type")
        except:
            st.info("📋 Adicionando coluna table_type à tabela PRODUTOS...")
            cursor.execute("ALTER TABLE ESTOQUE.PRODUTOS ADD COLUMN table_type VARCHAR(20) DEFAULT 'TIMELINE'")
            st.success("✅ Coluna table_type adicionada à tabela PRODUTOS")
        
        # Check and update UPLOAD_LOG table
        try:
            cursor.execute("SELECT table_type FROM CONFIG.UPLOAD_LOG LIMIT 1")
            st.success("✅ Tabela UPLOAD_LOG já tem coluna table_type")
        except:
            st.info("📋 Adicionando coluna table_type à tabela UPLOAD_LOG...")
            cursor.execute("ALTER TABLE CONFIG.UPLOAD_LOG ADD COLUMN table_type VARCHAR(20)")
            st.success("✅ Coluna table_type adicionada à tabela UPLOAD_LOG")
        
        # Create ANALYTICS_DATA table if it doesn't exist
        try:
            cursor.execute("SHOW TABLES LIKE 'ANALYTICS_DATA' IN SCHEMA ESTOQUE")
            result = cursor.fetchall()
            
            if not result:
                st.info("📊 Criando tabela ANALYTICS_DATA...")
                cursor.execute("""
                CREATE TABLE ESTOQUE.ANALYTICS_DATA (
                    id INTEGER AUTOINCREMENT PRIMARY KEY,
                    produto VARCHAR(200),
                    estoque INTEGER,
                    consumo_6_meses DECIMAL(10,2),
                    media_6_meses DECIMAL(10,2),
                    estoque_cobertura DECIMAL(8,2),
                    data_upload TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
                    usuario VARCHAR(50),
                    table_type VARCHAR(20) DEFAULT 'ANALYTICS'
                )
                """)
                st.success("✅ Tabela ANALYTICS_DATA criada")
            else:
                st.success("✅ Tabela ANALYTICS_DATA já existe")
        except Exception as e:
            st.warning(f"⚠️ Erro ao criar tabela ANALYTICS_DATA: {str(e)}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        st.success("🎉 Migração concluída! Todas as tabelas foram atualizadas.")
        return True
        
    except Exception as e:
        st.error(f"❌ Erro na migração: {str(e)}")
        return False 