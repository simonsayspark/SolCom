import streamlit as st

def load_page():
    """Snowflake management page"""
    st.title("❄️ SNOWFLAKE DATABASE")
    st.markdown("### 🔧 Gerenciamento de Banco de Dados")
    
    # Try to import Snowflake functions
    try:
        from bd.snowflake_config import test_connection, create_tables, get_database_statistics
        from bd.snowflake_tables import add_analytics_columns, check_database_structure
        snowflake_available = True
    except ImportError as e:
        st.error("❌ Snowflake não configurado!")
        st.code(f"Erro: {str(e)}")
        snowflake_available = False
        return
    
    # Connection status
    st.subheader("🔌 Status da Conexão")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("🔄 Testar Conexão", type="primary"):
            with st.spinner("Testando conexão..."):
                if test_connection():
                    st.success("✅ Conectado!")
                    st.session_state.snowflake_connected = True
                else:
                    st.error("❌ Falha na conexão")
                    st.session_state.snowflake_connected = False
    
    with col2:
        connection_status = getattr(st.session_state, 'snowflake_connected', None)
        if connection_status is True:
            st.success("🟢 Online")
        elif connection_status is False:
            st.error("🔴 Offline")
        else:
            st.info("⚪ Não testado")
    
    # Table management
    st.subheader("🗃️ Gerenciamento de Tabelas")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔨 Criar/Atualizar Tabelas", use_container_width=True):
            with st.spinner("Criando tabelas..."):
                if create_tables():
                    st.success("✅ Tabelas criadas!")
                else:
                    st.error("❌ Erro ao criar tabelas")
    
    with col2:
        if st.button("🔍 Verificar Estrutura", use_container_width=True):
            try:
                structure_info = check_database_structure()
                
                if structure_info:
                    for table_name, info in structure_info.items():
                        if info['exists']:
                            status_items = []
                            if info.get('has_empresa', False):
                                status_items.append("✅ Multi-empresa")
                            if info.get('has_moq', False):
                                status_items.append("✅ MOQ")
                            if info.get('has_ultimo_fornecedor', False):
                                status_items.append("✅ Fornecedor")
                            
                            if status_items:
                                st.success(f"✅ {table_name}: {', '.join(status_items)}")
                            else:
                                st.warning(f"⚠️ {table_name}: Estrutura básica")
                        else:
                            st.info(f"💡 {table_name}: Não existe")
            except Exception as e:
                st.error(f"Erro ao verificar estrutura: {str(e)}")
    
    with col3:
        if st.button("🆕 Migrar Analytics (MOQ+Fornecedor)", use_container_width=True):
            st.info("🔄 **Migração Segura**: Adiciona colunas MOQ e UltimoFornecedor à tabela ANALYTICS_DATA sem perder dados existentes")
            
            if st.button("✅ Confirmar Migração", type="primary"):
                with st.spinner("Executando migração..."):
                    if add_analytics_columns():
                        st.success("🎉 Migração concluída com sucesso!")
                        st.balloons()
                    else:
                        st.error("❌ Erro na migração")
    
    # Database statistics
    st.subheader("📊 Estatísticas")
    
    try:
        stats = get_database_statistics()
        
        if stats:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("🏢 MINIPA", stats.get('MINIPA', {}).get('total', 0))
                
            with col2:
                st.metric("🏭 MINIPA INDUSTRIA", stats.get('MINIPA_INDUSTRIA', {}).get('total', 0))
                
            with col3:
                st.metric("🌍 TOTAL", stats.get('TOTAL', {}).get('total', 0))
    except Exception as e:
        st.warning(f"⚠️ Erro ao carregar estatísticas: {str(e)}")
    
    # Cache management
    st.subheader("🔄 Cache")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🧹 Limpar Cache Analytics", use_container_width=True):
            try:
                from bd.snowflake_config import load_analytics_data
                load_analytics_data.clear()
                st.success("✅ Cache Analytics limpo!")
            except:
                st.cache_data.clear()
                st.success("✅ Cache geral limpo!")
    
    with col2:
        if st.button("🧹 Limpar Todo Cache", use_container_width=True):
            st.cache_data.clear()
            st.success("✅ Todo cache limpo!")
    
    # Help
    with st.expander("💡 Como usar"):
        st.markdown("""
        ### 🚀 Primeiros passos:
        1. **Teste a conexão** - Clique em "Testar Conexão"
        2. **Crie as tabelas** - Clique em "Criar/Atualizar Tabelas"
        3. **Migre para nova estrutura** - Clique em "Migrar Analytics" se já tem dados
        4. **Faça upload** - Vá para "Upload de Dados"
        5. **Use os dados** - Acesse Timeline e Analytics
        
        ### 🆕 Nova Estrutura Analytics:
        - **MOQ**: Quantidade mínima de pedido para otimização de compras
        - **UltimoFornecedor**: Rastreamento de fornecedores por produto
        - **Análise por Fornecedor**: Dashboards e relatórios por fornecedor
        
        ### 🔧 Se tiver problemas:
        - Use "Verificar Estrutura" para diagnóstico
        - Use "Migrar Analytics" se tem dados antigos sem MOQ/Fornecedor
        - Limpe o cache se os dados não aparecem
        
        ### ⚙️ Configuração:
        Configure credenciais em `.streamlit/secrets.toml`:
        ```toml
        [connections.snowflake]
        account = "sua_conta"
        user = "seu_usuario"
        password = "sua_senha"
        role = "ACCOUNTADMIN"
        warehouse = "COMPUTE_WH"
        database = "COMPRAS_MINIPA"
        schema = "ESTOQUE"
        ```
        """) 