import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go
import sys

# Add parent directory to path to import auth
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import auth

# Check authentication
if not auth.require_auth():
    st.stop()

st.set_page_config(page_title="Announcements", page_icon="📢", layout="wide")

# Data file path
ANNOUNCEMENTS_FILE = "announcements.json"

def load_announcements():
    """Carrega anúncios do arquivo JSON"""
    if os.path.exists(ANNOUNCEMENTS_FILE):
        try:
            with open(ANNOUNCEMENTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except:
            return []
    return []

def save_announcements(announcements):
    """Salva anúncios no arquivo JSON"""
    try:
        with open(ANNOUNCEMENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(announcements, f, ensure_ascii=False, indent=2, default=str)
        return True
    except:
        return False

def create_sample_announcements():
    """Cria anúncios de exemplo"""
    sample_data = [
        {
            "id": 1,
            "title": "🎉 Nova Política de Home Office",
            "content": "A partir de segunda-feira, implementaremos nossa nova política de trabalho híbrido. Funcionários podem trabalhar remotamente 2 dias por semana.",
            "type": "Política",
            "priority": "Alta",
            "department": "Todos",
            "author": "Recursos Humanos",
            "date": "2024-01-15",
            "expiry_date": "2024-02-15",
            "active": True
        },
        {
            "id": 2,
            "title": "📈 Resultados Q4 2023",
            "content": "Excelentes resultados no último trimestre! Aumentamos nossa receita em 15% e expandimos para 3 novos mercados.",
            "type": "Resultado",
            "priority": "Média",
            "department": "Todos",
            "author": "Diretoria",
            "date": "2024-01-10",
            "expiry_date": "2024-01-25",
            "active": True
        },
        {
            "id": 3,
            "title": "🛡️ Atualização de Segurança",
            "content": "Por favor, atualizem suas senhas até o final da semana. Nova política de segurança requer senhas com pelo menos 12 caracteres.",
            "type": "Segurança",
            "priority": "Crítica",
            "department": "TI",
            "author": "Segurança da Informação",
            "date": "2024-01-12",
            "expiry_date": "2024-01-19",
            "active": True
        },
        {
            "id": 4,
            "title": "🎂 Aniversário da Empresa",
            "content": "No próximo mês completamos 10 anos! Haverá uma celebração especial no escritório dia 20/02.",
            "type": "Evento",
            "priority": "Baixa",
            "department": "Todos",
            "author": "Eventos",
            "date": "2024-01-08",
            "expiry_date": "2024-02-20",
            "active": True
        },
        {
            "id": 5,
            "title": "📋 Novo Sistema de Compras",
            "content": "Implementamos um novo sistema para solicitações de compra. Treinamento obrigatório na sexta-feira às 14h.",
            "type": "Sistema",
            "priority": "Alta",
            "department": "Compras",
            "author": "TI",
            "date": "2024-01-14",
            "expiry_date": "2024-01-21",
            "active": True
        }
    ]
    return sample_data

def get_priority_color(priority):
    """Retorna cor baseada na prioridade"""
    colors = {
        "Crítica": "#FF4444",
        "Alta": "#FF8800",
        "Média": "#FFDD00",
        "Baixa": "#44AA44"
    }
    return colors.get(priority, "#CCCCCC")

def get_type_icon(announcement_type):
    """Retorna ícone baseado no tipo"""
    icons = {
        "Política": "📋",
        "Resultado": "📈",
        "Segurança": "🛡️",
        "Evento": "🎉",
        "Sistema": "⚙️",
        "Geral": "📢",
        "Urgente": "🚨"
    }
    return icons.get(announcement_type, "📢")

# Interface principal
st.title("📢 DASHBOARD DE ANÚNCIOS")
st.markdown("### 🏢 Central de Comunicação Corporativa")

# Sidebar para controles
# Show user info
auth.show_user_info()

st.sidebar.header("🎛️ Controles")

# Carregar anúncios
announcements = load_announcements()

# Get current user for role checking
current_user = auth.get_current_user()

# Botão para usar dados de exemplo (admin only)
if auth.is_admin(current_user):
    if st.sidebar.button("📊 Carregar Dados de Exemplo"):
        sample_announcements = create_sample_announcements()
        if save_announcements(sample_announcements):
            st.success("✅ Dados de exemplo carregados!")
            announcements = sample_announcements
            st.rerun()

# Seção para criar novo anúncio (admin only)
if auth.is_admin(current_user):
    with st.sidebar.expander("➕ Criar Novo Anúncio"):
        with st.form("new_announcement"):
            title = st.text_input("Título")
            content = st.text_area("Conteúdo", height=100)
            
            col1, col2 = st.columns(2)
            with col1:
                announcement_type = st.selectbox(
                    "Tipo",
                    ["Geral", "Política", "Resultado", "Segurança", "Evento", "Sistema", "Urgente"]
                )
                priority = st.selectbox("Prioridade", ["Baixa", "Média", "Alta", "Crítica"])
            
            with col2:
                department = st.selectbox(
                    "Departamento",
                    ["Todos", "TI", "Compras", "Vendas", "RH", "Financeiro", "Produção"]
                )
                author = st.text_input("Autor", value="Admin")
            
            expiry_date = st.date_input(
                "Data de Expiração",
                value=date.today() + timedelta(days=30)
            )
            
            if st.form_submit_button("📝 Criar Anúncio"):
                if title and content:
                    new_id = max([a.get('id', 0) for a in announcements] + [0]) + 1
                    new_announcement = {
                        "id": new_id,
                        "title": f"{get_type_icon(announcement_type)} {title}",
                        "content": content,
                        "type": announcement_type,
                        "priority": priority,
                        "department": department,
                        "author": author,
                        "date": date.today().isoformat(),
                        "expiry_date": expiry_date.isoformat(),
                        "active": True
                    }
                    announcements.append(new_announcement)
                    if save_announcements(announcements):
                        st.success("✅ Anúncio criado com sucesso!")
                        st.rerun()
                    else:
                        st.error("❌ Erro ao salvar anúncio")
                else:
                    st.error("⚠️ Preencha título e conteúdo")
else:
    st.sidebar.info("🔒 Apenas administradores podem criar anúncios")

# Filtros
st.sidebar.subheader("🔍 Filtros")
filter_type = st.sidebar.multiselect(
    "Tipo",
    options=list(set([a.get('type', 'Geral') for a in announcements])),
    default=list(set([a.get('type', 'Geral') for a in announcements]))
)

filter_priority = st.sidebar.multiselect(
    "Prioridade",
    options=["Crítica", "Alta", "Média", "Baixa"],
    default=["Crítica", "Alta", "Média", "Baixa"]
)

filter_department = st.sidebar.selectbox(
    "Departamento",
    ["Todos"] + ["TI", "Compras", "Vendas", "RH", "Financeiro", "Produção"]
)

# Área principal
if announcements:
    # Filtrar anúncios
    filtered_announcements = []
    for announcement in announcements:
        # Verificar se ainda está ativo
        try:
            expiry = datetime.strptime(announcement.get('expiry_date', '2099-12-31'), '%Y-%m-%d')
            is_active = expiry.date() >= date.today()
        except:
            is_active = True
        
        if (announcement.get('type') in filter_type and 
            announcement.get('priority') in filter_priority and
            (filter_department == "Todos" or announcement.get('department') in ["Todos", filter_department]) and
            is_active):
            filtered_announcements.append(announcement)
    
    if filtered_announcements:
        # Estatísticas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total = len(filtered_announcements)
            st.metric("📢 Total de Anúncios", total)
        
        with col2:
            criticos = len([a for a in filtered_announcements if a.get('priority') == 'Crítica'])
            st.metric("🚨 Críticos", criticos)
        
        with col3:
            hoje = len([a for a in filtered_announcements 
                       if a.get('date') == date.today().isoformat()])
            st.metric("📅 Hoje", hoje)
        
        with col4:
            expirando = len([a for a in filtered_announcements 
                           if datetime.strptime(a.get('expiry_date', '2099-12-31'), '%Y-%m-%d').date() 
                           <= date.today() + timedelta(days=7)])
            st.metric("⏰ Expirando", expirando)
        
        # Gráfico de distribuição por tipo
        if len(filtered_announcements) > 0:
            df_types = pd.DataFrame(filtered_announcements)
            type_counts = df_types['type'].value_counts()
            
            fig = px.pie(
                values=type_counts.values,
                names=type_counts.index,
                title="📊 Distribuição por Tipo"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Lista de anúncios
        st.subheader("📋 Anúncios Ativos")
        
        # Ordenar por prioridade e data
        priority_order = {"Crítica": 4, "Alta": 3, "Média": 2, "Baixa": 1}
        filtered_announcements.sort(
            key=lambda x: (priority_order.get(x.get('priority', 'Baixa'), 1), x.get('date')),
            reverse=True
        )
        
        for announcement in filtered_announcements:
            priority_color = get_priority_color(announcement.get('priority', 'Baixa'))
            
            with st.container():
                col1, col2 = st.columns([1, 10])
                
                with col1:
                    st.markdown(
                        f'<div style="background-color: {priority_color}; '
                        f'width: 5px; height: 100%; border-radius: 3px;"></div>',
                        unsafe_allow_html=True
                    )
                
                with col2:
                    st.markdown(f"### {announcement.get('title', 'Sem título')}")
                    
                    # Informações do anúncio
                    info_col1, info_col2, info_col3, info_col4 = st.columns(4)
                    
                    with info_col1:
                        st.write(f"**Tipo:** {announcement.get('type', 'Geral')}")
                    with info_col2:
                        st.write(f"**Prioridade:** {announcement.get('priority', 'Baixa')}")
                    with info_col3:
                        st.write(f"**Departamento:** {announcement.get('department', 'Todos')}")
                    with info_col4:
                        st.write(f"**Autor:** {announcement.get('author', 'Desconhecido')}")
                    
                    # Conteúdo
                    st.write(announcement.get('content', ''))
                    
                    # Datas
                    date_col1, date_col2 = st.columns(2)
                    with date_col1:
                        st.caption(f"📅 Criado em: {announcement.get('date', 'Data desconhecida')}")
                    with date_col2:
                        expiry = announcement.get('expiry_date', '2099-12-31')
                        try:
                            expiry_date = datetime.strptime(expiry, '%Y-%m-%d').date()
                            days_left = (expiry_date - date.today()).days
                            if days_left <= 0:
                                st.caption("⏰ **EXPIRADO**")
                            elif days_left <= 7:
                                st.caption(f"⏰ Expira em {days_left} dias")
                            else:
                                st.caption(f"📅 Expira em: {expiry}")
                        except:
                            st.caption(f"📅 Expira em: {expiry}")
                
                st.divider()
    
    else:
        st.info("🔍 Nenhum anúncio encontrado com os filtros aplicados.")

else:
    st.info("📢 Nenhum anúncio encontrado. Use os dados de exemplo ou crie um novo anúncio!")

# Botão para limpar todos os anúncios (admin only)
if auth.is_admin(current_user):
    if st.sidebar.button("🗑️ Limpar Todos os Anúncios", type="secondary"):
        if save_announcements([]):
            st.success("✅ Todos os anúncios foram removidos!")
            st.rerun() 