"""
Snowflake Upload Dashboard Data
Single connection function to get all data needed for upload page
"""

import streamlit as st
from .snowflake_connection import get_snowflake_connection

def get_upload_page_data(empresa: str, table_prefix: str = None, uploaded_filename: str = None, 
                        delete_version_id: int = None, delete_table_type: str = None,
                        repair_versions: bool = False):
    """
    Single function to get ALL data needed for the upload page in ONE Snowflake connection.
    This prevents multiple Duo authentication prompts.
    
    Args:
        empresa: Company code (MINIPA, MINIPA_INDUSTRIA)
        table_prefix: Table type for duplicate check (TIMELINE, ANALYTICS) - optional
        uploaded_filename: Filename to check for duplicates - optional
        delete_version_id: Version ID to delete - optional
        delete_table_type: Table type for deletion - optional
        repair_versions: Whether to repair active versions - optional
        
    Returns:
        Dictionary with all the data:
        {
            'stats': {
    
                'analytics': {'count': int, 'latest_upload': datetime, 'suppliers': int}
            },

            'versions_analytics': [...],
            'duplicate_check': {'is_duplicate': bool, 'version_info': {...}} or None,
            'delete_result': {'success': bool, 'message': str} or None,
            'repair_result': {'success': bool, 'fixed_count': int} or None
        }
    """
    # Initialize return structure
    result = {
        'stats': {
            'analytics': {'count': 0, 'latest_upload': None, 'suppliers': 0}
        },
        'versions_analytics': [],
        'duplicate_check': None,
        'delete_result': None,
        'repair_result': None
    }
    
    conn = get_snowflake_connection()
    if not conn:
        return result
        
    try:
        cursor = conn.cursor()
        
        # 1. Get statistics for analytics only (timeline table dropped)
        try:
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
        
        # Timeline removed - table dropped
        
        # 2. Get version history for analytics (limit 10)
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
        
        # 5. Handle version deletion if requested
        if delete_version_id and delete_table_type:
            try:
                cursor.execute("""
                DELETE FROM CONFIG.VERSIONS 
                WHERE empresa = %s AND version_id = %s AND table_type = %s
                """, (empresa, delete_version_id, delete_table_type))
                
                # Also delete data from appropriate table
                if delete_table_type == "ANALYTICS":
                    cursor.execute("""
                    DELETE FROM ESTOQUE.ANALYTICS_DATA 
                    WHERE empresa = %s AND version_id = %s
                    """, (empresa, delete_version_id))
                
                conn.commit()
                result['delete_result'] = {
                    'success': True,
                    'message': f'Versão {delete_version_id} deletada com sucesso'
                }
            except Exception as delete_error:
                result['delete_result'] = {
                    'success': False,
                    'message': str(delete_error)
                }
        
        # 6. Handle version repair if requested
        if repair_versions:
            try:
                fixed_count = 0
                
                # Get all unique empresa/table_type combinations
                cursor.execute("""
                SELECT DISTINCT empresa, table_type 
                FROM CONFIG.VERSIONS
                """)
                
                combinations = cursor.fetchall()
                
                for emp, tbl in combinations:
                    # First, set all versions to inactive
                    cursor.execute("""
                    UPDATE CONFIG.VERSIONS 
                    SET is_active = FALSE 
                    WHERE empresa = %s AND table_type = %s
                    """, (emp, tbl))
                    
                    # Then activate only the most recent one
                    cursor.execute("""
                    UPDATE CONFIG.VERSIONS 
                    SET is_active = TRUE 
                    WHERE empresa = %s AND table_type = %s 
                    AND upload_date = (
                        SELECT MAX(upload_date) 
                        FROM CONFIG.VERSIONS v2 
                        WHERE v2.empresa = %s AND v2.table_type = %s
                    )
                    """, (emp, tbl, emp, tbl))
                    
                    # Also update data tables
                    if tbl == 'ANALYTICS':
                        cursor.execute("""
                        UPDATE ESTOQUE.ANALYTICS_DATA 
                        SET is_active = FALSE 
                        WHERE empresa = %s
                        """, (emp,))
                        
                        cursor.execute("""
                        UPDATE ESTOQUE.ANALYTICS_DATA 
                        SET is_active = TRUE 
                        WHERE empresa = %s 
                        AND version_id = (
                            SELECT version_id FROM CONFIG.VERSIONS 
                            WHERE empresa = %s AND table_type = %s AND is_active = TRUE
                        )
                        """, (emp, emp, tbl))
                    
                    fixed_count += 1
                
                conn.commit()
                result['repair_result'] = {
                    'success': True,
                    'fixed_count': fixed_count
                }
            except Exception as repair_error:
                result['repair_result'] = {
                    'success': False,
                    'message': str(repair_error)
                }
        
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