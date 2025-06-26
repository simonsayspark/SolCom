import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from bd.column_mapping import apply_column_remap

from .analytics_utils import show_executive_summary, calculate_purchase_suggestions, show_purchase_list, show_analytics_dashboard, show_urgent_contacts, show_tabela_geral, show_priority_timeline
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
            from bd.snowflake_config import load_analytics_data
            load_analytics_data.clear()  # Clear specific function cache
            st.success("✅ Cache de análise limpo! Dados atualizados.")
            st.rerun()
    
    # Try to load data from Snowflake first
    try:
        from bd.snowflake_config import load_analytics_data, get_upload_versions
        
        # Get available versions for the selected company
        versions = get_upload_versions(empresa_code, "ANALYTICS", limit=20)
        
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
        df = load_analytics_data(empresa=empresa_code, version_id=selected_version_id)
        
        if df is not None and len(df) > 0:
            version_text = f"v{selected_version_id}" if selected_version_id else "ativa"
            st.success(f"✅ {empresa_selecionada} - Análise {version_text}: {len(df)} produtos carregados")
            
            # # DEBUG: Check if data_upload column exists before accessing it
            # if 'data_upload' in df.columns:
            #     st.info(f"📅 Data do upload: {df['data_upload'].max()}")
            # else:
            #     st.info("📅 Dados de análise carregados da nuvem")
                
            # # DEBUG: Show column mapping info for merged Excel
            # if 'monthly_volume' in df.columns or 'priority_score' in df.columns:
            #     with st.expander("🔍 Mapeamento de Colunas do Merged Excel", expanded=False):
            #         col1, col2 = st.columns(2)
            #         with col1:
            #             st.write("**Colunas Detectadas:**")
            #             if 'Media_6_Meses' in df.columns:
            #                 st.write(f"✅ Media_6_Meses presente ({len(df[df['Media_6_Meses'] > 0])} valores > 0)")
            #             if 'Média 6 Meses' in df.columns:
            #                 st.write(f"✅ Média 6 Meses presente ({len(df[df['Média 6 Meses'] > 0])} valores > 0)")
            #             if 'monthly_volume' in df.columns:
            #                 if 'Média 6 Meses' in df.columns and df['Média 6 Meses'].sum() == 0:
            #                     st.write(f"✅ monthly_volume → Média 6 Meses (fallback)")
            #                 else:
            #                     st.write(f"✅ monthly_volume presente (não usado)")
            #             if 'UltimoFornecedor' in df.columns:
            #                 st.write(f"✅ UltimoFornecedor presente")
            #             if 'preco_unitario' in df.columns:
            #                 st.write(f"✅ preco_unitario presente")
            #             if 'priority_score' in df.columns:
            #                 st.write(f"✅ priority_score presente")
            #         with col2:
            #             st.write("**Valores de Exemplo:**")
            #             if 'monthly_volume' in df.columns:
            #                 st.write(f"monthly_volume: {df['monthly_volume'].head(3).tolist()}")
            #             if 'UltimoFornecedor' in df.columns:
            #                 st.write(f"UltimoFornecedor: {df['UltimoFornecedor'].head(3).tolist()}")
            
            # # DEBUG: Handle merged Excel format - if Média 6 Meses is 0, try monthly_volume
            # if 'Média 6 Meses' in df.columns and 'monthly_volume' in df.columns:
            #     # Check if Média 6 Meses column has all zeros or is empty
            #     media_sum = df['Média 6 Meses'].sum()
            #     valid_media_count = len(df[df['Média 6 Meses'] > 0])
                
            #     # Only use monthly_volume if Média 6 Meses is truly empty/zero
            #     if media_sum == 0 and valid_media_count == 0 and df['monthly_volume'].sum() > 0:
            #         st.info("📊 Detectado formato Merged Excel - usando monthly_volume como consumo mensal")
            #         df['Média 6 Meses'] = df['monthly_volume']
            #     elif valid_media_count > 0:
            #         st.success(f"✅ Usando dados originais de Média 6 Meses ({valid_media_count} produtos com consumo)")
            
            # # DEBUG: Also handle Media_6_Meses (with underscore) mapping to Média 6 Meses (with space)
            # if 'Media_6_Meses' in df.columns and 'Média 6 Meses' not in df.columns:
            #     df['Média 6 Meses'] = df['Media_6_Meses']
            #     st.info("📊 Mapeando Media_6_Meses → Média 6 Meses")
            
            # # DEBUG: Also copy monthly_volume to Consumo 6 Meses if that's empty
            # if 'Consumo 6 Meses' in df.columns and 'monthly_volume' in df.columns:
            #     if df['Consumo 6 Meses'].sum() == 0 and df['monthly_volume'].sum() > 0:
            #         df['Consumo 6 Meses'] = df['monthly_volume']
            
            # # DEBUG: Ensure UltimoFornecedor has proper values (not empty/nan)
            # if 'UltimoFornecedor' in df.columns:
            #     df['UltimoFornecedor'] = df['UltimoFornecedor'].fillna('Brazil')
            #     df.loc[df['UltimoFornecedor'].str.strip() == '', 'UltimoFornecedor'] = 'Brazil'
            #     df.loc[df['UltimoFornecedor'].str.lower() == 'nan', 'UltimoFornecedor'] = 'Brazil'
            
            # # DEBUG: Calculate Estoque Cobertura if missing
            # if 'Estoque Cobertura' not in df.columns:
            #     if 'Estoque' in df.columns and 'Média 6 Meses' in df.columns:
            #         df['Estoque Cobertura'] = df.apply(
            #             lambda row: row['Estoque'] / row['Média 6 Meses'] if row['Média 6 Meses'] > 0 else 999, 
            #             axis=1
            #         )
        
        # else:
        #     st.info(f"💡 Nenhum dado de análise encontrado para {empresa_selecionada}.")
        #     st.markdown("👉 **Vá para 'Upload de Dados' e selecione '📊 Análise de Estoque (Export)' para enviar dados para esta empresa primeiro.**")
        #     df = None
            
    except ImportError:
        st.warning("⚠️ Snowflake não configurado. Usando upload local temporário.")
        df = None
        empresa_code = "MINIPA"  # Default for fallback
    except Exception as e:
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
                numeric_columns = ['Estoque', 'Média 6 Meses', 'Estoque Cobertura', 'Qtde Tot Compras', 'MOQ']
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
                """)
            return

    # Only show analysis if data is loaded (either from Snowflake or local upload)
    if df is not None:
        # Handle different column name formats using shared mapping
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
            'Qtde_Tot_Compras': 'Qtde Tot Compras'
        })
        
        # Handle merged Excel format - if Média 6 Meses is 0, try monthly_volume
        if 'Média 6 Meses' in df_processed.columns and 'monthly_volume' in df_processed.columns:
            # Check if Média 6 Meses column has all zeros or is empty
            media_sum = df_processed['Média 6 Meses'].sum()
            valid_media_count = len(df_processed[df_processed['Média 6 Meses'] > 0])
            
            # Only use monthly_volume if Média 6 Meses is truly empty/zero
            if media_sum == 0 and valid_media_count == 0 and df_processed['monthly_volume'].sum() > 0:
                # st.info("📊 Detectado formato Merged Excel - usando monthly_volume como consumo mensal")  # DEBUG: Commented out
                df_processed['Média 6 Meses'] = df_processed['monthly_volume']
            # elif valid_media_count > 0:
                # st.success(f"✅ Usando dados originais de Média 6 Meses ({valid_media_count} produtos com consumo)")  # DEBUG: Commented out
        
        # Also handle Media_6_Meses (with underscore) mapping to Média 6 Meses (with space)
        if 'Media_6_Meses' in df_processed.columns and 'Média 6 Meses' not in df_processed.columns:
            df_processed['Média 6 Meses'] = df_processed['Media_6_Meses']
            # st.info("📊 Mapeando Media_6_Meses → Média 6 Meses")  # DEBUG: Commented out
        
        # Also copy monthly_volume to Consumo 6 Meses if that's empty
        if 'Consumo 6 Meses' in df_processed.columns and 'monthly_volume' in df_processed.columns:
            if df_processed['Consumo 6 Meses'].sum() == 0 and df_processed['monthly_volume'].sum() > 0:
                df_processed['Consumo 6 Meses'] = df_processed['monthly_volume']
        
        # Ensure UltimoFornecedor has proper values (not empty/nan)
        if 'UltimoFornecedor' in df_processed.columns:
            df_processed['UltimoFornecedor'] = df_processed['UltimoFornecedor'].fillna('Brazil')
            df_processed.loc[df_processed['UltimoFornecedor'].str.strip() == '', 'UltimoFornecedor'] = 'Brazil'
            df_processed.loc[df_processed['UltimoFornecedor'].str.lower() == 'nan', 'UltimoFornecedor'] = 'Brazil'
        
        # Calculate Estoque Cobertura if missing
        if 'Estoque Cobertura' not in df_processed.columns:
            if 'Estoque' in df_processed.columns and 'Média 6 Meses' in df_processed.columns:
                df_processed['Estoque Cobertura'] = df_processed.apply(
                    lambda row: row['Estoque'] / row['Média 6 Meses'] if row['Média 6 Meses'] > 0 else 999, 
                    axis=1
                )
        
        # # DEBUG: Show column mapping info for merged Excel
        # if 'monthly_volume' in df_processed.columns or 'priority_score' in df_processed.columns:
        #     with st.expander("🔍 Mapeamento de Colunas do Merged Excel", expanded=False):
        #         col1, col2 = st.columns(2)
        #         with col1:
        #             st.write("**Colunas Detectadas:**")
        #             if 'Media_6_Meses' in df_processed.columns:
        #                 st.write(f"✅ Media_6_Meses presente ({len(df_processed[df_processed['Media_6_Meses'] > 0])} valores > 0)")
        #             if 'Média 6 Meses' in df_processed.columns:
        #                 st.write(f"✅ Média 6 Meses presente ({len(df_processed[df_processed['Média 6 Meses'] > 0])} valores > 0)")
        #             if 'monthly_volume' in df_processed.columns:
        #                 if 'Média 6 Meses' in df_processed.columns and df_processed['Média 6 Meses'].sum() == 0:
        #                     st.write(f"✅ monthly_volume → Média 6 Meses (fallback)")
        #                 else:
        #                     st.write(f"✅ monthly_volume presente (não usado)")
        #             if 'UltimoFornecedor' in df_processed.columns:
        #                 st.write(f"✅ UltimoFornecedor presente")
        #             if 'preco_unitario' in df_processed.columns:
        #                 st.write(f"✅ preco_unitario presente")
        #             if 'priority_score' in df_processed.columns:
        #                 st.write(f"✅ priority_score presente")
        #         with col2:
        #             st.write("**Valores de Exemplo:**")
        #             if 'monthly_volume' in df_processed.columns:
        #                 st.write(f"monthly_volume: {df_processed['monthly_volume'].head(3).tolist()}")
        #             if 'UltimoFornecedor' in df_processed.columns:
        #                 st.write(f"UltimoFornecedor: {df_processed['UltimoFornecedor'].head(3).tolist()}")
        
        # Use processed dataframe
        df = df_processed
        
        # Separate new and existing products
        produtos_novos = df[(df.get('Estoque', 0) == 0) & (df.get('Média 6 Meses', 0) == 0) & (df.get('Qtde Tot Compras', 0) > 0)]
        produtos_existentes = df[(df.get('Estoque', 0) > 0) | (df.get('Média 6 Meses', 0) > 0)]
        
        # Show company context
        st.info(f"📊 **Análise para {empresa_selecionada}** | Versão: {f'v{selected_version_id}' if 'selected_version_id' in locals() and selected_version_id else 'Ativa'}")
        
        # Show analytics tabs with company context - REDUCED TO 3 TABS
        tab1, tab2, tab3 = st.tabs([
            f"🎯 Timeline Prioritário - {empresa_selecionada}",
            f"📊 Dashboards - {empresa_selecionada}", 
            f"📋 Tabela Geral - {empresa_selecionada}"
        ])
        
        with tab1:
            show_priority_timeline(df, empresa_selecionada)
        
        with tab2:
            show_analytics_dashboard(produtos_existentes, produtos_novos, empresa_selecionada)
            
        with tab3:
            show_tabela_geral(df, empresa_selecionada)

