import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from bd.column_mapping import apply_column_remap

from .analytics_utils import show_executive_summary, calculate_purchase_suggestions, show_purchase_list, show_analytics_dashboard, show_urgent_contacts, show_tabela_geral, show_priority_timeline


def preprocess_analytics_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names and fill missing fields."""
    df_processed = df.copy()
    df_processed, _ = apply_column_remap(df_processed)
    df_processed = df_processed.rename(columns={
        'Consumo_6_Meses': 'Consumo 6 Meses',
        'Media_6_Meses': 'Média 6 Meses',
        'Estoque_Cobertura': 'Estoque Cobertura',
        'ultimo_fornecedor': 'UltimoFornecedor',
        'Preco_Unitario': 'preco_unitario',
        'Qtde_Embarque': 'Qtde Embarque',
        'Compras_Ate_30_Dias': 'Compras Até 30 Dias',
        'Compras_31_60_Dias': 'Compras 31 a 60 Dias',
        'Compras_61_90_Dias': 'Compras 61 a 90 Dias',
        'Compras_Mais_90_Dias': 'Compras > 90 Dias',
        'Qtde_Tot_Compras': 'Qtde Tot Compras',
        'carteira': 'Carteira'
    })

    if 'Média 6 Meses' in df_processed.columns and 'monthly_volume' in df_processed.columns:
        media_sum = df_processed['Média 6 Meses'].sum()
        valid_media_count = len(df_processed[df_processed['Média 6 Meses'] > 0])
        if media_sum == 0 and valid_media_count == 0 and df_processed['monthly_volume'].sum() > 0:
            df_processed['Média 6 Meses'] = df_processed['monthly_volume']

    if 'Media_6_Meses' in df_processed.columns and 'Média 6 Meses' not in df_processed.columns:
        df_processed['Média 6 Meses'] = df_processed['Media_6_Meses']

    if 'Consumo 6 Meses' in df_processed.columns and 'monthly_volume' in df_processed.columns:
        if df_processed['Consumo 6 Meses'].sum() == 0 and df_processed['monthly_volume'].sum() > 0:
            df_processed['Consumo 6 Meses'] = df_processed['monthly_volume']

    if 'UltimoFornecedor' in df_processed.columns:
        df_processed['UltimoFornecedor'] = df_processed['UltimoFornecedor'].fillna('Brazil')
        df_processed.loc[df_processed['UltimoFornecedor'].str.strip() == '', 'UltimoFornecedor'] = 'Brazil'
        df_processed.loc[df_processed['UltimoFornecedor'].str.lower() == 'nan', 'UltimoFornecedor'] = 'Brazil'
    
    # Ensure Carteira is numeric if present (allow negative values as requested)
    if 'Carteira' in df_processed.columns:
        df_processed['Carteira'] = pd.to_numeric(df_processed['Carteira'], errors='coerce').fillna(0)
        # Note: Allow negative values as they represent orders that exceed current stock
    else:
        # Add Carteira column with default 0 if not present
        df_processed['Carteira'] = 0

    if 'Estoque Cobertura' not in df_processed.columns:
        if 'Estoque' in df_processed.columns and 'Média 6 Meses' in df_processed.columns:
            df_processed['Estoque Cobertura'] = df_processed.apply(
                lambda row: row['Estoque'] / row['Média 6 Meses'] if row['Média 6 Meses'] > 0 else 999,
                axis=1
            )

    return df_processed

def load_page():
    """Análise avançada de dados Excel - Sistema Multi-Empresa de Gestão de Estoque"""
    
    # Header with company selector
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title("📊 Análise de Estoque Multi-Empresa")
      
    
    with col2:
        # Company selector
        empresa_selecionada = st.selectbox(
            "🏢 Empresa:",
            ["MINIPA", "MINIPA INDUSTRIA"],
            key="empresa_selector_analytics",
            help="Selecione a empresa para visualizar os dados de análise"
        )
        empresa_code = "MINIPA" if empresa_selecionada == "MINIPA" else "MINIPA_INDUSTRIA"
        
        # Store in session state for persistence
        st.session_state.current_empresa = empresa_code
    
    with col3:
        if st.button("🔄 Atualizar Dados", 
                    help="Atualizar dados do Snowflake (normalmente cache por 7 dias)",
                    use_container_width=True,
                    key="analytics_refresh"):
            from bd.snowflake_config import load_analytics_data, get_upload_versions
            from bd.snowflake_analytics_dashboard import get_cached_analytics_page_data
            load_analytics_data.clear()  # Clear old function cache
            get_cached_analytics_page_data.clear()  # Clear new function cache
            get_upload_versions.clear()  # Clear version cache
            st.success("✅ Cache de análise limpo! Dados atualizados.")
            st.rerun()
    
    # DEBUG: Add debugging information
    st.write("🔍 **DEBUG - Analytics Page Loading**")
    st.write(f"Empresa selecionada: {empresa_selecionada}")
    st.write(f"Empresa code: {empresa_code}")
    
    # Try to load data from Snowflake first
    try:
        from bd.snowflake_config import load_analytics_data, get_upload_versions
        from bd.snowflake_analytics_dashboard import get_cached_analytics_page_data
        
        st.write("🔍 DEBUG: Importing Snowflake functions - SUCCESS")
        
        # Get ALL data in ONE connection - versions and analytics data
        st.write("🔍 DEBUG: Calling get_cached_analytics_page_data...")
        initial_data = get_cached_analytics_page_data(empresa_code)
        st.write(f"🔍 DEBUG: Initial data keys: {list(initial_data.keys()) if initial_data else 'None'}")
        
        versions = initial_data['versions'] if initial_data else []
        st.write(f"🔍 DEBUG: Found {len(versions)} versions")
        
        # Version selector with custom names and filenames
        if versions:
            st.subheader(f"📦 Seleção de Versão - {empresa_selecionada}")
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Create version options with custom names and filenames
                version_options = ["Versão Ativa (mais recente)"]
                version_mapping = {0: None}  # 0 = active version
                
                for i, v in enumerate(versions):
                    display_name = v.get('description', '').strip()
                    if not display_name:
                        display_name = f"Versão {v['version_id']}"
                    
                    filename_info = f" - 📁 {v.get('arquivo_origem', 'N/A')}" if v.get('arquivo_origem') else ""
                    option_text = f"{display_name} ({v['upload_date']}){filename_info}"
                    
                    version_options.append(option_text)
                    version_mapping[i + 1] = v['version_id']
                
                selected_option = st.selectbox(
                    "Escolha a versão dos dados:",
                    options=range(len(version_options)),
                    format_func=lambda x: version_options[x],
                    help="Selecione uma versão específica ou use a versão ativa"
                )
                
                selected_version_id = version_mapping[selected_option]
                st.write(f"🔍 DEBUG: Selected version ID: {selected_version_id}")
                
                if selected_version_id:
                    st.info(f"📊 Carregando versão específica: {version_options[selected_option]}")
                else:
                    st.info("📊 Carregando versão ativa (mais recente)")
            
            with col2:
                st.metric("📊 Versões Disponíveis", len(versions))
                active_versions = len([v for v in versions if v['is_active']])
                st.metric("🟢 Versão Ativa", f"{active_versions}/1")
        else:
            selected_version_id = None
            st.info(f"💡 Nenhuma versão de análise encontrada para {empresa_selecionada}")
        
        # Load data with company and version selection
        st.write("🔍 DEBUG: Loading analytics data...")
        # If we need a different version than the initial load, get it
        if (selected_version_id is not None) or (initial_data.get('analytics_data') is None):
            # We need to reload with specific version
            st.write(f"🔍 DEBUG: Reloading with version {selected_version_id}")
            analytics_data = get_cached_analytics_page_data(empresa_code, selected_version_id)
            df = analytics_data['analytics_data'] if analytics_data else None
        else:
            # Use the data we already loaded
            st.write("🔍 DEBUG: Using initial data")
            df = initial_data['analytics_data'] if initial_data else None
        
        st.write(f"🔍 DEBUG: DataFrame loaded: {df is not None}")
        if df is not None:
            st.write(f"🔍 DEBUG: DataFrame shape: {df.shape}")
            st.write(f"🔍 DEBUG: DataFrame columns: {list(df.columns)}")
        else:
            # Deep debug when dataframe is None: run direct Snowflake checks
            try:
                from bd.snowflake_connection import get_snowflake_connection
                conn_dbg = get_snowflake_connection()
                if conn_dbg:
                    cur_dbg = conn_dbg.cursor()
                    # Count rows for the selected version
                    if selected_version_id is not None:
                        cur_dbg.execute("SELECT COUNT(*) FROM ESTOQUE.ANALYTICS_DATA WHERE empresa = %s AND version_id = %s", (empresa_code, selected_version_id))
                    else:
                        cur_dbg.execute("SELECT COUNT(*) FROM ESTOQUE.ANALYTICS_DATA WHERE empresa = %s AND is_active = TRUE", (empresa_code,))
                    count_rows = cur_dbg.fetchone()[0]
                    st.write(f"🔍 DEBUG: Row count for selection: {count_rows}")
                    # Show 3 sample column names by describing table
                    cur_dbg.execute("DESCRIBE TABLE ESTOQUE.ANALYTICS_DATA")
                    cols = [r[0] for r in cur_dbg.fetchall()]
                    st.write(f"🔍 DEBUG: Table columns (first 15): {cols[:15]}")
                    # Fetch a small sample to see data presence
                    sample_sql = "SELECT produto, estoque, media_6_meses, version_id FROM ESTOQUE.ANALYTICS_DATA WHERE empresa = %s "
                    if selected_version_id is not None:
                        sample_sql += "AND version_id = %s ORDER BY produto LIMIT 5"
                        cur_dbg.execute(sample_sql, (empresa_code, selected_version_id))
                    else:
                        sample_sql += "AND is_active = TRUE ORDER BY produto LIMIT 5"
                        cur_dbg.execute(sample_sql, (empresa_code,))
                    sample = cur_dbg.fetchall()
                    st.write(f"🔍 DEBUG: Sample rows: {sample}")
                    cur_dbg.close()
                    conn_dbg.close()
            except Exception as deep_dbg_e:
                st.write(f"🔍 DEBUG: Deep check failed: {str(deep_dbg_e)}")
        
        if df is not None and len(df) > 0:
            version_text = f"v{selected_version_id}" if selected_version_id else "ativa"
            st.success(f"✅ {len(df)} produtos carregados")
            
    except ImportError as ie:
        st.error(f"🔍 DEBUG: Import error: {str(ie)}")
        st.warning("⚠️ Snowflake não configurado. Usando upload local temporário.")
        df = None
        empresa_code = "MINIPA"  # Default for fallback
    except Exception as e:
        st.error(f"🔍 DEBUG: Exception during data loading: {str(e)}")
        import traceback
        st.text(traceback.format_exc())
        st.error(f"❌ Erro ao carregar dados de análise para {empresa_selecionada}: {str(e)}")
        df = None

    # Fallback to local upload if no cloud data
    if df is None:
        st.subheader("📁 Upload Local (Temporário)")
        st.markdown("⚠️ **Este upload é temporário. Para salvar na nuvem, use 'Upload de Dados' → 'Análise de Estoque'**")
        
        uploaded_file = st.file_uploader(
            "Faça upload do arquivo Excel (.xlsx)",
            type=['xlsx'],
            help="Arquivo deve conter planilha 'Export' com colunas: Produto, Estoque, Média 6 Meses, Estoque Cobertura, MOQ, UltimoFor"
        )
        
        if uploaded_file is not None:
            try:
                # Read the Excel file
                df = pd.read_excel(uploaded_file, sheet_name='Export')
                
                # Clean data
                df = df.dropna(subset=['Produto'])
                df = df[df['Produto'] != 'nan']
                df = df[~df['Produto'].str.contains('Filtros aplicados', na=False)]
                
                # Convert numeric columns
                numeric_columns = ['Estoque', 'Média 6 Meses', 'Estoque Cobertura', 'Qtde Tot Compras', 'MOQ', 'Carteira']
                for col in numeric_columns:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
                # Handle supplier column - fill empty values with Brazil
                if 'UltimoFornecedor' in df.columns:
                    df['UltimoFornecedor'] = df['UltimoFornecedor'].fillna('Brazil')
                    df.loc[df['UltimoFornecedor'].str.strip() == '', 'UltimoFornecedor'] = 'Brazil'
                
                st.success(f"✅ Dados carregados: {len(df)} produtos")
                
            except Exception as e:
                st.error(f"❌ Erro ao processar arquivo: {str(e)}")
                st.info("💡 Certifique-se de que o arquivo contém uma planilha 'Export' com as colunas necessárias")
                return
        else:
            st.info("📁 Faça upload de um arquivo Excel para análise local ou use os dados da nuvem")
            
            # Show sample format
            with st.expander("📋 Formato esperado do arquivo"):
                st.markdown("""
                **Planilha: 'Export'**
                
                Colunas necessárias:
                - `Produto`: Nome do produto
                - `Estoque`: Quantidade atual em estoque
                - `Média 6 Meses`: Consumo médio mensal
                - `Estoque Cobertura`: Cobertura em meses
                - `MOQ`: Quantidade mínima de pedido
                - `UltimoFor`: Último fornecedor (deixe vazio para 'Brazil')
                - `Qtde Tot Compras`: Quantidade total para compras (opcional)
                - `Carteira`: Pedidos já feitos (opcional)
                """)
            return

    # Only show analysis if data is loaded (either from Snowflake or local upload)
    if df is not None:
        st.write("🔍 DEBUG: Processing dataframe...")
        # Preprocess dataframe with caching to avoid recomputation
        df_processed = preprocess_analytics_dataframe(df)
        
        # Preprocessing already handles column normalization and coverage calculations
        
        # Use processed dataframe
        df = df_processed
        
        # Separate new and existing products
        produtos_novos = df[(df.get('Estoque', 0) == 0) & (df.get('Média 6 Meses', 0) == 0) & (df.get('Qtde Tot Compras', 0) > 0)]
        produtos_existentes = df[(df.get('Estoque', 0) > 0) | (df.get('Média 6 Meses', 0) > 0)]
        
        st.write(f"🔍 DEBUG: Produtos novos: {len(produtos_novos)}, Produtos existentes: {len(produtos_existentes)}")
        
        # Show company context
        st.info(f"📊 **Análise para {empresa_selecionada}** | Versão: {f'v{selected_version_id}' if 'selected_version_id' in locals() and selected_version_id else 'Ativa'}")
        
        # Show analytics tabs with company context - BACK TO 3 TABS
        tab1, tab2, tab3 = st.tabs([
            f"🎯 Timeline Prioritário - {empresa_selecionada}",
            f"📊 Dashboards - {empresa_selecionada}", 
            f"📋 Tabela Geral - {empresa_selecionada}"
        ])
        
        with tab1:
            try:
                # Pass CBM data from our initial load (if available)
                cbm_data = initial_data.get('timeline_cbm_data', {}) if 'initial_data' in locals() else {}
                if not cbm_data and 'analytics_data' in locals():
                    cbm_data = analytics_data.get('timeline_cbm_data', {})
                
                # Store CBM data in session state to be used by analytics_utils
                st.session_state['cbm_data'] = cbm_data
                
                show_priority_timeline(df, empresa_selecionada)
            except Exception as e:
                st.error(f"❌ Erro no Timeline Prioritário: {str(e)}")
                import traceback
                st.text(traceback.format_exc())
        
        with tab2:
            show_analytics_dashboard(produtos_existentes, produtos_novos, empresa_selecionada)
            
        with tab3:
            show_tabela_geral(df, empresa_selecionada)
    else:
        st.warning("🔍 DEBUG: No data loaded - showing upload option only")
