"""
Snowflake Analytics Dashboard Data
Single connection function to get all data needed for analytics page
"""

import streamlit as st
from .snowflake_connection import get_snowflake_connection

def get_analytics_page_data(empresa: str, version_id: int = None):
    """
    Single function to get ALL data needed for the analytics page in ONE Snowflake connection.
    This prevents multiple Duo authentication prompts.
    
    Args:
        empresa: Company code (MINIPA, MINIPA_INDUSTRIA)
        version_id: Optional specific version ID to load
        
    Returns:
        Dictionary with all the data:
        {
            'versions': [...],  # List of available versions
            'analytics_data': pd.DataFrame or None,  # The actual analytics data
            'data_info': {  # Summary info about the data
                'row_count': int,
                'latest_upload': datetime,
                'has_priority_data': bool
            }
        }
    """
    import pandas as pd
    
    # Initialize return structure
    result = {
        'versions': [],
        'analytics_data': None,
        'data_info': {
            'row_count': 0,
            'latest_upload': None,
            'has_priority_data': False
        }
    }
    
    conn = get_snowflake_connection()
    if not conn:
        return result
        
    try:
        cursor = conn.cursor()
        
        # 1. Get available versions for analytics
        try:
            cursor.execute("""
            SELECT upload_version, version_id, table_type, upload_date, 
                   description, arquivo_origem, linhas_processadas, status, created_by, is_active
            FROM CONFIG.VERSIONS 
            WHERE empresa = %s AND table_type = 'ANALYTICS'
            ORDER BY is_active DESC, upload_date DESC
            LIMIT 20
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
            result['versions'] = versions
        except Exception as version_error:
            # Don't fail if versions can't be loaded
            pass
        
        # 2. Check if analytics table exists
        try:
            cursor.execute("SELECT 1 FROM ESTOQUE.ANALYTICS_DATA LIMIT 1")
        except:
            # Table might not exist
            cursor.close()
            conn.close()
            return result
        
        # 3. Load the actual analytics data
        try:
            # Pick an effective version id: explicit > active from versions > latest
            effective_version_id = version_id
            if effective_version_id is None:
                # Try active version from versions list
                active_versions = [v for v in result['versions'] if v.get('is_active')]
                if active_versions:
                    effective_version_id = active_versions[0]['version_id']
                elif result['versions']:
                    # Fallback to most recent by order already returned
                    effective_version_id = result['versions'][0]['version_id']

            if effective_version_id is None:
                # No versions found for this company, return empty result
                cursor.close()
                conn.close()
                return result

            # Always load by a concrete version id to avoid is_active mismatches
            query = """
                SELECT produto as "Produto", 
                       estoque as "Estoque", 
                       media_6_meses as "Média 6 Meses",
                       consumo_6_meses as "Consumo 6 Meses",
                       estoque_cobertura as "Estoque Cobertura",
                       moq as "MOQ",
                       ultimo_fornecedor as "UltimoFornecedor",
                       qtde_tot_compras as "Qtde Tot Compras",
                       compras_ate_30_dias as "Compras Até 30 Dias",
                       compras_31_60_dias as "Compras 31 a 60 Dias", 
                       compras_61_90_dias as "Compras 61 a 90 Dias",
                       compras_mais_90_dias as "Compras > 90 Dias",
                       qtde_embarque as "Qtde Embarque",
                       preco_unitario as "preco_unitario",
                       carteira as "Carteira",
                       data_upload,
                       version_id,
                       -- Check for merged Excel columns
                       criticality,
                       priority_score,
                       relevance_class,
                       monthly_volume
                FROM ESTOQUE.ANALYTICS_DATA 
                WHERE empresa = %s AND version_id = %s
                ORDER BY produto
                """
            query_params = [empresa, effective_version_id]
            
            cursor.close()  # Close cursor before using pandas
            
            # Use pandas to read the data
            df = pd.read_sql(query, conn, params=query_params)
            
            if not df.empty:
                result['analytics_data'] = df
                result['data_info']['row_count'] = len(df)
                result['data_info']['latest_upload'] = df['data_upload'].max() if 'data_upload' in df.columns else None
                
                # Check if this is merged Excel data with priority columns
                priority_columns = ['priority_score', 'criticality', 'relevance_class']
                result['data_info']['has_priority_data'] = any(col in df.columns and df[col].notna().any() for col in priority_columns)
                
                # Remove metadata columns before returning
                columns_to_remove = ['data_upload', 'version_id']
                for col in columns_to_remove:
                    if col in df.columns:
                        df = df.drop(columns=[col])
                
                result['analytics_data'] = df
                
        except Exception as data_error:
            st.error(f"❌ Erro ao carregar dados de análise: {str(data_error)}")
            pass
        
        # 4. Load CBM data from timeline table (for Solicitação de Pedidos)
        try:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT item, cbm
            FROM ESTOQUE.PRODUTOS
            WHERE empresa = %s AND table_type = 'TIMELINE' AND is_active = TRUE
            AND item IS NOT NULL AND cbm IS NOT NULL
            """, (empresa,))
            
            cbm_data = {}
            for row in cursor.fetchall():
                produto = str(row[0]).strip()
                cbm = float(row[1] or 0)
                if produto and produto != 'nan' and cbm > 0:
                    cbm_data[produto] = cbm
            
            result['timeline_cbm_data'] = cbm_data
            cursor.close()
            
        except Exception as cbm_error:
            # Don't fail if CBM data can't be loaded
            pass
        
        conn.close()
        return result
        
    except Exception as e:
        if conn:
            conn.close()
        st.error(f"❌ Erro ao carregar dados do analytics: {str(e)}")
        return result

# Cache this function to avoid repeated calls on reruns
@st.cache_data(ttl=604800, show_spinner=False)  # 7 days cache - analytics update frequency
def get_cached_analytics_page_data(empresa: str, version_id: int = None):
    """
    Cached version of get_analytics_page_data.
    Use this to avoid repeated Snowflake connections on page reruns.
    Cache is keyed by empresa and version_id.
    """
    return get_analytics_page_data(empresa, version_id)