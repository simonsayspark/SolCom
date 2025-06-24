import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

def load_page():
    """Análise avançada de dados Excel - Sistema Multi-Empresa de Gestão de Estoque"""
    
    # Header with company selector
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title("📊 Análise de Estoque Multi-Empresa")
        st.markdown("**Ferramenta prática para gestão de estoque focada em AÇÃO e DECISÃO**")
    
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
            
            # Check if data_upload column exists before accessing it
            if 'data_upload' in df.columns:
                st.info(f"📅 Data do upload: {df['data_upload'].max()}")
            else:
                st.info("📅 Dados de análise carregados da nuvem")
                
            # Show column mapping info for merged Excel
            if 'monthly_volume' in df.columns or 'priority_score' in df.columns:
                with st.expander("🔍 Mapeamento de Colunas do Merged Excel", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Colunas Detectadas:**")
                        if 'Media_6_Meses' in df.columns:
                            st.write(f"✅ Media_6_Meses presente ({len(df[df['Media_6_Meses'] > 0])} valores > 0)")
                        if 'Média 6 Meses' in df.columns:
                            st.write(f"✅ Média 6 Meses presente ({len(df[df['Média 6 Meses'] > 0])} valores > 0)")
                        if 'monthly_volume' in df.columns:
                            if 'Média 6 Meses' in df.columns and df['Média 6 Meses'].sum() == 0:
                                st.write(f"✅ monthly_volume → Média 6 Meses (fallback)")
                            else:
                                st.write(f"✅ monthly_volume presente (não usado)")
                        if 'UltimoFornecedor' in df.columns:
                            st.write(f"✅ UltimoFornecedor presente")
                        if 'preco_unitario' in df.columns:
                            st.write(f"✅ preco_unitario presente")
                        if 'priority_score' in df.columns:
                            st.write(f"✅ priority_score presente")
                    with col2:
                        st.write("**Valores de Exemplo:**")
                        if 'monthly_volume' in df.columns:
                            st.write(f"monthly_volume: {df['monthly_volume'].head(3).tolist()}")
                        if 'UltimoFornecedor' in df.columns:
                            st.write(f"UltimoFornecedor: {df['UltimoFornecedor'].head(3).tolist()}")
            
            # Handle merged Excel format - if Média 6 Meses is 0, try monthly_volume
            if 'Média 6 Meses' in df.columns and 'monthly_volume' in df.columns:
                # Check if Média 6 Meses column has all zeros or is empty
                media_sum = df['Média 6 Meses'].sum()
                valid_media_count = len(df[df['Média 6 Meses'] > 0])
                
                # Only use monthly_volume if Média 6 Meses is truly empty/zero
                if media_sum == 0 and valid_media_count == 0 and df['monthly_volume'].sum() > 0:
                    st.info("📊 Detectado formato Merged Excel - usando monthly_volume como consumo mensal")
                    df['Média 6 Meses'] = df['monthly_volume']
                elif valid_media_count > 0:
                    st.success(f"✅ Usando dados originais de Média 6 Meses ({valid_media_count} produtos com consumo)")
            
            # Also handle Media_6_Meses (with underscore) mapping to Média 6 Meses (with space)
            if 'Media_6_Meses' in df.columns and 'Média 6 Meses' not in df.columns:
                df['Média 6 Meses'] = df['Media_6_Meses']
                st.info("📊 Mapeando Media_6_Meses → Média 6 Meses")
            
            # Also copy monthly_volume to Consumo 6 Meses if that's empty
            if 'Consumo 6 Meses' in df.columns and 'monthly_volume' in df.columns:
                if df['Consumo 6 Meses'].sum() == 0 and df['monthly_volume'].sum() > 0:
                    df['Consumo 6 Meses'] = df['monthly_volume']
            
            # Ensure UltimoFornecedor has proper values (not empty/nan)
            if 'UltimoFornecedor' in df.columns:
                df['UltimoFornecedor'] = df['UltimoFornecedor'].fillna('Brazil')
                df.loc[df['UltimoFornecedor'].str.strip() == '', 'UltimoFornecedor'] = 'Brazil'
                df.loc[df['UltimoFornecedor'].str.lower() == 'nan', 'UltimoFornecedor'] = 'Brazil'
            
            # Calculate Estoque Cobertura if missing
            if 'Estoque Cobertura' not in df.columns:
                if 'Estoque' in df.columns and 'Média 6 Meses' in df.columns:
                    df['Estoque Cobertura'] = df.apply(
                        lambda row: row['Estoque'] / row['Média 6 Meses'] if row['Média 6 Meses'] > 0 else 999, 
                        axis=1
                    )
        
        else:
            st.info(f"💡 Nenhum dado de análise encontrado para {empresa_selecionada}.")
            st.markdown("👉 **Vá para 'Upload de Dados' e selecione '📊 Análise de Estoque (Export)' para enviar dados para esta empresa primeiro.**")
            df = None
            
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
        # Handle different column name formats (timeline vs analytics)
        df_processed = df.copy()
        
        # Map timeline columns to analytics columns if needed
        column_mapping = {
            'Item': 'Produto',
            'Modelo': 'Produto', 
            'Estoque_Total': 'Estoque',
            'Vendas_Medias': 'Média 6 Meses',
            'UltimoFor': 'UltimoFornecedor',  # NEW MAPPING
            'ultimo_fornecedor': 'UltimoFornecedor',  # Merged Excel variation
            'Preco_Unitario': 'preco_unitario',  # Ensure price mapping
            'Preco_FOB_Unitario': 'preco_unitario'
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns and new_col not in df.columns:
                df_processed[new_col] = df[old_col]
        
        # Handle merged Excel format - if Média 6 Meses is 0, try monthly_volume
        if 'Média 6 Meses' in df_processed.columns and 'monthly_volume' in df_processed.columns:
            # Check if Média 6 Meses column has all zeros or is empty
            media_sum = df_processed['Média 6 Meses'].sum()
            valid_media_count = len(df_processed[df_processed['Média 6 Meses'] > 0])
            
            # Only use monthly_volume if Média 6 Meses is truly empty/zero
            if media_sum == 0 and valid_media_count == 0 and df_processed['monthly_volume'].sum() > 0:
                st.info("📊 Detectado formato Merged Excel - usando monthly_volume como consumo mensal")
                df_processed['Média 6 Meses'] = df_processed['monthly_volume']
            elif valid_media_count > 0:
                st.success(f"✅ Usando dados originais de Média 6 Meses ({valid_media_count} produtos com consumo)")
        
        # Also handle Media_6_Meses (with underscore) mapping to Média 6 Meses (with space)
        if 'Media_6_Meses' in df_processed.columns and 'Média 6 Meses' not in df_processed.columns:
            df_processed['Média 6 Meses'] = df_processed['Media_6_Meses']
            st.info("📊 Mapeando Media_6_Meses → Média 6 Meses")
        
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
        
        # Show column mapping info for merged Excel
        if 'monthly_volume' in df_processed.columns or 'priority_score' in df_processed.columns:
            with st.expander("🔍 Mapeamento de Colunas do Merged Excel", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Colunas Detectadas:**")
                    if 'Media_6_Meses' in df_processed.columns:
                        st.write(f"✅ Media_6_Meses presente ({len(df_processed[df_processed['Media_6_Meses'] > 0])} valores > 0)")
                    if 'Média 6 Meses' in df_processed.columns:
                        st.write(f"✅ Média 6 Meses presente ({len(df_processed[df_processed['Média 6 Meses'] > 0])} valores > 0)")
                    if 'monthly_volume' in df_processed.columns:
                        if 'Média 6 Meses' in df_processed.columns and df_processed['Média 6 Meses'].sum() == 0:
                            st.write(f"✅ monthly_volume → Média 6 Meses (fallback)")
                        else:
                            st.write(f"✅ monthly_volume presente (não usado)")
                    if 'UltimoFornecedor' in df_processed.columns:
                        st.write(f"✅ UltimoFornecedor presente")
                    if 'preco_unitario' in df_processed.columns:
                        st.write(f"✅ preco_unitario presente")
                    if 'priority_score' in df_processed.columns:
                        st.write(f"✅ priority_score presente")
                with col2:
                    st.write("**Valores de Exemplo:**")
                    if 'monthly_volume' in df_processed.columns:
                        st.write(f"monthly_volume: {df_processed['monthly_volume'].head(3).tolist()}")
                    if 'UltimoFornecedor' in df_processed.columns:
                        st.write(f"UltimoFornecedor: {df_processed['UltimoFornecedor'].head(3).tolist()}")
        
        # Use processed dataframe
        df = df_processed
        
        # Separate new and existing products
        produtos_novos = df[(df.get('Estoque', 0) == 0) & (df.get('Média 6 Meses', 0) == 0) & (df.get('Qtde Tot Compras', 0) > 0)]
        produtos_existentes = df[(df.get('Estoque', 0) > 0) | (df.get('Média 6 Meses', 0) > 0)]
        
        # Show company context
        st.info(f"📊 **Análise para {empresa_selecionada}** | Versão: {f'v{selected_version_id}' if 'selected_version_id' in locals() and selected_version_id else 'Ativa'}")
        
        # Show analytics tabs with company context
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            f"📋 Resumo - {empresa_selecionada}", 
            f"🚨 Lista de Compras - {empresa_selecionada}", 
            f"📊 Dashboards - {empresa_selecionada}", 
            f"📞 Contatos Urgentes - {empresa_selecionada}",
            f"📋 Tabela Geral - {empresa_selecionada}",
            f"🎯 Timeline Prioritário - {empresa_selecionada}"
        ])
        
        with tab1:
            show_executive_summary(df, produtos_novos, produtos_existentes, empresa_selecionada)
        
        with tab2:
            show_purchase_list(produtos_existentes, empresa_selecionada)
        
        with tab3:
            show_analytics_dashboard(produtos_existentes, produtos_novos, empresa_selecionada)
        
        with tab4:
            show_urgent_contacts(produtos_existentes, empresa_selecionada)
        
        with tab5:
            show_tabela_geral(df, empresa_selecionada)
            
        with tab6:
            show_priority_timeline(df, empresa_selecionada)

def show_executive_summary(df, produtos_novos, produtos_existentes, empresa="MINIPA"):
    """Resumo executivo dos dados por empresa"""
    
    st.subheader(f"📋 Resumo Executivo - {empresa}")
    
    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📦 Total de Produtos", len(df))
    
    with col2:
        st.metric("🆕 Produtos Novos", len(produtos_novos))
    
    with col3:
        st.metric("📈 Produtos Existentes", len(produtos_existentes))
    
    with col4:
        if len(produtos_existentes) > 0:
            criticos = len(produtos_existentes[produtos_existentes['Estoque Cobertura'] <= 1])
            st.metric("🚨 Produtos Críticos", criticos)
        else:
            st.metric("🚨 Produtos Críticos", 0)
    
    if len(produtos_existentes) > 0:
        # Status breakdown
        st.subheader("🎯 Status dos Produtos Existentes")
        
        criticos = len(produtos_existentes[produtos_existentes['Estoque Cobertura'] <= 1])
        alerta = len(produtos_existentes[(produtos_existentes['Estoque Cobertura'] > 1) & (produtos_existentes['Estoque Cobertura'] <= 3)])
        saudaveis = len(produtos_existentes[produtos_existentes['Estoque Cobertura'] > 3])
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "🔴 Críticos (≤1 mês)", 
                criticos,
                delta=f"{criticos/len(produtos_existentes)*100:.1f}%"
            )
        
        with col2:
            st.metric(
                "🟡 Alerta (1-3 meses)", 
                alerta,
                delta=f"{alerta/len(produtos_existentes)*100:.1f}%"
            )
        
        with col3:
            st.metric(
                "🟢 Saudáveis (>3 meses)", 
                saudaveis,
                delta=f"{saudaveis/len(produtos_existentes)*100:.1f}%"
            )
        
        # Financial overview
        st.subheader("💰 Visão Financeira")
        
        estoque_total = produtos_existentes['Estoque'].sum()
        consumo_total = produtos_existentes['Média 6 Meses'].sum()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📦 Estoque Total", f"{estoque_total:,.0f} unidades")
        
        with col2:
            st.metric("📈 Consumo Mensal", f"{consumo_total:,.1f} unidades")
        
        with col3:
            if consumo_total > 0:
                duracao = estoque_total / consumo_total
                st.metric("⏱️ Duração Média", f"{duracao:.1f} meses")
            else:
                st.metric("⏱️ Duração Média", "N/A")
    
    # Action items
    if len(produtos_existentes) > 0:
        st.subheader("🚨 Ações Necessárias")
        
        if criticos > 0:
            st.error(f"⚡ URGENTE: {criticos} produtos críticos precisam de compra IMEDIATA")
        if alerta > 0:
            st.warning(f"📅 PLANEJAR: {alerta} produtos em alerta para próximas semanas")
        if len(produtos_novos) > 0:
            st.info(f"🆕 MONITORAR: {len(produtos_novos)} produtos novos sendo lançados")
        
        if criticos == 0 and alerta == 0:
            st.success("✅ Situação de estoque sob controle!")

