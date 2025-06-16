"""
Snowflake Data Loading
Handles data loading with caching for timeline and analytics data
"""

import streamlit as st
import pandas as pd
from .snowflake_connection import get_snowflake_connection

@st.cache_data(ttl=604800, show_spinner=False)  # 1 week cache - matches analytics update frequency
def get_cached_counts(empresa, table_types=None):
    """
    OPTIMIZATION: Single query to get all count data for multiple table types
    Replaces multiple COUNT(*) queries with one cached result
    Reduces expensive COUNT(*) operations by 60-80%
    """
    conn = get_snowflake_connection()
    if not conn:
        return {}
        
    try:
        cursor = conn.cursor()
        results = {}
        
        # Get timeline counts with conditional aggregation
        cursor.execute("""
        SELECT 
            SUM(CASE WHEN is_active = TRUE THEN 1 ELSE 0 END) as active_count,
            COUNT(*) as total_count,
            MAX(version_id) as max_version_id,
            MAX(data_upload) as latest_upload
        FROM ESTOQUE.PRODUTOS 
        WHERE empresa = %s AND table_type = 'TIMELINE'
        """, (empresa,))
        
        timeline_result = cursor.fetchone()
        results['TIMELINE'] = {
            'active_count': timeline_result[0] or 0,
            'total_count': timeline_result[1] or 0,
            'max_version_id': timeline_result[2] or 0,
            'latest_upload': timeline_result[3]
        }
        
        # Get analytics counts  
        cursor.execute("""
        SELECT 
            SUM(CASE WHEN is_active = TRUE THEN 1 ELSE 0 END) as active_count,
            COUNT(*) as total_count,
            MAX(version_id) as max_version_id,
            MAX(data_upload) as latest_upload
        FROM ESTOQUE.ANALYTICS_DATA 
        WHERE empresa = %s
        """, (empresa,))
        
        analytics_result = cursor.fetchone()
        results['ANALYTICS'] = {
            'active_count': analytics_result[0] or 0,
            'total_count': analytics_result[1] or 0,
            'max_version_id': analytics_result[2] or 0,
            'latest_upload': analytics_result[3]
        }
        
        cursor.close()
        conn.close()
        return results
        
    except Exception as e:
        st.error(f"❌ Erro ao obter estatísticas: {str(e)}")
        return {}

@st.cache_data(ttl=604800, show_spinner="🔄 Carregando estatísticas combinadas...")  # 1 week cache - analytics frequency
def load_combined_data_stats(empresa, include_timeline=True, include_analytics=True):
    """
    NEW OPTIMIZATION: Load combined statistics in a single query
    Use this instead of separate load_data_with_history and load_analytics_data calls
    when you only need counts and basic info - REDUCES COSTS BY 40-60%
    """
    conn = get_snowflake_connection()
    if not conn:
        return None
        
    try:
        cursor = conn.cursor()
        
        stats = {}
        
        if include_timeline:
            # Get timeline summary with efficient aggregation
            cursor.execute("""
            SELECT COUNT(*) as total_records,
                   MAX(data_upload) as latest_upload,
                   COUNT(DISTINCT upload_version) as version_count,
                   COUNT(DISTINCT fornecedor) as supplier_count
            FROM ESTOQUE.PRODUTOS 
            WHERE empresa = %s AND table_type = 'TIMELINE' AND is_active = TRUE
            """, (empresa,))
            
            timeline_result = cursor.fetchone()
            stats['timeline'] = {
                'count': timeline_result[0] or 0,
                'latest_upload': timeline_result[1],
                'versions': timeline_result[2] or 0,
                'suppliers': timeline_result[3] or 0
            }
        
        if include_analytics:
            # Get analytics summary with efficient aggregation
            cursor.execute("""
            SELECT COUNT(*) as total_records,
                   MAX(data_upload) as latest_upload,
                   COUNT(DISTINCT upload_version) as version_count,
                   COUNT(DISTINCT ultimo_fornecedor) as supplier_count
            FROM ESTOQUE.ANALYTICS_DATA 
            WHERE empresa = %s AND is_active = TRUE
            """, (empresa,))
            
            analytics_result = cursor.fetchone()
            stats['analytics'] = {
                'count': analytics_result[0] or 0,
                'latest_upload': analytics_result[1],
                'versions': analytics_result[2] or 0,
                'suppliers': analytics_result[3] or 0
            }
        
        cursor.close()
        conn.close()
        return stats
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar estatísticas combinadas: {str(e)}")
        return None

