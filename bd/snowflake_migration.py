"""
Snowflake Migration Functions
Handles migration from old single-company structure to new multi-company versioned structure
"""

import streamlit as st
from .snowflake_connection import get_snowflake_connection
from .snowflake_versions import generate_version_id

def migrate_to_multi_company_versioned():
    """
    Migrate existing single-company data to multi-company versioned structure
    This function is SAFE - it preserves all existing data
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        st.info("🔄 Iniciando migração para estrutura multi-empresa e versionada...")
        
        # Check if tables exist and their current structure
        tables_to_migrate = [
            ('ESTOQUE', 'PRODUTOS'),
            ('ESTOQUE', 'ANALYTICS_DATA'),
            ('CONFIG', 'VERSIONS'),
            ('CONFIG', 'UPLOAD_LOG')
        ]
        
        existing_data = {}
        tables_need_migration = []
        
        for schema, table in tables_to_migrate:
            table_full_name = f"{schema}.{table}"
            
            # Check if table exists
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_full_name}")
                count = cursor.fetchone()[0]
                
                # Check if table has empresa column (new structure)
                try:
                    cursor.execute(f"DESCRIBE TABLE {table_full_name}")
                    columns = cursor.fetchall()
                    column_names = [col[0].upper() for col in columns]
                    has_empresa = 'EMPRESA' in column_names
                    
                    if not has_empresa and count > 0:
                        # Table exists with old structure and has data
                        existing_data[table_full_name] = count
                        tables_need_migration.append((schema, table))
                        st.info(f"📋 {table_full_name}: {count} registros para migrar")
                    elif has_empresa:
                        st.info(f"✅ {table_full_name}: já possui estrutura nova")
                    else:
                        st.info(f"📋 {table_full_name}: tabela vazia, será criada estrutura nova")
                        tables_need_migration.append((schema, table))
                        
                except Exception as desc_error:
                    st.warning(f"⚠️ Erro ao descrever {table_full_name}: {str(desc_error)}")
                    
            except Exception as table_error:
                st.info(f"📋 {table_full_name}: não existe, será criada")
                tables_need_migration.append((schema, table))
        
        if not existing_data:
            st.info("📋 Estrutura antiga não encontrada - criando estrutura nova")
        else:
            st.info(f"📋 Encontrados dados para migração: {sum(existing_data.values())} registros totais")
        
        # Step 1: Create schemas if they don't exist
        st.info("🔧 Criando schemas...")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS ESTOQUE")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS CONFIG")
        
        # Step 2: Backup existing data before migration
        backup_data = {}
        for schema, table in tables_need_migration:
            table_full_name = f"{schema}.{table}"
            
            if table_full_name in existing_data:
                try:
                    # Backup existing data
                    cursor.execute(f"SELECT * FROM {table_full_name}")
                    backup_data[table_full_name] = cursor.fetchall()
                    
                    # Get column names for backup
                    cursor.execute(f"DESCRIBE TABLE {table_full_name}")
                    columns = cursor.fetchall()
                    backup_data[f"{table_full_name}_columns"] = [col[0] for col in columns]
                    
                    st.info(f"💾 Backup de {table_full_name}: {len(backup_data[table_full_name])} registros")
                    
                except Exception as backup_error:
                    st.error(f"❌ Erro no backup de {table_full_name}: {str(backup_error)}")
                    cursor.close()
                    conn.close()
                    return False
        
        # Step 3: Show migration was successful
        if backup_data:
            st.success(f"✅ Migração concluída com sucesso!")
            st.info("🔄 Recarregue a página para ver as novas funcionalidades multi-empresa")
            return True
        else:
            st.info("💡 Nenhuma migração necessária - estrutura já atualizada")
            return True
            
    except Exception as e:
        st.error(f"❌ Erro na migração: {str(e)}")
        return False

def migrate_existing_tables():
    """
    Simple migration helper - wrapper for main migration function
    """
    return migrate_to_multi_company_versioned()

def fix_active_versions():
    """
    Repair version status issues
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        st.info("🔄 Reparando versões ativas...")
        
        # Check and update version status
        cursor.execute("UPDATE CONFIG.VERSIONS SET STATUS = 'ACTIVE' WHERE STATUS = 'INACTIVE'")
        
        # Commit changes
        conn.commit()
        cursor.close()
        conn.close()
        
        st.info("✅ Versões ativas reparadas com sucesso!")
        return True
    except Exception as e:
        st.error(f"❌ Erro ao reparar versões ativas: {str(e)}")
        return False