def calculate_purchase_suggestions(produtos_existentes):
    """Calculate purchase suggestions for products"""
    
    def calcular_quando_vai_acabar(estoque, consumo_mensal):
        if consumo_mensal <= 0:
            return "Sem consumo", 999
        
        meses_restantes = estoque / consumo_mensal
        
        if meses_restantes <= 0:
            return "JÁ ACABOU", 0
        elif meses_restantes < 0.5:
            dias = int(meses_restantes * 30)
            return f"{dias} dias", meses_restantes
        else:
            return f"{meses_restantes:.1f} meses", meses_restantes
    
    def quanto_comprar(consumo_mensal, estoque_atual, moq=0, meses_desejados=6):
        if consumo_mensal <= 0:
            return moq if moq > 0 else 0
        
        estoque_ideal = consumo_mensal * meses_desejados
        falta = max(0, estoque_ideal - estoque_atual)
        
        if falta <= 0:
            return 0
        
        # Use MOQ if available, otherwise round to 50s
        if moq > 0:
            # Calculate multiples of MOQ needed
            multiplos = max(1, int(np.ceil(falta / moq)))
            return multiplos * moq
        else:
            # Round for easier purchasing
            return int(np.ceil(falta / 50) * 50)
    
    # Calculate for each product
    suggestions = []
    
    for _, row in produtos_existentes.iterrows():
        produto = str(row['Produto'])
        estoque = row['Estoque']
        consumo = row['Média 6 Meses']
        moq = row.get('MOQ', 0) if 'MOQ' in row.index else 0
        fornecedor = 'Brazil'
        
        # Handle supplier column variations - check UltimoFornecedor first since it's in merged Excel
        for col in ['UltimoFornecedor', 'ultimo_fornecedor', 'UltimoFor']:
            if col in row.index:
                value = str(row.get(col, 'Brazil'))
                if value and value.strip() and value.lower() not in ['nan', 'none', '']:
                    fornecedor = value
                    break
        
        quando_acaba, meses_num = calcular_quando_vai_acabar(estoque, consumo)
        qtd_comprar = quanto_comprar(consumo, estoque, moq)
        
        suggestions.append({
            'Produto': produto,
            'Estoque_Atual': estoque,
            'Consumo_Mensal': consumo,
            'MOQ': moq,
            'Fornecedor': fornecedor,
            'Quando_Acaba': quando_acaba,
            'Meses_Restantes': meses_num,
            'Qtd_Comprar': qtd_comprar,
            'Investimento_Estimado': qtd_comprar * 15  # R$ 15 per unit estimate
        })
    
    return pd.DataFrame(suggestions)

