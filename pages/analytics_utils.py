"""Helper functions for analytics page."""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import auth

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
        # Handle None/NaN values properly without changing the logic
        if pd.isna(consumo_mensal) or consumo_mensal is None or consumo_mensal <= 0:
            return "Sem consumo", 999
        
        if pd.isna(estoque) or estoque is None:
            estoque = 0
            
        meses_restantes = estoque / consumo_mensal
        
        if meses_restantes <= 0:
            return "JÁ ACABOU", 0
        elif meses_restantes < 0.5:
            dias = int(meses_restantes * 30)
            return f"{dias} dias", meses_restantes
        else:
            return f"{meses_restantes:.1f} meses", meses_restantes
    
    def quanto_comprar(consumo_mensal, estoque_atual, moq=0, meses_desejados=6):
        # Handle None/NaN values
        if pd.isna(consumo_mensal) or consumo_mensal is None or consumo_mensal <= 0:
            return moq if moq > 0 else 0
            
        if pd.isna(estoque_atual) or estoque_atual is None:
            estoque_atual = 0
        
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
    
    # Check if current user is admin to show investment-related charts
    current_user = auth.get_current_user()
    show_admin_charts = current_user and current_user.get('username') == 'admin'
    
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
    
    # REMOVED: Chart 3: Top products to buy - as requested
    
    # Chart 4: Supplier analysis - ADMIN ONLY
    if 'Fornecedor' in suggestions_df.columns and show_admin_charts:
        st.subheader("🏭 Análise por Fornecedor - Admin")
        
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
            # Top suppliers by investment - ADMIN ONLY
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
            # Supplier distribution (always visible)
            fig_supplier_pie = px.pie(
                supplier_analysis.reset_index(),
                values='Produtos',
                names='Fornecedor',
                title='📊 Distribuição de Produtos por Fornecedor'
            )
            st.plotly_chart(fig_supplier_pie, use_container_width=True)
        
        # Show supplier summary table - ADMIN ONLY
        st.dataframe(supplier_analysis, use_container_width=True)
    
    elif 'Fornecedor' in suggestions_df.columns and not show_admin_charts:
        # Show only supplier distribution for non-admin users
        st.subheader("🏭 Distribuição por Fornecedor")
        
        supplier_analysis = suggestions_df.groupby('Fornecedor').agg({
            'Produto': 'count'
        }).round(1)
        supplier_analysis.columns = ['Produtos']
        supplier_analysis = supplier_analysis.sort_values('Produtos', ascending=False)
        
        # Supplier distribution (always visible)
        fig_supplier_pie = px.pie(
            supplier_analysis.reset_index(),
            values='Produtos',
            names='Fornecedor',
            title='📊 Distribuição de Produtos por Fornecedor'
        )
        st.plotly_chart(fig_supplier_pie, use_container_width=True)
    
    # Chart 5: Investment timeline and Product overview
    col1, col2 = st.columns(2)
    
    # Investment timeline - ADMIN ONLY
    if show_admin_charts:
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
                title='💰 Investimento por Período - Admin',
                color='Investimento',
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_invest, use_container_width=True)
        
        # Column 2 for admin users
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
            else:
                # Show total products summary
                st.metric("📦 Total de Produtos", len(produtos_existentes))
                st.metric("🚨 Produtos Críticos", muito_critico + critico)
                st.metric("✅ Produtos OK", ok)
    
    else:
        # For non-admin users, show only product overview in full width
        if len(produtos_novos) > 0:
            col1, col2 = st.columns(2)
            with col1:
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
            
            with col2:
                # Show summary metrics for non-admin users
                st.metric("📦 Total de Produtos", len(produtos_existentes))
                st.metric("🚨 Produtos Críticos", muito_critico + critico)
                st.metric("✅ Produtos OK", ok)
        else:
            # Show metrics only
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📦 Total de Produtos", len(produtos_existentes))
            with col2:
                st.metric("🚨 Produtos Críticos", muito_critico + critico)
            with col3:
                st.metric("✅ Produtos OK", ok)

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
        csv = filtered_df[display_columns].to_csv(index=False, sep=';', encoding='utf-8-sig', decimal=',')
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

    # Determine if the current user is admin to show investment subplot
    current_user = auth.get_current_user()
    # Only show investment data for the specific "admin" username, not "minipa"
    show_investment = current_user and current_user.get('username') == 'admin'
    
    # Debug: Show available columns
    # st.info(f"🔍 Colunas disponíveis: {', '.join(df.columns[:15])}...")
    
    # Enhanced priority data detection with debugging
    has_priority_score = 'priority_score' in df.columns
    has_criticality = 'criticality' in df.columns
    has_priority_values = False
    
    if has_priority_score:
        priority_values = df['priority_score'].dropna()
        has_priority_values = len(priority_values) > 0
        # st.info(f"🔍 Priority Score: Coluna existe: {has_priority_score}, Valores não-nulos: {len(priority_values)}")
    
    if has_criticality:
        criticality_values = df['criticality'].dropna()
        # st.info(f"🔍 Criticality: Coluna existe: {has_criticality}, Valores não-nulos: {len(criticality_values)}")
    
    # Check if we have priority data - more flexible detection
    has_priority_data = (has_priority_score and has_priority_values) or (has_criticality and len(df['criticality'].dropna()) > 0)
    
    if has_priority_data:
        st.success("✅ Dados de prioridade detectados! Usando análise prioritária 85/15.")
    else:
        st.info("📊 Dados de prioridade não encontrados. Usando análise básica de timeline.")
        # if has_priority_score:
        #     st.info("💡 Coluna priority_score existe mas não contém valores válidos.")
        # if has_criticality:
        #     st.info("💡 Coluna criticality existe mas não contém valores válidos.")
    
    # Debug: Show which consumption columns are found
    # with st.expander("🔍 Debug: Análise de Colunas", expanded=False):
    #     st.write("**Colunas de consumo detectadas:**")
    #     for col in ['Média 6 Meses', 'Media_6_Meses', 'media_6_meses', 'Media 6 Meses', 'Consumo 6 Meses', 'consumo_6_meses']:
    #         if col in df.columns:
    #             non_zero = len(df[df[col] > 0]) if pd.api.types.is_numeric_dtype(df[col]) else 0
    #             total = len(df[df[col].notna()]) if col in df.columns else 0
    #             st.write(f"- {col}: {non_zero} valores > 0 de {total} total")
    #     
    #     if 'monthly_volume' in df.columns:
    #         non_zero = len(df[df['monthly_volume'] > 0]) if pd.api.types.is_numeric_dtype(df['monthly_volume']) else 0
    #         total = len(df[df['monthly_volume'].notna()])
    #         st.write(f"- monthly_volume: {non_zero} valores > 0 de {total} total")
    #     
    #     # Show sample of first product's data
    #     if len(df) > 0:
    #         st.write("\n**Exemplo do primeiro produto:**")
    #         first_row = df.iloc[0]
    #         st.write(f"- Produto: {first_row.get('Produto', 'N/A')}")
    #         st.write(f"- Estoque: {first_row.get('Estoque', 'N/A')}")
    #         for col in ['Média 6 Meses', 'Media_6_Meses', 'media_6_meses']:
    #             if col in first_row.index:
    #                 st.write(f"- {col}: {first_row.get(col, 'N/A')}")
    
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
        
        # Handle supplier column variations - check mapped name first, then original names
        fornecedor = 'Brazil'
        for col in ['ultimo_fornecedor', 'UltimoFornecedor', 'UltimoFor']:  # Check mapped name first
            if col in row.index:
                value = str(row[col])  # Use direct indexing instead of .get()
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
        compras_ate_30_dias = float(row.get('Compras Até 30 Dias', row.get('Compras_Ate_30_Dias', 0)) or 0)
        previsao = float(row.get('Previsão', row.get('Previsao', 0)) or 0)
        
        # Calculate expected stock including incoming shipments
        estoque_esperado = estoque + qtde_embarque + compras_ate_30_dias
        
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
                    'Estoque_Esperado': estoque_esperado,
                    'Qtde_Embarque': qtde_embarque,
                    'Compras_Ate_30_Dias': compras_ate_30_dias,
                    'Media_Mensal': media_mensal,
                    'Meses_Cobertura': meses_cobertura,
                    'Meses_Cobertura_Esperada': meses_cobertura + ((qtde_embarque + compras_ate_30_dias) / media_mensal if media_mensal > 0 else 0),
                    'Dias_Ate_Pedido': dias_ate_pedido,
                    'Dias_Restantes_Esperado': 3650,  # No consumption, so large value
                    'Dias_Ate_Pedido_Esperado': 3650,  # No consumption, so large value
                    'Ainda_Urgente_Com_Estoque_Futuro': False,  # No consumption products are not urgent
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
                
            # Calculate expected coverage with incoming inventory
            # FIX: Nova cobertura total = cobertura atual + cobertura adicional
            cobertura_adicional = (qtde_embarque + compras_ate_30_dias) / media_mensal if media_mensal > 0 else 0
            meses_cobertura_esperada = meses_cobertura + cobertura_adicional
            
            dias_restantes = int(meses_cobertura * 30)
            dias_restantes_esperado = int(meses_cobertura_esperada * 30)
            
            # Determine lead time based on criticality
            if criticality in ['🔴 Critical', '🟡 High', '🟠 Medium']:
                lead_time_days = 120  # 4 months advance
            else:
                lead_time_days = 90   # 3 months advance
            
            # Calculate when to order
            # Add bounds checking to prevent overflow
            max_days = 365 * 10  # Max 10 years
            dias_restantes = min(dias_restantes, max_days)
            
            # Calculate when to order - allow negative values for overdue products
            try:
                data_esgotamento = hoje + timedelta(days=dias_restantes)
                data_pedido = data_esgotamento - timedelta(days=lead_time_days)
                dias_ate_pedido = (data_pedido - hoje).days
            except OverflowError:
                # If overflow, set to max reasonable values
                data_esgotamento = hoje + timedelta(days=max_days)
                data_pedido = hoje + timedelta(days=max_days - lead_time_days)
                dias_ate_pedido = max_days - lead_time_days
            
            # SIMPLIFIED urgency logic based on 4-month lead time
            if dias_ate_pedido <= 120:  # 4 months = 120 days
                # Anything within lead time is URGENT
                urgencia = 'URGENTE'
                # Color gradient based on urgency within the 4 months
                if dias_ate_pedido <= 0:
                    cor = '#8B0000'  # Dark red for overdue
                elif dias_ate_pedido <= 30:
                    cor = '#FF0000'  # Red for within 1 month
                elif dias_ate_pedido <= 60:
                    cor = '#FF4500'  # Orange red for within 2 months
                else:
                    cor = '#FFA500'  # Orange for within 4 months
            else:
                urgencia = 'MONITORAR'
                cor = '#32CD32'  # Green
            
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
            
            # Calculate if still urgent with expected stock
            dias_ate_pedido_esperado = dias_restantes_esperado - lead_time_days
            ainda_urgente_com_estoque_futuro = dias_ate_pedido_esperado <= 120  # Still within 4-month lead time
            
            timeline_data.append({
                'Produto': produto,
                'Fornecedor': fornecedor,
                'Estoque_Atual': estoque,
                'Estoque_Esperado': estoque_esperado,
                'Qtde_Embarque': qtde_embarque,
                'Compras_Ate_30_Dias': compras_ate_30_dias,
                'Media_Mensal': media_mensal,
                'Meses_Cobertura': meses_cobertura,
                'Meses_Cobertura_Esperada': meses_cobertura_esperada,
                'Dias_Ate_Pedido': dias_ate_pedido,
                'Dias_Restantes_Esperado': dias_restantes_esperado,
                'Dias_Ate_Pedido_Esperado': dias_ate_pedido_esperado,
                'Ainda_Urgente_Com_Estoque_Futuro': ainda_urgente_com_estoque_futuro,
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
    
    # Debug expander removed for cleaner UI
    
    # Convert to DataFrame for easier manipulation
    timeline_df = pd.DataFrame(timeline_data)
    
    # Sort by days to order to show most urgent first
    timeline_df = timeline_df.sort_values(['Dias_Ate_Pedido'])
    
    # Default scenario - removing the selector as requested
    scenario = "📦 MOQ (Quantidade Mínima)"  # Default to MOQ
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        urgencia_filter = st.selectbox(
            "🚨 Filtrar por Urgência:",
            ['Todos', 'URGENTE', 'MONITORAR']
        )
    
    with col2:
        fornecedor_filter = st.selectbox(
            "🏭 Filtrar por Fornecedor:",
            ['Todos'] + timeline_df['Fornecedor'].unique().tolist()
        )
    
    # Apply filters FIRST to determine the correct max value
    filtered_df = timeline_df.copy()
    
    if urgencia_filter != 'Todos':
        filtered_df = filtered_df[filtered_df['Urgencia'] == urgencia_filter]
    
    if fornecedor_filter != 'Todos':
        filtered_df = filtered_df[filtered_df['Fornecedor'] == fornecedor_filter]
    
    # NEW: Additional filter for urgent products that still need ordering even with incoming stock
    filter_critical_with_incoming = False
    if urgencia_filter == 'URGENTE':
        # Show checkbox only when URGENTE is selected
        st.markdown("---")  # Separator
        filter_critical_with_incoming = st.checkbox(
            "🚨 Mostrar apenas produtos que continuam críticos mesmo com estoque futuro",
            value=False,
            help="Filtra produtos que permanecerão dentro do lead time de 4 meses mesmo após receber pedidos em trânsito"
        )
        
        if filter_critical_with_incoming:
            # Filter products that are still urgent even with incoming stock
            filtered_df = filtered_df[filtered_df['Ainda_Urgente_Com_Estoque_Futuro'] == True]
            st.info(f"🎯 {len(filtered_df)} produtos continuam urgentes mesmo com entregas futuras confirmadas")
            
            # Debug calculations expander removed
    
    with col3:
        # Show top N products selector - now based on filtered results
        if len(filtered_df) > 0:
            # Make "show all" more prominent when there are many filtered products
          
            
            # Add a checkbox to show all
            show_all = st.checkbox(
                f"✅ Mostrar todos os {len(filtered_df)} produtos filtrados", 
                value=False,
                help="Marque para exibir todos os produtos que atendem aos filtros selecionados"
            )
            
            if show_all:
                n_produtos = len(filtered_df)
                st.success(f"✅ Exibindo todos os {n_produtos} produtos filtrados")
            else:
                n_produtos = st.number_input(
                    "📊 Mostrar Top N produtos:",
                    min_value=10,
                    max_value=len(filtered_df),  # Now based on filtered count
                    value=min(50, len(filtered_df)),
                    step=10,
                    help=f"Total disponível após filtros: {len(filtered_df)} produtos"
                )
        else:
            n_produtos = 0
            st.warning("Nenhum produto encontrado com os filtros selecionados")
    
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
    
    # Metrics - simplified
    col1, col2 = st.columns(2)
    
    # Count urgency categories
    urgentes = len(filtered_df[filtered_df['Urgencia'] == 'URGENTE'])
    monitorar = len(filtered_df[filtered_df['Urgencia'] == 'MONITORAR'])
    
    col1.metric("🔴 Urgentes (≤ 4 meses)", urgentes)
    col2.metric("🟢 Monitorar (> 4 meses)", monitorar)
    
    # Show critical products summary
    if urgentes > 0:
        with st.expander("⚡ Produtos Urgentes - Ação Imediata (Lead time ≤ 4 meses)", expanded=False):
            critical_products = filtered_df[filtered_df['Urgencia'] == 'URGENTE']
            for _, prod in critical_products.iterrows():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                with col1:
                    st.write(f"**{prod['Produto']}** - {prod['Fornecedor']}")
                    # Show expected inventory info if available
                    if prod['Qtde_Embarque'] > 0 or prod['Compras_Ate_30_Dias'] > 0:
                        incoming_total = prod['Qtde_Embarque'] + prod['Compras_Ate_30_Dias']
                        st.caption(f"📦 Em trânsito: {incoming_total:.0f} unids (+{prod['Meses_Cobertura_Esperada'] - prod['Meses_Cobertura']:.1f} meses)")
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
        # Debug: Show filtering info
        # Debug info removed
        
        # Limit display based on user selection
        display_df = filtered_df.head(n_produtos)
        
        # Show info about displayed products
        st.success(f"📊 **Exibindo {len(display_df)} produtos** (de {len(filtered_df)} produtos filtrados)")
        if len(display_df) < len(filtered_df):
            st.warning(f"⚠️ Alguns produtos não estão sendo exibidos. Use o seletor acima ou marque 'Mostrar todos' para ver todos os {len(filtered_df)} produtos.")
        
        # Convert days to months and handle negative values for display
        display_df['Meses_Ate_Pedido'] = display_df['Dias_Ate_Pedido'] / 30
        display_df['Meses_Adicional_Embarque'] = display_df.apply(lambda row: 
            (row['Qtde_Embarque'] + row['Compras_Ate_30_Dias']) / row['Media_Mensal'] 
            if row['Media_Mensal'] > 0 else 0, axis=1)
        
        # Debug: Show chart info
        st.write(f"🎯 **Produtos no gráfico:** {len(display_df)} | **Altura do gráfico:** {max(1800, len(display_df) * 80)} pixels | **Pixels por produto:** 80")
        
        # Create figure with vertical subplot layout for better visibility
        rows = 2 if show_investment else 1
        subplot_titles = [
            '📅 Timeline de Pedidos (em meses)'
        ]
        row_heights = [1.0]
        if show_investment:
            subplot_titles.append('💰 Investimento por Cenário')
            row_heights = [0.7, 0.3]

        fig = make_subplots(
            rows=rows, cols=1,
            subplot_titles=tuple(subplot_titles),
            row_heights=row_heights,
            vertical_spacing=0.08
        )
        
        # 1. Timeline bar chart (main chart) - show in months with stacked bar for expected inventory
        # Current inventory coverage (darker colors)
        fig.add_trace(
            go.Bar(
                y=display_df['Produto'],
                x=display_df['Meses_Cobertura'],
                orientation='h',
                marker_color=display_df['Cor'],
                text=[f"{row['Meses_Cobertura']:.1f}m" for _, row in display_df.iterrows()],
                textposition='inside',
                hovertemplate=(
                    '<b>%{y}</b><br>' +
                    '<b>ESTOQUE ATUAL</b><br>' +
                    'Cobertura atual: %{x:.1f} meses<br>' +
                    'Estoque atual: %{customdata[0]:.0f} unidades<br>' +
                    'Consumo mensal: %{customdata[1]:.1f} unidades<br>' +
                    '<extra></extra>'
                ),
                customdata=np.column_stack((
                    display_df['Estoque_Atual'],
                    display_df['Media_Mensal']
                )),
                name='Estoque Atual',
                legendgroup='timeline'
            ),
            row=1, col=1
        )
        
        # Expected incoming inventory coverage (lighter colors) - stacked
        # Create lighter versions of the original colors
        lighter_colors = []
        for color in display_df['Cor']:
            if color == '#8B0000':  # Dark red -> Light red
                lighter_colors.append('#FF6B6B')
            elif color == '#FF0000':  # Red -> Light red
                lighter_colors.append('#FF9999')
            elif color == '#FF4500':  # Orange red -> Light orange
                lighter_colors.append('#FFA500')
            elif color == '#FFD700':  # Gold -> Light yellow
                lighter_colors.append('#FFEB3B')
            elif color == '#32CD32':  # Green -> Light green
                lighter_colors.append('#90EE90')
            else:
                lighter_colors.append(color)
        
        # Add expected inventory only if there's incoming stock
        has_incoming = display_df['Meses_Adicional_Embarque'].sum() > 0
        if has_incoming:
            fig.add_trace(
                go.Bar(
                    y=display_df['Produto'],
                    x=display_df['Meses_Adicional_Embarque'],
                    orientation='h',
                    marker_color=lighter_colors,
                    marker_pattern_shape="/",  # Add pattern to distinguish
                    text=[f"+{row['Meses_Adicional_Embarque']:.1f}m" if row['Meses_Adicional_Embarque'] > 0 else "" 
                          for _, row in display_df.iterrows()],
                    textposition='inside',
                    hovertemplate=(
                        '<b>%{y}</b><br>' +
                        '<b>ESTOQUE ESPERADO</b><br>' +
                        'Cobertura adicional: +%{x:.1f} meses<br>' +
                        'Qtde em trânsito: %{customdata[0]:.0f} unidades<br>' +
                        'Compras até 30 dias: %{customdata[1]:.0f} unidades<br>' +
                        'Total esperado: %{customdata[2]:.0f} unidades<br>' +
                        'Nova cobertura total: %{customdata[4]:.1f} + %{customdata[5]:.1f} = %{customdata[6]:.1f} meses<br>' +
                        '<extra></extra>'
                    ),
                    customdata=np.column_stack((
                        display_df['Qtde_Embarque'],
                        display_df['Compras_Ate_30_Dias'],
                        display_df['Qtde_Embarque'] + display_df['Compras_Ate_30_Dias'],
                        display_df['Meses_Cobertura_Esperada'],
                        display_df['Meses_Cobertura'],
                        display_df['Meses_Adicional_Embarque'],
                        display_df['Meses_Cobertura'] + display_df['Meses_Adicional_Embarque']
                    )),
                    name='Estoque Esperado',
                    legendgroup='timeline'
                ),
                row=1, col=1
            )
        

        
        # 2. Investment comparison chart - only for admins
        if show_investment:
            fig.add_trace(
                go.Bar(
                    y=display_df['Produto'],
                    x=display_df['Investimento_MOQ'],
                    orientation='h',
                    marker_color='#FF6B6B',
                    name='Inv. MOQ',
                    showlegend=True,
                    text=[f'R$ {x:,.0f}' for x in display_df['Investimento_MOQ']],
                    textposition='outside',
                    hovertemplate='<b>%{y}</b><br>Investimento MOQ: R$ %{x:,.2f}<extra></extra>'
                ),
                row=2, col=1
            )

            fig.add_trace(
                go.Bar(
                    y=display_df['Produto'],
                    x=display_df['Investimento_Negotiated'],
                    orientation='h',
                    marker_color='#4ECDC4',
                    name='Inv. Negociado',
                    showlegend=True,
                    text=[f'R$ {x:,.0f}' for x in display_df['Investimento_Negotiated']],
                    textposition='outside',
                    hovertemplate='<b>%{y}</b><br>Investimento Negociado: R$ %{x:,.2f}<extra></extra>'
                ),
                row=2, col=1
            )
            
            fig.add_trace(
                go.Bar(
                    y=display_df['Produto'],
                    x=display_df['Investimento_Ideal'],
                    orientation='h',
                    marker_color='#45B7D1',
                    name='Inv. Ideal',
                    showlegend=True,
                    text=[f'R$ {x:,.0f}' for x in display_df['Investimento_Ideal']],
                    textposition='outside',
                    hovertemplate='<b>%{y}</b><br>Investimento Ideal: R$ %{x:,.2f}<extra></extra>'
                ),
                row=2, col=1
            )
        
        # Update layout - make graphs much taller for better visibility
        # Increased height per product to ensure proper alignment
        layout_kwargs = dict(
            title=f'📊 Timeline de Compras - {empresa}',
            height=max(1800, len(display_df) * 80),
            showlegend=True,
            barmode='stack',
            font=dict(size=14),
            margin=dict(l=300, r=100, t=100, b=100),
            yaxis=dict(tickmode='array', tickvals=display_df['Produto'].tolist(), ticktext=display_df['Produto'].tolist()),
        )
        if show_investment:
            layout_kwargs['yaxis2'] = dict(tickmode='array', tickvals=display_df['Produto'].tolist(), ticktext=display_df['Produto'].tolist())

        fig.update_layout(**layout_kwargs)
        
        # Update axes
        fig.update_xaxes(title_text="Meses até Pedido", row=1, col=1, title_font_size=14)
        if show_investment:
            fig.update_xaxes(title_text="Investimento (R$)", row=2, col=1, title_font_size=14, tickformat=",.0f")
        
        # Set barmode for each subplot individually
        # Row 1 (timeline) should be stacked, row 2 should be grouped
        fig.update_traces(row=1, col=1, offsetgroup=1)
        if show_investment:
            fig.update_traces(row=2, col=1, offsetgroup=2)
        
        # Update y-axes to show all products with proper alignment
        # Fix alignment issue by ensuring consistent y-axis configuration
        rows_iter = [1] + ([2] if show_investment else [])
        for row_num in rows_iter:
            fig.update_yaxes(
                tickfont_size=13, 
                row=row_num, 
                col=1,
                automargin=True,  # Auto adjust margins
                fixedrange=True,  # Prevent zooming which can cause misalignment
                categoryorder='array',  # Ensure consistent ordering
                categoryarray=display_df['Produto'].tolist()  # Explicit product order
            )
        
        # Add zero line to timeline at 4 months (lead time threshold)
        fig.add_vline(x=4, line_dash="dash", line_color="orange", row=1, col=1)
        fig.add_annotation(
            x=4, y=len(display_df)-1,
            text="Lead Time (4 meses)",
            showarrow=True,
            arrowhead=2,
            row=1, col=1,
            font=dict(color="orange", size=12)
        )
        
        # Add zero line
        fig.add_vline(x=0, line_dash="solid", line_color="red", line_width=2, row=1, col=1)
        fig.add_annotation(
            x=0, y=0,
            text="Prazo Esgotado",
            showarrow=True,
            arrowhead=2,
            row=1, col=1,
            font=dict(color="red", size=12, weight="bold"),
            xshift=-10
        )
        
        # Check if we have overdue products to show
        min_months = display_df['Meses_Ate_Pedido'].min()
        if min_months < 0:
            # Add shaded region for overdue products
            fig.add_vrect(
                x0=min_months - 0.5, x1=0,
                fillcolor="red", opacity=0.1,
                line_width=0,
                annotation_text="ATRASADO",
                annotation_position="top left",
                row=1, col=1
            )
        
        # Extend x-axis range to show negative values for products with less than 4 months
        max_months = max(display_df['Meses_Ate_Pedido'].max(), 12)
        x_min = min(min_months - 1, -2) if min_months < 0 else -1
        fig.update_xaxes(range=[x_min, max_months], row=1, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
        
      
    


    # Add Solicitação de Pedidos table right after Detalhamento de Compras
    st.subheader("📋 Solicitação de Pedidos")
    
    # Load CBM data from session state (already loaded in analytics.py)
    cbm_data = st.session_state.get('cbm_data', {})
    if not cbm_data:
        st.info("ℹ️ Dados CBM não disponíveis - valores serão mostrados como 0")
    
    # Create the purchase request dataframe with the requested columns using the same filtered data
    solicitacao_data = []
    
    for idx, row in filtered_df.iterrows():
        # Skip empty rows
        produto = str(row.get('Produto', '')).strip()
        if not produto or produto == 'nan':
            continue
        
        # Map columns from the processed timeline data (filtered_df)
        # 1. Produto - already extracted above
        # 2. Fornecedor - use the processed Fornecedor column
        fornecedor = str(row.get('Fornecedor', 'Brazil'))
        
        # 3. Qtd (MOQ) - use the processed Qtd_MOQ column
        qtd_moq = float(row.get('Qtd_MOQ', 0) or 0)
        
        # 🔧 FIX: Get price from multiple sources with proper fallback
        preco_fob_unit = 0
        # First try the timeline processed data
        if 'Preco_Unit' in row.index:
            preco_fob_unit = float(row.get('Preco_Unit', 0) or 0)
        
        # If still zero, try original data with mapped column names
        if preco_fob_unit == 0:
            original_row = df[df['Produto'] == produto]
            if len(original_row) > 0:
                for price_col in ['preco_unitario', 'Preco_Unitario', 'preco_unitário', 'Preço FOB Unitário', 'Preço Unitário']:
                    if price_col in original_row.columns:
                        preco_fob_unit = float(original_row[price_col].iloc[0] or 0)
                        if preco_fob_unit > 0:
                            break
        
        # 5. Preco FOB Total - calculate total investment
        preco_fob_total = qtd_moq * preco_fob_unit
        
        # 6. Estoque Total - use the processed Estoque_Atual column
        estoque_total = float(row.get('Estoque_Atual', 0) or 0)
        
        # 7. In Transit Ship - get from original data using standardized column name
        in_transit_ship = 0
        original_row = df[df['Produto'] == produto]
        if len(original_row) > 0:
            # Try multiple column variations
            for transit_col in ['Qtde_Embarque', 'Qtde Embarque', 'In_Transit', 'In Transit']:
                if transit_col in original_row.columns:
                    in_transit_ship = float(original_row[transit_col].iloc[0] or 0)
                    if in_transit_ship > 0:
                        break
        
        # 8. Avg Sales - use the processed Media_Mensal column
        avg_sales = float(row.get('Media_Mensal', 0) or 0)
        
        # 9. Estoque + inTransit - calculate total expected stock
        estoque_mais_intransit = estoque_total + in_transit_ship
        
        # 10. Compras até 30 dias - get from timeline data
        compras_ate_30_dias = float(row.get('Compras_Ate_30_Dias', 0) or 0)
        
        # 11. New Previsao com New POs (pedidos) - FIX: Use Nova Cobertura Total
        # Nova Cobertura Total = (estoque_total + in_transit_ship + compras_ate_30_dias) / avg_sales
        if avg_sales > 0:
            new_previsao_com_pos = (estoque_total + in_transit_ship + compras_ate_30_dias) / avg_sales
        else:
            new_previsao_com_pos = 999  # No consumption
        
        # 🔧 FIX: Enhanced CBM lookup with better fallback logic
        cbm = 0
        # First try from timeline processed data
        if 'CBM' in row.index:
            cbm = float(row.get('CBM', 0) or 0)
        
        # If still zero, try original analytics data
        if cbm == 0:
            original_row = df[df['Produto'] == produto]
            if len(original_row) > 0 and 'CBM' in original_row.columns:
                cbm = float(original_row['CBM'].iloc[0] or 0)
        
        # If still zero, try timeline data mapping
        if cbm == 0:
            cbm = cbm_data.get(produto, 0)
        
        # 12. MOQ - use the processed MOQ column
        moq = float(row.get('MOQ', 0) or 0)
        
        # 13. OBS - empty column for manual notes
        obs = ""
        
        solicitacao_data.append({
            'Produto': produto,
            'Fornecedor': fornecedor,
            'Qtd (MOQ)': qtd_moq,
            'Preco FOB Unit': preco_fob_unit,
            'Preco FOB Total': preco_fob_total,
            'Estoque Total': estoque_total,
            'In Transit Ship': in_transit_ship,
            'Compras até 30 dias': compras_ate_30_dias,
            'Avg Sales': avg_sales,
            'Estoque + inTransit': estoque_mais_intransit,
            'New Previsao com New POs (pedidos)': new_previsao_com_pos,
            'CBM': cbm,
            'MOQ': moq,
            'OBS': obs
        })
    
    if not solicitacao_data:
        st.warning("⚠️ Nenhum produto com dados suficientes para solicitação de pedidos.")
    else:
        # Convert to DataFrame
        solicitacao_df = pd.DataFrame(solicitacao_data)
        
        # Format numeric columns for better display
        formatted_solicitacao = solicitacao_df.copy()
        
        # Round numeric columns to 2 decimal places
        numeric_columns = formatted_solicitacao.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if col != 'MOQ':  # Keep MOQ as integer
                formatted_solicitacao[col] = formatted_solicitacao[col].round(2)
            else:
                formatted_solicitacao[col] = formatted_solicitacao[col].astype(int)
        
        # Format currency columns
        currency_columns = ['Preco FOB Unit', 'Preco FOB Total']
        for col in currency_columns:
            if col in formatted_solicitacao.columns:
                formatted_solicitacao[col] = formatted_solicitacao[col].apply(lambda x: f'$ {x:,.2f}' if x > 0 else '$ 0.00')
        
        # Display the dataframe
        st.dataframe(
            formatted_solicitacao,
            use_container_width=True,
            height=400,
            hide_index=True
        )
        
        # Export options for Solicitação de Pedidos
        st.subheader("📥 Exportar Solicitação de Pedidos")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Export original data (not formatted) for CSV
            csv = solicitacao_df.to_csv(index=False, sep=';', encoding='utf-8-sig', decimal=',')
            st.download_button(
                label="📄 Baixar como CSV",
                data=csv,
                file_name=f'solicitacao_pedidos_{empresa}_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.csv',
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
                    solicitacao_df.to_excel(writer, sheet_name='Solicitação de Pedidos', index=False)
                    
                    # Get the xlsxwriter workbook and worksheet objects
                    workbook = writer.book
                    worksheet = writer.sheets['Solicitação de Pedidos']
                    
                    # Add some cell formatting
                    header_format = workbook.add_format({
                        'bold': True,
                        'text_wrap': True,
                        'valign': 'top',
                        'fg_color': '#D7E4BD',
                        'border': 1
                    })
                    
                    # Currency format for price columns
                    currency_format = workbook.add_format({
                        'num_format': '$ #,##0.00',
                        'border': 1
                    })
                    
                    # Write the column headers with the defined format
                    for col_num, value in enumerate(solicitacao_df.columns.values):
                        worksheet.write(0, col_num, value, header_format)
                    
                    # Apply currency formatting to price columns
                    for col_num, column in enumerate(solicitacao_df.columns):
                        if 'Preco' in column:
                            worksheet.set_column(col_num, col_num, 15, currency_format)
                        else:
                            # Auto-adjust columns width
                            column_width = max(solicitacao_df[column].astype(str).map(len).max(), len(column))
                            worksheet.set_column(col_num, col_num, min(column_width + 2, 50))
                
                # Reset buffer position
                buffer.seek(0)
                
                st.download_button(
                    label="📊 Baixar como Excel",
                    data=buffer,
                    file_name=f'solicitacao_pedidos_{empresa}_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                    mime='application/vnd.ms-excel',
                    use_container_width=True
                )
            except ImportError:
                st.warning("⚠️ xlsxwriter não instalado. Usando método alternativo para Excel.")
                # Fallback method without xlsxwriter
                import io
                excel_buffer = io.BytesIO()
                solicitacao_df.to_excel(excel_buffer, index=False)
                excel_buffer.seek(0)
                
                st.download_button(
                    label="📊 Baixar como Excel",
                    data=excel_buffer,
                    file_name=f'solicitacao_pedidos_{empresa}_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                    mime='application/vnd.ms-excel',
                    use_container_width=True
                )

