import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

def show_dashboard():
    """Enhanced dashboard with real system data"""
    st.title("🏢 DASHBOARD EXECUTIVO - SISTEMA DE ESTOQUE")
    st.markdown("### 📊 Visão Geral Multi-Empresa em Tempo Real")
    
    # Company selector
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        empresa_selecionada = st.selectbox(
            "🏢 Empresa:",
            ["MINIPA", "MINIPA INDUSTRIA", "TODAS"],
            key="dashboard_empresa",
            help="Selecione a empresa para visualizar dados específicos"
        )
    
    with col2:
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            # Clear all caches
            try:
                from bd.snowflake_config import load_data_with_history, load_analytics_data
                load_data_with_history.clear()
                load_analytics_data.clear()
                st.success("✅ Dados atualizados!")
                st.rerun()
            except:
                st.info("Cache limpo localmente")
    
    with col3:
        st.metric("🕒 Última Atualização", datetime.now().strftime("%H:%M"))
    
    # Load real data from the system
    try:
        from bd.snowflake_config import (load_data_with_history, load_analytics_data, 
                                        get_upload_versions, get_snowflake_connection)
        snowflake_available = True
    except ImportError:
        snowflake_available = False
    
    if snowflake_available:
        # Load data for both companies
        companies = ["MINIPA", "MINIPA_INDUSTRIA"] if empresa_selecionada == "TODAS" else [empresa_selecionada]
        
        all_timeline_data = []
        all_analytics_data = []
        company_stats = {}
        
        for company in companies:
            # Load timeline data
            timeline_data = load_data_with_history(empresa=company)
            if timeline_data is not None and len(timeline_data) > 0:
                timeline_data['Empresa'] = company
                all_timeline_data.append(timeline_data)
            
            # Load analytics data
            analytics_data = load_analytics_data(empresa=company)
            if analytics_data is not None and len(analytics_data) > 0:
                analytics_data['Empresa'] = company
                all_analytics_data.append(analytics_data)
            
            # Get version information
            timeline_versions = get_upload_versions(company, "TIMELINE", limit=5)
            analytics_versions = get_upload_versions(company, "ANALYTICS", limit=5)
            
            company_stats[company] = {
                'timeline_products': len(timeline_data) if timeline_data is not None else 0,
                'analytics_products': len(analytics_data) if analytics_data is not None else 0,
                'timeline_versions': len(timeline_versions),
                'analytics_versions': len(analytics_versions),
                'last_timeline_upload': timeline_versions[0]['upload_date'] if timeline_versions else "Nunca",
                'last_analytics_upload': analytics_versions[0]['upload_date'] if analytics_versions else "Nunca"
            }
        
        # Combine data
        combined_timeline = pd.concat(all_timeline_data) if all_timeline_data else None
        combined_analytics = pd.concat(all_analytics_data) if all_analytics_data else None
        
        # Show system status
        st.subheader("🚀 Status do Sistema")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_timeline = sum([stats['timeline_products'] for stats in company_stats.values()])
            st.metric("📅 Produtos Timeline", total_timeline)
        
        with col2:
            total_analytics = sum([stats['analytics_products'] for stats in company_stats.values()])
            st.metric("📊 Produtos Analytics", total_analytics)
        
        with col3:
            total_versions = sum([stats['timeline_versions'] + stats['analytics_versions'] for stats in company_stats.values()])
            st.metric("📦 Versões Totais", total_versions)
        
        with col4:
            # Calculate system health
            health_score = min(100, (total_timeline + total_analytics) / 10)
            st.metric("💚 Saúde do Sistema", f"{health_score:.0f}%")
        
        # Company comparison
        if len(companies) > 1:
            st.subheader("🏢 Comparação entre Empresas")
            
            comparison_data = []
            for company, stats in company_stats.items():
                comparison_data.append({
                    'Empresa': company,
                    'Timeline': stats['timeline_products'],
                    'Analytics': stats['analytics_products'],
                    'Versões': stats['timeline_versions'] + stats['analytics_versions']
                })
            
            comparison_df = pd.DataFrame(comparison_data)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig_comparison = px.bar(
                    comparison_df,
                    x='Empresa',
                    y=['Timeline', 'Analytics'],
                    title='📊 Produtos por Empresa',
                    barmode='group'
                )
                st.plotly_chart(fig_comparison, use_container_width=True)
            
            with col2:
                fig_versions = px.pie(
                    comparison_df,
                    values='Versões',
                    names='Empresa',
                    title='📦 Distribuição de Versões'
                )
                st.plotly_chart(fig_versions, use_container_width=True)
        
        # Analytics insights
        if combined_analytics is not None and len(combined_analytics) > 0:
            st.subheader("🚨 Alertas Críticos de Estoque")
            
            # Calculate critical products
            if 'Estoque Cobertura' in combined_analytics.columns:
                criticos = combined_analytics[combined_analytics['Estoque Cobertura'] <= 1]
                alerta = combined_analytics[(combined_analytics['Estoque Cobertura'] > 1) & 
                                          (combined_analytics['Estoque Cobertura'] <= 3)]
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("🔴 Críticos (≤1 mês)", len(criticos), 
                             delta=f"{len(criticos)/len(combined_analytics)*100:.1f}%")
                
                with col2:
                    st.metric("🟡 Alerta (1-3 meses)", len(alerta),
                             delta=f"{len(alerta)/len(combined_analytics)*100:.1f}%")
                
                with col3:
                    saudaveis = len(combined_analytics) - len(criticos) - len(alerta)
                    st.metric("🟢 Saudáveis (>3 meses)", saudaveis,
                             delta=f"{saudaveis/len(combined_analytics)*100:.1f}%")
                
                # Show critical products table
                if len(criticos) > 0:
                    st.error(f"⚠️ {len(criticos)} produtos precisam de ação IMEDIATA!")
                    
                    # Show top 10 critical products
                    critical_display = criticos.head(10)[['Produto', 'Estoque', 'Média 6 Meses', 'Estoque Cobertura', 'Empresa']]
                    st.dataframe(critical_display, use_container_width=True)
                else:
                    st.success("✅ Nenhum produto crítico no momento!")
        
        # Timeline insights
        if combined_timeline is not None and len(combined_timeline) > 0:
            st.subheader("💰 Análise Financeira")
            
            # Calculate financial metrics
            if 'Preco_Unitario' in combined_timeline.columns and 'QTD' in combined_timeline.columns:
                combined_timeline['Valor_Total'] = combined_timeline['Preco_Unitario'] * combined_timeline['QTD']
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    total_value = combined_timeline['Valor_Total'].sum()
                    st.metric("💰 Valor Total Timeline", f"R$ {total_value:,.0f}")
                
                with col2:
                    avg_price = combined_timeline['Preco_Unitario'].mean()
                    st.metric("💵 Preço Médio", f"R$ {avg_price:.2f}")
                
                with col3:
                    total_qty = combined_timeline['QTD'].sum()
                    st.metric("📦 Quantidade Total", f"{total_qty:,.0f}")
                
                # Top suppliers analysis
                if 'Fornecedor' in combined_timeline.columns:
                    st.subheader("🏭 Análise de Fornecedores")
                    
                    supplier_analysis = combined_timeline.groupby('Fornecedor').agg({
                        'Valor_Total': 'sum',
                        'QTD': 'sum',
                        'Produto': 'count'
                    }).round(2)
                    supplier_analysis.columns = ['Valor Total', 'Quantidade', 'Produtos']
                    supplier_analysis = supplier_analysis.sort_values('Valor Total', ascending=False)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Top 10 suppliers by value
                        fig_suppliers = px.bar(
                            supplier_analysis.head(10).reset_index(),
                            x='Valor Total',
                            y='Fornecedor',
                            orientation='h',
                            title='💰 Top 10 Fornecedores por Valor'
                        )
                        st.plotly_chart(fig_suppliers, use_container_width=True)
                    
                    with col2:
                        # Supplier distribution
                        fig_supplier_pie = px.pie(
                            supplier_analysis.head(8).reset_index(),
                            values='Produtos',
                            names='Fornecedor',
                            title='📊 Distribuição de Produtos'
                        )
                        st.plotly_chart(fig_supplier_pie, use_container_width=True)
        
        # System activity
        st.subheader("📈 Atividade do Sistema")
        
        activity_data = []
        for company, stats in company_stats.items():
            activity_data.append({
                'Empresa': company,
                'Último Upload Timeline': stats['last_timeline_upload'],
                'Último Upload Analytics': stats['last_analytics_upload'],
                'Produtos Timeline': stats['timeline_products'],
                'Produtos Analytics': stats['analytics_products']
            })
        
        activity_df = pd.DataFrame(activity_data)
        st.dataframe(activity_df, use_container_width=True)
        
        # Quick actions
        st.subheader("⚡ Ações Rápidas")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📅 Ir para Timeline", use_container_width=True):
                st.switch_page("pages/timeline.py")
        
        with col2:
            if st.button("📊 Ir para Analytics", use_container_width=True):
                st.switch_page("pages/analytics.py")
        
        with col3:
            if st.button("📁 Fazer Upload", use_container_width=True):
                st.switch_page("pages/upload.py")
        
        with col4:
            if st.button("📢 Ver Anúncios", use_container_width=True):
                st.switch_page("pages/announcements.py")
        
        # System recommendations
        st.subheader("💡 Recomendações do Sistema")
        
        recommendations = []
        
        # Check for critical products
        if combined_analytics is not None and 'Estoque Cobertura' in combined_analytics.columns:
            criticos = len(combined_analytics[combined_analytics['Estoque Cobertura'] <= 1])
            if criticos > 0:
                recommendations.append(f"🚨 **URGENTE**: {criticos} produtos críticos precisam de compra imediata")
        
        # Check for old uploads
        for company, stats in company_stats.items():
            if stats['timeline_products'] == 0:
                recommendations.append(f"📅 **{company}**: Nenhum dado de timeline encontrado - faça upload")
            if stats['analytics_products'] == 0:
                recommendations.append(f"📊 **{company}**: Nenhum dado de analytics encontrado - faça upload")
        
        # Check for version management
        total_versions = sum([stats['timeline_versions'] + stats['analytics_versions'] for stats in company_stats.values()])
        if total_versions > 20:
            recommendations.append("🗑️ **Limpeza**: Considere deletar versões antigas para otimizar performance")
        
        if recommendations:
            for rec in recommendations:
                st.warning(rec)
        else:
            st.success("✅ Sistema funcionando perfeitamente! Nenhuma ação necessária.")
    
    else:
        # Fallback for when Snowflake is not available
        st.warning("⚠️ Snowflake não configurado. Mostrando dados de exemplo.")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📅 Produtos Timeline", "0", help="Configure Snowflake para ver dados reais")
        
        with col2:
            st.metric("📊 Produtos Analytics", "0", help="Configure Snowflake para ver dados reais")
        
        with col3:
            st.metric("📦 Versões Totais", "0", help="Configure Snowflake para ver dados reais")
        
        with col4:
            st.metric("💚 Saúde do Sistema", "0%", help="Configure Snowflake para ver dados reais")
        
        st.info("💡 **Para ver dados reais**: Configure a conexão com Snowflake e faça upload de dados nas páginas Timeline e Analytics.")
    
    # Footer with system info
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>🚀 Sistema de Gestão de Estoque Multi-Empresa | 💡 Otimizado com cache inteligente | 🔒 Dados seguros no Snowflake</p>
        <p>📞 Suporte: Acesse a página de Upload para gerenciar dados | 🔄 Cache: Timeline 25 dias, Analytics 6 dias</p>
    </div>
    """, unsafe_allow_html=True) 