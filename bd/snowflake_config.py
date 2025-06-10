"""
Snowflake Database Configuration
Multi-company, versioned database structure for MINIPA purchasing system
"""

import streamlit as st
import pandas as pd
import snowflake.connector
from snowflake.snowpark import Session
import json
from datetime import datetime
import uuid

# Multi-company database schema structure
DATABASE_SCHEMA = {
    "database": "COMPRAS_MINIPA",
    "companies": ["MINIPA", "MINIPA_INDUSTRIA"],
    "schemas": {
        "ESTOQUE": "Inventory and stock data (multi-company, versioned)",
        "TIMELINE": "Purchase timeline analysis (multi-company, versioned)", 
        "ANALYTICS": "Reports and analytics (multi-company, versioned)",
        "CONFIG": "Configuration, metadata, and version control"
    },
    "versioning": {
        "enabled": True,
        "snapshot_based": True,
        "retention_days": 365
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
    Create the multi-company, versioned table structure for MINIPA system
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # Create main inventory table with company and version support
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ESTOQUE.PRODUTOS (
            id INTEGER AUTOINCREMENT PRIMARY KEY,
            empresa VARCHAR(50) NOT NULL,
            upload_version VARCHAR(50) NOT NULL,
            version_id INTEGER NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
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
            table_type VARCHAR(20) DEFAULT 'TIMELINE',
            version_description TEXT,
            created_by VARCHAR(50),
            UNIQUE(empresa, upload_version, item, modelo)
        )
        """)
        
        # Create analytics data table with company and version support
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ESTOQUE.ANALYTICS_DATA (
            id INTEGER AUTOINCREMENT PRIMARY KEY,
            empresa VARCHAR(50) NOT NULL,
            upload_version VARCHAR(50) NOT NULL,
            version_id INTEGER NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            produto VARCHAR(200),
            estoque INTEGER,
            consumo_6_meses DECIMAL(10,2),
            media_6_meses DECIMAL(10,2),
            estoque_cobertura DECIMAL(8,2),
            data_upload TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
            usuario VARCHAR(50),
            table_type VARCHAR(20) DEFAULT 'ANALYTICS',
            version_description TEXT,
            created_by VARCHAR(50),
            UNIQUE(empresa, upload_version, produto)
        )
        """)
        
        # Create timeline analysis table with company and version support
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS TIMELINE.ANALISES (
            id INTEGER AUTOINCREMENT PRIMARY KEY,
            empresa VARCHAR(50) NOT NULL,
            upload_version VARCHAR(50) NOT NULL,
            version_id INTEGER NOT NULL,
            produto_id INTEGER,
            dias_restantes INTEGER,
            urgencia VARCHAR(20),
            qtd_comprar INTEGER,
            valor_pedido DECIMAL(12,2),
            data_analise TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
            meta_meses INTEGER,
            created_by VARCHAR(50)
        )
        """)
        
        # Create version control table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS CONFIG.VERSIONS (
            id INTEGER AUTOINCREMENT PRIMARY KEY,
            empresa VARCHAR(50) NOT NULL,
            upload_version VARCHAR(50) NOT NULL,
            version_id INTEGER NOT NULL,
            table_type VARCHAR(20) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            upload_date TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
            created_by VARCHAR(50),
            description TEXT,
            arquivo_origem VARCHAR(255),
            linhas_processadas INTEGER,
            status VARCHAR(20) DEFAULT 'ACTIVE',
            UNIQUE(empresa, upload_version, table_type)
        )
        """)
        
        # Create file upload log with enhanced tracking
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS CONFIG.UPLOAD_LOG (
            id INTEGER AUTOINCREMENT PRIMARY KEY,
            empresa VARCHAR(50) NOT NULL,
            upload_version VARCHAR(50) NOT NULL,
            version_id INTEGER NOT NULL,
            nome_arquivo VARCHAR(255),
            tamanho_arquivo INTEGER,
            linhas_processadas INTEGER,
            data_upload TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
            usuario VARCHAR(50),
            status VARCHAR(20),
            table_type VARCHAR(20),
            error_details TEXT,
            processing_time_seconds INTEGER
        )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"❄️ Erro ao criar tabelas: {str(e)}")
        return False

