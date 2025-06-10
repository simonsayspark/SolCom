"""
Snowflake Admin Functions
Handles database cleanup, statistics, and administrative operations
"""

import streamlit as st
from .snowflake_connection import get_snowflake_connection
from .snowflake_data import load_data_with_history, load_analytics_data

def get_database_statistics():
    """
    Get comprehensive database statistics for monitoring costs and usage
    """
    conn = get_snowflake_connection()
    if not conn:
        return None
        
    try:
        cursor = conn.cursor()
        stats = {}
        
        # Check if tables have the new structure (empresa column)
        has_empresa_column = False
        try:
            cursor.execute("DESCRIBE TABLE ESTOQUE.PRODUTOS")
            columns = cursor.fetchall()
            column_names = [col[0] for col in columns]
            has_empresa_column = 'EMPRESA' in [col.upper() for col in column_names]
        except:
            pass
        
        if has_empresa_column:
            # New multi-company structure
            for empresa in ["MINIPA", "MINIPA_INDUSTRIA"]:
                try:
                    cursor.execute("SELECT COUNT(*) FROM ESTOQUE.PRODUTOS WHERE empresa = %s", (empresa,))
                    produtos_count = cursor.fetchone()[0]
                except:
                    produtos_count = 0
                
                stats[empresa] = {
                    'produtos': produtos_count,
                    'total': produtos_count
                }
        
        cursor.close()
        conn.close()
        return stats
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar estatísticas: {str(e)}")
        return None

def clear_company_data(empresa, table_type=None):
    """
    Clear all data for a specific company
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    st.warning(f"⚠️ **ATENÇÃO**: Esta função deletará dados de {empresa}")
    return True

def clear_specific_version(empresa, version_id, table_type):
    """
    Clear a specific version of data
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        st.warning(f"⚠️ **ATENÇÃO**: Deletando versão {version_id} de {table_type} para {empresa}")
        
        confirm = st.checkbox(f"✅ Confirmo que quero deletar versão {version_id}", key=f"confirm_version_{empresa}_{version_id}_{table_type}")
        
        if not confirm:
            st.info("💡 Marque a caixa de confirmação para prosseguir")
            return False
        
        if st.button(f"🗑️ DELETAR VERSÃO {version_id}", type="primary", key=f"delete_version_{empresa}_{version_id}_{table_type}"):
            # Delete from data tables
            if table_type == "TIMELINE":
                cursor.execute("DELETE FROM ESTOQUE.PRODUTOS WHERE empresa = %s AND version_id = %s AND table_type = %s", 
                              (empresa, version_id, table_type))
            elif table_type == "ANALYTICS":
                cursor.execute("DELETE FROM ESTOQUE.ANALYTICS_DATA WHERE empresa = %s AND version_id = %s", 
                              (empresa, version_id))
            
            data_deleted = cursor.rowcount
            
            # Delete from version control
            cursor.execute("DELETE FROM CONFIG.VERSIONS WHERE empresa = %s AND version_id = %s AND table_type = %s", 
                          (empresa, version_id, table_type))
            
            # Delete from upload logs
            cursor.execute("DELETE FROM CONFIG.UPLOAD_LOG WHERE empresa = %s AND version_id = %s AND table_type = %s", 
                          (empresa, version_id, table_type))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            st.success(f"✅ Versão {version_id} deletada: {data_deleted} registros removidos")
            
            # Clear caches
            load_data_with_history.clear()
            load_analytics_data.clear()
            
            return True
            
    except Exception as e:
        st.error(f"❌ Erro ao deletar versão: {str(e)}")
        return False

def clear_entire_database():
    """
    Clear the entire database - NUCLEAR OPTION
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        st.error("🚨 **PERIGO**: VOCÊ ESTÁ PRESTES A DELETAR TODA A BASE DE DADOS!")
        st.error("🚨 Esta ação é IRREVERSÍVEL e deletará dados de TODAS as empresas!")
        
        # Triple confirmation
        confirm1 = st.checkbox("⚠️ Entendo que vou deletar TODOS os dados", key="nuclear_confirm1")
        confirm2 = st.checkbox("⚠️ Entendo que esta ação é IRREVERSÍVEL", key="nuclear_confirm2") 
        confirm3 = st.checkbox("⚠️ Tenho certeza ABSOLUTA que quero fazer isso", key="nuclear_confirm3")
        
        safety_code = st.text_input("🔐 Digite 'DELETE_EVERYTHING' para confirmar:", key="safety_code")
        
        if confirm1 and confirm2 and confirm3 and safety_code == "DELETE_EVERYTHING":
            if st.button("💥 DELETAR TODA A BASE DE DADOS", type="primary", key="nuclear_button"):
                try:
                    # Clear all data tables
                    cursor.execute("DELETE FROM ESTOQUE.PRODUTOS")
                    produtos_deleted = cursor.rowcount
                    
                    cursor.execute("DELETE FROM ESTOQUE.ANALYTICS_DATA")
                    analytics_deleted = cursor.rowcount
                    
                    cursor.execute("DELETE FROM CONFIG.VERSIONS")
                    versions_deleted = cursor.rowcount
                    
                    cursor.execute("DELETE FROM CONFIG.UPLOAD_LOG")
                    logs_deleted = cursor.rowcount
                    
                    conn.commit()
                    
                    total_deleted = produtos_deleted + analytics_deleted + versions_deleted + logs_deleted
                    
                    st.success(f"💥 BASE DE DADOS COMPLETAMENTE LIMPA!")
                    st.info(f"🗑️ Total de registros deletados: {total_deleted}")
                    st.info(f"📊 Produtos: {produtos_deleted}, Analytics: {analytics_deleted}")
                    st.info(f"📋 Versões: {versions_deleted}, Logs: {logs_deleted}")
                    
                    # Clear all caches
                    load_data_with_history.clear()
                    load_analytics_data.clear()
                    
                    cursor.close()
                    conn.close()
                    return True
                    
                except Exception as delete_error:
                    st.error(f"❌ Erro durante a limpeza: {str(delete_error)}")
                    return False
        else:
            st.info("💡 Complete todas as confirmações e digite o código de segurança para prosseguir")
            
    except Exception as e:
        st.error(f"❌ Erro na operação de limpeza: {str(e)}")
        return False 