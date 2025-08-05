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
            SELECT version_id, upload_date, description, is_active, arquivo_origem
            FROM CONFIG.UPLOAD_VERSIONS
            WHERE empresa = %s AND table_type = 'TIMELINE'
            ORDER BY upload_date DESC
            LIMIT 10
            """, (empresa,))
            
            columns = [desc[0].lower() for desc in cursor.description]
            result['versions_timeline'] = [
                dict(zip(columns, row)) for row in cursor.fetchall()
            ]
        except Exception as timeline_version_error:
            # Don't fail the whole function if version fetch fails
            pass
        
        # 3. Get version history for analytics (limit 10)
        try:
            cursor.execute("""
            SELECT version_id, upload_date, description, is_active, arquivo_origem
            FROM CONFIG.UPLOAD_VERSIONS
            WHERE empresa = %s AND table_type = 'ANALYTICS'
            ORDER BY upload_date DESC
            LIMIT 10
            """, (empresa,))
            
            columns = [desc[0].lower() for desc in cursor.description]
            result['versions_analytics'] = [
                dict(zip(columns, row)) for row in cursor.fetchall()
            ]
        except Exception as analytics_version_error:
            # Don't fail the whole function if version fetch fails
            pass
        
        # 4. Check for duplicate file (if filename provided)
        if table_prefix and uploaded_filename:
            try:
                cursor.execute("""
                SELECT version_id, upload_date, description, is_active, arquivo_origem
                FROM CONFIG.UPLOAD_VERSIONS
                WHERE empresa = %s AND table_type = %s AND arquivo_origem = %s
                ORDER BY upload_date DESC
                LIMIT 1
                """, (empresa, table_prefix, uploaded_filename))
                
                duplicate_row = cursor.fetchone()
                if duplicate_row:
                    columns = [desc[0].lower() for desc in cursor.description]
                    version_info = dict(zip(columns, duplicate_row))
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