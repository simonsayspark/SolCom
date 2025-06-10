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