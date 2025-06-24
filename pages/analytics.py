import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

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
            'UltimoFor': 'UltimoFornecedor'  # NEW MAPPING
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns and new_col not in df.columns:
                df_processed[new_col] = df[old_col]
        
        # Calculate Estoque Cobertura if missing
        if 'Estoque Cobertura' not in df_processed.columns:
            if 'Estoque' in df_processed.columns and 'Média 6 Meses' in df_processed.columns:
                df_processed['Estoque Cobertura'] = df_processed.apply(
                    lambda row: row['Estoque'] / row['Média 6 Meses'] if row['Média 6 Meses'] > 0 else 999, 
                    axis=1
                )
        
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
        fornecedor = row.get('UltimoFornecedor', 'Brazil') if 'UltimoFornecedor' in row.index else 'Brazil'
        
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
    
    # Check if we have priority data
    has_priority_data = 'priority_score' in df.columns and df['priority_score'].notna().any()
    
    if has_priority_data:
        st.success("✅ Dados de prioridade detectados! Usando análise prioritária 85/15.")
    else:
        st.info("📊 Dados de prioridade não encontrados. Usando análise básica de timeline.")
    
    # Prepare data for timeline analysis
    timeline_data = []
    hoje = datetime.now()
    
    for idx, row in df.iterrows():
        # Skip empty rows
        produto = str(row.get('Produto', '')).strip()
        if not produto or produto == 'nan':
            continue
        
        # Get basic data
        estoque = float(row.get('Estoque', 0) or 0)
        media_mensal = float(row.get('Media_6_Meses', row.get('Média 6 Meses', 0)) or 0)
        moq = float(row.get('MOQ', 0) or 0)
        fornecedor = str(row.get('ultimo_fornecedor', row.get('UltimoFornecedor', 'Brazil')))
        preco = float(row.get('preco_unitario', row.get('Preco_Unitario', 0)) or 0)
        
        # Get priority data if available
        priority_score = float(row.get('priority_score', 0) or 0)
        criticality = str(row.get('criticality', 'N/A'))
        relevance_class = str(row.get('relevance_class', 'N/A'))
        annual_impact = float(row.get('annual_impact', 0) or 0)
        
        # Calculate timeline metrics
        if media_mensal > 0:
            meses_cobertura = estoque / media_mensal
            dias_restantes = int(meses_cobertura * 30)
            
            # Determine lead time based on criticality
            if criticality in ['🔴 Critical', '🟡 High', '🟠 Medium']:
                lead_time_days = 120  # 4 months advance
            else:
                lead_time_days = 90   # 3 months advance
            
            # Calculate when to order
            data_esgotamento = hoje + timedelta(days=dias_restantes)
            data_pedido = data_esgotamento - timedelta(days=lead_time_days)
            dias_ate_pedido = (data_pedido - hoje).days
            
            # Calculate optimal quantity (6 months target)
            qtd_ideal = media_mensal * 6
            if moq > 0:
                multiplos = max(1, int(np.ceil(qtd_ideal / moq)))
                qtd_comprar = multiplos * moq
            else:
                qtd_comprar = int(np.ceil(qtd_ideal / 50) * 50)  # Round to 50s
            
            # Calculate investment
            investimento = qtd_comprar * preco if preco > 0 else 0
            
            # Determine urgency
            if dias_ate_pedido <= 0:
                urgencia = 'COMPRAR AGORA'
                cor = '#FF0000'
            elif dias_ate_pedido <= 30:
                urgencia = 'URGENTE'
                cor = '#FF8C00'
            elif dias_ate_pedido <= 60:
                urgencia = 'PRÓXIMO MÊS'
                cor = '#FFD700'
            else:
                urgencia = 'MONITORAR'
                cor = '#32CD32'
            
            timeline_data.append({
                'Produto': produto,
                'Fornecedor': fornecedor,
                'Estoque_Atual': estoque,
                'Media_Mensal': media_mensal,
                'Meses_Cobertura': meses_cobertura,
                'Dias_Ate_Pedido': dias_ate_pedido,
                'MOQ': moq,
                'Qtd_Comprar': qtd_comprar,
                'Investimento': investimento,
                'Preco_Unit': preco,
                'Priority_Score': priority_score,
                'Criticality': criticality,
                'Relevance': relevance_class,
                'Annual_Impact': annual_impact,
                'Urgencia': urgencia,
                'Cor': cor
            })
    
    if not timeline_data:
        st.warning("⚠️ Nenhum produto com dados suficientes para análise de timeline.")
        return
    
    # Convert to DataFrame for easier manipulation
    timeline_df = pd.DataFrame(timeline_data)
    
    # Sort by priority if available, otherwise by urgency
    if has_priority_data:
        timeline_df = timeline_df.sort_values(['Priority_Score'], ascending=False)
    else:
        timeline_df = timeline_df.sort_values(['Dias_Ate_Pedido'])
    
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
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    comprar_agora = len(filtered_df[filtered_df['Urgencia'] == 'COMPRAR AGORA'])
    urgentes = len(filtered_df[filtered_df['Urgencia'] == 'URGENTE'])
    proximo_mes = len(filtered_df[filtered_df['Urgencia'] == 'PRÓXIMO MÊS'])
    investimento_total = filtered_df['Investimento'].sum()
    
    col1.metric("🔴 Comprar Agora", comprar_agora)
    col2.metric("🟠 Urgentes", urgentes)
    col3.metric("🟡 Próximo Mês", proximo_mes)
    col4.metric("💰 Investimento", f"R$ {investimento_total:,.0f}")
    
    # Interactive Timeline Chart
    if len(filtered_df) > 0:
        # Limit display to top 50 for readability
        display_df = filtered_df.head(50)
        
        # Create figure with subplots
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('📅 Dias até Pedido', '💰 Investimento Necessário'),
            column_widths=[0.6, 0.4]
        )
        
        # Timeline bar chart
        fig.add_trace(
            go.Bar(
                y=display_df['Produto'],
                x=display_df['Dias_Ate_Pedido'],
                orientation='h',
                marker_color=display_df['Cor'],
                text=display_df['Urgencia'],
                textposition='auto',
                hovertemplate=(
                    '<b>%{y}</b><br>' +
                    'Dias até pedido: %{x}<br>' +
                    'Urgência: %{text}<br>' +
                    'Estoque: %{customdata[0]:.0f}<br>' +
                    'Consumo: %{customdata[1]:.1f}/mês<br>' +
                    'Cobertura: %{customdata[2]:.1f} meses<br>' +
                    '<extra></extra>'
                ),
                customdata=np.column_stack((
                    display_df['Estoque_Atual'],
                    display_df['Media_Mensal'],
                    display_df['Meses_Cobertura']
                ))
            ),
            row=1, col=1
        )
        
        # Investment bar chart
        fig.add_trace(
            go.Bar(
                y=display_df['Produto'],
                x=display_df['Investimento'],
                orientation='h',
                marker_color='lightblue',
                text=[f'R$ {x:,.0f}' for x in display_df['Investimento']],
                textposition='auto',
                hovertemplate=(
                    '<b>%{y}</b><br>' +
                    'Investimento: R$ %{x:,.2f}<br>' +
                    'Quantidade: %{customdata[0]:.0f}<br>' +
                    'Preço Unit: R$ %{customdata[1]:.2f}<br>' +
                    'MOQ: %{customdata[2]:.0f}<br>' +
                    '<extra></extra>'
                ),
                customdata=np.column_stack((
                    display_df['Qtd_Comprar'],
                    display_df['Preco_Unit'],
                    display_df['MOQ']
                ))
            ),
            row=1, col=2
        )
        
        # Update layout
        fig.update_layout(
            title=f'Timeline de Compras - {empresa} (Top 50 produtos)',
            height=max(600, len(display_df) * 20),
            showlegend=False
        )
        
        fig.update_xaxes(title_text="Dias até Pedido", row=1, col=1)
        fig.update_xaxes(title_text="Investimento (R$)", row=1, col=2)
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Detailed table with priority information
    st.subheader("📋 Detalhamento de Compras")
    
    # Select columns to display based on available data
    if has_priority_data:
        display_columns = [
            'Produto', 'Fornecedor', 'Urgencia', 'Dias_Ate_Pedido',
            'Qtd_Comprar', 'MOQ', 'Investimento', 'Priority_Score',
            'Criticality', 'Annual_Impact'
        ]
    else:
        display_columns = [
            'Produto', 'Fornecedor', 'Urgencia', 'Dias_Ate_Pedido',
            'Qtd_Comprar', 'MOQ', 'Investimento', 'Estoque_Atual',
            'Media_Mensal', 'Meses_Cobertura'
        ]
    
    # Format the dataframe for display
    display_timeline_df = filtered_df[display_columns].copy()
    
    # Format numeric columns
    if 'Investimento' in display_timeline_df.columns:
        display_timeline_df['Investimento'] = display_timeline_df['Investimento'].apply(lambda x: f'R$ {x:,.2f}')
    if 'Annual_Impact' in display_timeline_df.columns:
        display_timeline_df['Annual_Impact'] = display_timeline_df['Annual_Impact'].apply(lambda x: f'R$ {x:,.2f}')
    if 'Priority_Score' in display_timeline_df.columns:
        display_timeline_df['Priority_Score'] = display_timeline_df['Priority_Score'].round(3)
    
    st.dataframe(
        display_timeline_df,
        use_container_width=True,
        height=400,
        hide_index=True
    )
    
    # Export options
    col1, col2 = st.columns(2)
    
    with col1:
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 Baixar Timeline CSV",
            data=csv,
            file_name=f'timeline_prioritario_{empresa}_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.csv',
            mime='text/csv',
            use_container_width=True
        )
    
    with col2:
        # Create purchase order summary
        if len(filtered_df[filtered_df['Urgencia'].isin(['COMPRAR AGORA', 'URGENTE'])]) > 0:
            urgent_items = filtered_df[filtered_df['Urgencia'].isin(['COMPRAR AGORA', 'URGENTE'])]
            
            summary_text = f"""ORDEM DE COMPRA - {empresa}
Data: {datetime.now().strftime('%d/%m/%Y')}

ITENS URGENTES:
{'='*50}
"""
            for _, item in urgent_items.iterrows():
                summary_text += f"""
Produto: {item['Produto']}
Fornecedor: {item['Fornecedor']}
Quantidade: {item['Qtd_Comprar']:.0f} unidades
MOQ: {item['MOQ']:.0f}
Investimento: R$ {item['Investimento']:,.2f}
{'Priority: ' + item['Criticality'] if has_priority_data else ''}
{'-'*30}
"""
            
            summary_text += f"""
TOTAL URGENTE: R$ {urgent_items['Investimento'].sum():,.2f}
"""
            
            st.download_button(
                label="📝 Baixar Ordem de Compra",
                data=summary_text,
                file_name=f'ordem_compra_{empresa}_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.txt',
                mime='text/plain',
                use_container_width=True
            ) 