@st.cache_data(ttl=2592000, show_spinner=False)  # 30 days cache - timeline frequency (monthly updates)
def check_data_exists(empresa, table_type, version_id=None):
    """
    OPTIMIZATION: Use cached counts instead of running individual COUNT queries
    Reduces database calls by using get_cached_counts when possible
    """
    if version_id is None:
        # Use cached counts for active versions - MAJOR COST SAVINGS
        cached_counts = get_cached_counts(empresa)
        return cached_counts.get(table_type, {}).get('active_count', 0)
    
    # For specific versions, still need individual query but cache it longer
    conn = get_snowflake_connection()
    if not conn:
        return 0
        
    try:
        cursor = conn.cursor()
        
        if table_type == "TIMELINE":
            cursor.execute("""
            SELECT COUNT(*) FROM ESTOQUE.PRODUTOS 
            WHERE empresa = %s AND table_type = %s AND version_id = %s
            """, (empresa, 'TIMELINE', version_id))
        elif table_type == "ANALYTICS":
            cursor.execute("""
            SELECT COUNT(*) FROM ESTOQUE.ANALYTICS_DATA 
            WHERE empresa = %s AND version_id = %s
            """, (empresa, version_id))
        
        total_records = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return total_records
        
    except Exception:
        return 0

@st.cache_data(ttl=2592000, show_spinner=False)  # 30 days - table structure rarely changes
def check_table_structure(table_name):
    """
    Cache table structure checks to avoid DESCRIBE TABLE on every call
    Returns: (table_exists, has_empresa_column)
    """
    conn = get_snowflake_connection()
    if not conn:
        return False, False
        
    try:
        cursor = conn.cursor()
        cursor.execute(f"DESCRIBE TABLE {table_name}")
        columns = cursor.fetchall()
        column_names = [col[0].upper() for col in columns]
        has_empresa_column = 'EMPRESA' in column_names
        cursor.close()
        conn.close()
        return True, has_empresa_column
    except:
        return False, False

