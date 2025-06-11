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

@st.cache_data(ttl=3600, show_spinner="🔄 Carregando versões...")  # 1 hour cache
def get_upload_versions(empresa, table_type=None, limit=50):
    """
    Get list of upload versions for a company
    Returns list of version info or empty list if failed
    """
    conn = get_snowflake_connection()
    if not conn:
        return []
        
    try:
        cursor = conn.cursor()
        
        if table_type:
            query = """
            SELECT upload_version, version_id, table_type, upload_date, 
                   description, arquivo_origem, linhas_processadas, status, created_by, is_active
            FROM CONFIG.VERSIONS 
            WHERE empresa = %s AND table_type = %s
            ORDER BY upload_date DESC
            LIMIT %s
            """
            params = (empresa, table_type, limit)
        else:
            query = """
            SELECT upload_version, version_id, table_type, upload_date, 
                   description, arquivo_origem, linhas_processadas, status, created_by, is_active
            FROM CONFIG.VERSIONS 
            WHERE empresa = %s
            ORDER BY upload_date DESC
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