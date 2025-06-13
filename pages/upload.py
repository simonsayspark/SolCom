import streamlit as st
import pandas as pd
from datetime import datetime

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
                                        load_analytics_data, test_connection, get_upload_versions, delete_version)
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
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Try to load existing data for selected company
            timeline_data = load_data_with_history(empresa=empresa_code)
            analytics_data = load_analytics_data(empresa=empresa_code)
            
            # Show data summary
            if timeline_data is not None and len(timeline_data) > 0:
                st.success(f"📅 Timeline: {len(timeline_data)} produtos salvos")
                if 'data_upload' in timeline_data.columns:
                    st.info(f"🕒 Último upload Timeline: {timeline_data['data_upload'].max()}")
            else:
                st.info("📅 Timeline: Nenhum dado encontrado")
            
            if analytics_data is not None and len(analytics_data) > 0:
                st.success(f"📊 Analytics: {len(analytics_data)} produtos salvos")
                if 'data_upload' in analytics_data.columns:
                    st.info(f"🕒 Último upload Analytics: {analytics_data['data_upload'].max()}")
            else:
                st.info("📊 Analytics: Nenhum dado encontrado")
            
            # Show version history with delete options
            with st.expander(f"📋 Histórico de Versões - {empresa_selecionada}"):
                try:
                    versions_timeline = get_upload_versions(empresa_code, "TIMELINE", limit=10)
                    versions_analytics = get_upload_versions(empresa_code, "ANALYTICS", limit=10)
                    
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
                            
                            col1, col2 = st.columns([5, 1])
                            with col1:
                                st.write(f"{status_icon} **{display_name}** - {v['upload_date']}{filename_info}")
                            with col2:
                                if not v['is_active']:  # Can't delete active version
                                    if st.button("🗑️", key=f"del_timeline_{v['version_id']}_{i}", help="Deletar versão"):
                                        st.session_state[f"confirm_delete_timeline_{v['version_id']}"] = True
                                        st.rerun()
                                else:
                                    st.write("🔒 Ativa")
                            
                            # Show confirmation dialog
                            if st.session_state.get(f"confirm_delete_timeline_{v['version_id']}", False):
                                st.error(f"⚠️ Deletar {display_name}?")
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("✅ Confirmar", key=f"confirm_del_timeline_{v['version_id']}"):
                                        try:
                                            # Call the actual deletion function
                                            if delete_version(empresa_code, v['version_id'], "TIMELINE"):
                                                st.success(f"✅ {display_name} deletada!")
                                                st.session_state[f"confirm_delete_timeline_{v['version_id']}"] = False
                                                st.rerun()
                                            else:
                                                st.error("❌ Falha ao deletar versão")
                                        except Exception as e:
                                            st.error(f"❌ Erro ao deletar: {str(e)}")
                                with col2:
                                    if st.button("❌ Cancelar", key=f"cancel_del_timeline_{v['version_id']}"):
                                        st.session_state[f"confirm_delete_timeline_{v['version_id']}"] = False
                                        st.rerun()
                    
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
                            
                            col1, col2 = st.columns([5, 1])
                            with col1:
                                st.write(f"{status_icon} **{display_name}** - {v['upload_date']}{filename_info}")
                            with col2:
                                if not v['is_active']:  # Can't delete active version
                                    if st.button("🗑️", key=f"del_analytics_{v['version_id']}_{i}", help="Deletar versão"):
                                        st.session_state[f"confirm_delete_analytics_{v['version_id']}"] = True
                                        st.rerun()
                                else:
                                    st.write("🔒 Ativa")
                            
                            # Show confirmation dialog
                            if st.session_state.get(f"confirm_delete_analytics_{v['version_id']}", False):
                                st.error(f"⚠️ Deletar {display_name}?")
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("✅ Confirmar", key=f"confirm_del_analytics_{v['version_id']}"):
                                        try:
                                            # Call the actual deletion function
                                            if delete_version(empresa_code, v['version_id'], "ANALYTICS"):
                                                st.success(f"✅ {display_name} deletada!")
                                                st.session_state[f"confirm_delete_analytics_{v['version_id']}"] = False
                                                st.rerun()
                                            else:
                                                st.error("❌ Falha ao deletar versão")
                                        except Exception as e:
                                            st.error(f"❌ Erro ao deletar: {str(e)}")
                                with col2:
                                    if st.button("❌ Cancelar", key=f"cancel_del_analytics_{v['version_id']}"):
                                        st.session_state[f"confirm_delete_analytics_{v['version_id']}"] = False
                                        st.rerun()
                    
                    if not versions_timeline and not versions_analytics:
                        st.info("Nenhuma versão encontrada. Faça seu primeiro upload!")
                except Exception as e:
                    st.warning(f"Erro ao carregar versões: {str(e)}")
        
        with col2:
            st.info("🔗 Snowflake (monitoring disabled)")
    
    # File upload section
    st.subheader(f"📤 Upload de Arquivo - {empresa_selecionada}")
    
    # Create two distinct upload options
    upload_type = st.radio(
        "📋 Selecione o tipo de dados:",
        ["📅 Timeline de Compras (MOQ/Fornecedores)", "📊 Análise de Estoque (Export)"],
        help="Escolha o tipo correto para que os dados sejam processados adequadamente"
    )
    
    # Version description
    st.subheader("📝 Descrição da Versão")
    version_description = st.text_input(
        "Descrição desta versão (opcional):",
        placeholder="Ex: Atualização de preços Q4 2024, Novos fornecedores, etc.",
        help="Adicione uma descrição para identificar facilmente esta versão"
    )
    
    if upload_type == "📅 Timeline de Compras (MOQ/Fornecedores)":
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
                    
                    # Check for duplicate files
                    file_hash = str(hash(str(df_full.values.tobytes())))
                    is_duplicate = False
                    
                    try:
                        existing_versions = get_upload_versions(empresa_code, table_prefix, limit=50)
                        for version in existing_versions:
                            if version.get('arquivo_origem') == uploaded_file.name:
                                is_duplicate = True
                                st.warning(f"⚠️ **Arquivo duplicado detectado!** \n\n📁 **{uploaded_file.name}** já foi enviado anteriormente como versão v{version['version_id']} em {version['upload_date']}")
                                
                                # Show option to proceed anyway
                                if st.checkbox("🔄 Enviar mesmo assim (criar nova versão)", key="force_upload"):
                                    is_duplicate = False
                                break
                    except:
                        pass  # If version check fails, allow upload
                    
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
                                
                                # Upload to Snowflake
                                success = upload_excel_to_snowflake(
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