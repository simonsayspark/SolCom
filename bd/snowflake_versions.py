"""
Snowflake Version Management
Handles data versioning, version control, and version history
"""

import streamlit as st
import uuid
from datetime import datetime
from .snowflake_connection import get_snowflake_connection

def generate_version_id(empresa, table_type):
    """
    Generate a unique version ID for uploads
    Format: EMPRESA_TABLETYPE_YYYYMMDD_HHMMSS
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_id = f"{empresa}_{table_type}_{timestamp}"
        return version_id
    except Exception as e:
        st.error(f"❌ Erro ao gerar ID de versão: {str(e)}")
        return f"ERROR_{uuid.uuid4().hex[:8]}"

def create_new_version(empresa, table_type, description="", created_by="minipa", arquivo_origem=""):
    """
    Create a new version entry in the version control system
    Returns version info or None if failed
    """
    conn = get_snowflake_connection()
    if not conn:
        return None
        
    try:
        cursor = conn.cursor()
        
        # Generate unique upload version
        upload_version = str(uuid.uuid4())
        
        # Generate sequential version ID
        cursor.execute("""
        SELECT COALESCE(MAX(version_id), 0) + 1 
        FROM CONFIG.VERSIONS 
        WHERE empresa = %s AND table_type = %s
        """, (empresa, table_type))
        
        version_id = cursor.fetchone()[0]
        
        # Create version record
        cursor.execute("""
        INSERT INTO CONFIG.VERSIONS 
        (empresa, upload_version, version_id, table_type, created_by, description, arquivo_origem)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (empresa, upload_version, version_id, table_type, created_by, description, arquivo_origem))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            'upload_version': upload_version,
            'version_id': version_id,
            'empresa': empresa,
            'table_type': table_type
        }
        
    except Exception as e:
        st.error(f"❌ Erro ao criar versão: {str(e)}")
        return None

