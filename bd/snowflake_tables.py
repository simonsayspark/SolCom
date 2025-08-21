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
            priority_score DECIMAL(5,4),
            criticality VARCHAR(20),
            relevance_class VARCHAR(20),
            annual_impact DECIMAL(12,2),
            monthly_volume DECIMAL(10,2),
            volume_normalized DECIMAL(5,4),
            price_normalized DECIMAL(5,4),
            raw_multiplication DECIMAL(12,2),
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
            moq INTEGER DEFAULT 0,
            ultimo_fornecedor VARCHAR(200) DEFAULT 'Brazil',
            data_upload TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
            usuario VARCHAR(50),
            table_type VARCHAR(20) DEFAULT 'ANALYTICS',
            version_description TEXT,
            created_by VARCHAR(50),
            preco_unitario DECIMAL(10,2),
            priority_score DECIMAL(5,4),
            criticality VARCHAR(20),
            relevance_class VARCHAR(20),
            annual_impact DECIMAL(12,2),
            monthly_volume DECIMAL(10,2),
            volume_normalized DECIMAL(5,4),
            price_normalized DECIMAL(5,4),
            raw_multiplication DECIMAL(12,2),
            qtde_embarque DECIMAL(10,2),
            compras_ate_30_dias DECIMAL(10,2),
            compras_31_60_dias DECIMAL(10,2),
            compras_61_90_dias DECIMAL(10,2),
            compras_mais_90_dias DECIMAL(10,2),
            previsao DECIMAL(10,2),
            qtde_tot_compras DECIMAL(10,2),
            carteira DECIMAL(10,2),
            carteira_estoque DECIMAL(10,2),
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
                    'has_upload_version': 'UPLOAD_VERSION' in [col.upper() for col in column_names],
                    'has_moq': 'MOQ' in [col.upper() for col in column_names],
                    'has_ultimo_fornecedor': 'ULTIMO_FORNECEDOR' in [col.upper() for col in column_names]
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

def add_analytics_columns():
    """
    Add MOQ and ultimo_fornecedor columns to existing ANALYTICS_DATA table
    This is a safe migration that won't lose existing data
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        st.info("🔄 Verificando e adicionando colunas MOQ e UltimoFornecedor...")
        
        # Check if table exists
        try:
            cursor.execute("SELECT COUNT(*) FROM ESTOQUE.ANALYTICS_DATA LIMIT 1")
            table_exists = True
        except:
            st.warning("⚠️ Tabela ANALYTICS_DATA não existe. Execute 'Criar Tabelas' primeiro.")
            return False
        
        # Check current columns
        cursor.execute("DESCRIBE TABLE ESTOQUE.ANALYTICS_DATA")
        columns = cursor.fetchall()
        column_names = [col[0].upper() for col in columns]
        
        changes_made = False
        
        # Add MOQ column if missing
        if 'MOQ' not in column_names:
            try:
                cursor.execute("ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN moq INTEGER DEFAULT 0")
                st.success("✅ Coluna MOQ adicionada com sucesso!")
                changes_made = True
            except Exception as e:
                st.error(f"❌ Erro ao adicionar coluna MOQ: {str(e)}")
        else:
            st.info("✅ Coluna MOQ já existe")
        
        # Add ultimo_fornecedor column if missing
        if 'ULTIMO_FORNECEDOR' not in column_names:
            try:
                cursor.execute("ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN ultimo_fornecedor VARCHAR(200) DEFAULT 'Brazil'")
                st.success("✅ Coluna ultimo_fornecedor adicionada com sucesso!")
                changes_made = True
            except Exception as e:
                st.error(f"❌ Erro ao adicionar coluna ultimo_fornecedor: {str(e)}")
        else:
            st.info("✅ Coluna ultimo_fornecedor já existe")
        
        # Add priority analysis columns if missing
        priority_columns = [
            ('PRECO_UNITARIO', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN preco_unitario DECIMAL(10,2)"),
            ('PRIORITY_SCORE', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN priority_score DECIMAL(5,4)"),
            ('CRITICALITY', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN criticality VARCHAR(20)"),
            ('RELEVANCE_CLASS', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN relevance_class VARCHAR(20)"),
            ('ANNUAL_IMPACT', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN annual_impact DECIMAL(12,2)"),
            ('MONTHLY_VOLUME', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN monthly_volume DECIMAL(10,2)"),
            ('VOLUME_NORMALIZED', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN volume_normalized DECIMAL(5,4)"),
            ('PRICE_NORMALIZED', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN price_normalized DECIMAL(5,4)"),
            ('RAW_MULTIPLICATION', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN raw_multiplication DECIMAL(12,2)"),
            ('QTDE_EMBARQUE', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN qtde_embarque DECIMAL(10,2)"),
            ('COMPRAS_ATE_30_DIAS', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN compras_ate_30_dias DECIMAL(10,2)"),
            ('COMPRAS_31_60_DIAS', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN compras_31_60_dias DECIMAL(10,2)"),
            ('COMPRAS_61_90_DIAS', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN compras_61_90_dias DECIMAL(10,2)"),
            ('COMPRAS_MAIS_90_DIAS', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN compras_mais_90_dias DECIMAL(10,2)"),
            ('PREVISAO', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN previsao DECIMAL(10,2)"),
            ('QTDE_TOT_COMPRAS', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN qtde_tot_compras DECIMAL(10,2)")
        ]
        
        for col_name, alter_sql in priority_columns:
            if col_name not in column_names:
                try:
                    cursor.execute(alter_sql)
                    st.success(f"✅ Coluna {col_name.lower()} adicionada com sucesso!")
                    changes_made = True
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        st.error(f"❌ Erro ao adicionar coluna {col_name.lower()}: {str(e)}")
            else:
                st.info(f"✅ Coluna {col_name.lower()} já existe")
        
        if changes_made:
            conn.commit()
            st.success("🎉 Migração concluída! Estrutura da tabela ANALYTICS_DATA atualizada.")
            
            # Show updated structure
            cursor.execute("DESCRIBE TABLE ESTOQUE.ANALYTICS_DATA")
            updated_columns = cursor.fetchall()
            st.info(f"📊 Colunas atualizadas: {[col[0] for col in updated_columns]}")
        else:
            st.info("✅ Tabela já está atualizada - nenhuma alteração necessária")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"❌ Erro na migração: {str(e)}")
        return False 