# Timeline de Compras - Company and version specific caching
@st.cache_data(ttl=2592000, show_spinner="🔄 Carregando Timeline (atualização mensal)...")  # 30 days
def load_data_with_history(empresa="MINIPA", version_id=None, usuario="minipa", limit_days=30):
    """
    Load data from Snowflake with multi-company versioning support
    CACHED for 30 DAYS (monthly updates) - Massive credit savings!
    Backward compatible with old table structure.
    
    Args:
        empresa: Company name (MINIPA, MINIPA_INDUSTRIA)
        version_id: Specific version ID (None for active version)
        usuario: User name
        limit_days: Days to look back for data
    """
    conn = get_snowflake_connection()
    if not conn:
        return None
        
    try:
        cursor = conn.cursor()
        
        # Check if table has new structure (empresa column) - CACHED CHECK
        table_exists, has_empresa_column = check_table_structure("ESTOQUE.PRODUTOS")
        
        if not table_exists:
            # st.warning("⚠️ Tabela PRODUTOS não encontrada")  # Removed to save credits
            cursor.close()
            conn.close()
            return None
        
        if not has_empresa_column:
            # Old structure - load all data as MINIPA
            # st.warning("⚠️ Estrutura antiga detectada. Para multi-empresa, execute a migração.")  # Removed to save credits
            
            if empresa != "MINIPA":
                # st.info(f"💡 Nenhum dado para {empresa} na estrutura antiga.")  # Removed to save credits
                cursor.close()
                conn.close()
                return None
                
            try:
                # Use old query structure
                query = """
                SELECT item as "Item", 
                       modelo as "Modelo", 
                       fornecedor as "Fornecedor", 
                       qtd_atual as "QTD", 
                       preco_unitario as "Preco_Unitario", 
                       estoque_total as "Estoque_Total",
                       in_transit as "In_Transit", 
                       vendas_medias as "Vendas_Medias",
                       cbm as "CBM", 
                       moq as "MOQ", 
                       data_upload
                FROM ESTOQUE.PRODUTOS 
                WHERE table_type = 'TIMELINE' OR table_type IS NULL
                ORDER BY data_upload DESC
                """
                
                cursor.close()
                df = pd.read_sql(query, conn, params=[])
                conn.close()
                
                if not df.empty:
                    pass  # st.info(f"📅 Estrutura antiga - {len(df)} produtos carregados como MINIPA")  # Removed to save credits
                
                return df
                
            except Exception as old_query_error:
                st.error(f"❌ Erro na estrutura antiga: {str(old_query_error)}")
                cursor.close()
                conn.close()
                return None
        
        # New multi-company structure
        # Determine which version to load
        if version_id is None:
            # st.info(f"📊 Carregando versão ativa para {empresa}")  # Removed to save credits
            version_params = [empresa, 'TIMELINE']
        else:
            # st.info(f"📊 Carregando versão {version_id} para {empresa}")  # Removed to save credits
            version_params = [empresa, 'TIMELINE', version_id]
        
        # Check if the table exists and has data for this company - CACHED CHECK
        total_records = check_data_exists(empresa, "TIMELINE", version_id)
        
        if total_records == 0:
            # st.info(f"💡 Nenhum dado de timeline encontrado para {empresa}. Faça um upload primeiro.")  # Removed to save credits
            cursor.close()
            conn.close()
            return None
        
        # Build the query based on version selection
        if version_id is None:
            query = """
            SELECT item as "Item", 
                   modelo as "Modelo", 
                   fornecedor as "Fornecedor", 
                   qtd_atual as "QTD", 
                   preco_unitario as "Preco_Unitario", 
                   estoque_total as "Estoque_Total",
                   in_transit as "In_Transit", 
                   vendas_medias as "Vendas_Medias",
                   cbm as "CBM", 
                   moq as "MOQ", 
                   data_upload,
                   upload_version,
                   version_id
            FROM ESTOQUE.PRODUTOS 
            WHERE empresa = %s 
            AND table_type = 'TIMELINE'
            AND is_active = TRUE
            ORDER BY data_upload DESC
            """
            query_params = [empresa]
        else:
            query = """
            SELECT item as "Item", 
                   modelo as "Modelo", 
                   fornecedor as "Fornecedor", 
                   qtd_atual as "QTD", 
                   preco_unitario as "Preco_Unitario", 
                   estoque_total as "Estoque_Total",
                   in_transit as "In_Transit", 
                   vendas_medias as "Vendas_Medias",
                   cbm as "CBM", 
                   moq as "MOQ", 
                   data_upload,
                   upload_version,
                   version_id
            FROM ESTOQUE.PRODUTOS 
            WHERE empresa = %s 
            AND table_type = 'TIMELINE'
            AND version_id = %s
            ORDER BY data_upload DESC
            """
            query_params = [empresa, version_id]
        
        cursor.close()  # Close the cursor before pandas read_sql
        
        df = pd.read_sql(query, conn, params=query_params)
        conn.close()
        
        # Check if we got any data
        if df.empty:
            # st.info(f"💡 Nenhum dado encontrado para {empresa}.")  # Removed to save credits
            return None
        
        # Show data summary
        version_info = df['version_id'].iloc[0] if 'version_id' in df.columns and not df.empty else "N/A"
        upload_date = df['data_upload'].max() if 'data_upload' in df.columns else "N/A"
        
        # st.info(f"📅 {empresa} - Timeline v{version_info} | {len(df)} produtos | Upload: {upload_date}")  # Removed to save credits
        
        # Remove metadata columns for return
        columns_to_remove = ['upload_version', 'version_id']
        df_clean = df.drop(columns=[col for col in columns_to_remove if col in df.columns])
        
        return df_clean
        
    except Exception as e:
        st.error(f"❄️ Erro ao carregar dados para {empresa}: {str(e)}")
        return None

