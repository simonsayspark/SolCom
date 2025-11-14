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
        
        # Sheet info removed for cleaner UI
        
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
            # Column standardization happens silently
            
            original_columns = list(df_full.columns)
            df_full, change_pairs = apply_column_remap(df_full)
            renamed_columns = list(df_full.columns)

            changes_made = [f"'{old}' → '{new}'" for old, new in change_pairs]
            
            if changes_made:
                st.success("✅ Colunas padronizadas")
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
                # Priority columns detected
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
    st.markdown("**Upload seus arquivos Excel aqui. Os dados serão salvos localmente com controle de versão para cada empresa.**")
    
    # Import local storage functions
    from bd.local_storage import (save_uploaded_data, get_upload_page_data, 
                                  delete_version, check_duplicate)
    
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
    st.subheader(f"📊 Status dos Dados - {empresa_selecionada}")
    
    # Get ALL data from local storage
    dashboard_data = get_upload_page_data(empresa_code)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Show analytics data
        analytics_stats = dashboard_data['stats']['analytics']
        analytics_count = analytics_stats.get('count', 0)
        
        if analytics_count > 0:
            st.success(f"📊 Analytics: {analytics_count} produtos salvos")
            if analytics_stats.get('latest_upload'):
                st.info(f"🕒 Último upload: {analytics_stats['latest_upload']}")
        else:
            st.info("📊 Analytics: Nenhum dado encontrado")
        
        # Show version history with delete options
        with st.expander(f"📋 Histórico de Versões - {empresa_selecionada}", expanded=False):
            try:
                # Use the data we already fetched
                versions_analytics = dashboard_data['versions_analytics']
                
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
                                        # Delete version using local storage
                                        result = delete_version(empresa_code, "ANALYTICS", v['version_id'])
                                        if result['success']:
                                            st.success(f"✅ {display_name} deletada!")
                                            st.session_state[f"confirm_delete_analytics_{v['version_id']}"] = False
                                            st.rerun()
                                        else:
                                            st.error(f"❌ {result['message']}")
                                with col2:
                                    if st.button("❌ Cancelar", 
                                                key=f"cancel_del_analytics_{v['version_id']}",
                                                use_container_width=True):
                                        st.session_state[f"confirm_delete_analytics_{v['version_id']}"] = False
                                        st.rerun()
                            
                            st.divider()  # Visual separator between versions
                
                if not versions_analytics:
                    st.info("Nenhuma versão encontrada. Faça seu primeiro upload!")
            except Exception as e:
                st.warning(f"Erro ao carregar versões: {str(e)}")
    
    with col2:
            st.info("💾 **Armazenamento Local**")
            st.write("Dados salvos localmente")
            st.write("Sem necessidade de autenticação")
    
    # File upload section
    st.subheader(f"📤 Upload de Arquivo - {empresa_selecionada}")
    
    st.info("""
    🎯 **Análise de Estoque com Prioridades:** Upload de Excel que já passou pelo processo de merge e priority analysis
    - Colunas esperadas: Produto, Estoque, Média 6 Meses, preco_unitario, priority_score, criticality, etc.
    - Este formato é gerado pelos scripts do Test folder (data_merger.py + priority_analysis.py)
    """)
    
    # Version description
    st.subheader("📝 Descrição da Versão")
    version_description = st.text_input(
        "Descrição desta versão (opcional):",
        placeholder="Ex: Atualização de preços Q4 2024, Novos fornecedores, etc.",
        help="Adicione uma descrição para identificar facilmente esta versão"
    )
    
    table_prefix = "ANALYTICS"
    uploaded_file = st.file_uploader(
        "📁 Arquivo Excel Merged com Prioridades",
        type=['xlsx', 'xls'],
        help="Arquivo que já passou pelo data merger e priority analysis",
        key="merged_upload"
    )
    
    if uploaded_file is not None:
        st.subheader("🔍 Análise do Arquivo")
        
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
                
                # Check for duplicate files
                duplicate_check = check_duplicate(empresa_code, table_prefix, uploaded_file.name)
                is_duplicate = duplicate_check['is_duplicate']
                
                if is_duplicate:
                    st.warning("⚠️ **Arquivo duplicado detectado!**")
                    
                    # Show option to proceed anyway
                    if st.checkbox("🔄 Enviar mesmo assim (criar nova versão)", key="force_upload"):
                        is_duplicate = False
                
                # Upload button
                col1, col2 = st.columns([2, 1])
                with col1:
                    upload_button = st.button("💾 Salvar Localmente", 
                                             type="primary" if not is_duplicate else "secondary", 
                                             use_container_width=True,
                                             disabled=is_duplicate)
                with col2:
                    if is_duplicate:
                        st.error("🚫 Duplicado")
                    else:
                        st.info(f"📊 Para: {empresa_selecionada}")
                
                if upload_button:
                    with st.spinner(f"📤 Processando e salvando dados localmente ({empresa_selecionada})..."):
                        try:
                            # Clean DataFrame for upload
                            df_clean = df_full.copy()
                            for col in df_clean.columns:
                                if df_clean[col].dtype == 'object':
                                    df_clean[col] = df_clean[col].fillna('')
                                else:
                                    df_clean[col] = df_clean[col].fillna(0)
                            
                            # Save to local storage
                            result = save_uploaded_data(
                                df=df_clean, 
                                empresa=empresa_code,
                                table_type=table_prefix,
                                filename=uploaded_file.name,
                                description=version_description or f"Upload {table_prefix} - {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}"
                            )
                            
                            if result['success']:
                                st.success(f"🎉 Dados salvos com sucesso para {empresa_selecionada}!")
                                st.balloons()
                                
                                st.info("✅ **Dados salvos para Análise de Estoque**") 
                                st.write("👉 Acesse a página '📊 Análise de Estoque' para ver os relatórios")
                                
                                st.rerun()
                            else:
                                st.error(f"❌ {result['message']}")
                                
                        except Exception as e:
                            st.error(f"❌ Erro ao processar: {str(e)}")
            else:
                st.error("❌ Não foi possível processar o arquivo")
                st.info("💡 Verifique se o arquivo Excel tem dados válidos")
                
        except Exception as e:
            st.error(f"❌ Erro ao analisar arquivo: {str(e)}")
            st.info("💡 Tente com um arquivo Excel válido")
    
    # Additional help section
    with st.expander("💡 Dicas para Upload"):
        st.markdown("""
        **Formato de arquivo suportado:**
        - ✅ Arquivos Excel (.xlsx, .xls)
        - ✅ Headers a partir da linha 9 ou 10
        - ✅ Colunas esperadas: Produto, Estoque, Média 6 Meses, preco_unitario, priority_score, criticality, relevance_class, etc.
        
        **Para melhores resultados:**
        - 📋 Certifique-se que os dados não tenham linhas vazias no topo
        - 📊 Números devem estar formatados como números (não texto)
        - 🔤 Nomes de produtos devem estar na coluna 'Produto'
        - 🎯 Arquivo deve ter passado pelo processo de merge e priority analysis
        """)
    
    # Refresh button
    st.divider()
    if st.button("🔄 Recarregar dados", use_container_width=True):
        st.rerun() 