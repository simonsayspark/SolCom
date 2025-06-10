"""
Snowflake Table Management
Handles table creation, schema management, and database structure
"""

import streamlit as st
from .snowflake_connection import get_snowflake_connection

def create_tables():
    """
    Create the multi-company, versioned table structure for MINIPA system
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # Create schemas first
        cursor.execute("CREATE SCHEMA IF NOT EXISTS ESTOQUE")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS CONFIG")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS TIMELINE")
        
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

def check_database_structure():
    """
    Check current database structure and return detailed information
    """
    conn = get_snowflake_connection()
    if not conn:
        return None
        
    try:
        cursor = conn.cursor()
        
        structure_info = {}
        
        # Check each table
        tables_to_check = [
            ('ESTOQUE', 'PRODUTOS'),
            ('ESTOQUE', 'ANALYTICS_DATA'), 
            ('CONFIG', 'VERSIONS'),
            ('CONFIG', 'UPLOAD_LOG')
        ]
        
        for schema, table in tables_to_check:
            table_full_name = f"{schema}.{table}"
            
            try:
                # Check if table exists
                cursor.execute(f"SELECT COUNT(*) FROM {table_full_name}")
                count = cursor.fetchone()[0]
                
                # Get column information
                cursor.execute(f"DESCRIBE TABLE {table_full_name}")
                columns = cursor.fetchall()
                column_names = [col[0] for col in columns]
                
                structure_info[table_full_name] = {
                    'exists': True,
                    'count': count,
                    'columns': column_names,
                    'has_empresa': 'EMPRESA' in [col.upper() for col in column_names],
                    'has_table_type': 'TABLE_TYPE' in [col.upper() for col in column_names],
                    'has_upload_version': 'UPLOAD_VERSION' in [col.upper() for col in column_names]
                }
                
            except Exception as e:
                structure_info[table_full_name] = {
                    'exists': False,
                    'error': str(e),
                    'count': 0,
                    'columns': []
                }
        
        cursor.close()
        conn.close()
        return structure_info
        
    except Exception as e:
        st.error(f"❌ Erro ao verificar estrutura: {str(e)}")
        return None

def force_create_new_structure():
    """
    Force create the new multi-company structure from scratch
    This will drop existing tables and create new ones
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        st.warning("⚠️ **ATENÇÃO**: Esta operação irá recriar todas as tabelas!")
        st.info("🔄 Criando estrutura completamente nova...")
        
        # Step 1: Create schemas
        st.info("🔧 Criando schemas...")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS ESTOQUE")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS CONFIG")
        conn.commit()
        
        # Step 2: Drop existing tables (if they exist)
        tables_to_drop = [
            'ESTOQUE.PRODUTOS',
            'ESTOQUE.ANALYTICS_DATA',
            'CONFIG.VERSIONS', 
            'CONFIG.UPLOAD_LOG'
        ]
        
        for table in tables_to_drop:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                st.info(f"🗑️ Removida tabela antiga: {table}")
            except:
                pass  # Table might not exist
        
        conn.commit()
        
        # Step 3: Create new tables with complete structure
        st.info("🔧 Criando tabelas com estrutura nova...")
        
        # Use the create_tables function to create clean tables
        cursor.close()
        conn.close()
        
        success = create_tables()
        
        if success:
            st.success("🎉 Estrutura nova criada com sucesso!")
            st.info("💡 Agora você pode fazer uploads normalmente")
        
        return success
        
    except Exception as e:
        st.error(f"❌ Erro ao criar estrutura nova: {str(e)}")
        return False 