@st.cache_data(ttl=604800, show_spinner=False)  # 1 week cache - matches your analytics update frequency
def get_upload_versions(empresa, table_type=None, limit=50):
    """
    OPTIMIZATION: Reduced cache time for more accurate version info
    Combined query to reduce database calls and improve ordering
    """
    conn = get_snowflake_connection()
    if not conn:
        return []
        
    try:
        cursor = conn.cursor()
        
        # OPTIMIZED: Use better ordering - active versions first, then by date
        if table_type:
            query = """
            SELECT upload_version, version_id, table_type, upload_date, 
                   description, arquivo_origem, linhas_processadas, status, created_by, is_active
            FROM CONFIG.VERSIONS 
            WHERE empresa = %s AND table_type = %s
            ORDER BY is_active DESC, upload_date DESC  -- Active versions first
            LIMIT %s
            """
            params = (empresa, table_type, limit)
        else:
            query = """
            SELECT upload_version, version_id, table_type, upload_date, 
                   description, arquivo_origem, linhas_processadas, status, created_by, is_active
            FROM CONFIG.VERSIONS 
            WHERE empresa = %s
            ORDER BY is_active DESC, table_type, upload_date DESC  -- Active first, then by type
            LIMIT %s
            """
            params = (empresa, limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        versions = []
        for row in results:
            versions.append({
                'upload_version': row[0],
                'version_id': row[1],
                'table_type': row[2],
                'upload_date': row[3],
                'description': row[4] or "",
                'arquivo_origem': row[5] or "",
                'linhas_processadas': row[6] or 0,
                'status': row[7] or "UNKNOWN",
                'created_by': row[8] or "",
                'is_active': row[9] or False
            })
        
        cursor.close()
        conn.close()
        return versions
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar versões: {str(e)}")
        return []

@st.cache_data(ttl=604800, show_spinner=False)  # 1 week cache - matches your data update pattern  
def get_version_summary(empresa, table_type=None):
    """
    NEW OPTIMIZATION: Get version summary without loading full version list
    Useful for quick status checks without expensive queries
    """
    conn = get_snowflake_connection()
    if not conn:
        return {}
        
    try:
        cursor = conn.cursor()
        
        if table_type:
            cursor.execute("""
            SELECT 
                COUNT(*) as total_versions,
                SUM(CASE WHEN is_active = TRUE THEN 1 ELSE 0 END) as active_versions,
                MAX(upload_date) as latest_upload,
                MAX(linhas_processadas) as max_records
            FROM CONFIG.VERSIONS 
            WHERE empresa = %s AND table_type = %s
            """, (empresa, table_type))
        else:
            cursor.execute("""
            SELECT 
                COUNT(*) as total_versions,
                SUM(CASE WHEN is_active = TRUE THEN 1 ELSE 0 END) as active_versions,
                MAX(upload_date) as latest_upload,
                MAX(linhas_processadas) as max_records
            FROM CONFIG.VERSIONS 
            WHERE empresa = %s
            """, (empresa,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return {
            'total_versions': result[0] or 0,
            'active_versions': result[1] or 0,
            'latest_upload': result[2],
            'max_records': result[3] or 0
        }
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar resumo de versões: {str(e)}")
        return {}

def set_active_version(empresa, upload_version, table_type):
    """
    Set a specific version as active (deactivate others)
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # First, deactivate all versions for this company and table type
        if table_type == "TIMELINE":
            cursor.execute("""
            UPDATE ESTOQUE.PRODUTOS 
            SET is_active = FALSE 
            WHERE empresa = %s AND table_type = %s
            """, (empresa, table_type))
        elif table_type == "ANALYTICS":
            cursor.execute("""
            UPDATE ESTOQUE.ANALYTICS_DATA 
            SET is_active = FALSE 
            WHERE empresa = %s
            """, (empresa,))
        
        # Then activate the selected version
        if table_type == "TIMELINE":
            cursor.execute("""
            UPDATE ESTOQUE.PRODUTOS 
            SET is_active = TRUE 
            WHERE empresa = %s AND upload_version = %s AND table_type = %s
            """, (empresa, upload_version, table_type))
        elif table_type == "ANALYTICS":
            cursor.execute("""
            UPDATE ESTOQUE.ANALYTICS_DATA 
            SET is_active = TRUE 
            WHERE empresa = %s AND upload_version = %s
            """, (empresa, upload_version))
        
        # Update version control
        cursor.execute("""
        UPDATE CONFIG.VERSIONS 
        SET is_active = FALSE 
        WHERE empresa = %s AND table_type = %s
        """, (empresa, table_type))
        
        cursor.execute("""
        UPDATE CONFIG.VERSIONS 
        SET is_active = TRUE 
        WHERE empresa = %s AND upload_version = %s AND table_type = %s
        """, (empresa, upload_version, table_type))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        st.success(f"✅ Versão ativada para {empresa} - {table_type}")
        return True
        
    except Exception as e:
        st.error(f"❌ Erro ao ativar versão: {str(e)}")
        return False

def get_version_by_id(empresa, version_id, table_type):
    """
    Get specific version information by version ID
    """
    conn = get_snowflake_connection()
    if not conn:
        return None
        
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT upload_version, version_id, table_type, upload_date, 
               description, arquivo_origem, linhas_processadas, status, created_by, is_active
        FROM CONFIG.VERSIONS 
        WHERE empresa = %s AND version_id = %s AND table_type = %s
        """, (empresa, version_id, table_type))
        
        result = cursor.fetchone()
        
        if result:
            version_info = {
                'upload_version': result[0],
                'version_id': result[1],
                'table_type': result[2],
                'upload_date': result[3],
                'description': result[4] or "",
                'arquivo_origem': result[5] or "",
                'linhas_processadas': result[6] or 0,
                'status': result[7] or "UNKNOWN",
                'created_by': result[8] or "",
                'is_active': result[9] or False
            }
            
            cursor.close()
            conn.close()
            return version_info
        else:
            cursor.close()
            conn.close()
            return None
            
    except Exception as e:
        st.error(f"❌ Erro ao buscar versão: {str(e)}")
        return None

def get_active_version(empresa, table_type):
    """
    Get the currently active version for a company and table type
    """
    conn = get_snowflake_connection()
    if not conn:
        return None
        
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT upload_version, version_id, upload_date, description, 
               arquivo_origem, linhas_processadas, created_by
        FROM CONFIG.VERSIONS 
        WHERE empresa = %s AND table_type = %s AND is_active = TRUE
        ORDER BY upload_date DESC
        LIMIT 1
        """, (empresa, table_type))
        
        result = cursor.fetchone()
        
        if result:
            version_info = {
                'upload_version': result[0],
                'version_id': result[1],
                'upload_date': result[2],
                'description': result[3] or "",
                'arquivo_origem': result[4] or "",
                'linhas_processadas': result[5] or 0,
                'created_by': result[6] or ""
            }
            
            cursor.close()
            conn.close()
            return version_info
        else:
            cursor.close()
            conn.close()
            return None
            
    except Exception as e:
        st.error(f"❌ Erro ao buscar versão ativa: {str(e)}")
        return None

def delete_version(empresa, version_id, table_type):
    """
    Delete a specific version (cannot delete active version)
    Returns True if successful, False otherwise
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # First check if this version is active
        cursor.execute("""
        SELECT is_active FROM CONFIG.VERSIONS 
        WHERE empresa = %s AND version_id = %s AND table_type = %s
        """, (empresa, version_id, table_type))
        
        result = cursor.fetchone()
        if not result:
            st.error("❌ Versão não encontrada")
            cursor.close()
            conn.close()
            return False
            
        if result[0]:  # is_active = True
            st.error("❌ Não é possível deletar a versão ativa")
            cursor.close()
            conn.close()
            return False
        
        # Get upload_version for data deletion
        cursor.execute("""
        SELECT upload_version FROM CONFIG.VERSIONS 
        WHERE empresa = %s AND version_id = %s AND table_type = %s
        """, (empresa, version_id, table_type))
        
        upload_version_result = cursor.fetchone()
        if not upload_version_result:
            st.error("❌ Upload version não encontrada")
            cursor.close()
            conn.close()
            return False
            
        upload_version = upload_version_result[0]
        
        # Delete data from appropriate table
        if table_type == "TIMELINE":
            cursor.execute("""
            DELETE FROM ESTOQUE.PRODUTOS 
            WHERE empresa = %s AND upload_version = %s AND table_type = %s
            """, (empresa, upload_version, table_type))
        elif table_type == "ANALYTICS":
            cursor.execute("""
            DELETE FROM ESTOQUE.ANALYTICS_DATA 
            WHERE empresa = %s AND upload_version = %s
            """, (empresa, upload_version))
        
        # Delete version record
        cursor.execute("""
        DELETE FROM CONFIG.VERSIONS 
        WHERE empresa = %s AND version_id = %s AND table_type = %s
        """, (empresa, version_id, table_type))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Clear cache to refresh data
        get_upload_versions.clear()
        
        return True
        
    except Exception as e:
        st.error(f"❌ Erro ao deletar versão: {str(e)}")
        return False

def fix_active_versions():
    """
    Fix the is_active status to ensure only the latest version per company/table_type is active
    This is a repair function for existing data
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # Get all companies and table types
        cursor.execute("""
        SELECT DISTINCT empresa, table_type 
        FROM CONFIG.VERSIONS 
        ORDER BY empresa, table_type
        """)
        
        combinations = cursor.fetchall()
        fixed_count = 0
        
        for empresa, table_type in combinations:
            # First, deactivate all versions for this combination
            cursor.execute("""
            UPDATE CONFIG.VERSIONS 
            SET is_active = FALSE 
            WHERE empresa = %s AND table_type = %s
            """, (empresa, table_type))
            
            # Deactivate in data tables
            if table_type == "TIMELINE":
                cursor.execute("""
                UPDATE ESTOQUE.PRODUTOS 
                SET is_active = FALSE 
                WHERE empresa = %s AND table_type = %s
                """, (empresa, table_type))
            elif table_type == "ANALYTICS":
                cursor.execute("""
                UPDATE ESTOQUE.ANALYTICS_DATA 
                SET is_active = FALSE 
                WHERE empresa = %s
                """, (empresa,))
            
            # Find the latest version (highest version_id)
            cursor.execute("""
            SELECT upload_version, version_id 
            FROM CONFIG.VERSIONS 
            WHERE empresa = %s AND table_type = %s 
            ORDER BY version_id DESC 
            LIMIT 1
            """, (empresa, table_type))
            
            latest_version = cursor.fetchone()
            if latest_version:
                upload_version, version_id = latest_version
                
                # Set the latest version as active in version control
                cursor.execute("""
                UPDATE CONFIG.VERSIONS 
                SET is_active = TRUE 
                WHERE empresa = %s AND upload_version = %s AND table_type = %s
                """, (empresa, upload_version, table_type))
                
                # Set the latest version as active in data tables
                if table_type == "TIMELINE":
                    cursor.execute("""
                    UPDATE ESTOQUE.PRODUTOS 
                    SET is_active = TRUE 
                    WHERE empresa = %s AND upload_version = %s AND table_type = %s
                    """, (empresa, upload_version, table_type))
                elif table_type == "ANALYTICS":
                    cursor.execute("""
                    UPDATE ESTOQUE.ANALYTICS_DATA 
                    SET is_active = TRUE 
                    WHERE empresa = %s AND upload_version = %s
                    """, (empresa, upload_version))
                
                fixed_count += 1
                st.info(f"✅ {empresa} - {table_type}: v{version_id} definida como ativa")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        st.success(f"🔧 Reparação concluída! {fixed_count} combinações empresa/tipo corrigidas.")
        
        # Clear cache to refresh data
        get_upload_versions.clear()
        
        return True
        
    except Exception as e:
        st.error(f"❌ Erro ao reparar versões ativas: {str(e)}")
        return False 