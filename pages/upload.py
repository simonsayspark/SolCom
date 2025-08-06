import streamlit as st
import pandas as pd
from datetime import datetime
from bd.column_mapping import apply_column_remap

def analyze_and_process_excel(uploaded_file, file_type="Auto-detectar"):
    """Advanced Excel analysis and processing based on actual user table structure"""
    try:
        # Read the Excel file to understand structure
        xl_file = pd.ExcelFile(uploaded_file)
        sheets = xl_file.sheet_names
        
        st.info(f"📋 Planilhas encontradas: {sheets}")
        
        # Try different sheets and header positions
        best_sheet = None
        best_header_row = 0
        best_df = None
        best_score = 0
        
        # Try different starting rows to find headers - expanded range
        for sheet in sheets[:5]:  # Check first 5 sheets
            for header_row in [0, 8, 9, 10, 7, 6, 11, 12]:
                try:
                    df_sample = pd.read_excel(uploaded_file, sheet_name=sheet, header=header_row, nrows=20)
                    
                    # Check if we found real headers (not None or Unnamed)
                    valid_columns = 0
                    real_headers = []
                    
                    for col in df_sample.columns:
                        col_str = str(col).strip()
                        if (col_str != 'None' and 
                            not col_str.startswith('Unnamed') and 
                            col_str != 'nan' and
                            len(col_str) > 0):
                            valid_columns += 1
                            real_headers.append(col_str)
                    
                    # Score this attempt
                    data_rows = len(df_sample.dropna(how='all'))
                    score = valid_columns * data_rows
                    
                    if score > best_score and valid_columns >= 3 and data_rows >= 3:
                        best_score = score
                        best_sheet = sheet
                        best_header_row = header_row
                        best_df = df_sample
                        
                except Exception as e:
                    continue
        
        if best_df is not None:
            # Load the full dataset
            df_full = pd.read_excel(uploaded_file, sheet_name=best_sheet, header=best_header_row)
            df_full = df_full.dropna(how='all')  # Remove completely empty rows
            
            # 🔧 CRITICAL FIX: Apply column renaming BEFORE upload to fix zero prices issue
            st.info("🔄 Padronizando nomes das colunas...")
            
            original_columns = list(df_full.columns)
            df_full, change_pairs = apply_column_remap(df_full)
            renamed_columns = list(df_full.columns)

            changes_made = [f"'{old}' → '{new}'" for old, new in change_pairs]
            
            if changes_made:
                st.success(f"✅ Colunas padronizadas: {len(changes_made)} alterações")
                with st.expander("📋 Ver alterações nas colunas"):
                    for change in changes_made:
                        st.write(f"• {change}")
                        
                # Show critical price column fix
                if any('Preco_Unitario' in change for change in changes_made):
                    st.success("🔧 **CORREÇÃO CRÍTICA**: Coluna de preços padronizada - isso deve resolver o problema de preços zero!")
                
                # 🔧 DEBUG: Check if Previsão Total column was processed
                # Commented out to reduce debug spam
                # previsao_changes = [change for change in changes_made if 'Previsao_Total_New_Pos' in change or 'Previsao' in change]
                # if previsao_changes:
                #     st.success("🔧 **PREVISÃO TOTAL ENCONTRADA**: " + previsao_changes[0])
                # else:
                #     st.warning("⚠️ **PREVISÃO TOTAL NÃO ENCONTRADA** - Verifique se a coluna existe no Excel")
                #     
                #     # Show available columns that might be Previsão Total
                #     previsao_candidates = [col for col in original_columns if 'previs' in col.lower() or 'total' in col.lower()]
                #     if previsao_candidates:
                #         st.info(f"🔍 Colunas candidatas encontradas: {', '.join(previsao_candidates)}")
                #     
                #     # Show exact column names for debugging
                #     st.info(f"📋 Todas as colunas originais: {', '.join(original_columns[:10])}{'...' if len(original_columns) > 10 else ''}")
            
            # 🔧 NEW: Detect if this is a merged Excel file with priority analysis
            priority_columns = ['priority_score', 'criticality', 'relevance_class', 'preco_unitario']
            has_priority_data = any(col in df_full.columns for col in priority_columns)
            
            if has_priority_data:
                st.success("🎯 **MERGED EXCEL DETECTADO**: Este arquivo contém dados de análise prioritária!")
                detected_priority_cols = [col for col in priority_columns if col in df_full.columns]
                st.info(f"📊 Colunas de prioridade encontradas: {', '.join(detected_priority_cols)}")
            else:
                st.info("📊 **EXCEL PADRÃO**: Dados básicos de estoque detectados")
            
            st.success(f"✅ Detectado automaticamente: planilha '{best_sheet}', linha {best_header_row + 1}")
            return df_full, best_sheet, best_header_row
        else:
            st.warning("⚠️ Detecção automática falhou. Usando primeira planilha, linha 1.")
            df_full = pd.read_excel(uploaded_file, sheet_name=sheets[0], header=0)
            return df_full, sheets[0], 0
                        
    except Exception as e:
        st.error(f"❌ Erro ao analisar Excel: {str(e)}")
        return None, None, 0