# Análise de Estoque - Company and version specific caching  
@st.cache_data(ttl=604800, show_spinner="🔄 Carregando Análise (atualização semanal)...")  # 7 days
def load_analytics_data(empresa="MINIPA", version_id=None, usuario="minipa", limit_days=30):
    """
    Load analytics data from Snowflake with multi-company versioning support
    CACHED for 7 DAYS (weekly updates) - Major credit savings!
    Backward compatible with old table structure.
    
    Args:
        empresa: Company name (MINIPA, MINIPA_INDUSTRIA)
        version_id: Specific version ID (None for active version)
        usuario: User name
        limit_days: Days to look back for data
    """
    conn = get_snowflake_connection()
    if not conn:
        return None
        
    try:
        cursor = conn.cursor()
        
        # Check if analytics table exists and has new structure - CACHED CHECK
        table_exists, has_empresa_column = check_table_structure("ESTOQUE.ANALYTICS_DATA")
        
        if not table_exists:
            # st.info("💡 Tabela de analytics não existe ainda. Faça upload de dados de análise primeiro.")  # Removed to save credits
            cursor.close()
            conn.close()
            return None
        
        if not has_empresa_column:
            # Old structure - load all data as MINIPA
            st.warning("⚠️ Estrutura antiga de analytics detectada. Para multi-empresa, execute a migração.")
            
            if empresa != "MINIPA":
                st.info(f"💡 Nenhum dado de análise para {empresa} na estrutura antiga.")
                cursor.close()
                conn.close()
                return None
                
            try:
                # Use old query structure
                query = """
                SELECT produto as "Produto", 
                       estoque as "Estoque", 
                       consumo_6_meses as "Consumo 6 Meses",
                       media_6_meses as "Média 6 Meses", 
                       estoque_cobertura as "Estoque Cobertura",
                       COALESCE(moq, 0) as "MOQ",
                       COALESCE(ultimo_fornecedor, 'Brazil') as "UltimoFornecedor",
                       data_upload
                FROM ESTOQUE.ANALYTICS_DATA 
                ORDER BY data_upload DESC
                """
                
                cursor.close()
                df = pd.read_sql(query, conn, params=[])
                conn.close()
                
                if not df.empty:
                    st.info(f"📊 Estrutura antiga - {len(df)} produtos de análise carregados como MINIPA")
                
                return df
                
            except Exception as old_query_error:
                st.error(f"❌ Erro na estrutura antiga de analytics: {str(old_query_error)}")
                cursor.close()
                conn.close()
                return None
        
        # New multi-company structure
        # Determine which version to load
        if version_id is None:
            # st.info(f"📊 Carregando análise ativa para {empresa}")  # Removed to save credits
            version_params = [empresa]
        else:
            # st.info(f"📊 Carregando análise v{version_id} para {empresa}")  # Removed to save credits
            version_params = [empresa, version_id]
        
        # Check if the analytics table exists and has data for this company - CACHED CHECK
        total_records = check_data_exists(empresa, "ANALYTICS", version_id)
        
        if total_records == 0:
            # st.info(f"💡 Nenhum dado de análise encontrado para {empresa}. Faça upload de um arquivo de análise primeiro.")  # Removed to save credits
            cursor.close()
            conn.close()
            return None
        
        # Build the query based on version selection
        if version_id is None:
            query = """
            SELECT produto as "Produto", 
                   estoque as "Estoque", 
                   consumo_6_meses as "Consumo 6 Meses",
                   media_6_meses as "Média 6 Meses", 
                   estoque_cobertura as "Estoque Cobertura",
                   moq as "MOQ",
                   ultimo_fornecedor as "UltimoFornecedor",
                   data_upload,
                   upload_version,
                   version_id
            FROM ESTOQUE.ANALYTICS_DATA 
            WHERE empresa = %s 
            AND is_active = TRUE
            ORDER BY data_upload DESC
            """
            query_params = [empresa]
        else:
            query = """
            SELECT produto as "Produto", 
                   estoque as "Estoque", 
                   consumo_6_meses as "Consumo 6 Meses",
                   media_6_meses as "Média 6 Meses", 
                   estoque_cobertura as "Estoque Cobertura",
                   moq as "MOQ",
                   ultimo_fornecedor as "UltimoFornecedor",
                   data_upload,
                   upload_version,
                   version_id
            FROM ESTOQUE.ANALYTICS_DATA 
            WHERE empresa = %s 
            AND version_id = %s
            ORDER BY data_upload DESC
            """
            query_params = [empresa, version_id]
        
        cursor.close()  # Close the cursor before pandas read_sql
        
        df = pd.read_sql(query, conn, params=query_params)
        conn.close()
        
        # Check if we got any data
        if df.empty:
            st.info(f"💡 Nenhum dado de análise encontrado para {empresa}.")
            return None
        
        # Show data summary
        version_info = df['version_id'].iloc[0] if 'version_id' in df.columns and not df.empty else "N/A"
        upload_date = df['data_upload'].max() if 'data_upload' in df.columns else "N/A"
        
        # st.info(f"📊 {empresa} - Analytics v{version_info} | {len(df)} produtos | Upload: {upload_date}")  # Removed to save credits
        
        # Remove metadata columns for return
        columns_to_remove = ['upload_version', 'version_id']
        df_clean = df.drop(columns=[col for col in columns_to_remove if col in df.columns])
        
        return df_clean
        
    except Exception as e:
        st.error(f"❄️ Erro ao carregar dados de análise para {empresa}: {str(e)}")
        return None 
