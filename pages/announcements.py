import streamlit as st
import json
import os
from datetime import date, timedelta

def show_announcements():
    """Simplified announcements page"""
    st.title("📢 DASHBOARD DE ANÚNCIOS")
    st.markdown("### 🏢 Central de Comunicação Corporativa")
    
    # Data file path
    ANNOUNCEMENTS_FILE = "announcements.json"

    def load_announcements():
        """Load announcements from JSON file"""
        if os.path.exists(ANNOUNCEMENTS_FILE):
            try:
                with open(ANNOUNCEMENTS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_announcements(announcements):
        """Save announcements to JSON file"""
        try:
            with open(ANNOUNCEMENTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(announcements, f, ensure_ascii=False, indent=2, default=str)
            return True
        except:
            return False

    def create_sample_announcements():
        """Create sample announcements"""
        return [
            {
                "id": 1,
                "title": "🎉 Nova Política de Home Office",
                "content": "A partir de segunda-feira, implementaremos nossa nova política de trabalho híbrido.",
                "type": "Política",
                "priority": "Alta",
                "department": "Todos",
                "author": "Recursos Humanos",
                "date": "2024-01-15",
                "active": True
            },
            {
                "id": 2,
                "title": "📈 Resultados Q4 2023",
                "content": "Excelentes resultados no último trimestre! Aumentamos nossa receita em 15%.",
                "type": "Resultado",
                "priority": "Média",
                "department": "Todos",
                "author": "Diretoria",
                "date": "2024-01-10",
                "active": True
            }
        ]

    # Get current user
    try:
        import auth
        current_user = auth.get_current_user()
        is_admin = auth.is_admin(current_user)
    except:
        current_user = {"name": "User"}
        is_admin = True  # Default to admin for demo
    
    # Load announcements
    announcements = load_announcements()
    
    # Sidebar controls
    st.sidebar.header("🎛️ Controles")
    
    # Admin controls
    if is_admin:
        st.sidebar.success("🔑 Modo Administrador")
        
        # Sample data button
        if st.sidebar.button("📊 Carregar Dados de Exemplo"):
            sample_announcements = create_sample_announcements()
            if save_announcements(sample_announcements):
                st.success("✅ Dados de exemplo carregados!")
                announcements = sample_announcements
                st.rerun()
        
        # Create new announcement
        with st.sidebar.expander("➕ Criar Novo Anúncio"):
            with st.form("new_announcement"):
                title = st.text_input("Título")
                content = st.text_area("Conteúdo", height=100)
                
                col1, col2 = st.columns(2)
                with col1:
                    announcement_type = st.selectbox(
                        "Tipo",
                        ["Geral", "Política", "Resultado", "Segurança", "Evento"]
                    )
                    priority = st.selectbox("Prioridade", ["Baixa", "Média", "Alta", "Crítica"])
                
                with col2:
                    department = st.selectbox("Departamento", ["Todos", "Importação"])
                    author = st.text_input("Autor", value=current_user['name'])
                
                if st.form_submit_button("📝 Criar Anúncio"):
                    if title and content:
                        new_id = max([a.get('id', 0) for a in announcements] + [0]) + 1
                        new_announcement = {
                            "id": new_id,
                            "title": f"📢 {title}",
                            "content": content,
                            "type": announcement_type,
                            "priority": priority,
                            "department": department,
                            "author": author,
                            "date": date.today().isoformat(),
                            "active": True
                        }
                        announcements.append(new_announcement)
                        
                        if save_announcements(announcements):
                            st.success("✅ Anúncio criado com sucesso!")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao salvar anúncio")
                    else:
                        st.error("⚠️ Preencha todos os campos obrigatórios")
    
    # Display announcements
    if announcements:
        st.subheader("📋 Anúncios Ativos")
        
        # Filter controls
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_type = st.selectbox("Filtrar por tipo:", ["Todos"] + list(set(a['type'] for a in announcements)))
        with col2:
            filter_priority = st.selectbox("Filtrar por prioridade:", ["Todas"] + list(set(a['priority'] for a in announcements)))
        with col3:
            filter_dept = st.selectbox("Filtrar por departamento:", ["Todos"] + list(set(a['department'] for a in announcements)))
        
        # Apply filters
        filtered_announcements = announcements
        if filter_type != "Todos":
            filtered_announcements = [a for a in filtered_announcements if a['type'] == filter_type]
        if filter_priority != "Todas":
            filtered_announcements = [a for a in filtered_announcements if a['priority'] == filter_priority]
        if filter_dept != "Todos":
            filtered_announcements = [a for a in filtered_announcements if a['department'] == filter_dept]
        
        # Display filtered announcements
        for announcement in filtered_announcements:
            if announcement.get('active', True):
                # Color based on priority
                priority_colors = {
                    "Crítica": "🔴",
                    "Alta": "🟠", 
                    "Média": "🟡",
                    "Baixa": "🟢"
                }
                priority_icon = priority_colors.get(announcement['priority'], "⚪")
                
                with st.container():
                    st.markdown(f"""
                    <div style="border-left: 4px solid #1f77b4; padding: 10px; margin: 10px 0; background: #f8f9fa;">
                        <h4>{announcement['title']}</h4>
                        <p>{announcement['content']}</p>
                        <small>
                            {priority_icon} {announcement['priority']} | 
                            📂 {announcement['type']} | 
                            🏢 {announcement['department']} | 
                            👤 {announcement['author']} | 
                            📅 {announcement['date']}
                        </small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Admin delete button
                    if is_admin:
                        if st.button(f"🗑️ Deletar", key=f"delete_{announcement['id']}"):
                            announcements = [a for a in announcements if a['id'] != announcement['id']]
                            save_announcements(announcements)
                            st.rerun()
                    
                    st.divider()
        
        if not filtered_announcements:
            st.info("💡 Nenhum anúncio corresponde aos filtros selecionados")
    else:
        st.info("💡 Nenhum anúncio encontrado")
        if is_admin:
            st.info("👉 Use 'Carregar Dados de Exemplo' ou crie um novo anúncio")
    
    # Statistics
    if announcements:
        st.subheader("📊 Estatísticas")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📢 Total", len(announcements))
        with col2:
            active_count = len([a for a in announcements if a.get('active', True)])
            st.metric("✅ Ativos", active_count)
        with col3:
            critical_count = len([a for a in announcements if a.get('priority') == 'Crítica'])
            st.metric("🔴 Críticos", critical_count)
        with col4:
            recent_count = len([a for a in announcements if a.get('date', '') >= (date.today() - timedelta(days=7)).isoformat()])
            st.metric("🆕 Esta semana", recent_count)
    
    # Help section
    with st.expander("💡 Como usar"):
        st.markdown("""
        ### 📢 Sistema de Anúncios
        
        **Para usuários:**
        - Visualize anúncios por prioridade e departamento
        - Use os filtros para encontrar anúncios específicos
        - Anúncios críticos aparecem em destaque
        
        **Para administradores:**
        - Crie novos anúncios usando o formulário na sidebar
        - Delete anúncios desnecessários
        - Monitore estatísticas de engajamento
        
        **Tipos de anúncio:**
        - 🏢 **Geral**: Comunicados gerais da empresa
        - 📋 **Política**: Mudanças em políticas internas
        - 📈 **Resultado**: Resultados financeiros e operacionais
        - 🛡️ **Segurança**: Alertas de segurança da informação
        - 🎉 **Evento**: Eventos corporativos e celebrações
        """) 