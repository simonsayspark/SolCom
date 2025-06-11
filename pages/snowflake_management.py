# import streamlit as st

# def show_snowflake():
#     """Snowflake management page"""
#     st.title("❄️ SNOWFLAKE DATABASE")
#     st.markdown("### 🔧 Gerenciamento de Banco de Dados")
    
#     # Try to import Snowflake functions
#     try:
#         from bd.snowflake_config import test_connection, create_tables, get_database_statistics
#         snowflake_available = True
#     except ImportError as e:
#         st.error("❌ Snowflake não configurado!")
#         st.code(f"Erro: {str(e)}")
#         snowflake_available = False
#         return
    
#     # Connection status
#     st.subheader("🔌 Status da Conexão")
    
#     col1, col2 = st.columns([2, 1])
    
#     with col1:
#         if st.button("🔄 Testar Conexão", type="primary"):
#             with st.spinner("Testando conexão..."):
#                 if test_connection():
#                     st.success("✅ Conectado!")
#                     st.session_state.snowflake_connected = True
#                 else:
#                     st.error("❌ Falha na conexão")
#                     st.session_state.snowflake_connected = False
    
#     with col2:
#         connection_status = getattr(st.session_state, 'snowflake_connected', None)
#         if connection_status is True:
#             st.success("🟢 Online")
#         elif connection_status is False:
#             st.error("🔴 Offline")
#         else:
#             st.info("⚪ Não testado")
    
#     # Table management
#     st.subheader("🗃️ Gerenciamento de Tabelas")
    
#     col1, col2, col3 = st.columns(3)
    
#     with col1:
#         if st.button("🔨 Criar/Atualizar Tabelas", use_container_width=True):
#             with st.spinner("Criando tabelas..."):
#                 if create_tables():
#                     st.success("✅ Tabelas criadas!")
#                 else:
#                     st.error("❌ Erro ao criar tabelas")
    
#     with col2:
#         if st.button("🔍 Estrutura Avançada", use_container_width=True):
#             try:
#                 from bd.snowflake_config import check_database_structure
#                 structure_info = check_database_structure()
                
#                 if structure_info:
#                     for table_name, info in structure_info.items():
#                         if info['exists']:
#                             if info['has_empresa']:
#                                 st.success(f"✅ {table_name}: OK")
#                             else:
#                                 st.warning(f"⚠️ {table_name}: Estrutura antiga")
#                         else:
#                             st.info(f"💡 {table_name}: Não existe")
#             except ImportError:
#                 st.warning("Função avançada não disponível")
    
#     with col3:
#         if st.button("🚀 Migração Multi-Empresa", use_container_width=True):
#             try:
#                 from bd.snowflake_config import migrate_to_multi_company_versioned
#                 with st.spinner("Executando migração..."):
#                     migrate_to_multi_company_versioned()
#             except ImportError:
#                 st.error("Função de migração não disponível")
    
#     # Database statistics
#     st.subheader("📊 Estatísticas")
    
#     try:
#         stats = get_database_statistics()
        
#         if stats:
#             col1, col2, col3 = st.columns(3)
            
#             with col1:
#                 st.metric("🏢 MINIPA", stats.get('MINIPA', {}).get('total', 0))
                
#             with col2:
#                 st.metric("🏭 MINIPA INDUSTRIA", stats.get('MINIPA_INDUSTRIA', {}).get('total', 0))
                
#             with col3:
#                 st.metric("🌍 TOTAL", stats.get('TOTAL', {}).get('total', 0))
#     except Exception as e:
#         st.warning(f"⚠️ Erro ao carregar estatísticas: {str(e)}")
    
#     # Cache management
#     st.subheader("🔄 Cache")
    
#     col1, col2 = st.columns(2)
    
#     with col1:
#         if st.button("🧹 Limpar Cache Timeline", use_container_width=True):
#             try:
#                 from bd.snowflake_config import load_data_with_history
#                 load_data_with_history.clear()
#                 st.success("✅ Cache Timeline limpo!")
#             except:
#                 st.cache_data.clear()
#                 st.success("✅ Cache geral limpo!")
    
#     with col2:
#         if st.button("🧹 Limpar Todo Cache", use_container_width=True):
#             st.cache_data.clear()
#             st.success("✅ Todo cache limpo!")
    
#     # Help
#     with st.expander("💡 Como usar"):
#         st.markdown("""
#         ### 🚀 Primeiros passos:
#         1. **Teste a conexão** - Clique em "Testar Conexão"
#         2. **Crie as tabelas** - Clique em "Criar/Atualizar Tabelas"
#         3. **Faça upload** - Vá para "Upload de Dados"
#         4. **Use os dados** - Acesse Timeline e Analytics
        
#         ### 🔧 Se tiver problemas:
#         - Use "Estrutura Avançada" para diagnóstico
#         - Use "Migração Multi-Empresa" se tem dados antigos
#         - Limpe o cache se os dados não aparecem
        
#         ### ⚙️ Configuração:
#         Configure credenciais em `.streamlit/secrets.toml`:
#         ```toml
#         [connections.snowflake]
#         account = "sua_conta"
#         user = "seu_usuario"
#         password = "sua_senha"
#         role = "ACCOUNTADMIN"
#         warehouse = "COMPUTE_WH"
#         database = "COMPRAS_MINIPA"
#         schema = "ESTOQUE"
#         ```
#         """) 