def show_data_upload():
    """Upload functionality for multi-company data"""
    st.header("📁 Central de Upload de Dados Multi-Empresa")
    st.markdown("**Upload seus arquivos Excel aqui. Os dados serão salvos na nuvem com controle de versão para cada empresa.**")
    
    # Import Snowflake functions
    try:
        from bd.snowflake_config import (upload_excel_to_snowflake, load_data_with_history, 
                                        load_analytics_data, test_connection, get_upload_versions, 
                                        delete_version, fix_active_versions)
        from bd.snowflake_upload_dashboard import get_cached_upload_page_data
        from bd.snowflake_upload_optimized import upload_excel_to_snowflake_optimized
        snowflake_available = True
    except ImportError:
        snowflake_available = False
    
    # Company selection
    st.subheader("🏢 Seleção da Empresa")
    col1, col2 = st.columns(2)
    
    with col1:
        empresa_selecionada = st.radio(
            "Selecione a empresa:",
            ["🏢 MINIPA", "🏭 MINIPA INDUSTRIA"],
            index=0
        )
        empresa_code = "MINIPA" if empresa_selecionada == "🏢 MINIPA" else "MINIPA_INDUSTRIA"
    
    with col2:
        st.info(f"""
        **Empresa Selecionada:** {empresa_selecionada}
        
        📊 **Isolamento de Dados:**
        - Cada empresa tem seus próprios dados
        - Controle de versão independente  
        - Histórico completo por empresa
        """)
    
    # Show current data status
    if snowflake_available:
        st.subheader(f"📊 Status dos Dados - {empresa_selecionada}")
        
        # Get ALL data in ONE Snowflake connection call
        dashboard_data = get_cached_upload_page_data(empresa_code)
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Show timeline data
            timeline_stats = dashboard_data['stats']['timeline']
            timeline_count = timeline_stats.get('count', 0)
            
            if timeline_count > 0:
                st.success(f"📅 Timeline: {timeline_count} produtos salvos")
                if timeline_stats.get('latest_upload'):
                    st.info(f"🕒 Último upload Timeline: {timeline_stats['latest_upload']}")
                st.info(f"🏭 Fornecedores: {timeline_stats.get('suppliers', 0)}")
            else:
                st.info("📅 Timeline: Nenhum dado encontrado")
            
            # Show analytics data
            analytics_stats = dashboard_data['stats']['analytics']
            analytics_count = analytics_stats.get('count', 0)
            
            if analytics_count > 0:
                st.success(f"📊 Analytics: {analytics_count} produtos salvos")
                if analytics_stats.get('latest_upload'):
                    st.info(f"🕒 Último upload Analytics: {analytics_stats['latest_upload']}")
                st.info(f"🏭 Fornecedores: {analytics_stats.get('suppliers', 0)}")
            else:
                st.info("📊 Analytics: Nenhum dado encontrado")
            
            # Show version history with delete options
            with st.expander(f"📋 Histórico de Versões - {empresa_selecionada}", expanded=True):
                try:
                    # Use the data we already fetched
                    versions_timeline = dashboard_data['versions_timeline']
                    versions_analytics = dashboard_data['versions_analytics']
                    
                    if versions_timeline:
                        st.write("**📅 Timeline de Compras:**")
                        for i, v in enumerate(versions_timeline[:5]):
                            status_icon = "🟢" if v['is_active'] else "⚪"
                            
                            # Use custom description or fallback to version number
                            display_name = v.get('description', '').strip()
                            if not display_name:
                                display_name = f"Versão {v['version_id']}"
                            
                            # Show filename if available
                            filename_info = f" - 📁 {v.get('arquivo_origem', 'N/A')}" if v.get('arquivo_origem') else ""
                            
                            # Create a container for each version
                            version_container = st.container()
                            with version_container:
                                col1, col2 = st.columns([4, 1])
                                with col1:
                                    st.write(f"{status_icon} **{display_name}** - {v['upload_date']}{filename_info}")
                                with col2:
                                    if not v['is_active']:  # Can't delete active version
                                        delete_button = st.button("🗑️ Deletar", 
                                                                 key=f"del_timeline_{v['version_id']}_{i}", 
                                                                 help="Deletar esta versão",
                                                                 type="secondary",
                                                                 use_container_width=True)
                                        if delete_button:
                                            st.session_state[f"confirm_delete_timeline_{v['version_id']}"] = True
                                            st.rerun()
                                    else:
                                        st.write("🔒 **Ativa**")
                                
                                # Show confirmation dialog
                                if st.session_state.get(f"confirm_delete_timeline_{v['version_id']}", False):
                                    st.error(f"⚠️ **CONFIRMAR EXCLUSÃO:** {display_name}")
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        if st.button("✅ SIM, DELETAR", 
                                                    key=f"confirm_del_timeline_{v['version_id']}",
                                                    type="primary",
                                                    use_container_width=True):
                                            # Use the consolidated function for deletion
                                            delete_data = get_cached_upload_page_data(
                                                empresa_code,
                                                delete_version_id=v['version_id'],
                                                delete_table_type="TIMELINE"
                                            )
                                            if delete_data['delete_result'] and delete_data['delete_result']['success']:
                                                st.success(f"✅ {display_name} deletada!")
                                                get_cached_upload_page_data.clear()  # Clear cache
                                                st.session_state[f"confirm_delete_timeline_{v['version_id']}"] = False
                                                st.rerun()
                                            else:
                                                st.error("❌ Falha ao deletar versão")
                                    with col2:
                                        if st.button("❌ Cancelar", 
                                                    key=f"cancel_del_timeline_{v['version_id']}",
                                                    use_container_width=True):
                                            st.session_state[f"confirm_delete_timeline_{v['version_id']}"] = False
                                            st.rerun()
                                
                                st.divider()  # Visual separator between versions
                    
                    if versions_analytics:
                        st.write("**📊 Análise de Estoque:**")
                        for i, v in enumerate(versions_analytics[:5]):
                            status_icon = "🟢" if v['is_active'] else "⚪"
                            
                            # Use custom description or fallback to version number
                            display_name = v.get('description', '').strip()
                            if not display_name:
                                display_name = f"Versão {v['version_id']}"
                            
                            # Show filename if available
                            filename_info = f" - 📁 {v.get('arquivo_origem', 'N/A')}" if v.get('arquivo_origem') else ""
                            
                            # Create a container for each version
                            version_container = st.container()
                            with version_container:
                                col1, col2 = st.columns([4, 1])
                                with col1:
                                    st.write(f"{status_icon} **{display_name}** - {v['upload_date']}{filename_info}")
                                with col2:
                                    if not v['is_active']:  # Can't delete active version
                                        delete_button = st.button("🗑️ Deletar", 
                                                                 key=f"del_analytics_{v['version_id']}_{i}", 
                                                                 help="Deletar esta versão",
                                                                 type="secondary",
                                                                 use_container_width=True)
                                        if delete_button:
                                            st.session_state[f"confirm_delete_analytics_{v['version_id']}"] = True
                                            st.rerun()
                                    else:
                                        st.write("🔒 **Ativa**")
                                
                                # Show confirmation dialog
                                if st.session_state.get(f"confirm_delete_analytics_{v['version_id']}", False):
                                    st.error(f"⚠️ **CONFIRMAR EXCLUSÃO:** {display_name}")
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        if st.button("✅ SIM, DELETAR", 
                                                    key=f"confirm_del_analytics_{v['version_id']}",
                                                    type="primary",
                                                    use_container_width=True):
                                            # Use the consolidated function for deletion
                                            delete_data = get_cached_upload_page_data(
                                                empresa_code,
                                                delete_version_id=v['version_id'],
                                                delete_table_type="ANALYTICS"
                                            )
                                            if delete_data['delete_result'] and delete_data['delete_result']['success']:
                                                st.success(f"✅ {display_name} deletada!")
                                                get_cached_upload_page_data.clear()  # Clear cache
                                                st.session_state[f"confirm_delete_analytics_{v['version_id']}"] = False
                                                st.rerun()
                                            else:
                                                st.error("❌ Falha ao deletar versão")
                                    with col2:
                                        if st.button("❌ Cancelar", 
                                                    key=f"cancel_del_analytics_{v['version_id']}",
                                                    use_container_width=True):
                                            st.session_state[f"confirm_delete_analytics_{v['version_id']}"] = False
                                            st.rerun()
                                
                                st.divider()  # Visual separator between versions
                    
                    if not versions_timeline and not versions_analytics:
                        st.info("Nenhuma versão encontrada. Faça seu primeiro upload!")
                except Exception as e:
                    st.warning(f"Erro ao carregar versões: {str(e)}")
        
        with col2:
            st.info("🔗 Snowflake (monitoring disabled)")
            
            # Add database migration button
            if st.button("🔄 Migração do BD", 
                        use_container_width=True,
                        help="Atualiza o banco de dados para suportar Excel merged com análise de prioridade"):
                try:
                    from bd.snowflake_migration import migrate_to_merged_excel_support
                    with st.spinner("🔄 Executando migração do banco de dados..."):
                        if migrate_to_merged_excel_support():
                            st.success("✅ Migração concluída! O banco agora suporta dados merged Excel.")
                            st.info("💡 Agora você pode fazer upload de arquivos Excel merged com análise de prioridade.")
                        else:
                            st.error("❌ Erro na migração do banco de dados")
                except ImportError:
                    st.error("❌ Módulo de migração não disponível")
                except Exception as e:
                    st.error(f"❌ Erro na migração: {str(e)}")
            
            # Add repair button for version issues
            if st.button("🔧 Reparar Versões", 
                        use_container_width=True,
                        help="Corrige o status 'ativa' das versões - use se todas as versões aparecem como ativas"):
                with st.spinner("🔧 Reparando status das versões..."):
                    # Use the consolidated function for repair
                    repair_data = get_cached_upload_page_data(
                        empresa_code,
                        repair_versions=True
                    )
                    if repair_data['repair_result'] and repair_data['repair_result']['success']:
                        st.success(f"✅ Versões reparadas! {repair_data['repair_result']['fixed_count']} combinações corrigidas.")
                        # Clear the cache to show updated data
                        get_cached_upload_page_data.clear()
                        get_upload_versions.clear()
                        st.rerun()
                    else:
                        st.error("❌ Erro ao reparar versões")
    
    # File upload section
    st.subheader(f"📤 Upload de Arquivo - {empresa_selecionada}")
    
    # Create two distinct upload options
    upload_type = st.radio(
        "📋 Selecione o tipo de dados:",
        ["📊 Análise de Estoque com Prioridades (Merged Excel)", "📅 Timeline de Compras (MOQ/Fornecedores)", "📊 Análise de Estoque (Export)"],
        help="Escolha o tipo correto para que os dados sejam processados adequadamente"
    )
    
    # Version description
    st.subheader("📝 Descrição da Versão")
    version_description = st.text_input(
        "Descrição desta versão (opcional):",
        placeholder="Ex: Atualização de preços Q4 2024, Novos fornecedores, etc.",
        help="Adicione uma descrição para identificar facilmente esta versão"
    )
    
    if upload_type == "📊 Análise de Estoque com Prioridades (Merged Excel)":
        st.info("""
        🎯 **Para Análise com Prioridades:** Upload de Excel que já passou pelo processo de merge e priority analysis
        - Colunas esperadas: Produto, Estoque, Média 6 Meses, preco_unitario, priority_score, criticality, etc.
        - Este formato é gerado pelos scripts do Test folder (data_merger.py + priority_analysis.py)
        """)
        table_prefix = "ANALYTICS"
        uploaded_file = st.file_uploader(
            "📁 Arquivo Excel Merged com Prioridades",
            type=['xlsx', 'xls'],
            help="Arquivo que já passou pelo data merger e priority analysis",
            key="merged_upload"
        )
    elif upload_type == "📅 Timeline de Compras (MOQ/Fornecedores)":
        st.info("📝 **Para Timeline:** Upload com colunas Item, Fornecedor, QTD, Modelo, Preço FOB, MOQ, etc.")
        table_prefix = "TIMELINE"
        uploaded_file = st.file_uploader(
            "📁 Arquivo Excel para Timeline de Compras",
            type=['xlsx', 'xls'],
            help="Arquivo com dados de fornecedores, MOQ, preços FOB, etc.",
            key="timeline_upload"
        )
    else:
        st.info("📊 **Para Análise:** Upload com colunas Produto, Estoque, Média 6 Meses, Estoque Cobertura, etc.")
        table_prefix = "ANALYTICS"
        uploaded_file = st.file_uploader(
            "📁 Arquivo Excel para Análise de Estoque",
            type=['xlsx', 'xls'],
            help="Arquivo Export com dados de estoque e consumo",
            key="analytics_upload"
        )
    
    if uploaded_file is not None:
        st.subheader("🔍 Análise do Arquivo")
        
        if snowflake_available:
            try:
                # Use sophisticated Excel analysis to handle different header positions
                df_full, detected_sheet, detected_header = analyze_and_process_excel(uploaded_file)
                
                if df_full is not None and len(df_full) > 0:
                    st.success(f"✅ Dados carregados: {len(df_full)} linhas")
                    st.dataframe(df_full.head(10))
                    
                    # Show data quality info
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("📊 Linhas", len(df_full))
                    with col2:
                        st.metric("📋 Colunas", len(df_full.columns))
                    with col3:
                        st.metric("✅ Valores válidos", df_full.count().sum())
                    with col4:
                        file_size = len(uploaded_file.getvalue()) / 1024
                        st.metric("📁 Tamanho", f"{file_size:.1f} KB")
                    
                    # Check for duplicate files - Get fresh data with duplicate check
                    file_hash = str(hash(str(df_full.values.tobytes())))
                    is_duplicate = False
                    
                    # Get fresh data that includes duplicate check for this specific file
                    upload_check_data = get_cached_upload_page_data(
                        empresa_code, 
                        table_prefix=table_prefix, 
                        uploaded_filename=uploaded_file.name
                    )
                    
                    if upload_check_data['duplicate_check'] and upload_check_data['duplicate_check']['is_duplicate']:
                        version = upload_check_data['duplicate_check']['version_info']
                        is_duplicate = True
                        st.warning(f"⚠️ **Arquivo duplicado detectado!** \n\n📁 **{uploaded_file.name}** já foi enviado anteriormente como versão v{version['version_id']} em {version['upload_date']}")
                        
                        # Show option to proceed anyway
                        if st.checkbox("🔄 Enviar mesmo assim (criar nova versão)", key="force_upload"):
                            is_duplicate = False
                    
                    # Upload button
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        upload_button = st.button("💾 Salvar na Nuvem", 
                                                 type="primary" if not is_duplicate else "secondary", 
                                                 use_container_width=True,
                                                 disabled=is_duplicate)
                    with col2:
                        if is_duplicate:
                            st.error("🚫 Duplicado")
                        else:
                            st.info(f"📊 Para: {empresa_selecionada}")
                    
                    if upload_button:
                        with st.spinner(f"📤 Processando e enviando dados para Snowflake ({empresa_selecionada})..."):
                            try:
                                # Clean DataFrame for upload
                                df_clean = df_full.copy()
                                for col in df_clean.columns:
                                    if df_clean[col].dtype == 'object':
                                        df_clean[col] = df_clean[col].fillna('')
                                    else:
                                        df_clean[col] = df_clean[col].fillna(0)
                                
                                # Debug: Show consumption columns being uploaded
                                # Commented out to reduce debug spam
                                # if table_prefix == "ANALYTICS":
                                #     st.info("🔍 **Debug: Verificando colunas de consumo antes do upload:**")
                                #     consumo_cols = []
                                #     for col in ['Consumo 6 Meses', 'Consumo_6_Meses', 'Média 6 Meses', 'Media_6_Meses']:
                                #         if col in df_clean.columns:
                                #             non_zero = len(df_clean[df_clean[col] > 0])
                                #             consumo_cols.append(f"• {col}: {non_zero} valores > 0")
                                #     
                                #     if consumo_cols:
                                #         st.success("✅ Colunas de consumo encontradas:")
                                #         for info in consumo_cols:
                                #             st.write(info)
                                #     else:
                                #         st.warning("⚠️ Nenhuma coluna de consumo encontrada! Verifique os dados.")
                                
                                # Upload to Snowflake - Use optimized version
                                success = upload_excel_to_snowflake_optimized(
                                    df=df_clean, 
                                    arquivo_nome=uploaded_file.name, 
                                    empresa=empresa_code,
                                    usuario="minipa", 
                                    table_type=table_prefix,
                                    description=version_description or f"Upload {table_prefix} - {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}"
                                )
                                
                                if success:
                                    st.success(f"🎉 Dados salvos com sucesso para {empresa_selecionada}!")
                                    st.balloons()
                                    
                                    # Show different messages based on upload type
                                    if table_prefix == "TIMELINE":
                                        st.info("✅ **Dados salvos para Timeline de Compras**")
                                        st.write("👉 Acesse a página '📅 Timeline de Compras' para ver a análise")
                                    else:
                                        st.info("✅ **Dados salvos para Análise de Estoque**") 
                                        st.write("👉 Acesse a página '📊 Análise de Estoque' para ver os relatórios")
                                    
                                    # Clear cache for this company to show new data immediately
                                    if table_prefix == "TIMELINE":
                                        load_data_with_history.clear()
                                    else:
                                        load_analytics_data.clear()
                                    
                                    # Clear version cache to show new version
                                    get_upload_versions.clear()
                                    
                                    # Also clear the new dashboard cache
                                    get_cached_upload_page_data.clear()
                                    
                                    st.rerun()
                                else:
                                    st.error(f"❌ Erro ao salvar dados para {empresa_selecionada}")
                                    
                            except Exception as e:
                                st.error(f"❌ Erro ao processar: {str(e)}")
                else:
                    st.error("❌ Não foi possível processar o arquivo")
                    st.info("💡 Verifique se o arquivo Excel tem dados válidos")
                    
            except Exception as e:
                st.error(f"❌ Erro ao analisar arquivo: {str(e)}")
                st.info("💡 Tente com um arquivo Excel válido")
        else:
            st.warning("⚠️ Snowflake não configurado. Dados serão usados apenas localmente.")
    
    # Additional help section
    with st.expander("💡 Dicas para Upload"):
        st.markdown("""
        **Formato de arquivo suportado:**
        - ✅ Arquivos Excel (.xlsx, .xls)
        - ✅ Headers a partir da linha 9 ou 10
        - ✅ Colunas: Item, Fornecedor, QTD, Modelo, Preço FOB, Estoque Total, In Transit, Avg Sales, CBM, MOQ
        
        **Para melhores resultados:**
        - 📋 Certifique-se que os dados não tenham linhas vazias no topo
        - 📊 Números devem estar formatados como números (não texto)
        - 🔤 Nomes de produtos devem estar na coluna 'Modelo' ou 'Item'
        """)
    
    # Show cloud data status
    if snowflake_available:
        st.divider()
        st.subheader("☁️ Status da Nuvem")
        if st.button("🔄 Recarregar dados da nuvem", use_container_width=True):
            st.rerun() 