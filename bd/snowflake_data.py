"""
Snowflake Data Loading
Handles data loading with caching for timeline and analytics data
"""

import streamlit as st
import pandas as pd
from .snowflake_connection import get_snowflake_connection

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
        
        # Check if table has new structure (empresa column)
        has_empresa_column = False
        try:
            cursor.execute("DESCRIBE TABLE ESTOQUE.PRODUTOS")
            columns = cursor.fetchall()
            column_names = [col[0].upper() for col in columns]
            has_empresa_column = 'EMPRESA' in column_names
        except:
            st.warning("⚠️ Tabela PRODUTOS não encontrada")
            cursor.close()
            conn.close()
            return None
        
        if not has_empresa_column:
            # Old structure - load all data as MINIPA
            st.warning("⚠️ Estrutura antiga detectada. Para multi-empresa, execute a migração.")
            
            if empresa != "MINIPA":
                st.info(f"💡 Nenhum dado para {empresa} na estrutura antiga.")
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
                    st.info(f"📅 Estrutura antiga - {len(df)} produtos carregados como MINIPA")
                
                return df
                
            except Exception as old_query_error:
                st.error(f"❌ Erro na estrutura antiga: {str(old_query_error)}")
                cursor.close()
                conn.close()
                return None
        
        # New multi-company structure
        # Determine which version to load
        if version_id is None:
            st.info(f"📊 Carregando versão ativa para {empresa}")
            version_params = [empresa, 'TIMELINE']
        else:
            st.info(f"📊 Carregando versão {version_id} para {empresa}")
            version_params = [empresa, 'TIMELINE', version_id]
        
        # Check if the table exists and has data for this company
        try:
            if version_id is None:
                cursor.execute("""
                SELECT COUNT(*) FROM ESTOQUE.PRODUTOS 
                WHERE empresa = %s AND table_type = %s AND is_active = TRUE
                """, version_params)
            else:
                cursor.execute("""
                SELECT COUNT(*) FROM ESTOQUE.PRODUTOS 
                WHERE empresa = %s AND table_type = %s AND version_id = %s
                """, version_params)
            
            total_records = cursor.fetchone()[0]
            
        except Exception as table_error:
            st.warning(f"⚠️ Erro ao verificar dados para {empresa}: {str(table_error)}")
            cursor.close()
            conn.close()
            return None
        
        if total_records == 0:
            st.info(f"💡 Nenhum dado de timeline encontrado para {empresa}. Faça um upload primeiro.")
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
            st.info(f"💡 Nenhum dado encontrado para {empresa}.")
            return None
        
        # Show data summary
        version_info = df['version_id'].iloc[0] if 'version_id' in df.columns and not df.empty else "N/A"
        upload_date = df['data_upload'].max() if 'data_upload' in df.columns else "N/A"
        
        st.info(f"📅 {empresa} - Timeline v{version_info} | {len(df)} produtos | Upload: {upload_date}")
        
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
        
        # Check if analytics table exists and has new structure
        has_empresa_column = False
        table_exists = False
        try:
            cursor.execute("DESCRIBE TABLE ESTOQUE.ANALYTICS_DATA")
            columns = cursor.fetchall()
            column_names = [col[0].upper() for col in columns]
            has_empresa_column = 'EMPRESA' in column_names
            table_exists = True
        except:
            # Table doesn't exist yet
            st.info("💡 Tabela de analytics não existe ainda. Faça upload de dados de análise primeiro.")
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
            st.info(f"📊 Carregando análise ativa para {empresa}")
            version_params = [empresa]
        else:
            st.info(f"📊 Carregando análise v{version_id} para {empresa}")
            version_params = [empresa, version_id]
        
        # Check if the analytics table exists and has data for this company
        try:
            if version_id is None:
                cursor.execute("""
                SELECT COUNT(*) FROM ESTOQUE.ANALYTICS_DATA 
                WHERE empresa = %s AND is_active = TRUE
                """, version_params)
            else:
                cursor.execute("""
                SELECT COUNT(*) FROM ESTOQUE.ANALYTICS_DATA 
                WHERE empresa = %s AND version_id = %s
                """, version_params)
            
            total_records = cursor.fetchone()[0]
            
            if total_records == 0:
                st.info(f"💡 Nenhum dado de análise encontrado para {empresa}. Faça upload de um arquivo de análise primeiro.")
                cursor.close()
                conn.close()
                return None
                
        except Exception as table_error:
            # Table doesn't exist yet
            st.warning(f"⚠️ Erro ao verificar dados de análise para {empresa}: {str(table_error)}")
            st.info("💡 A tabela será criada automaticamente no primeiro upload de análise.")
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
        
        st.info(f"📊 {empresa} - Analytics v{version_info} | {len(df)} produtos | Upload: {upload_date}")
        
        # Remove metadata columns for return
        columns_to_remove = ['upload_version', 'version_id']
        df_clean = df.drop(columns=[col for col in columns_to_remove if col in df.columns])
        
        return df_clean
        
    except Exception as e:
        st.error(f"❄️ Erro ao carregar dados de análise para {empresa}: {str(e)}")
        return None 