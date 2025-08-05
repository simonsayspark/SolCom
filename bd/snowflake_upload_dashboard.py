"""
Snowflake Upload Dashboard Data
Single connection function to get all data needed for upload page
"""

import streamlit as st
from .snowflake_connection import get_snowflake_connection

def get_upload_page_data(empresa: str, table_prefix: str = None, uploaded_filename: str = None):
    """
    Single function to get ALL data needed for the upload page in ONE Snowflake connection.
    This prevents multiple Duo authentication prompts.
    
    Args:
        empresa: Company code (MINIPA, MINIPA_INDUSTRIA)
        table_prefix: Table type for duplicate check (TIMELINE, ANALYTICS) - optional
        uploaded_filename: Filename to check for duplicates - optional
        
    Returns:
        Dictionary with all the data:
        {
            'stats': {
                'timeline': {'count': int, 'latest_upload': datetime, 'suppliers': int},
                'analytics': {'count': int, 'latest_upload': datetime, 'suppliers': int}
            },
            'versions_timeline': [...],
            'versions_analytics': [...],
            'duplicate_check': {'is_duplicate': bool, 'version_info': {...}} or None
        }
    """
    # Initialize return structure
    result = {
        'stats': {
            'timeline': {'count': 0, 'latest_upload': None, 'suppliers': 0},
            'analytics': {'count': 0, 'latest_upload': None, 'suppliers': 0}
        },
        'versions_timeline': [],
        'versions_analytics': [],
        'duplicate_check': None
    }
    
    conn = get_snowflake_connection()
    if not conn:
        return result
        
    try:
        cursor = conn.cursor()
        
        # 1. Get combined statistics for both timeline and analytics
        try:
            # Timeline stats
            cursor.execute("""
            SELECT COUNT(*) as total_records,
                   MAX(data_upload) as latest_upload,
                   COUNT(DISTINCT fornecedor) as supplier_count
            FROM ESTOQUE.PRODUTOS 
            WHERE empresa = %s AND table_type = 'TIMELINE' AND is_active = TRUE
            """, (empresa,))
            
            timeline_result = cursor.fetchone()
            if timeline_result:
                result['stats']['timeline'] = {
                    'count': timeline_result[0] or 0,
                    'latest_upload': timeline_result[1],
                    'suppliers': timeline_result[2] or 0
                }
            
            # Analytics stats
            cursor.execute("""
            SELECT COUNT(*) as total_records,
                   MAX(data_upload) as latest_upload,
                   COUNT(DISTINCT ultimo_fornecedor) as supplier_count
            FROM ESTOQUE.ANALYTICS_DATA 
            WHERE empresa = %s AND is_active = TRUE
            """, (empresa,))
            
            analytics_result = cursor.fetchone()
            if analytics_result:
                result['stats']['analytics'] = {
                    'count': analytics_result[0] or 0,
                    'latest_upload': analytics_result[1],
                    'suppliers': analytics_result[2] or 0
                }
        except Exception as stats_error:
            # Don't fail the whole function if stats fail
            pass
        
        # 2. Get version history for timeline (limit 10)
        try:
            cursor.execute("""
            SELECT upload_version, version_id, table_type, upload_date, 
                   description, arquivo_origem, linhas_processadas, status, created_by, is_active
            FROM CONFIG.VERSIONS 
            WHERE empresa = %s AND table_type = 'TIMELINE'
            ORDER BY is_active DESC, upload_date DESC
            LIMIT 10
            """, (empresa,))
            
            versions = []
            for row in cursor.fetchall():
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
            result['versions_timeline'] = versions
        except Exception as timeline_version_error:
            # Don't fail the whole function if version fetch fails
            pass
        
        # 3. Get version history for analytics (limit 10)
        try:
            cursor.execute("""
            SELECT upload_version, version_id, table_type, upload_date, 
                   description, arquivo_origem, linhas_processadas, status, created_by, is_active
            FROM CONFIG.VERSIONS 
            WHERE empresa = %s AND table_type = 'ANALYTICS'
            ORDER BY is_active DESC, upload_date DESC
            LIMIT 10
            """, (empresa,))
            
            versions = []
            for row in cursor.fetchall():
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
            result['versions_analytics'] = versions
        except Exception as analytics_version_error:
            # Don't fail the whole function if version fetch fails
            pass
        
        # 4. Check for duplicate file (if filename provided)
        if table_prefix and uploaded_filename:
            try:
                cursor.execute("""
                SELECT upload_version, version_id, table_type, upload_date, 
                       description, arquivo_origem, linhas_processadas, status, created_by, is_active
                FROM CONFIG.VERSIONS
                WHERE empresa = %s AND table_type = %s AND arquivo_origem = %s
                ORDER BY upload_date DESC
                LIMIT 1
                """, (empresa, table_prefix, uploaded_filename))
                
                duplicate_row = cursor.fetchone()
                if duplicate_row:
                    version_info = {
                        'upload_version': duplicate_row[0],
                        'version_id': duplicate_row[1],
                        'table_type': duplicate_row[2],
                        'upload_date': duplicate_row[3],
                        'description': duplicate_row[4] or "",
                        'arquivo_origem': duplicate_row[5] or "",
                        'linhas_processadas': duplicate_row[6] or 0,
                        'status': duplicate_row[7] or "UNKNOWN",
                        'created_by': duplicate_row[8] or "",
                        'is_active': duplicate_row[9] or False
                    }
                    result['duplicate_check'] = {
                        'is_duplicate': True,
                        'version_info': version_info
                    }
                else:
                    result['duplicate_check'] = {
                        'is_duplicate': False,
                        'version_info': None
                    }
            except Exception as duplicate_error:
                # Don't fail the whole function if duplicate check fails
                pass
        
        cursor.close()
        conn.close()
        return result
        
    except Exception as e:
        if conn:
            conn.close()
        st.error(f"❌ Erro ao carregar dados do dashboard: {str(e)}")
        return result

# Cache this function to avoid repeated calls on reruns
@st.cache_data(ttl=300, show_spinner=False)  # 5 minute cache
def get_cached_upload_page_data(empresa: str, table_prefix: str = None, uploaded_filename: str = None):
    """
    Cached version of get_upload_page_data.
    Use this to avoid repeated Snowflake connections on page reruns.
    """
    return get_upload_page_data(empresa, table_prefix, uploaded_filename)