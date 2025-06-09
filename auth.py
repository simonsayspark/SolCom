import streamlit as st
import hashlib
import json
import os
from datetime import datetime, timedelta

# Authentication file path
AUTH_FILE = "users.json"

def hash_password(password):
    """Hash a password for storing."""
    return hashlib.sha256(str(password).encode()).hexdigest()

def verify_password(password, hashed):
    """Verify a password against its hash."""
    return hash_password(password) == hashed

def load_users():
    """Load users from JSON file."""
    if os.path.exists(AUTH_FILE):
        try:
            with open(AUTH_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return create_default_users()
    return create_default_users()

def save_users(users):
    """Save users to JSON file."""
    try:
        with open(AUTH_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def create_default_users():
    """Create default users if no auth file exists."""
    default_users = {
        "minipa": {
            "password": hash_password("{878460@}"),
            "role": "admin",
            "name": "MINIPA Admin",
            "department": "Administração",
            "created": datetime.now().isoformat(),
            "last_login": None
        }
    }
    save_users(default_users)
    return default_users

def authenticate_user(username, password):
    """Authenticate a user."""
    users = load_users()
    
    if username in users:
        user_data = users[username]
        if verify_password(password, user_data["password"]):
            # Update last login
            user_data["last_login"] = datetime.now().isoformat()
            users[username] = user_data
            save_users(users)
            return user_data
    return None

def is_admin(user_data):
    """Check if user is admin."""
    return user_data and user_data.get("role") == "admin"

def get_current_user():
    """Get current authenticated user from session state."""
    return st.session_state.get("user", None)

def logout():
    """Logout current user."""
    for key in ["authenticated", "user"]:
        if key in st.session_state:
            del st.session_state[key]

def require_auth():
    """Require authentication to access the app."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        show_login_page()
        return False
    return True

def show_login_page():
    """Display the login page."""
    st.set_page_config(page_title="Login", page_icon="🔐", layout="centered")
    
    # Custom CSS for login page
    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        background-color: #f8f9fa;
    }
    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    st.markdown('<div class="login-header">', unsafe_allow_html=True)
    st.title("🔐 Login Corporativo")
    st.markdown("### Acesso ao Dashboard")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Login form
    with st.form("login_form"):
        username = st.text_input("👤 Usuário", placeholder="Digite seu usuário")
        password = st.text_input("🔑 Senha", type="password", placeholder="Digite sua senha")
        
        col1, col2 = st.columns(2)
        with col1:
            login_button = st.form_submit_button("🚀 Entrar", use_container_width=True)
        with col2:
            show_help = st.form_submit_button("ℹ️ Ajuda", use_container_width=True)
        
        if login_button:
            if username and password:
                user_data = authenticate_user(username, password)
                if user_data:
                    st.session_state.authenticated = True
                    st.session_state.user = user_data
                    st.success(f"✅ Bem-vindo, {user_data['name']}!")
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos!")
            else:
                st.warning("⚠️ Preencha usuário e senha!")
        
        if show_help:
            st.info("""
            **👥 Credenciais de Acesso:**
            
            **MINIPA:** Entre em contato com o administrador para obter as credenciais
            - Acesso completo ao sistema
            - Pode criar/editar anúncios
            - Acessa todas as funcionalidades
            - Gerencia timeline de compras
            - Controle administrativo total
            """)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>🔒 Sistema Seguro | 📧 Problemas de acesso? Contate o administrador</p>
    </div>
    """, unsafe_allow_html=True)

def show_user_info():
    """Show current user info in sidebar."""
    user = get_current_user()
    if user:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 👤 Usuário Logado")
        st.sidebar.write(f"**Nome:** {user['name']}")
        st.sidebar.write(f"**Departamento:** {user['department']}")
        st.sidebar.write(f"**Tipo:** {user['role'].title()}")
        
        if user.get('last_login'):
            try:
                last_login = datetime.fromisoformat(user['last_login'])
                st.sidebar.write(f"**Último acesso:** {last_login.strftime('%d/%m/%Y %H:%M')}")
            except:
                pass
        
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            logout()
            st.rerun()

def check_page_permission(page_name, required_role="user"):
    """Check if current user has permission to access a page."""
    user = get_current_user()
    if not user:
        return False
    
    if required_role == "admin" and not is_admin(user):
        st.error("🚫 Acesso negado! Apenas administradores podem acessar esta funcionalidade.")
        return False
    
    return True 