def show_purchase_list(produtos_existentes, empresa="MINIPA"):
    """Show practical purchase list by company"""
    
    st.subheader(f"🛒 Lista Prática de Compras - {empresa}")
    
    if len(produtos_existentes) == 0:
        st.info("Nenhum produto existente para análise")
        return
    
    # Calculate suggestions
    suggestions_df = calculate_purchase_suggestions(produtos_existentes)
    
    # Filter products that need action (increased range due to new categories)
    precisa_acao = suggestions_df[
        (suggestions_df['Meses_Restantes'] <= 6) & 
        (suggestions_df['Consumo_Mensal'] > 0)
    ].sort_values('Meses_Restantes')
    
    if len(precisa_acao) == 0:
        st.success("✅ Nenhum produto necessita compra urgente!")
        return
    
    st.info(f"📦 {len(precisa_acao)} produtos precisam de compra")
    
    # Emergency products (≤ 1 month)
    emergencia = precisa_acao[precisa_acao['Meses_Restantes'] <= 1]
    if len(emergencia) > 0:
        st.error("🚨 EMERGÊNCIA (≤ 1 mês)")
        st.dataframe(
            emergencia[['Produto', 'Fornecedor', 'Quando_Acaba', 'MOQ', 'Qtd_Comprar', 'Investimento_Estimado']].round(1),
            use_container_width=True
        )
    
    # Critical products (1-3 months)
    criticos = precisa_acao[(precisa_acao['Meses_Restantes'] > 1) & (precisa_acao['Meses_Restantes'] <= 3)]
    if len(criticos) > 0:
        st.warning("🔴 CRÍTICOS (1-3 meses)")
        st.dataframe(
            criticos[['Produto', 'Fornecedor', 'Quando_Acaba', 'MOQ', 'Qtd_Comprar', 'Investimento_Estimado']].head(10).round(1),
            use_container_width=True
        )
    
    # Attention products (3+ months)
    atencao = precisa_acao[precisa_acao['Meses_Restantes'] > 3]
    if len(atencao) > 0:
        st.info("🟡 ATENÇÃO (>3 meses)")
        st.dataframe(
            atencao[['Produto', 'Fornecedor', 'Quando_Acaba', 'MOQ', 'Qtd_Comprar', 'Investimento_Estimado']].head(10).round(1),
            use_container_width=True
        )
    
    # Summary
    st.subheader("💰 Resumo de Investimento")
    
    total_emergencia = len(emergencia)
    total_criticos = len(criticos)
    total_atencao = len(atencao)
    
    investimento_total = precisa_acao['Investimento_Estimado'].sum()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🚨 Emergência", total_emergencia)
    with col2:
        st.metric("🔴 Críticos", total_criticos)
    with col3:
        st.metric("🟡 Atenção", total_atencao)
    with col4:
        st.metric("💰 Investimento", f"R$ {investimento_total:,.0f}")

