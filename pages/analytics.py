import streamlit as st

def show_excel_analytics():
    """Analytics page with company support"""
    st.title("📊 ANÁLISE DE ESTOQUE")
    st.markdown("### 🎯 Análise inteligente de estoque e consumo")
    
    # Company selector
    col1, col2 = st.columns([3, 1])
    with col1:
        empresa_selecionada = st.selectbox(
            "🏢 Empresa:",
            ["MINIPA", "MINIPA INDUSTRIA"],
            key="empresa_selector_analytics"
        )
        empresa_code = "MINIPA" if empresa_selecionada == "MINIPA" else "MINIPA_INDUSTRIA"
    
    with col2:
        if st.button("🔄 Forçar Atualização", use_container_width=True):
            try:
                from bd.snowflake_config import load_analytics_data
                load_analytics_data.clear()
                st.success("✅ Cache limpo!")
                st.rerun()
            except ImportError:
                st.warning("⚠️ Snowflake não configurado")

    # Try to load analytics data
    try:
        from bd.snowflake_config import load_analytics_data, get_upload_versions
        
        # Get available versions
        versions = get_upload_versions(empresa_code, "ANALYTICS", limit=20)
        
        # Version selector
        if versions:
            st.subheader(f"📦 Seleção de Versão - {empresa_selecionada}")
            
            version_options = [{"id": None, "label": "🟢 Versão Ativa (Atual)"}]
            for v in versions:
                status_icon = "🟢" if v['is_active'] else "⚪"
                version_options.append({
                    "id": v['version_id'],
                    "label": f"{status_icon} Versão {v['version_id']}"
                })
            
            selected_version_idx = st.selectbox(
                "Escolha a versão:",
                range(len(version_options)),
                format_func=lambda x: version_options[x]["label"],
                key="version_selector_analytics"
            )
            
            selected_version_id = version_options[selected_version_idx]["id"]
        else:
            selected_version_id = None
            st.info(f"💡 Nenhuma versão encontrada para {empresa_selecionada}")
        
        # Load analytics data
        df = load_analytics_data(empresa=empresa_code, version_id=selected_version_id)
        
        if df is not None and len(df) > 0:
            version_text = f"v{selected_version_id}" if selected_version_id else "ativa"
            st.success(f"✅ {empresa_selecionada} - Versão {version_text}: {len(df)} produtos carregados")
            
            # Show analytics data
            st.dataframe(df.head(20))
            
            # Basic analytics metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 Total Produtos", len(df))
            with col2:
                if 'Estoque' in df.columns:
                    st.metric("📦 Estoque Total", f"{df['Estoque'].sum():,.0f}")
            with col3:
                if 'Consumo 6 Meses' in df.columns:
                    st.metric("📈 Consumo 6M", f"{df['Consumo 6 Meses'].sum():,.0f}")
            with col4:
                if 'Estoque Cobertura' in df.columns:
                    avg_coverage = df['Estoque Cobertura'].mean()
                    st.metric("⏱️ Cobertura Média", f"{avg_coverage:.1f} meses")
                    
            # Basic analysis
            st.subheader("🔍 Análise Rápida")
            
            if 'Estoque Cobertura' in df.columns:
                # Products with low coverage
                low_coverage = df[df['Estoque Cobertura'] < 3.0]
                if len(low_coverage) > 0:
                    st.warning(f"⚠️ {len(low_coverage)} produtos com cobertura < 3 meses")
                    with st.expander("Ver produtos com baixa cobertura"):
                        st.dataframe(low_coverage[['Produto', 'Estoque', 'Estoque Cobertura']])
                
                # Products with high coverage
                high_coverage = df[df['Estoque Cobertura'] > 12.0]
                if len(high_coverage) > 0:
                    st.info(f"💡 {len(high_coverage)} produtos com cobertura > 12 meses")
                    with st.expander("Ver produtos com alta cobertura"):
                        st.dataframe(high_coverage[['Produto', 'Estoque', 'Estoque Cobertura']])
                    
        else:
            st.info(f"💡 Nenhum dado de análise encontrado para {empresa_selecionada}.")
            st.markdown("👉 **Vá para 'Upload de Dados' e faça upload de um arquivo de análise primeiro.**")
            
    except ImportError:
        st.warning("⚠️ Snowflake não configurado. Use 'Upload de Dados' primeiro.")
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {str(e)}")
        
    # Instructions
    st.markdown("""
    ### 💡 Como usar:
    1. **Selecione a empresa** no menu superior
    2. **Escolha a versão** dos dados que quer analisar
    3. **Analise as métricas** de estoque e cobertura
    4. **Verifique alertas** de produtos com baixa/alta cobertura
    
    ### 📊 Dados necessários:
    - **Produto**: Nome/código do produto
    - **Estoque**: Quantidade atual em estoque
    - **Consumo 6 Meses**: Consumo dos últimos 6 meses
    - **Média 6 Meses**: Média mensal de consumo
    - **Estoque Cobertura**: Meses de cobertura do estoque atual
    
    ### 🔄 Próximas melhorias:
    - Gráficos de análise de estoque
    - Relatórios de compras sugeridas
    - Análise de sazonalidade
    - Classificação ABC
    """) 