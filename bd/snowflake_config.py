"""
Snowflake Configuration - Refactored & Modular
Main module that imports from organized sub-modules

This replaces the original 2000+ line monolithic snowflake_config.py 
with a clean, modular structure.
"""

# Import all functions from modular files
from .snowflake_connection import (
    get_snowflake_connection,
    get_snowpark_session, 
    test_connection,
    DATABASE_SCHEMA
)

from .snowflake_tables import (
    create_tables,
    check_database_structure,
    force_create_new_structure,
    add_analytics_columns
)

from .snowflake_data import (
    load_data_with_history,
    load_analytics_data
)

from .snowflake_versions import (
    generate_version_id,
    create_new_version,
    get_upload_versions,
    set_active_version,
    get_version_by_id,
    get_active_version,
    delete_version
)

from .snowflake_upload import (
    upload_excel_to_snowflake,
    analyze_excel_structure
)

from .snowflake_migration import (
    migrate_to_multi_company_versioned,
    migrate_existing_tables
)

from .snowflake_admin import (
    clear_company_data,
    get_database_statistics
)

# Export all functions for backward compatibility
__all__ = [
    # Connection
    'get_snowflake_connection',
    'get_snowpark_session',
    'test_connection',
    'DATABASE_SCHEMA',
    
    # Tables
    'create_tables',
    'check_database_structure', 
    'force_create_new_structure',
    'add_analytics_columns',
    
    # Data Loading
    'load_data_with_history',
    'load_analytics_data',
    
    # Version Management
    'generate_version_id',
    'create_new_version',
    'get_upload_versions',
    'set_active_version',
    'get_version_by_id',
    'get_active_version',
    'delete_version',
    
    # Upload & Analysis
    'upload_excel_to_snowflake',
    'analyze_excel_structure',
    
    # Migration
    'migrate_to_multi_company_versioned',
    'migrate_existing_tables',
    
    # Admin
    'clear_company_data',
    'get_database_statistics'
]

# Convenience function to show structure
def show_module_structure():
    """
    Display the new modular structure for reference
    """
    import streamlit as st
    
    st.info("""
    🏗️ **Nova Estrutura Modular do Snowflake:**
    
    📁 **bd/snowflake_connection.py** - Conexões & configuração básica ✅
    📁 **bd/snowflake_tables.py** - Criação e gerenciamento de tabelas ✅
    📁 **bd/snowflake_data.py** - Carregamento de dados (com cache) ✅
    📁 **bd/snowflake_versions.py** - Controle de versões ✅
    📁 **bd/snowflake_upload.py** - Upload e análise de Excel ✅
    📁 **bd/snowflake_migration.py** - Funções de migração ✅
    📁 **bd/snowflake_admin.py** - Administração e limpeza ✅
    
    ✅ **Vantagens da refatoração:**
    - Arquivos menores e mais fáceis de debugar
    - Separação clara de responsabilidades  
    - Imports organizados
    - Menos erros de sintaxe
    - Manutenção mais simples
    
    📊 **Estatísticas:**
    - Original: 2055 linhas em 1 arquivo
    - Novo: ~1200 linhas em 7 arquivos
    - Redução: ~40% menos código total
    """)

if __name__ == "__main__":
    show_module_structure() 