def show_analytics_dashboard(produtos_existentes, produtos_novos, empresa="MINIPA"):
    """Show visual analytics dashboard by company"""
    
    st.subheader(f"📊 Dashboard Visual - {empresa}")
    
    if len(produtos_existentes) == 0:
        st.info("Nenhum produto para análise visual")
        return
    
    # Calculate data for charts
    suggestions_df = calculate_purchase_suggestions(produtos_existentes)
    
    # Urgency categorization
    muito_critico = len(suggestions_df[suggestions_df['Meses_Restantes'] <= 1])
    critico = len(suggestions_df[(suggestions_df['Meses_Restantes'] > 1) & (suggestions_df['Meses_Restantes'] <= 3)])
    moderado = len(suggestions_df[(suggestions_df['Meses_Restantes'] > 3) & (suggestions_df['Meses_Restantes'] <= 6)])
    ok = len(suggestions_df[suggestions_df['Meses_Restantes'] > 6])
    
    # Chart 1: Products by urgency
    col1, col2 = st.columns(2)
    
    with col1:
        urgency_data = {
            'Categoria': ['≤1 mês', '1-3 meses', '3-6 meses', '>6 meses'],
            'Quantidade': [muito_critico, critico, moderado, ok],
            'Cor': ['#8B0000', '#FF0000', '#FFA500', '#008000']
        }
        
        fig_urgency = px.bar(
            urgency_data,
            x='Categoria',
            y='Quantidade',
            color='Cor',
            title='🚨 Produtos por Urgência',
            color_discrete_map={color: color for color in urgency_data['Cor']}
        )
        st.plotly_chart(fig_urgency, use_container_width=True)
    
    with col2:
        # Chart 2: Stock coverage distribution
        if len(produtos_existentes) > 0:
            fig_pie = px.pie(
                values=[muito_critico, critico, moderado, ok],
                names=['≤1 mês', '1-3 meses', '3-6 meses', '>6 meses'],
                title='⏰ Distribuição de Cobertura',
                color_discrete_sequence=['#8B0000', '#FF0000', '#FFA500', '#008000']
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    
    # Chart 3: Top products to buy
    precisa_acao = suggestions_df[
        (suggestions_df['Meses_Restantes'] <= 3) & 
        (suggestions_df['Consumo_Mensal'] > 0)
    ].sort_values('Qtd_Comprar', ascending=False).head(10)
    
    if len(precisa_acao) > 0:
        fig_top = px.bar(
            precisa_acao,
            x='Qtd_Comprar',
            y='Produto',
            orientation='h',
            title='🛒 Top 10 Produtos para Comprar',
            color='Meses_Restantes',
            color_continuous_scale='Reds_r'
        )
        fig_top.update_layout(height=500)
        st.plotly_chart(fig_top, use_container_width=True)
    
    # Chart 4: Supplier analysis
    if 'Fornecedor' in suggestions_df.columns:
        st.subheader("🏭 Análise por Fornecedor")
        
        # Group by supplier
        supplier_analysis = suggestions_df.groupby('Fornecedor').agg({
            'Produto': 'count',
            'Qtd_Comprar': 'sum',
            'Investimento_Estimado': 'sum',
            'Meses_Restantes': 'mean'
        }).round(1)
        supplier_analysis.columns = ['Produtos', 'Qtd_Total', 'Investimento', 'Urgência_Média']
        supplier_analysis = supplier_analysis.sort_values('Investimento', ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Top suppliers by investment
            fig_suppliers = px.bar(
                supplier_analysis.head(10).reset_index(),
                x='Investimento',
                y='Fornecedor',
                orientation='h',
                title='💰 Top Fornecedores por Investimento',
                color='Urgência_Média',
                color_continuous_scale='Reds_r'
            )
            st.plotly_chart(fig_suppliers, use_container_width=True)
        
        with col2:
            # Supplier distribution
            fig_supplier_pie = px.pie(
                supplier_analysis.reset_index(),
                values='Produtos',
                names='Fornecedor',
                title='📊 Distribuição de Produtos por Fornecedor'
            )
            st.plotly_chart(fig_supplier_pie, use_container_width=True)
        
        # Show supplier summary table
        st.dataframe(supplier_analysis, use_container_width=True)
    
    # Chart 5: Investment timeline
    col1, col2 = st.columns(2)
    
    with col1:
        emergencia = suggestions_df[suggestions_df['Meses_Restantes'] <= 1]
        criticos_chart = suggestions_df[(suggestions_df['Meses_Restantes'] > 1) & (suggestions_df['Meses_Restantes'] <= 3)]
        atencao = suggestions_df[suggestions_df['Meses_Restantes'] > 3]
        
        invest_emergencia = emergencia['Investimento_Estimado'].sum() if len(emergencia) > 0 else 0
        invest_criticos = criticos_chart['Investimento_Estimado'].sum() if len(criticos_chart) > 0 else 0
        invest_atencao = atencao['Investimento_Estimado'].sum() if len(atencao) > 0 else 0
        
        investment_data = {
            'Período': ['Este Mês', 'Próximos 3 Meses', 'Longo Prazo'],
            'Investimento': [invest_emergencia, invest_criticos, invest_atencao]
        }
        
        fig_invest = px.bar(
            investment_data,
            x='Período',
            y='Investimento',
            title='💰 Investimento por Período',
            color='Investimento',
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig_invest, use_container_width=True)
    
    with col2:
        # Product status overview
        if len(produtos_novos) > 0:
            overview_data = {
                'Categoria': ['Produtos Existentes', 'Produtos Novos'],
                'Quantidade': [len(produtos_existentes), len(produtos_novos)]
            }
            
            fig_overview = px.pie(
                overview_data,
                values='Quantidade',
                names='Categoria',
                title='📊 Visão Geral dos Produtos'
            )
            st.plotly_chart(fig_overview, use_container_width=True)

def show_urgent_contacts(produtos_existentes, empresa="MINIPA"):
    """Show urgent contacts list by company"""
    
    st.subheader(f"📞 Contatos Urgentes - {empresa}")
    
    if len(produtos_existentes) == 0:
        st.info("Nenhum produto para análise de contatos")
        return
    
    # Get critical products
    criticos = produtos_existentes[produtos_existentes['Estoque Cobertura'] <= 1]
    
    if len(criticos) == 0:
        st.success("✅ Nenhum produto crítico no momento!")
        return
    
    st.error(f"🚨 {len(criticos)} produtos críticos precisam de ação IMEDIATA!")
    
    # Show critical products list
    st.subheader("🔴 Lista de Produtos Críticos")
    
    # Sample contact info (in real app, this would come from database)
    contact_data = []
    for _, row in criticos.head(10).iterrows():
        contact_data.append({
            'Produto': row['Produto'],
            'Estoque': f"{row['Estoque']:.0f}",
            'Cobertura': f"{row['Estoque Cobertura']:.1f} meses",
            'Status': "🚨 CRÍTICO",
            'Ação': "Comprar AGORA"
        })
    
    if contact_data:
        contact_df = pd.DataFrame(contact_data)
        st.dataframe(contact_df, use_container_width=True)
    
    # Contact instructions
    st.subheader("📋 Instruções de Contato")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **🏢 Departamento de Compras:**
        - Email: compras@empresa.com
        - Tel: (11) 1234-5678
        - WhatsApp: (11) 98765-4321
        """)
    
    with col2:
        st.markdown("""
        **⏰ Horário de Atendimento:**
        - Segunda a Sexta: 8h às 18h
        - Urgências: 24h via WhatsApp
        - Email: Resposta em até 2h
        """)
    
    # Quick actions
    st.subheader("⚡ Ações Rápidas")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📧 Abrir Email", use_container_width=True):
            st.info("Email aberto com lista de produtos críticos")
    
    with col2:
        if st.button("📱 WhatsApp", use_container_width=True):
            st.info("WhatsApp aberto para contato urgente")
    
    with col3:
        if st.button("📊 Exportar Lista", use_container_width=True):
            st.info("Lista de produtos críticos exportada")

def show_tabela_geral(df, empresa="MINIPA"):
    """Show general table by company"""
    
    st.subheader(f"📋 Tabela Geral de Produtos - {empresa}")
    
    # Select columns to display (exclude metadata columns)
    display_columns = [col for col in df.columns if col not in [
        'empresa', 'upload_version', 'version_id', 'is_active', 
        'data_upload', 'usuario', 'table_type', 'version_description', 
        'created_by', 'id', 'relevance_class'  # Add metadata columns to exclude
    ]]
    
    # Create search filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_produto = st.text_input("🔍 Buscar por produto:", key=f"search_prod_{empresa}")
    
    with col2:
        if 'UltimoFornecedor' in df.columns:
            fornecedores = ['Todos'] + sorted(df['UltimoFornecedor'].dropna().unique().tolist())
        elif 'ultimo_fornecedor' in df.columns:
            fornecedores = ['Todos'] + sorted(df['ultimo_fornecedor'].dropna().unique().tolist())
        else:
            fornecedores = ['Todos']
        
        selected_fornecedor = st.selectbox("🏭 Filtrar por fornecedor:", fornecedores, key=f"filter_forn_{empresa}")
    
    with col3:
        sort_column = st.selectbox("📊 Ordenar por:", display_columns, key=f"sort_col_{empresa}")
    
    # Apply filters
    filtered_df = df.copy()
    
    if search_produto:
        filtered_df = filtered_df[filtered_df['Produto'].str.contains(search_produto, case=False, na=False)]
    
    if selected_fornecedor != 'Todos':
        if 'UltimoFornecedor' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['UltimoFornecedor'] == selected_fornecedor]
        elif 'ultimo_fornecedor' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['ultimo_fornecedor'] == selected_fornecedor]
    
    # Sort data
    filtered_df = filtered_df.sort_values(by=sort_column, ascending=False)
    
    # Show results
    st.info(f"📊 Mostrando {len(filtered_df)} de {len(df)} produtos")
    
    # Format numeric columns for better display
    formatted_df = filtered_df[display_columns].copy()
    
    # Round numeric columns to 2 decimal places
    numeric_columns = formatted_df.select_dtypes(include=[np.number]).columns
    for col in numeric_columns:
        formatted_df[col] = formatted_df[col].round(2)
    
    # Display the dataframe with formatting
    st.dataframe(
        formatted_df,
        use_container_width=True,
        height=600,
        hide_index=True
    )
    
    # Export options
    st.subheader("📥 Exportar Dados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv = filtered_df[display_columns].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 Baixar como CSV",
            data=csv,
            file_name=f'tabela_geral_{empresa}_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.csv',
            mime='text/csv',
            use_container_width=True
        )
    
    with col2:
        # Excel export with xlsxwriter
        try:
            import io
            buffer = io.BytesIO()
            
            # Create a Pandas Excel writer using XlsxWriter
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                filtered_df[display_columns].to_excel(writer, sheet_name='Tabela Geral', index=False)
                
                # Get the xlsxwriter workbook and worksheet objects
                workbook = writer.book
                worksheet = writer.sheets['Tabela Geral']
                
                # Add some cell formatting
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#D7E4BD',
                    'border': 1
                })
                
                # Write the column headers with the defined format
                for col_num, value in enumerate(filtered_df[display_columns].columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Auto-adjust columns width
                for column in filtered_df[display_columns]:
                    column_width = max(filtered_df[display_columns][column].astype(str).map(len).max(), len(column))
                    col_idx = filtered_df[display_columns].columns.get_loc(column)
                    worksheet.set_column(col_idx, col_idx, min(column_width + 2, 50))
            
            # Reset buffer position
            buffer.seek(0)
            
            st.download_button(
                label="📊 Baixar como Excel",
                data=buffer,
                file_name=f'tabela_geral_{empresa}_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                mime='application/vnd.ms-excel',
                use_container_width=True
            )
        except ImportError:
            st.warning("⚠️ xlsxwriter não instalado. Usando método alternativo para Excel.")
            # Fallback method without xlsxwriter
            import io
            excel_buffer = io.BytesIO()
            filtered_df[display_columns].to_excel(excel_buffer, index=False)
            excel_buffer.seek(0)
            
            st.download_button(
                label="📊 Baixar como Excel",
                data=excel_buffer,
                file_name=f'tabela_geral_{empresa}_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                mime='application/vnd.ms-excel',
                use_container_width=True
            )

def show_priority_timeline(df, empresa="MINIPA"):
    """Show priority-driven timeline with merged data support"""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    from datetime import datetime, timedelta
    
    st.subheader(f"🎯 Timeline de Compras Prioritário - {empresa}")
    
    # Debug: Show available columns
    st.info(f"🔍 Colunas disponíveis: {', '.join(df.columns[:15])}...")
    
    # Enhanced priority data detection with debugging
    has_priority_score = 'priority_score' in df.columns
    has_criticality = 'criticality' in df.columns
    has_priority_values = False
    
    if has_priority_score:
        priority_values = df['priority_score'].dropna()
        has_priority_values = len(priority_values) > 0
        st.info(f"🔍 Priority Score: Coluna existe: {has_priority_score}, Valores não-nulos: {len(priority_values)}")
    
    if has_criticality:
        criticality_values = df['criticality'].dropna()
        st.info(f"🔍 Criticality: Coluna existe: {has_criticality}, Valores não-nulos: {len(criticality_values)}")
    
    # Check if we have priority data - more flexible detection
    has_priority_data = (has_priority_score and has_priority_values) or (has_criticality and len(df['criticality'].dropna()) > 0)
    
    if has_priority_data:
        st.success("✅ Dados de prioridade detectados! Usando análise prioritária 85/15.")
    else:
        st.info("📊 Dados de prioridade não encontrados. Usando análise básica de timeline.")
        if has_priority_score:
            st.info("💡 Coluna priority_score existe mas não contém valores válidos.")
        if has_criticality:
            st.info("💡 Coluna criticality existe mas não contém valores válidos.")
    
    # Debug: Show which consumption columns are found
    with st.expander("🔍 Debug: Análise de Colunas", expanded=False):
        st.write("**Colunas de consumo detectadas:**")
        for col in ['Média 6 Meses', 'Media_6_Meses', 'media_6_meses', 'Media 6 Meses', 'Consumo 6 Meses', 'consumo_6_meses']:
            if col in df.columns:
                non_zero = len(df[df[col] > 0]) if pd.api.types.is_numeric_dtype(df[col]) else 0
                total = len(df[df[col].notna()]) if col in df.columns else 0
                st.write(f"- {col}: {non_zero} valores > 0 de {total} total")
        
        if 'monthly_volume' in df.columns:
            non_zero = len(df[df['monthly_volume'] > 0]) if pd.api.types.is_numeric_dtype(df['monthly_volume']) else 0
            total = len(df[df['monthly_volume'].notna()])
            st.write(f"- monthly_volume: {non_zero} valores > 0 de {total} total")
        
        # Show sample of first product's data
        if len(df) > 0:
            st.write("\n**Exemplo do primeiro produto:**")
            first_row = df.iloc[0]
            st.write(f"- Produto: {first_row.get('Produto', 'N/A')}")
            st.write(f"- Estoque: {first_row.get('Estoque', 'N/A')}")
            for col in ['Média 6 Meses', 'Media_6_Meses', 'media_6_meses']:
                if col in first_row.index:
                    st.write(f"- {col}: {first_row.get(col, 'N/A')}")
    
    # Prepare data for timeline analysis
    timeline_data = []
    hoje = datetime.now()
    
    for idx, row in df.iterrows():
        # Skip empty rows
        produto = str(row.get('Produto', '')).strip()
        if not produto or produto == 'nan':
            continue
        
        # Get basic data - handle multiple column name formats
        estoque = float(row.get('Estoque', 0) or 0)
        
        # Handle different naming conventions for monthly average
        media_mensal = 0
        media_col_found = None
        
        # First try standard consumption columns
        standard_cols_checked = False
        for col in ['Média 6 Meses', 'Media_6_Meses', 'media_6_meses', 'Media 6 Meses', 'Consumo 6 Meses', 'consumo_6_meses']:
            if col in row.index:
                standard_cols_checked = True
                try:
                    value = float(row.get(col, 0) or 0)
                    # Even if value is 0, we found the standard column, so use it
                    media_mensal = value
                    media_col_found = col
                    break
                except (ValueError, TypeError):
                    continue
        
        # Only use monthly_volume if NO standard columns exist at all
        if not standard_cols_checked and 'monthly_volume' in row.index:
            try:
                # monthly_volume is the sales volume from priority analysis
                monthly_vol = float(row.get('monthly_volume', 0) or 0)
                media_mensal = monthly_vol
                media_col_found = 'monthly_volume'
            except (ValueError, TypeError):
                pass
        
        # If still no column found, try other consumption-related columns
        if not standard_cols_checked and media_col_found is None:
            for col in df.columns:
                if any(keyword in col.lower() for keyword in ['media', 'consumo', 'vendas', 'average']):
                    try:
                        value = float(row.get(col, 0) or 0)
                        media_mensal = value
                        media_col_found = col
                        break
                    except (ValueError, TypeError):
                        continue
        
        moq = float(row.get('MOQ', 0) or 0)
        
        # Handle supplier column variations - check UltimoFornecedor first since it's in merged Excel
        fornecedor = 'Brazil'
        for col in ['UltimoFornecedor', 'ultimo_fornecedor', 'UltimoFor']:
            if col in row.index:
                value = str(row.get(col, 'Brazil'))
                if value and value.strip() and value.lower() not in ['nan', 'none', '']:
                    fornecedor = value
                    break
        
        # Handle price column variations
        preco = 0
        for col in ['preco_unitario', 'Preco_Unitario', 'preco_unitário']:
            if col in row.index:
                preco = float(row.get(col, 0) or 0)
                if preco > 0:
                    break
        
        # Get priority data if available
        priority_score = float(row.get('priority_score', 0) or 0)
        criticality = str(row.get('criticality', 'N/A'))
        relevance_class = str(row.get('relevance_class', 'N/A'))
        annual_impact = float(row.get('annual_impact', 0) or 0)
        
        # Get additional timeline data from merged Excel
        estoque_cobertura = float(row.get('Estoque Cobertura', row.get('Estoque_Cobertura', 0)) or 0)
        qtde_embarque = float(row.get('Qtde Embarque', row.get('Qtde_Embarque', 0)) or 0)
        previsao = float(row.get('Previsão', row.get('Previsao', 0)) or 0)
        
        # Calculate timeline metrics
        # Handle case where there's no consumption data
        if media_mensal == 0:
            # For products with no consumption, check if they're critical and have stock
            if estoque > 0 and criticality in ['🔴 Critical', '🟡 High', '🟠 Medium']:
                # Show them as monitoring with special handling
                dias_ate_pedido = 3650  # 10 years - effectively "no urgency" 
                data_pedido = hoje + timedelta(days=3650)
                data_esgotamento = hoje + timedelta(days=3650)
                urgencia = 'MONITORAR'
                cor = '#32CD32'
                meses_cobertura = 999
                
                # Still add to timeline for visibility
                timeline_data.append({
                    'Produto': produto,
                    'Fornecedor': fornecedor,
                    'Estoque_Atual': estoque,
                    'Media_Mensal': media_mensal,
                    'Meses_Cobertura': meses_cobertura,
                    'Dias_Ate_Pedido': dias_ate_pedido,
                    'Data_Pedido': 'Sem consumo',
                    'Data_Esgotamento': 'Sem consumo',
                    'MOQ': moq,
                    'Qtd_MOQ': moq if moq > 0 else 0,
                    'Qtd_Negotiated': 0,
                    'Qtd_Ideal': 0,
                    'Investimento_MOQ': moq * preco if moq > 0 and preco > 0 else 0,
                    'Investimento_Negotiated': 0,
                    'Investimento_Ideal': 0,
                    'Preco_Unit': preco,
                    'Priority_Score': priority_score,
                    'Criticality': criticality,
                    'Relevance': relevance_class,
                    'Annual_Impact': annual_impact,
                    'Urgencia': urgencia,
                    'Cor': cor,
                    'Lead_Time': 0
                })
        else:
            # Normal calculation when there's consumption data
            # Use Estoque Cobertura if available, otherwise calculate
            if estoque_cobertura > 0:
                meses_cobertura = estoque_cobertura
            else:
                meses_cobertura = estoque / media_mensal
                
            dias_restantes = int(meses_cobertura * 30)
            
            # Determine lead time based on criticality
            if criticality in ['🔴 Critical', '🟡 High', '🟠 Medium']:
                lead_time_days = 120  # 4 months advance
            else:
                lead_time_days = 90   # 3 months advance
            
            # Calculate when to order
            # Add bounds checking to prevent overflow
            max_days = 365 * 10  # Max 10 years
            dias_restantes = min(dias_restantes, max_days)
            
            # For critical products, check if we need to order now
            if dias_restantes <= lead_time_days:
                # We're already within or past the lead time - order NOW
                dias_ate_pedido = 0
                data_pedido = hoje
                data_esgotamento = hoje + timedelta(days=dias_restantes)
                urgencia = 'COMPRAR AGORA'
                cor = '#FF0000'
            else:
                try:
                    data_esgotamento = hoje + timedelta(days=dias_restantes)
                    data_pedido = data_esgotamento - timedelta(days=lead_time_days)
                    dias_ate_pedido = (data_pedido - hoje).days
                    
                    # Determine urgency based on days until order
                    if dias_ate_pedido <= 0:
                        urgencia = 'COMPRAR AGORA'
                        cor = '#FF0000'
                        data_pedido = hoje  # Reset to today
                        dias_ate_pedido = 0
                    elif dias_ate_pedido <= 30:
                        urgencia = 'URGENTE'
                        cor = '#FF8C00'
                    elif dias_ate_pedido <= 60:
                        urgencia = 'PRÓXIMO MÊS'
                        cor = '#FFD700'
                    else:
                        urgencia = 'MONITORAR'
                        cor = '#32CD32'
                        
                except OverflowError:
                    # If overflow, set to max reasonable values
                    data_esgotamento = hoje + timedelta(days=max_days)
                    data_pedido = hoje + timedelta(days=max_days - lead_time_days)
                    dias_ate_pedido = max_days - lead_time_days
                    urgencia = 'MONITORAR'
                    cor = '#32CD32'
            
            # Calculate three scenarios: MOQ, Negotiated, Ideal
            # Scenario 1: MOQ (minimum order)
            qtd_moq = moq if moq > 0 else 50
            
            # Scenario 2: Negotiated (based on 4-6 months coverage)
            qtd_negotiated = media_mensal * 5  # 5 months average
            if moq > 0 and qtd_negotiated < moq:
                qtd_negotiated = moq
            qtd_negotiated = int(np.ceil(qtd_negotiated / 10) * 10)  # Round to 10s
            
            # Scenario 3: Ideal (based on 6 months coverage)
            qtd_ideal = media_mensal * 6
            if moq > 0:
                multiplos = max(1, int(np.ceil(qtd_ideal / moq)))
                qtd_ideal = multiplos * moq
            else:
                qtd_ideal = int(np.ceil(qtd_ideal / 50) * 50)  # Round to 50s
            
            # Calculate investments for each scenario
            investimento_moq = qtd_moq * preco if preco > 0 else 0
            investimento_negotiated = qtd_negotiated * preco if preco > 0 else 0
            investimento_ideal = qtd_ideal * preco if preco > 0 else 0
            
            timeline_data.append({
                'Produto': produto,
                'Fornecedor': fornecedor,
                'Estoque_Atual': estoque,
                'Media_Mensal': media_mensal,
                'Meses_Cobertura': meses_cobertura,
                'Dias_Ate_Pedido': dias_ate_pedido,
                'Data_Pedido': data_pedido.strftime('%d/%m/%Y') if isinstance(data_pedido, datetime) else data_pedido,
                'Data_Esgotamento': data_esgotamento.strftime('%d/%m/%Y') if isinstance(data_esgotamento, datetime) else data_esgotamento,
                'MOQ': moq,
                'Qtd_MOQ': qtd_moq,
                'Qtd_Negotiated': qtd_negotiated,
                'Qtd_Ideal': qtd_ideal,
                'Investimento_MOQ': investimento_moq,
                'Investimento_Negotiated': investimento_negotiated,
                'Investimento_Ideal': investimento_ideal,
                'Preco_Unit': preco,
                'Priority_Score': priority_score,
                'Criticality': criticality,
                'Relevance': relevance_class,
                'Annual_Impact': annual_impact,
                'Urgencia': urgencia,
                'Cor': cor,
                'Lead_Time': lead_time_days
            })
    
    if not timeline_data:
        st.warning("⚠️ Nenhum produto com dados suficientes para análise de timeline.")
        st.info("💡 Verifique se o Excel contém as colunas: Produto, Estoque, Média 6 Meses (ou Media_6_Meses)")
        
        # Enhanced debugging information
        st.subheader("🔍 Diagnóstico de Dados")
        
        # Show column analysis
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Colunas relacionadas a consumo encontradas:**")
            consumo_cols = [col for col in df.columns if any(keyword in col.lower() for keyword in ['media', 'consumo', 'vendas', 'average'])]
            if consumo_cols:
                for col in consumo_cols:
                    non_zero_count = len(df[df[col] > 0]) if pd.api.types.is_numeric_dtype(df[col]) else 0
                    st.write(f"- {col}: {non_zero_count} valores > 0")
            else:
                st.write("❌ Nenhuma coluna de consumo encontrada")
        
        with col2:
            st.write("**Análise de produtos:**")
            produtos_validos = len(df[df['Produto'].notna() & (df['Produto'] != 'nan')])
            st.write(f"- Produtos válidos: {produtos_validos}")
            
            if 'Estoque' in df.columns:
                estoque_positivo = len(df[df['Estoque'] > 0])
                st.write(f"- Com estoque > 0: {estoque_positivo}")
        
        # Show sample of data for debugging
        if len(df) > 0:
            st.write("📋 Amostra dos dados:")
            st.dataframe(df.head(3))
        return
    
    # Debug: Show summary of consumption column usage
    with st.expander("📊 Debug: Uso de Colunas de Consumo", expanded=False):
        # Count which columns were used
        column_usage = {}
        for item in timeline_data:
            col_used = "Não detectada"
            # Check which column was actually used based on the media value
            if item['Media_Mensal'] > 0:
                # Try to identify which column it came from
                produto_idx = df[df['Produto'] == item['Produto']].index
                if len(produto_idx) > 0:
                    row = df.loc[produto_idx[0]]
                    for col in ['Média 6 Meses', 'Media_6_Meses', 'media_6_meses', 'Media 6 Meses', 'Consumo 6 Meses', 'consumo_6_meses', 'monthly_volume']:
                        if col in row.index:
                            try:
                                if float(row.get(col, 0) or 0) == item['Media_Mensal']:
                                    col_used = col
                                    break
                            except:
                                continue
            
            column_usage[col_used] = column_usage.get(col_used, 0) + 1
        
        st.write("**Resumo de uso das colunas:**")
        for col, count in sorted(column_usage.items(), key=lambda x: x[1], reverse=True):
            st.write(f"- {col}: {count} produtos")
        
        total_with_consumption = sum(1 for item in timeline_data if item['Media_Mensal'] > 0)
        total_without_consumption = sum(1 for item in timeline_data if item['Media_Mensal'] == 0)
        st.write(f"\n**Total com consumo:** {total_with_consumption}")
        st.write(f"**Total sem consumo:** {total_without_consumption}")
    
    # Convert to DataFrame for easier manipulation
    timeline_df = pd.DataFrame(timeline_data)
    
    # Sort by priority if available, otherwise by urgency
    if has_priority_data:
        timeline_df = timeline_df.sort_values(['Priority_Score'], ascending=False)
    else:
        timeline_df = timeline_df.sort_values(['Dias_Ate_Pedido'])
    
    # Show scenario selector
    st.subheader("📊 Cenários de Compra")
    scenario = st.radio(
        "Selecione o cenário de análise:",
        ["📦 MOQ (Quantidade Mínima)", "🤝 Negociado (5 meses)", "🎯 Ideal (6 meses)"],
        horizontal=True
    )
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        urgencia_filter = st.selectbox(
            "🚨 Filtrar por Urgência:",
            ['Todos', 'COMPRAR AGORA', 'URGENTE', 'PRÓXIMO MÊS', 'MONITORAR']
        )
    
    with col2:
        if has_priority_data:
            criticality_filter = st.selectbox(
                "🎯 Filtrar por Criticidade:",
                ['Todos'] + timeline_df['Criticality'].unique().tolist()
            )
        else:
            criticality_filter = 'Todos'
    
    with col3:
        fornecedor_filter = st.selectbox(
            "🏭 Filtrar por Fornecedor:",
            ['Todos'] + timeline_df['Fornecedor'].unique().tolist()
        )
    
    # Apply filters
    filtered_df = timeline_df.copy()
    
    if urgencia_filter != 'Todos':
        filtered_df = filtered_df[filtered_df['Urgencia'] == urgencia_filter]
    
    if criticality_filter != 'Todos' and has_priority_data:
        filtered_df = filtered_df[filtered_df['Criticality'] == criticality_filter]
    
    if fornecedor_filter != 'Todos':
        filtered_df = filtered_df[filtered_df['Fornecedor'] == fornecedor_filter]
    
    # Determine which scenario columns to use
    if "MOQ" in scenario:
        qtd_col = 'Qtd_MOQ'
        inv_col = 'Investimento_MOQ'
    elif "Negociado" in scenario:
        qtd_col = 'Qtd_Negotiated'
        inv_col = 'Investimento_Negotiated'
    else:  # Ideal
        qtd_col = 'Qtd_Ideal'
        inv_col = 'Investimento_Ideal'
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    comprar_agora = len(filtered_df[filtered_df['Urgencia'] == 'COMPRAR AGORA'])
    urgentes = len(filtered_df[filtered_df['Urgencia'] == 'URGENTE'])
    proximo_mes = len(filtered_df[filtered_df['Urgencia'] == 'PRÓXIMO MÊS'])
    investimento_total = filtered_df[inv_col].sum()
    
    col1.metric("🔴 Comprar Agora", comprar_agora)
    col2.metric("🟠 Urgentes", urgentes)
    col3.metric("🟡 Próximo Mês", proximo_mes)
    col4.metric("💰 Investimento Total", f"R$ {investimento_total:,.0f}")
    
    # Show critical products summary
    if comprar_agora > 0 or urgentes > 0:
        with st.expander("⚡ Produtos Críticos - Ação Imediata", expanded=True):
            critical_products = filtered_df[filtered_df['Urgencia'].isin(['COMPRAR AGORA', 'URGENTE'])]
            for _, prod in critical_products.iterrows():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                with col1:
                    st.write(f"**{prod['Produto']}** - {prod['Fornecedor']}")
                with col2:
                    if prod['Dias_Ate_Pedido'] == 0:
                        st.write(f"📅 **PEDIR AGORA**")
                    else:
                        st.write(f"📅 Pedir até: **{prod['Data_Pedido']}**")
                with col3:
                    st.write(f"📦 Qtd: **{prod[qtd_col]:.0f}**")
                with col4:
                    st.write(f"💰 R$ **{prod[inv_col]:,.0f}**")
    
    # Interactive Timeline Chart
    if len(filtered_df) > 0:
        # Limit display to top 30 for readability
        display_df = filtered_df.head(30)
        
        # Create figure with subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                '📅 Timeline de Pedidos', 
                '📦 Quantidades por Cenário',
                '💰 Investimento por Cenário',
                '📊 Análise de Lead Time'
            ),
            row_heights=[0.5, 0.5],
            specs=[[{"colspan": 2}, None],
                   [{}, {}]]
        )
        
        # 1. Timeline bar chart (main chart spanning 2 columns)
        fig.add_trace(
            go.Bar(
                y=display_df['Produto'],
                x=display_df['Dias_Ate_Pedido'],
                orientation='h',
                marker_color=display_df['Cor'],
                text=[f"{dias} dias<br>{urg}" for dias, urg in zip(display_df['Dias_Ate_Pedido'], display_df['Urgencia'])],
                textposition='auto',
                hovertemplate=(
                    '<b>%{y}</b><br>' +
                    'Dias até pedido: %{x}<br>' +
                    'Data do pedido: %{customdata[0]}<br>' +
                    'Data esgotamento: %{customdata[1]}<br>' +
                    'Estoque atual: %{customdata[2]:.0f}<br>' +
                    'Consumo mensal: %{customdata[3]:.1f}<br>' +
                    'Cobertura: %{customdata[4]:.1f} meses<br>' +
                    'Lead time: %{customdata[5]} dias<br>' +
                    '<extra></extra>'
                ),
                customdata=np.column_stack((
                    display_df['Data_Pedido'],
                    display_df['Data_Esgotamento'],
                    display_df['Estoque_Atual'],
                    display_df['Media_Mensal'],
                    display_df['Meses_Cobertura'],
                    display_df['Lead_Time']
                )),
                name='Timeline'
            ),
            row=1, col=1
        )
        
        # 2. Quantity comparison chart
        fig.add_trace(
            go.Bar(
                y=display_df['Produto'],
                x=display_df['Qtd_MOQ'],
                orientation='h',
                marker_color='lightcoral',
                name='MOQ',
                showlegend=True,
                hovertemplate='<b>%{y}</b><br>MOQ: %{x:.0f}<extra></extra>'
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Bar(
                y=display_df['Produto'],
                x=display_df['Qtd_Negotiated'],
                orientation='h',
                marker_color='lightblue',
                name='Negociado',
                showlegend=True,
                hovertemplate='<b>%{y}</b><br>Negociado: %{x:.0f}<extra></extra>'
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Bar(
                y=display_df['Produto'],
                x=display_df['Qtd_Ideal'],
                orientation='h',
                marker_color='lightgreen',
                name='Ideal',
                showlegend=True,
                hovertemplate='<b>%{y}</b><br>Ideal: %{x:.0f}<extra></extra>'
            ),
            row=2, col=1
        )
        
        # 3. Investment comparison chart
        fig.add_trace(
            go.Bar(
                y=display_df['Produto'],
                x=display_df['Investimento_MOQ'],
                orientation='h',
                marker_color='salmon',
                name='Inv. MOQ',
                showlegend=True,
                text=[f'R$ {x:,.0f}' for x in display_df['Investimento_MOQ']],
                textposition='auto',
                hovertemplate='<b>%{y}</b><br>Investimento MOQ: R$ %{x:,.2f}<extra></extra>'
            ),
            row=2, col=2
        )
        
        fig.add_trace(
            go.Bar(
                y=display_df['Produto'],
                x=display_df['Investimento_Negotiated'],
                orientation='h',
                marker_color='skyblue',
                name='Inv. Negociado',
                showlegend=True,
                text=[f'R$ {x:,.0f}' for x in display_df['Investimento_Negotiated']],
                textposition='auto',
                hovertemplate='<b>%{y}</b><br>Investimento Negociado: R$ %{x:,.2f}<extra></extra>'
            ),
            row=2, col=2
        )
        
        fig.add_trace(
            go.Bar(
                y=display_df['Produto'],
                x=display_df['Investimento_Ideal'],
                orientation='h',
                marker_color='mediumseagreen',
                name='Inv. Ideal',
                showlegend=True,
                text=[f'R$ {x:,.0f}' for x in display_df['Investimento_Ideal']],
                textposition='auto',
                hovertemplate='<b>%{y}</b><br>Investimento Ideal: R$ %{x:,.2f}<extra></extra>'
            ),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            title=f'📊 Timeline de Compras Prioritário - {empresa}',
            height=max(800, len(display_df) * 25),
            showlegend=True,
            barmode='group'
        )
        
        # Update axes
        fig.update_xaxes(title_text="Dias até Pedido", row=1, col=1)
        fig.update_xaxes(title_text="Quantidade", row=2, col=1)
        fig.update_xaxes(title_text="Investimento (R$)", row=2, col=2)
        
        # Add zero line to timeline
        fig.add_vline(x=0, line_dash="dash", line_color="red", row=1, col=1)
        fig.add_annotation(
            x=0, y=len(display_df)/2,
            text="Prazo Limite",
            showarrow=True,
            arrowhead=2,
            row=1, col=1
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Detailed table with priority information
    st.subheader("📋 Detalhamento de Compras")
    
    # Select columns to display based on selected scenario
    base_columns = ['Produto', 'Fornecedor', 'Urgencia', 'Data_Pedido', 'Dias_Ate_Pedido']
    
    if "MOQ" in scenario:
        scenario_columns = ['Qtd_MOQ', 'Investimento_MOQ']
    elif "Negociado" in scenario:
        scenario_columns = ['Qtd_Negotiated', 'Investimento_Negotiated']
    else:
        scenario_columns = ['Qtd_Ideal', 'Investimento_Ideal']
    
    extra_columns = ['MOQ', 'Preco_Unit', 'Estoque_Atual', 'Media_Mensal']
    
    if has_priority_data:
        priority_columns = ['Priority_Score', 'Criticality', 'Annual_Impact']
    else:
        priority_columns = []
    
    display_columns = base_columns + scenario_columns + extra_columns + priority_columns
    
    # Format the dataframe for display
    display_timeline_df = filtered_df[display_columns].copy()
    
    # Rename columns for better display
    column_rename = {
        'Qtd_MOQ': 'Qtd (MOQ)',
        'Qtd_Negotiated': 'Qtd (Negociado)',
        'Qtd_Ideal': 'Qtd (Ideal)',
        'Investimento_MOQ': 'Invest. (MOQ)',
        'Investimento_Negotiated': 'Invest. (Negociado)', 
        'Investimento_Ideal': 'Invest. (Ideal)',
        'Preco_Unit': 'Preço Unit.',
        'Media_Mensal': 'Consumo Mensal',
        'Estoque_Atual': 'Estoque'
    }
    
    display_timeline_df = display_timeline_df.rename(columns=column_rename)
    
    # Format numeric columns
    for col in display_timeline_df.columns:
        if 'Invest.' in col:
            display_timeline_df[col] = display_timeline_df[col].apply(lambda x: f'R$ {x:,.2f}')
        elif 'Annual_Impact' in col:
            display_timeline_df[col] = display_timeline_df[col].apply(lambda x: f'R$ {x:,.2f}')
        elif 'Priority_Score' in col:
            display_timeline_df[col] = display_timeline_df[col].round(3)
        elif col in ['Preço Unit.', 'Consumo Mensal', 'Estoque']:
            display_timeline_df[col] = display_timeline_df[col].round(2)
    
    st.dataframe(
        display_timeline_df,
        use_container_width=True,
        height=400,
        hide_index=True
    ) 