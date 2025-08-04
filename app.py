import streamlit as st
import auth
import sys
import os

# Authentication check
if not auth.require_auth():
    st.stop()

st.set_page_config(page_title="Dashboard Corporativo", page_icon="🏢", layout="wide")

# Add pages directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Main app router with lazy loading for performance"""
    
    # Initialize session state
    if "current_page" not in st.session_state:
        st.session_state.current_page = "home"

    # Sidebar navigation
    with st.sidebar:
        st.title("🏢 MENU PRINCIPAL")
        
        # Navigation buttons
        if st.button("🏠 Dashboard", use_container_width=True):
            st.session_state.current_page = "home"
            st.rerun()

        if st.button("📁 Upload de Dados", use_container_width=True):
            st.session_state.current_page = "upload"
            st.rerun()

        if st.button("📊 Análise de Estoque", use_container_width=True):
            st.session_state.current_page = "analytics"
            st.rerun()

        if st.button("📢 Anúncios", use_container_width=True):
            st.session_state.current_page = "announcements"
            st.rerun()

        if st.button("🔧 Ferramentas", use_container_width=True):
            st.session_state.current_page = "ferramentas"
            st.rerun()

        # if st.button("❄️ Gerenciar Snowflake", use_container_width=True):
        #     st.session_state.current_page = "snowflake"
        #     st.rerun()

        # User info and logout
        st.divider()
        current_user = auth.get_current_user()
        st.info(f"👤 {current_user['name']}")
        
        if st.button("🚪 Logout", use_container_width=True):
            auth.logout()
            st.rerun()
        
    # Route to appropriate page with lazy loading
    page = st.session_state.current_page
    
    try:
        if page == "home":
            from pages.dashboard import show_dashboard
            show_dashboard()
        elif page == "upload":
            from pages.upload import show_data_upload
            show_data_upload()
        elif page == "analytics":
            from pages.analytics import load_page
            load_page()
        elif page == "announcements":
            from pages.announcements import show_announcements
            show_announcements()
        elif page == "ferramentas":
            from pages.ferramentas import show_ferramentas
            show_ferramentas()
        # elif page == "snowflake":
        #     from pages.snowflake_management import show_snowflake
        #     show_snowflake()
        else:
            st.error(f"Page '{page}' not found!")

    except ImportError as e:
        st.error(f"❌ Error loading page: {str(e)}")
        st.info("💡 Make sure all page modules are properly configured")
 
if __name__ == "__main__":
    main() 