def generate_version_id(empresa, table_type):
    """
    Generate next version ID for a company and table type
    """
    conn = get_snowflake_connection()
    if not conn:
        return 1
        
    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT COALESCE(MAX(version_id), 0) + 1 
        FROM CONFIG.VERSIONS 
        WHERE empresa = %s AND table_type = %s
        """, (empresa, table_type))
        
        result = cursor.fetchone()
        version_id = result[0] if result else 1
        
        cursor.close()
        conn.close()
        return version_id
        
    except Exception as e:
        st.warning(f"⚠️ Erro ao gerar version_id: {str(e)}")
        return 1

def create_new_version(empresa, table_type, description="", created_by="minipa", arquivo_origem=""):
    """
    Create a new version entry and return the version details
    """
    version_id = generate_version_id(empresa, table_type)
    upload_version = f"{empresa}_{table_type}_v{version_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    conn = get_snowflake_connection()
    if not conn:
        return None
        
    try:
        cursor = conn.cursor()
        
        # First, mark all previous versions as inactive for this company/table_type
        cursor.execute("""
        UPDATE CONFIG.VERSIONS 
        SET is_active = FALSE 
        WHERE empresa = %s AND table_type = %s
        """, (empresa, table_type))
        
        # Create new version entry
        cursor.execute("""
        INSERT INTO CONFIG.VERSIONS 
        (empresa, upload_version, version_id, table_type, is_active, created_by, description, arquivo_origem)
        VALUES (%s, %s, %s, %s, TRUE, %s, %s, %s)
        """, (empresa, upload_version, version_id, table_type, created_by, description, arquivo_origem))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            'empresa': empresa,
            'upload_version': upload_version,
            'version_id': version_id,
            'table_type': table_type,
            'description': description,
            'created_by': created_by
        }
        
    except Exception as e:
        st.error(f"❄️ Erro ao criar nova versão: {str(e)}")
        return None

def get_upload_versions(empresa, table_type=None, limit=50):
    """
    Get upload versions for a company, optionally filtered by table type
    """
    conn = get_snowflake_connection()
    if not conn:
        return []
        
    try:
        cursor = conn.cursor()
        
        if table_type:
            query = """
            SELECT empresa, upload_version, version_id, table_type, is_active, 
                   upload_date, created_by, description, arquivo_origem, linhas_processadas, status
            FROM CONFIG.VERSIONS 
            WHERE empresa = %s AND table_type = %s
            ORDER BY version_id DESC, upload_date DESC
            LIMIT %s
            """
            cursor.execute(query, (empresa, table_type, limit))
        else:
            query = """
            SELECT empresa, upload_version, version_id, table_type, is_active, 
                   upload_date, created_by, description, arquivo_origem, linhas_processadas, status
            FROM CONFIG.VERSIONS 
            WHERE empresa = %s
            ORDER BY version_id DESC, upload_date DESC
            LIMIT %s
            """
            cursor.execute(query, (empresa, limit))
        
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()
        
        versions = []
        for row in results:
            version_dict = dict(zip(columns, row))
            versions.append(version_dict)
        
        cursor.close()
        conn.close()
        return versions
        
    except Exception as e:
        st.error(f"❄️ Erro ao carregar versões: {str(e)}")
        return []

def set_active_version(empresa, upload_version, table_type):
    """
    Set a specific version as active for a company and table type
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # First, deactivate all versions for this company/table_type
        cursor.execute("""
        UPDATE CONFIG.VERSIONS 
        SET is_active = FALSE 
        WHERE empresa = %s AND table_type = %s
        """, (empresa, table_type))
        
        # Activate the specified version
        cursor.execute("""
        UPDATE CONFIG.VERSIONS 
        SET is_active = TRUE 
        WHERE empresa = %s AND upload_version = %s AND table_type = %s
        """, (empresa, upload_version, table_type))
        
        # Update corresponding data table records
        if table_type == "TIMELINE":
            cursor.execute("""
            UPDATE ESTOQUE.PRODUTOS 
            SET is_active = CASE 
                WHEN upload_version = %s THEN TRUE 
                ELSE FALSE 
            END
            WHERE empresa = %s AND table_type = %s
            """, (upload_version, empresa, table_type))
        elif table_type == "ANALYTICS":
            cursor.execute("""
            UPDATE ESTOQUE.ANALYTICS_DATA 
            SET is_active = CASE 
                WHEN upload_version = %s THEN TRUE 
                ELSE FALSE 
            END
            WHERE empresa = %s AND table_type = %s
            """, (upload_version, empresa, table_type))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"❄️ Erro ao ativar versão: {str(e)}")
        return False