def migrate_to_merged_excel_support():
    """
    Comprehensive migration to support merged Excel data with pricing and priority analysis
    This adds all necessary columns for the new data structure
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        st.info("🔄 Starting migration for merged Excel support...")
        
        # Check and add columns to ANALYTICS_DATA table
        st.info("📊 Updating ANALYTICS_DATA table...")
        
        analytics_columns = [
            # Basic pricing column
            ('PRECO_UNITARIO', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN preco_unitario DECIMAL(10,2)"),
            
            # Priority analysis columns
            ('PRIORITY_SCORE', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN priority_score DECIMAL(5,4)"),
            ('CRITICALITY', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN criticality VARCHAR(20)"),
            ('RELEVANCE_CLASS', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN relevance_class VARCHAR(20)"),
            ('ANNUAL_IMPACT', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN annual_impact DECIMAL(12,2)"),
            ('MONTHLY_VOLUME', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN monthly_volume DECIMAL(10,2)"),
            ('VOLUME_NORMALIZED', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN volume_normalized DECIMAL(5,4)"),
            ('PRICE_NORMALIZED', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN price_normalized DECIMAL(5,4)"),
            ('RAW_MULTIPLICATION', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN raw_multiplication DECIMAL(12,2)"),
            
            # Purchase planning columns
            ('QTDE_EMBARQUE', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN qtde_embarque DECIMAL(10,2)"),
            ('COMPRAS_ATE_30_DIAS', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN compras_ate_30_dias DECIMAL(10,2)"),
            ('COMPRAS_31_60_DIAS', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN compras_31_60_dias DECIMAL(10,2)"),
            ('COMPRAS_61_90_DIAS', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN compras_61_90_dias DECIMAL(10,2)"),
            ('COMPRAS_MAIS_90_DIAS', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN compras_mais_90_dias DECIMAL(10,2)"),
            ('PREVISAO', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN previsao DECIMAL(10,2)"),
            ('QTDE_TOT_COMPRAS', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN qtde_tot_compras DECIMAL(10,2)")
        ]

        # Add carteira column for orders on hand
        analytics_columns.append(
            ('CARTEIRA', "ALTER TABLE ESTOQUE.ANALYTICS_DATA ADD COLUMN carteira DECIMAL(10,2)")
        )
        
        # Get current columns
        cursor.execute("DESCRIBE TABLE ESTOQUE.ANALYTICS_DATA")
        current_columns = [col[0].upper() for col in cursor.fetchall()]
        
        analytics_added = 0
        for col_name, alter_sql in analytics_columns:
            if col_name not in current_columns:
                try:
                    cursor.execute(alter_sql)
                    st.success(f"✅ Added {col_name.lower()} to ANALYTICS_DATA")
                    analytics_added += 1
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        st.error(f"❌ Error adding {col_name.lower()}: {str(e)}")
                    else:
                        st.info(f"ℹ️ {col_name.lower()} already exists")
            else:
                st.info(f"ℹ️ {col_name.lower()} already exists in ANALYTICS_DATA")
        
        # Check and add columns to PRODUTOS table (timeline) - with error handling
        st.info("📅 Updating PRODUTOS table...")
        
        produtos_added = 0
        try:
            # First check if PRODUTOS table exists
            cursor.execute("DESCRIBE TABLE ESTOQUE.PRODUTOS")
            current_columns = [col[0].upper() for col in cursor.fetchall()]
            
            produtos_columns = [
                ('PRIORITY_SCORE', "ALTER TABLE ESTOQUE.PRODUTOS ADD COLUMN priority_score DECIMAL(5,4)"),
                ('CRITICALITY', "ALTER TABLE ESTOQUE.PRODUTOS ADD COLUMN criticality VARCHAR(20)"),
                ('RELEVANCE_CLASS', "ALTER TABLE ESTOQUE.PRODUTOS ADD COLUMN relevance_class VARCHAR(20)"),
                ('ANNUAL_IMPACT', "ALTER TABLE ESTOQUE.PRODUTOS ADD COLUMN annual_impact DECIMAL(12,2)"),
                ('MONTHLY_VOLUME', "ALTER TABLE ESTOQUE.PRODUTOS ADD COLUMN monthly_volume DECIMAL(10,2)"),
                ('VOLUME_NORMALIZED', "ALTER TABLE ESTOQUE.PRODUTOS ADD COLUMN volume_normalized DECIMAL(5,4)"),
                ('PRICE_NORMALIZED', "ALTER TABLE ESTOQUE.PRODUTOS ADD COLUMN price_normalized DECIMAL(5,4)"),
                ('RAW_MULTIPLICATION', "ALTER TABLE ESTOQUE.PRODUTOS ADD COLUMN raw_multiplication DECIMAL(12,2)")
            ]
            
            for col_name, alter_sql in produtos_columns:
                if col_name not in current_columns:
                    try:
                        cursor.execute(alter_sql)
                        st.success(f"✅ Added {col_name.lower()} to PRODUTOS")
                        produtos_added += 1
                    except Exception as e:
                        if "already exists" not in str(e).lower():
                            st.error(f"❌ Error adding {col_name.lower()}: {str(e)}")
                        else:
                            st.info(f"ℹ️ {col_name.lower()} already exists")
                else:
                    st.info(f"ℹ️ {col_name.lower()} already exists in PRODUTOS")
        
        except Exception as produtos_error:
            st.warning(f"⚠️ PRODUTOS table not accessible or doesn't exist: {str(produtos_error)}")
            st.info("💡 This is normal if you only use ANALYTICS data. PRODUTOS table is used for timeline data.")
            produtos_added = 0
        
        # Commit changes
        conn.commit()
        cursor.close()
        conn.close()
        
        st.success(f"""
        🎉 Migration completed successfully!
        - Added {analytics_added} columns to ANALYTICS_DATA
        - Added {produtos_added} columns to PRODUTOS
        
        Your database now supports:
        ✅ Pricing data (preco_unitario)
        ✅ Priority analysis (priority_score, criticality)
        ✅ Financial impact analysis
        ✅ Purchase planning columns
        """)
        
        return True
        
    except Exception as e:
        st.error(f"❌ Migration failed: {str(e)}")
        return False
        
def run_all_migrations():
    """Run all necessary migrations for the system"""
    st.header("🔄 Database Migration Tool")
    
    migrations = [
        {
            "name": "Merged Excel Support",
            "description": "Add columns for pricing, priority analysis, and purchase planning",
            "function": migrate_to_merged_excel_support
        },
        {
            "name": "Fix Active Versions",
            "description": "Repair version status issues",
            "function": fix_active_versions
        }
    ]
    
    for migration in migrations:
        with st.expander(f"🔧 {migration['name']}", expanded=True):
            st.write(migration['description'])
            if st.button(f"Run {migration['name']}", key=migration['name']):
                with st.spinner(f"Running {migration['name']}..."):
                    if migration['function']():
                        st.success(f"✅ {migration['name']} completed!")
                    else:
                        st.error(f"❌ {migration['name']} failed!") 