def get_version_by_id(empresa, version_id, table_type):
    """
    Get specific version details by version ID
    """
    conn = get_snowflake_connection()
    if not conn:
        return None
        
    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT empresa, upload_version, version_id, table_type, is_active, 
               upload_date, created_by, description, arquivo_origem, linhas_processadas, status
        FROM CONFIG.VERSIONS 
        WHERE empresa = %s AND version_id = %s AND table_type = %s
        """, (empresa, version_id, table_type))
        
        result = cursor.fetchone()
        if result:
            columns = [desc[0] for desc in cursor.description]
            version_dict = dict(zip(columns, result))
            cursor.close()
            conn.close()
            return version_dict
        
        cursor.close()
        conn.close()
        return None
        
    except Exception as e:
        st.error(f"❄️ Erro ao carregar versão: {str(e)}")
        return None

def upload_excel_to_snowflake(df, arquivo_nome, empresa="MINIPA", usuario="minipa", table_type="TIMELINE", description=""):
    """
    Upload Excel data to Snowflake with multi-company versioning support
    Returns True if successful, False otherwise
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    start_time = datetime.now()
    
    try:
        cursor = conn.cursor()
        
        # Create new version for this upload
        st.info(f"🔄 Criando nova versão para {empresa} - {table_type}...")
        version_info = create_new_version(
            empresa=empresa, 
            table_type=table_type, 
            description=description, 
            created_by=usuario, 
            arquivo_origem=arquivo_nome
        )
        
        if not version_info:
            st.error("❌ Erro ao criar nova versão")
            return False
        
        upload_version = version_info['upload_version']
        version_id = version_info['version_id']
        
        st.success(f"✅ Nova versão criada: v{version_id} ({upload_version})")
        
        # Ensure tables exist
        st.info(f"🔧 Verificando estrutura das tabelas...")
        if not create_tables():
            st.warning("⚠️ Erro ao verificar/criar tabelas - continuando...")
        
        # Clean the dataframe - remove NaN and empty rows
        df_clean = df.copy()
        df_clean = df_clean.dropna(how='all')
        
        # Get actual column names from the dataframe
        available_columns = list(df_clean.columns)
        st.info(f"📊 Colunas encontradas: {available_columns}")
        
        success_count = 0
        error_count = 0
        
        # Helper functions for safe data conversion
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
        
        # Insert new data row by row based on table type
        if table_type == "TIMELINE":
            st.info(f"📋 Processando {len(df_clean)} linhas para Timeline de {empresa}...")
            
            for idx, row in df_clean.iterrows():
                try:
                    # Extract values for timeline table
                    item = str(row.get('Item', '')) if 'Item' in row.index else ''
                    modelo = str(row.get('Modelo', '')) if 'Modelo' in row.index else ''
                    fornecedor = str(row.get('Fornecedor', '')) if 'Fornecedor' in row.index else ''
                    
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
                    
                    # Insert timeline data with versioning
                    cursor.execute("""
                    INSERT INTO ESTOQUE.PRODUTOS 
                    (empresa, upload_version, version_id, is_active, item, modelo, fornecedor, 
                     qtd_atual, preco_unitario, estoque_total, in_transit, vendas_medias, 
                     cbm, moq, usuario, table_type, version_description, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (empresa, upload_version, version_id, True, item, modelo, fornecedor, 
                          qtd_atual, preco_unitario, estoque_total, in_transit, vendas_medias, 
                          cbm, moq, usuario, table_type, description, usuario))
                    
                    success_count += 1
                    
                except Exception as row_error:
                    error_count += 1
                    if error_count <= 5:  # Show only first 5 errors
                        st.warning(f"⚠️ Erro na linha {idx + 1}: {str(row_error)}")
                    continue
                    
        else:  # ANALYTICS
            st.info(f"📊 Processando {len(df_clean)} linhas para Analytics de {empresa}...")
            
            for idx, row in df_clean.iterrows():
                try:
                    # Extract values for analytics table
                    produto = str(row.get('Produto', ''))
                    if not produto:  # Try alternative column names
                        produto = str(row.get('Item', '') or row.get('Modelo', ''))
                    
                    estoque = safe_numeric(row.get('Estoque', 0))
                    consumo_6_meses = safe_float(row.get('Consumo 6 Meses', 0.0))
                    media_6_meses = safe_float(row.get('Média 6 Meses', 0.0))
                    estoque_cobertura = safe_float(row.get('Estoque Cobertura', 0.0))
                    
                    # Skip completely empty rows
                    if not produto and all(v == 0 for v in [estoque, consumo_6_meses, media_6_meses]):
                        continue
                    
                    # Insert analytics data with versioning
                    cursor.execute("""
                    INSERT INTO ESTOQUE.ANALYTICS_DATA 
                    (empresa, upload_version, version_id, is_active, produto, estoque, 
                     consumo_6_meses, media_6_meses, estoque_cobertura, usuario, table_type, 
                     version_description, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (empresa, upload_version, version_id, True, produto, estoque, 
                          consumo_6_meses, media_6_meses, estoque_cobertura, usuario, table_type, 
                          description, usuario))
                    
                    success_count += 1
                    
                except Exception as row_error:
                    error_count += 1
                    if error_count <= 5:  # Show only first 5 errors
                        st.warning(f"⚠️ Erro na linha {idx + 1}: {str(row_error)}")
                    continue
        
        # Calculate processing time
        end_time = datetime.now()
        processing_time = int((end_time - start_time).total_seconds())
        
        # Update version record with processing results
        try:
            cursor.execute("""
            UPDATE CONFIG.VERSIONS 
            SET linhas_processadas = %s, status = %s
            WHERE empresa = %s AND upload_version = %s AND table_type = %s
            """, (success_count, 'SUCCESS' if success_count > 0 else 'PARTIAL', empresa, upload_version, table_type))
        except Exception as version_update_error:
            st.warning(f"⚠️ Erro ao atualizar registro de versão: {str(version_update_error)}")
        
        # Log the upload
        try:
            cursor.execute("""
            INSERT INTO CONFIG.UPLOAD_LOG 
            (empresa, upload_version, version_id, nome_arquivo, linhas_processadas, 
             usuario, status, table_type, processing_time_seconds)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (empresa, upload_version, version_id, arquivo_nome, success_count, usuario, 
                  'SUCCESS' if success_count > 0 else 'PARTIAL', table_type, processing_time))
        except Exception as log_error:
            st.warning(f"⚠️ Erro ao registrar log: {str(log_error)}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Show results
        if success_count > 0:
            st.success(f"✅ {success_count} linhas processadas com sucesso para {empresa}!")
            if error_count > 0:
                st.warning(f"⚠️ {error_count} linhas com erro foram ignoradas")
            
            st.info(f"""
            🎯 **Resumo do Upload:**
            - 🏢 Empresa: {empresa}
            - 📊 Tipo: {table_type}
            - 📦 Versão: v{version_id}
            - ✅ Sucesso: {success_count} linhas
            - ⚠️ Erros: {error_count} linhas
            - ⏱️ Tempo: {processing_time}s
            """)
            return True
        else:
            st.error("❌ Nenhuma linha foi processada com sucesso")
            return False
        
    except Exception as e:
        st.error(f"❄️ Erro ao fazer upload: {str(e)}")
        st.error(f"📊 Detalhes do erro: {type(e).__name__}")
        
        # Log the error
        try:
            end_time = datetime.now()
            processing_time = int((end_time - start_time).total_seconds())
            
            cursor.execute("""
            INSERT INTO CONFIG.UPLOAD_LOG 
            (empresa, upload_version, version_id, nome_arquivo, linhas_processadas, 
             usuario, status, table_type, error_details, processing_time_seconds)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (empresa, version_info['upload_version'] if 'version_info' in locals() else 'ERROR', 
                  version_info['version_id'] if 'version_info' in locals() else 0, 
                  arquivo_nome, 0, usuario, 'ERROR', table_type, str(e), processing_time))
            conn.commit()
        except:
            pass  # Don't fail if logging fails
        
        # Show more helpful error message
        error_str = str(e)
        if "does not exist" in error_str:
            st.error("🔧 **Problema**: As tabelas não existem no Snowflake")
            st.info("💡 **Solução**: Vá para a página 'Snowflake' e clique em 'Criar Tabelas'")
        elif "UNIQUE constraint" in error_str:
            st.error("🔧 **Problema**: Dados duplicados detectados")
            st.info("💡 **Solução**: Verifique se os dados já foram importados para esta versão")
        
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

# Timeline de Compras - Company and version specific caching
@st.cache_data(ttl=2592000, show_spinner="🔄 Carregando Timeline (atualização mensal)...")  # 30 days
def load_data_with_history(empresa="MINIPA", version_id=None, usuario="minipa", limit_days=30):
    """
    Load data from Snowflake with multi-company versioning support
    CACHED for 30 DAYS (monthly updates) - Massive credit savings!
    
    Args:
        empresa: Company name (MINIPA, MINIPA_INDUSTRIA)
        version_id: Specific version ID (None for active version)
        usuario: User name
        limit_days: Days to look back for data
    """
    conn = get_snowflake_connection()
    if not conn:
        return None
        
    try:
        cursor = conn.cursor()
        
        # Determine which version to load
        if version_id is None:
            # Load active version
            version_filter = "is_active = TRUE"
            version_params = [empresa, 'TIMELINE']
            st.info(f"📊 Carregando versão ativa para {empresa}")
        else:
            # Load specific version
            version_filter = "version_id = %s"
            version_params = [empresa, 'TIMELINE', version_id]
            st.info(f"📊 Carregando versão {version_id} para {empresa}")
        
        # Check if the table exists and has data for this company
        try:
            if version_id is None:
                cursor.execute("""
                SELECT COUNT(*) FROM ESTOQUE.PRODUTOS 
                WHERE empresa = %s AND table_type = %s AND is_active = TRUE
                """, version_params)
            else:
                cursor.execute("""
                SELECT COUNT(*) FROM ESTOQUE.PRODUTOS 
                WHERE empresa = %s AND table_type = %s AND version_id = %s
                """, version_params)
            
            total_records = cursor.fetchone()[0]
            
        except Exception as table_error:
            st.warning(f"⚠️ Erro ao verificar dados para {empresa}: {str(table_error)}")
            cursor.close()
            conn.close()
            return None
        
        if total_records == 0:
            st.info(f"💡 Nenhum dado de timeline encontrado para {empresa}. Faça um upload primeiro.")
            cursor.close()
            conn.close()
            return None
        
        # Build the query based on version selection
        if version_id is None:
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
                   upload_version,
                   version_id
            FROM ESTOQUE.PRODUTOS 
            WHERE empresa = %s 
            AND table_type = 'TIMELINE'
            AND is_active = TRUE
            ORDER BY data_upload DESC
            """
            query_params = [empresa]
        else:
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
                   upload_version,
                   version_id
            FROM ESTOQUE.PRODUTOS 
            WHERE empresa = %s 
            AND table_type = 'TIMELINE'
            AND version_id = %s
            ORDER BY data_upload DESC
            """
            query_params = [empresa, version_id]
        
        cursor.close()  # Close the cursor before pandas read_sql
        
        df = pd.read_sql(query, conn, params=query_params)
        conn.close()
        
        # Check if we got any data
        if df.empty:
            st.info(f"💡 Nenhum dado encontrado para {empresa}.")
            return None
        
        # Show data summary
        version_info = df['version_id'].iloc[0] if not df.empty else "N/A"
        upload_date = df['data_upload'].max() if 'data_upload' in df.columns else "N/A"
        
        st.info(f"📅 {empresa} - Timeline v{version_info} | {len(df)} produtos | Upload: {upload_date}")
        
        # Remove metadata columns for return
        columns_to_remove = ['upload_version', 'version_id']
        df_clean = df.drop(columns=[col for col in columns_to_remove if col in df.columns])
        
        return df_clean
        
    except Exception as e:
        st.error(f"❄️ Erro ao carregar dados para {empresa}: {str(e)}")
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

# Análise de Estoque - Company and version specific caching  
@st.cache_data(ttl=604800, show_spinner="🔄 Carregando Análise (atualização semanal)...")  # 7 days
def load_analytics_data(empresa="MINIPA", version_id=None, usuario="minipa", limit_days=30):
    """
    Load analytics data from Snowflake with multi-company versioning support
    CACHED for 7 DAYS (weekly updates) - Major credit savings!
    
    Args:
        empresa: Company name (MINIPA, MINIPA_INDUSTRIA)
        version_id: Specific version ID (None for active version)
        usuario: User name
        limit_days: Days to look back for data
    """
    conn = get_snowflake_connection()
    if not conn:
        return None
        
    try:
        cursor = conn.cursor()
        
        # Determine which version to load
        if version_id is None:
            st.info(f"📊 Carregando análise ativa para {empresa}")
            version_params = [empresa]
        else:
            st.info(f"📊 Carregando análise v{version_id} para {empresa}")
            version_params = [empresa, version_id]
        
        # Check if the analytics table exists and has data for this company
        try:
            if version_id is None:
                cursor.execute("""
                SELECT COUNT(*) FROM ESTOQUE.ANALYTICS_DATA 
                WHERE empresa = %s AND is_active = TRUE
                """, version_params)
            else:
                cursor.execute("""
                SELECT COUNT(*) FROM ESTOQUE.ANALYTICS_DATA 
                WHERE empresa = %s AND version_id = %s
                """, version_params)
            
            total_records = cursor.fetchone()[0]
            
            if total_records == 0:
                st.info(f"💡 Nenhum dado de análise encontrado para {empresa}. Faça upload de um arquivo de análise primeiro.")
                cursor.close()
                conn.close()
                return None
                
        except Exception as table_error:
            # Table doesn't exist yet
            st.warning(f"⚠️ Erro ao verificar dados de análise para {empresa}: {str(table_error)}")
            st.info("💡 A tabela será criada automaticamente no primeiro upload de análise.")
            cursor.close()
            conn.close()
            return None
        
        # Build the query based on version selection
        if version_id is None:
            query = """
            SELECT produto as "Produto", 
                   estoque as "Estoque", 
                   consumo_6_meses as "Consumo 6 Meses",
                   media_6_meses as "Média 6 Meses", 
                   estoque_cobertura as "Estoque Cobertura",
                   data_upload,
                   upload_version,
                   version_id
            FROM ESTOQUE.ANALYTICS_DATA 
            WHERE empresa = %s 
            AND is_active = TRUE
            ORDER BY data_upload DESC
            """
            query_params = [empresa]
        else:
            query = """
            SELECT produto as "Produto", 
                   estoque as "Estoque", 
                   consumo_6_meses as "Consumo 6 Meses",
                   media_6_meses as "Média 6 Meses", 
                   estoque_cobertura as "Estoque Cobertura",
                   data_upload,
                   upload_version,
                   version_id
            FROM ESTOQUE.ANALYTICS_DATA 
            WHERE empresa = %s 
            AND version_id = %s
            ORDER BY data_upload DESC
            """
            query_params = [empresa, version_id]
        
        cursor.close()
        
        df = pd.read_sql(query, conn, params=query_params)
        conn.close()
        
        # Check if we got any data
        if df.empty:
            st.info(f"💡 Nenhum dado de análise encontrado para {empresa}.")
            return None
        
        # Show data summary
        version_info = df['version_id'].iloc[0] if not df.empty else "N/A"
        upload_date = df['data_upload'].max() if 'data_upload' in df.columns else "N/A"
        
        st.info(f"📊 {empresa} - Análise v{version_info} | {len(df)} produtos | Upload: {upload_date}")
        
        # Remove metadata columns for return
        columns_to_remove = ['upload_version', 'version_id']
        df_clean = df.drop(columns=[col for col in columns_to_remove if col in df.columns])
        
        return df_clean
        
    except Exception as e:
        st.error(f"❄️ Erro ao carregar dados de análise para {empresa}: {str(e)}")
        return None

def migrate_to_multi_company_versioned():
    """
    Migrate existing tables to multi-company, versioned structure
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        st.info("🔄 Iniciando migração para estrutura multi-empresa e versionada...")
        
        # Step 1: Check if old structure exists
        old_structure_exists = False
        try:
            cursor.execute("SELECT COUNT(*) FROM ESTOQUE.PRODUTOS WHERE empresa IS NULL")
            old_records = cursor.fetchone()[0]
            if old_records > 0:
                old_structure_exists = True
                st.info(f"📊 Encontrados {old_records} registros na estrutura antiga")
        except:
            st.info("📋 Estrutura antiga não encontrada - criando estrutura nova")
        
        # Step 2: Create new table structure
        st.info("🔧 Atualizando estrutura das tabelas...")
        if not create_tables():
            st.error("❌ Erro ao criar nova estrutura")
            return False
        
        # Step 3: Migrate existing data if found
        if old_structure_exists:
            st.info("📦 Migrando dados existentes para MINIPA como versão 1...")
            
            # Create version 1 for MINIPA TIMELINE
            version_timeline = create_new_version(
                empresa="MINIPA", 
                table_type="TIMELINE", 
                description="Migração automática de dados existentes", 
                created_by="system"
            )
            
            if version_timeline:
                # Migrate TIMELINE data
                cursor.execute("""
                UPDATE ESTOQUE.PRODUTOS 
                SET empresa = 'MINIPA',
                    upload_version = %s,
                    version_id = %s,
                    is_active = TRUE,
                    table_type = COALESCE(table_type, 'TIMELINE'),
                    created_by = 'system',
                    version_description = 'Migração automática de dados existentes'
                WHERE empresa IS NULL
                """, (version_timeline['upload_version'], version_timeline['version_id']))
                
                migrated_timeline = cursor.rowcount
                st.success(f"✅ {migrated_timeline} registros de timeline migrados")
            
            # Check for analytics data
            try:
                cursor.execute("SELECT COUNT(*) FROM ESTOQUE.ANALYTICS_DATA WHERE empresa IS NULL")
                old_analytics = cursor.fetchone()[0]
                
                if old_analytics > 0:
                    # Create version 1 for MINIPA ANALYTICS
                    version_analytics = create_new_version(
                        empresa="MINIPA", 
                        table_type="ANALYTICS", 
                        description="Migração automática de dados existentes", 
                        created_by="system"
                    )
                    
                    if version_analytics:
                        cursor.execute("""
                        UPDATE ESTOQUE.ANALYTICS_DATA 
                        SET empresa = 'MINIPA',
                            upload_version = %s,
                            version_id = %s,
                            is_active = TRUE,
                            created_by = 'system',
                            version_description = 'Migração automática de dados existentes'
                        WHERE empresa IS NULL
                        """, (version_analytics['upload_version'], version_analytics['version_id']))
                        
                        migrated_analytics = cursor.rowcount
                        st.success(f"✅ {migrated_analytics} registros de analytics migrados")
            except:
                st.info("📊 Nenhum dado de analytics para migrar")
            
            # Update old upload logs
            try:
                cursor.execute("""
                UPDATE CONFIG.UPLOAD_LOG 
                SET empresa = 'MINIPA',
                    upload_version = 'LEGACY_IMPORT',
                    version_id = 1
                WHERE empresa IS NULL
                """)
                st.success("✅ Logs de upload atualizados")
            except:
                st.info("📋 Nenhum log para atualizar")
        
        conn.commit()
        
        # Step 4: Verify migration
        st.info("🔍 Verificando migração...")
        
        # Check MINIPA data
        cursor.execute("SELECT COUNT(*) FROM ESTOQUE.PRODUTOS WHERE empresa = 'MINIPA'")
        minipa_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM CONFIG.VERSIONS WHERE empresa = 'MINIPA'")
        minipa_versions = cursor.fetchone()[0]
        
        st.success(f"✅ MINIPA: {minipa_count} produtos, {minipa_versions} versões")
        
        cursor.close()
        conn.close()
        
        st.success("🎉 Migração concluída com sucesso!")
        st.info("""
        **📋 Próximos passos:**
        1. ✅ Estrutura multi-empresa criada
        2. ✅ Dados existentes migrados para MINIPA
        3. 👉 Agora você pode fazer upload para MINIPA INDUSTRIA
        4. 👉 Use os seletores de empresa e versão nas páginas
        """)
        
        return True
        
    except Exception as e:
        st.error(f"❌ Erro na migração: {str(e)}")
        try:
            conn.rollback()
        except:
            pass
        return False 

def migrate_existing_tables():
    """
    Legacy migration function - redirects to new multi-company migration
    """
    st.warning("⚠️ Esta função foi atualizada para suporte multi-empresa")
    st.info("👉 Use 'Migrar para Multi-Empresa' para atualizar completamente")
    return migrate_to_multi_company_versioned() 

def clear_company_data(empresa, table_type=None):
    """
    Clear all data for a specific company
    
    Args:
        empresa: Company name (MINIPA, MINIPA_INDUSTRIA)
        table_type: Optional - specific table type (TIMELINE, ANALYTICS) or None for all
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        st.warning(f"⚠️ **ATENÇÃO**: Você está prestes a DELETAR dados de {empresa}")
        
        if table_type:
            st.info(f"🗑️ Limpando dados de {table_type} para {empresa}")
        else:
            st.info(f"🗑️ Limpando TODOS os dados para {empresa}")
        
        confirm = st.checkbox(f"✅ Confirmo que quero deletar dados de {empresa}", key=f"confirm_delete_{empresa}_{table_type}")
        
        if not confirm:
            st.info("💡 Marque a caixa de confirmação para prosseguir")
            return False
        
        if st.button(f"🗑️ DELETAR DADOS DE {empresa}", type="primary", key=f"delete_btn_{empresa}_{table_type}"):
            deleted_count = 0
            
            # Clear timeline data
            if table_type is None or table_type == "TIMELINE":
                cursor.execute("DELETE FROM ESTOQUE.PRODUTOS WHERE empresa = %s AND table_type = 'TIMELINE'", (empresa,))
                timeline_deleted = cursor.rowcount
                deleted_count += timeline_deleted
                st.info(f"🗑️ Timeline: {timeline_deleted} registros deletados")
            
            # Clear analytics data  
            if table_type is None or table_type == "ANALYTICS":
                cursor.execute("DELETE FROM ESTOQUE.ANALYTICS_DATA WHERE empresa = %s", (empresa,))
                analytics_deleted = cursor.rowcount
                deleted_count += analytics_deleted
                st.info(f"🗑️ Analytics: {analytics_deleted} registros deletados")
            
            # Clear version control records
            if table_type:
                cursor.execute("DELETE FROM CONFIG.VERSIONS WHERE empresa = %s AND table_type = %s", (empresa, table_type))
            else:
                cursor.execute("DELETE FROM CONFIG.VERSIONS WHERE empresa = %s", (empresa,))
            versions_deleted = cursor.rowcount
            st.info(f"🗑️ Versões: {versions_deleted} registros deletados")
            
            # Clear upload logs
            if table_type:
                cursor.execute("DELETE FROM CONFIG.UPLOAD_LOG WHERE empresa = %s AND table_type = %s", (empresa, table_type))
            else:
                cursor.execute("DELETE FROM CONFIG.UPLOAD_LOG WHERE empresa = %s", (empresa,))
            logs_deleted = cursor.rowcount
            st.info(f"🗑️ Logs: {logs_deleted} registros deletados")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            st.success(f"✅ {deleted_count} registros de dados deletados para {empresa}")
            st.balloons()
            
            # Clear caches
            load_data_with_history.clear()
            load_analytics_data.clear()
            st.success("🧹 Cache limpo!")
            
            return True
            
    except Exception as e:
        st.error(f"❌ Erro ao deletar dados: {str(e)}")
        return False

def clear_specific_version(empresa, version_id, table_type):
    """
    Clear a specific version of data
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        st.warning(f"⚠️ **ATENÇÃO**: Deletando versão {version_id} de {table_type} para {empresa}")
        
        confirm = st.checkbox(f"✅ Confirmo que quero deletar versão {version_id}", key=f"confirm_version_{empresa}_{version_id}_{table_type}")
        
        if not confirm:
            st.info("💡 Marque a caixa de confirmação para prosseguir")
            return False
        
        if st.button(f"🗑️ DELETAR VERSÃO {version_id}", type="primary", key=f"delete_version_{empresa}_{version_id}_{table_type}"):
            # Delete from data tables
            if table_type == "TIMELINE":
                cursor.execute("DELETE FROM ESTOQUE.PRODUTOS WHERE empresa = %s AND version_id = %s AND table_type = %s", 
                              (empresa, version_id, table_type))
            elif table_type == "ANALYTICS":
                cursor.execute("DELETE FROM ESTOQUE.ANALYTICS_DATA WHERE empresa = %s AND version_id = %s", 
                              (empresa, version_id))
            
            data_deleted = cursor.rowcount
            
            # Delete from version control
            cursor.execute("DELETE FROM CONFIG.VERSIONS WHERE empresa = %s AND version_id = %s AND table_type = %s", 
                          (empresa, version_id, table_type))
            
            # Delete from upload logs
            cursor.execute("DELETE FROM CONFIG.UPLOAD_LOG WHERE empresa = %s AND version_id = %s AND table_type = %s", 
                          (empresa, version_id, table_type))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            st.success(f"✅ Versão {version_id} deletada: {data_deleted} registros removidos")
            
            # Clear caches
            load_data_with_history.clear()
            load_analytics_data.clear()
            
            return True
            
    except Exception as e:
        st.error(f"❌ Erro ao deletar versão: {str(e)}")
        return False

def clear_entire_database():
    """
    Clear the entire database - NUCLEAR OPTION
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        st.error("🚨 **PERIGO**: VOCÊ ESTÁ PRESTES A DELETAR TODA A BASE DE DADOS!")
        st.error("🚨 Esta ação é IRREVERSÍVEL e deletará dados de TODAS as empresas!")
        
        # Triple confirmation
        confirm1 = st.checkbox("⚠️ Entendo que vou deletar TODOS os dados", key="nuclear_confirm1")
        confirm2 = st.checkbox("⚠️ Entendo que esta ação é IRREVERSÍVEL", key="nuclear_confirm2") 
        confirm3 = st.checkbox("⚠️ Tenho certeza ABSOLUTA que quero fazer isso", key="nuclear_confirm3")
        
        safety_code = st.text_input("🔐 Digite 'DELETE_EVERYTHING' para confirmar:", key="safety_code")
        
        if confirm1 and confirm2 and confirm3 and safety_code == "DELETE_EVERYTHING":
            if st.button("💥 DELETAR TODA A BASE DE DADOS", type="primary", key="nuclear_button"):
                try:
                    # Clear all data tables
                    cursor.execute("DELETE FROM ESTOQUE.PRODUTOS")
                    produtos_deleted = cursor.rowcount
                    
                    cursor.execute("DELETE FROM ESTOQUE.ANALYTICS_DATA")
                    analytics_deleted = cursor.rowcount
                    
                    cursor.execute("DELETE FROM TIMELINE.ANALISES")
                    timeline_deleted = cursor.rowcount
                    
                    cursor.execute("DELETE FROM CONFIG.VERSIONS")
                    versions_deleted = cursor.rowcount
                    
                    cursor.execute("DELETE FROM CONFIG.UPLOAD_LOG")
                    logs_deleted = cursor.rowcount
                    
                    conn.commit()
                    
                    total_deleted = produtos_deleted + analytics_deleted + timeline_deleted + versions_deleted + logs_deleted
                    
                    st.success(f"💥 BASE DE DADOS COMPLETAMENTE LIMPA!")
                    st.info(f"🗑️ Total de registros deletados: {total_deleted}")
                    st.info(f"📊 Produtos: {produtos_deleted}, Analytics: {analytics_deleted}, Timeline: {timeline_deleted}")
                    st.info(f"📋 Versões: {versions_deleted}, Logs: {logs_deleted}")
                    
                    # Clear all caches
                    load_data_with_history.clear()
                    load_analytics_data.clear()
                    
                    cursor.close()
                    conn.close()
                    return True
                    
                except Exception as delete_error:
                    st.error(f"❌ Erro durante a limpeza: {str(delete_error)}")
                    return False
        else:
            st.info("💡 Complete todas as confirmações e digite o código de segurança para prosseguir")
            
    except Exception as e:
        st.error(f"❌ Erro na operação de limpeza: {str(e)}")
        return False

def get_database_statistics():
    """
    Get comprehensive database statistics for monitoring costs and usage
    """
    conn = get_snowflake_connection()
    if not conn:
        return None
        
    try:
        cursor = conn.cursor()
        
        stats = {}
        
        # Company statistics
        for empresa in ["MINIPA", "MINIPA_INDUSTRIA"]:
            cursor.execute("SELECT COUNT(*) FROM ESTOQUE.PRODUTOS WHERE empresa = %s", (empresa,))
            produtos_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ESTOQUE.ANALYTICS_DATA WHERE empresa = %s", (empresa,))
            analytics_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM CONFIG.VERSIONS WHERE empresa = %s", (empresa,))
            versions_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM CONFIG.UPLOAD_LOG WHERE empresa = %s", (empresa,))
            uploads_count = cursor.fetchone()[0]
            
            stats[empresa] = {
                'produtos': produtos_count,
                'analytics': analytics_count, 
                'versions': versions_count,
                'uploads': uploads_count,
                'total': produtos_count + analytics_count + versions_count + uploads_count
            }
        
        # Overall statistics
        cursor.execute("SELECT COUNT(*) FROM ESTOQUE.PRODUTOS")
        total_produtos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ESTOQUE.ANALYTICS_DATA")
        total_analytics = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM CONFIG.VERSIONS")
        total_versions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM CONFIG.UPLOAD_LOG")
        total_uploads = cursor.fetchone()[0]
        
        stats['TOTAL'] = {
            'produtos': total_produtos,
            'analytics': total_analytics,
            'versions': total_versions,
            'uploads': total_uploads,
            'total': total_produtos + total_analytics + total_versions + total_uploads
        }
        
        cursor.close()
        conn.close()
        
        return stats
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar estatísticas: {str(e)}")
        return None 