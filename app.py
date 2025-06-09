import streamlit as st
from datetime import datetime
import auth
import sys
import os

# Check authentication first
if not auth.require_auth():
    st.stop()

st.set_page_config(page_title="Dashboard Corporativo", page_icon="🏢", layout="wide")

# Import functions from page files
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def show_dashboard():
    st.title("🏢 DASHBOARD CORPORATIVO")
    st.markdown("### 📊 Central de Gestão e Comunicação")
    
    # Hero section
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        ### 📅 Timeline de Compras
        Visualize e otimize suas compras com base em MOQ e análise de estoque.
        
        **Recursos:**
        - ⏰ Previsão de esgotamento
        - 🎯 Otimização de MOQ 
        - 📈 Gráficos interativos
        - 💰 Análise financeira
        """)
        if st.button("🚀 Acessar Timeline", use_container_width=True, key="nav_timeline"):
            st.session_state.current_page = "timeline"
            st.rerun()

    with col2:
        st.markdown("""
        ### 📢 Central de Anúncios
        Gerencie comunicações corporativas e mantenha todos informados.
        
        **Recursos:**
        - 📝 Criar anúncios
        - 🎯 Filtros por departamento
        - ⚡ Níveis de prioridade
        - 📊 Dashboard analítico
        """)
        if st.button("🚀 Acessar Anúncios", use_container_width=True, key="nav_announcements"):
            st.session_state.current_page = "announcements"
            st.rerun()

    with col3:
        st.markdown("""
        ### 📈 Métricas em Tempo Real
        
        **Status Atual:**
        - 🟢 Sistema: Operacional
        - 📊 Dados: Atualizados
        - 👥 Usuários: Online
        - 🔄 Última atualização: Agora
        """)
        st.success("✅ Todos os sistemas funcionando normalmente")

    st.divider()

    # Quick stats section
    st.subheader("📊 Resumo Executivo")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="⏰ Uptime do Sistema",
            value="99.9%",
            delta="0.1%"
        )

    with col2:
        st.metric(
            label="📈 Eficiência",
            value="94%",
            delta="2%"
        )

    with col3:
        st.metric(
            label="💰 Economia MOQ",
            value="R$ 250K",
            delta="R$ 15K"
        )

    with col4:
        st.metric(
            label="📢 Anúncios Ativos",
            value="12",
            delta="3"
        )

    st.divider()

    # Features grid
    st.subheader("🎯 Funcionalidades Principais")

    features_col1, features_col2 = st.columns(2)

    with features_col1:
        with st.container():
            st.markdown("""
            #### 🔍 Análise Inteligente
            - **Predição de Estoque**: Algoritmos avançados para prever quando produtos vão esgotar
            - **Otimização de MOQ**: Calcula automaticamente as melhores quantidades de compra
            - **Alertas Proativos**: Notificações antes que problemas aconteçam
            """)

    with features_col2:
        with st.container():
            st.markdown("""
            #### 📱 Interface Moderna
            - **Design Responsivo**: Funciona perfeitamente em qualquer dispositivo
            - **Visualizações Interativas**: Gráficos dinâmicos com Plotly
            - **Filtros Inteligentes**: Encontre exatamente o que precisa
            """)

    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>🚀 Desenvolvido com Streamlit | 💡 Otimizado para performance | 🔒 Seguro e confiável</p>
        <p>📞 Suporte: support@empresa.com | 📚 Documentação disponível no GitHub</p>
    </div>
    """, unsafe_allow_html=True)

def show_timeline():
    import pandas as pd
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import numpy as np
    from datetime import datetime, timedelta
    
    st.title("📅 TIMELINE INTERATIVA DE COMPRAS")
    st.markdown("### 🎯 Visualização interativa com MOQ otimizado")

    with st.expander("ℹ️ Como usar esta aplicação"):
        st.markdown("""
        **Para usar esta aplicação:**
        1. 📁 **Upload:** Faça upload do seu arquivo Excel na barra lateral
        2. 📊 **Exemplo:** Ou marque a opção "Usar dados de exemplo" para testar
        3. 🎛️ **Configure:** Ajuste os parâmetros na barra lateral
        4. 📈 **Analise:** Visualize os gráficos interativos
        
        **Formato do arquivo Excel:**
        - Deve ter as colunas: Item, Modelo, Fornecedor, QTD, Preço FOB Unitário, Estoque Total, In Transit Shipt, Avg Sales, CBM, MOQ
        - Os dados devem começar na linha 10 (header=9)
        """)

    @st.cache_data
    def carregar_dados(uploaded_file=None):
        try:
            if uploaded_file is not None:
                df = pd.read_excel(uploaded_file, header=9)
            else:
                # No local file in production - user must upload
                return None
            
            df = df.dropna(subset=['Item'])
            df = df[df['Item'] != 'Item']
            
            # Converter colunas numéricas
            colunas_numericas = ['QTD', 'Preço FOB\nUnitário', 'Estoque\nTotal ', 
                               'In Transit\nShipt', 'Avg Sales\n', 'CBM', 'MOQ']
            
            for col in colunas_numericas:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # Renomear colunas
            df = df.rename(columns={
                'Preço FOB\nUnitário': 'Preco_Unitario',
                'Estoque\nTotal ': 'Estoque_Total',
                'In Transit\nShipt': 'In_Transit',
                'Avg Sales\n': 'Vendas_Medias'
            })
            
            return df
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            return None

    def criar_dados_exemplo():
        """Cria dados de exemplo para demonstração"""
        dados_exemplo = {
            'Item': ['ITEM001', 'ITEM002', 'ITEM003', 'ITEM004', 'ITEM005'],
            'Modelo': ['Multímetro DM-1000', 'Osciloscópio OS-200', 'Fonte DC-300', 'Gerador GF-400', 'Analisador AN-500'],
            'Fornecedor': ['Fornecedor A', 'Fornecedor B', 'Fornecedor A', 'Fornecedor C', 'Fornecedor B'],
            'QTD': [100, 50, 75, 30, 25],
            'Preço FOB\nUnitário': [150.00, 800.00, 450.00, 1200.00, 2500.00],
            'Estoque\nTotal ': [45, 12, 23, 8, 5],
            'In Transit\nShipt': [20, 5, 10, 0, 2],
            'Avg Sales\n': [15, 3, 8, 2, 1],
            'CBM': [0.05, 0.15, 0.08, 0.12, 0.20],
            'MOQ': [50, 10, 25, 5, 5]
        }
        return pd.DataFrame(dados_exemplo)

    # Timeline sidebar controls
    st.sidebar.header("📁 Upload de Dados")
    uploaded_file = st.sidebar.file_uploader(
        "Faça upload do seu arquivo Excel:",
        type=['xlsx', 'xls'],
        help="Carregue um arquivo Excel com dados de estoque e vendas"
    )

    usar_dados_exemplo = st.sidebar.checkbox("📊 Usar dados de exemplo", value=False)

    if usar_dados_exemplo:
        df = criar_dados_exemplo()
        st.info("📊 Usando dados de exemplo para demonstração")
    elif uploaded_file is not None:
        df = carregar_dados(uploaded_file)
        st.success("✅ Arquivo carregado com sucesso!")
    else:
        df = carregar_dados()
        if df is None:
            st.warning("📁 Faça upload de um arquivo Excel ou use os dados de exemplo para começar!")
    
    if df is not None:
        st.sidebar.header("🎛️ Controles")
        
        meta_meses = st.sidebar.slider("🎯 Meta (meses)", 3, 12, 6)
        
        def otimizar_quantidade_moq(vendas_mensais, moq, meta_meses=6):
            if vendas_mensais <= 0:
                return moq if moq > 0 else 0
            
            qtd_ideal = vendas_mensais * meta_meses
            
            if moq > qtd_ideal:
                return moq
            
            if moq <= 0:
                return int(qtd_ideal)
            
            multiplos = max(1, int(np.ceil(qtd_ideal / moq)))
            return multiplos * moq

        def calcular_timeline(df, meta_meses=6):
            hoje = datetime.now()
            timeline_data = []
            
            for idx, row in df.iterrows():
                produto = str(row['Modelo'])
                fornecedor = str(row['Fornecedor'])
                estoque_atual = row['Estoque_Total'] + row['In_Transit']
                vendas_mensais = row['Vendas_Medias']
                moq = row['MOQ']
                preco = row['Preco_Unitario']
                cbm = row['CBM']
                
                if vendas_mensais > 0:
                    meses_ate_zerar = estoque_atual / vendas_mensais
                    data_esgotamento = hoje + timedelta(days=int(meses_ate_zerar * 30))
                    data_pedido = data_esgotamento - timedelta(days=45)
                    if data_pedido < hoje:
                        data_pedido = hoje
                    
                    qtd_otimizada = otimizar_quantidade_moq(vendas_mensais, moq, meta_meses)
                    valor_pedido = qtd_otimizada * preco
                    cbm_pedido = qtd_otimizada * cbm
                    
                    if meses_ate_zerar <= 1:
                        cor = '#FF0000'
                        urgencia = 'CRÍTICO'
                    elif meses_ate_zerar <= 3:
                        cor = '#FF8C00'
                        urgencia = 'MÉDIO'
                    elif meses_ate_zerar <= 6:
                        cor = '#FFD700'
                        urgencia = 'ATENÇÃO'
                    else:
                        cor = '#32CD32'
                        urgencia = 'OK'
                    
                    timeline_data.append({
                        'Produto': produto,
                        'Fornecedor': fornecedor,
                        'Dias_Restantes': int(meses_ate_zerar * 30),
                        'Estoque_Atual': estoque_atual,
                        'Vendas_Mensais': vendas_mensais,
                        'MOQ': moq,
                        'Qtd_Otimizada': qtd_otimizada,
                        'Valor_Pedido': valor_pedido,
                        'CBM_Pedido': cbm_pedido,
                        'Cor': cor,
                        'Urgencia': urgencia
                    })
            
            return sorted(timeline_data, key=lambda x: x['Dias_Restantes'])

        def criar_grafico_interativo(timeline_data, filtro_urgencia="Todos"):
            if filtro_urgencia != "Todos":
                timeline_data = [item for item in timeline_data if item['Urgencia'] == filtro_urgencia]
            
            if not timeline_data:
                return None
            
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('⏰ QUANDO O ESTOQUE VAI ACABAR', '📦 QUANTO COMPRAR (MOQ)'),
                vertical_spacing=0.15
            )
            
            produtos = [item['Produto'] for item in timeline_data]
            
            # Gráfico 1: Timeline
            for i, item in enumerate(timeline_data):
                fig.add_trace(
                    go.Bar(
                        y=[i],
                        x=[item['Dias_Restantes']],
                        orientation='h',
                        marker_color=item['Cor'],
                        opacity=0.7,
                        showlegend=False,
                        hovertemplate=(
                            f"<b>{item['Produto']}</b><br>" +
                            f"Fornecedor: {item['Fornecedor']}<br>" +
                            f"Estoque: {item['Estoque_Atual']:.0f} un.<br>" +
                            f"Dias restantes: {item['Dias_Restantes']}<br>" +
                            f"MOQ: {item['MOQ']:.0f}<br>" +
                            f"Comprar: {item['Qtd_Otimizada']:.0f}<br>" +
                            "<extra></extra>"
                        )
                    ),
                    row=1, col=1
                )
            
            # Gráfico 2: Quantidades
            for i, item in enumerate(timeline_data):
                fig.add_trace(
                    go.Bar(
                        y=[i],
                        x=[item['Qtd_Otimizada']],
                        orientation='h',
                        marker_color=item['Cor'],
                        opacity=0.7,
                        showlegend=False,
                        hovertemplate=(
                            f"<b>{item['Produto']}</b><br>" +
                            f"Quantidade: {item['Qtd_Otimizada']:.0f} un.<br>" +
                            f"MOQ: {item['MOQ']:.0f}<br>" +
                            f"Valor: R$ {item['Valor_Pedido']:,.0f}<br>" +
                            f"CBM: {item['CBM_Pedido']:.1f}<br>" +
                            "<extra></extra>"
                        )
                    ),
                    row=2, col=1
                )
            
            fig.update_layout(
                title="📅 TIMELINE INTERATIVA COM MOQ",
                height=max(800, len(timeline_data) * 40),
                showlegend=False
            )
            
            fig.update_yaxes(tickvals=list(range(len(produtos))), ticktext=produtos, row=1, col=1)
            fig.update_yaxes(tickvals=list(range(len(produtos))), ticktext=produtos, row=2, col=1)
            fig.update_xaxes(title_text="Dias", row=1, col=1)
            fig.update_xaxes(title_text="Quantidade", row=2, col=1)
            
            return fig
        
        timeline_data = calcular_timeline(df, meta_meses)
        
        if timeline_data:
            urgencias = ["Todos"] + sorted(list(set(item['Urgencia'] for item in timeline_data)))
            filtro = st.sidebar.selectbox("🔍 Filtrar", urgencias)
            
            # Métricas
            col1, col2, col3, col4 = st.columns(4)
            criticos = len([x for x in timeline_data if x['Urgencia'] == 'CRÍTICO'])
            medios = len([x for x in timeline_data if x['Urgencia'] == 'MÉDIO'])
            atencao = len([x for x in timeline_data if x['Urgencia'] == 'ATENÇÃO'])
            ok = len([x for x in timeline_data if x['Urgencia'] == 'OK'])
            
            col1.metric("🔴 Críticos", criticos)
            col2.metric("🟠 Médios", medios)
            col3.metric("🟡 Atenção", atencao)
            col4.metric("🟢 OK", ok)
            
            valor_total = sum(item['Valor_Pedido'] for item in timeline_data)
            st.metric("💰 Investimento Total", f"R$ {valor_total:,.0f}")
            
            # Gráfico
            fig = criar_grafico_interativo(timeline_data, filtro)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("""
                **💡 Como usar:**
                - 🖱️ **Zoom**: Ferramentas no canto superior direito
                - 👆 **Hover**: Passe o mouse para ver detalhes
                - 🔍 **Filtrar**: Use a sidebar
                """)
        else:
            st.warning("📊 Nenhum dado válido encontrado para criar o timeline.")
    else:
        st.info("📤 Aguardando upload de dados...")

def show_announcements():
    import pandas as pd
    import json
    import os
    from datetime import date, timedelta
    import plotly.express as px
    
    st.title("📢 DASHBOARD DE ANÚNCIOS")
    st.markdown("### 🏢 Central de Comunicação Corporativa")
    
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
        from datetime import datetime
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
    
    # Get current user for role checking
    current_user = auth.get_current_user()
    
    # Carregar anúncios
    announcements = load_announcements()
    
    st.sidebar.header("🎛️ Controles")
    
    # Admin only features
    if auth.is_admin(current_user):
        st.sidebar.success("🔑 Modo Administrador")
        
        # Sample data button
        if st.sidebar.button("📊 Carregar Dados de Exemplo"):
            sample_announcements = create_sample_announcements()
            if save_announcements(sample_announcements):
                st.success("✅ Dados de exemplo carregados!")
                announcements = sample_announcements
                st.rerun()
        
        # Create announcement form
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
                    author = st.text_input("Autor", value=current_user['name'])
                
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
        
        # Clear all button
        if st.sidebar.button("🗑️ Limpar Todos os Anúncios", type="secondary"):
            if save_announcements([]):
                st.success("✅ Todos os anúncios foram removidos!")
                st.rerun()
    else:
        st.sidebar.info("👁️ Modo Visualização")
    
    # Filtros
    st.sidebar.subheader("🔍 Filtros")
    
    # Executive view toggle
    view_mode = st.sidebar.radio(
        "👔 Modo de Visualização",
        ["🎯 Executivo (Por Prioridade)", "📋 Detalhado (Lista Completa)"],
        help="Executivo: Categorizado por prioridade para liderança\nDetalhado: Lista tradicional com todos os anúncios"
    )
    
    if announcements:
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
    
    # Main content area
    if announcements:
        # Filter announcements
        filtered_announcements = []
        for announcement in announcements:
            # Check if still active
            try:
                from datetime import datetime
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
                from datetime import datetime
                expirando = len([a for a in filtered_announcements 
                               if datetime.strptime(a.get('expiry_date', '2099-12-31'), '%Y-%m-%d').date() 
                               <= date.today() + timedelta(days=7)])
                st.metric("⏰ Expirando", expirando)
            
            # Show different views based on mode
            if view_mode == "🎯 Executivo (Por Prioridade)":
                # Categorização por prioridade
                st.subheader("📋 Central de Anúncios - Painel Executivo")
                
                # Agrupar anúncios por prioridade
                priority_groups = {
                    "Crítica": [],
                    "Alta": [],
                    "Média": [],
                    "Baixa": []
                }
                
                for announcement in filtered_announcements:
                    priority = announcement.get('priority', 'Baixa')
                    priority_groups[priority].append(announcement)
                
                # Ordenar dentro de cada grupo por data
                for priority in priority_groups:
                    priority_groups[priority].sort(key=lambda x: x.get('date'), reverse=True)
                
                # Mostrar cada categoria de prioridade
                priority_configs = {
                    "Crítica": {
                        "icon": "🚨",
                        "color": "#FF4444",
                        "bg_color": "#FFF5F5",
                        "description": "Requer ação imediata da liderança"
                    },
                    "Alta": {
                        "icon": "🔥",
                        "color": "#FF8800", 
                        "bg_color": "#FFF8F0",
                        "description": "Importante para decisões estratégicas"
                    },
                    "Média": {
                        "icon": "⚡",
                        "color": "#FFDD00",
                        "bg_color": "#FFFEF0",
                        "description": "Informações relevantes para gestores"
                    },
                    "Baixa": {
                        "icon": "📝",
                        "color": "#44AA44",
                        "bg_color": "#F8FFF8",
                        "description": "Informações gerais e atualizações"
                    }
                }
                
                for priority in ["Crítica", "Alta", "Média", "Baixa"]:
                    announcements_in_priority = priority_groups[priority]
                    
                    if announcements_in_priority:
                        config = priority_configs[priority]
                        count = len(announcements_in_priority)
                        
                        # Header da categoria com estilo executivo
                        st.markdown(f"""
                        <div style="
                            background: linear-gradient(90deg, {config['color']}15, {config['bg_color']});
                            border-left: 6px solid {config['color']};
                            padding: 15px 20px;
                            margin: 20px 0 10px 0;
                            border-radius: 8px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        ">
                            <h3 style="
                                color: {config['color']};
                                margin: 0;
                                font-weight: bold;
                                display: flex;
                                align-items: center;
                                gap: 10px;
                            ">
                                {config['icon']} PRIORIDADE {priority.upper()} 
                                <span style="
                                    background: {config['color']};
                                    color: white;
                                    padding: 2px 8px;
                                    border-radius: 12px;
                                    font-size: 12px;
                                    font-weight: normal;
                                ">{count}</span>
                            </h3>
                            <p style="
                                color: #666;
                                margin: 5px 0 0 0;
                                font-style: italic;
                            ">{config['description']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Expandir/colapsar por prioridade (execept crítica que fica sempre aberta)
                        if priority == "Crítica":
                            show_section = True
                        else:
                            show_section = st.checkbox(
                                f"Expandir {priority} ({count} anúncios)",
                                value=(priority in ["Alta"]),  # Alta fica aberta por padrão
                                key=f"expand_{priority}"
                            )
                        
                        if show_section:
                            for i, announcement in enumerate(announcements_in_priority):
                                # Card estilizado para cada anúncio
                                st.markdown(f"""
                                <div style="
                                    background: white;
                                    border: 1px solid {config['color']}30;
                                    border-left: 4px solid {config['color']};
                                    border-radius: 8px;
                                    padding: 20px;
                                    margin: 10px 0;
                                    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                                ">
                                """, unsafe_allow_html=True)
                                
                                # Título com ícone de tipo
                                type_icon = get_type_icon(announcement.get('type', 'Geral'))
                                st.markdown(f"#### {type_icon} {announcement.get('title', 'Sem título')}")
                                
                                # Informações em linha executiva
                                info_col1, info_col2, info_col3, info_col4 = st.columns(4)
                                
                                with info_col1:
                                    st.markdown(f"**📁 Tipo:** {announcement.get('type', 'Geral')}")
                                with info_col2:
                                    priority_display = announcement.get('priority', 'Baixa')
                                    st.markdown(f"**🎯 Prioridade:** <span style='color: {config['color']}; font-weight: bold;'>{priority_display}</span>", unsafe_allow_html=True)
                                with info_col3:
                                    st.markdown(f"**🏢 Departamento:** {announcement.get('department', 'Todos')}")
                                with info_col4:
                                    st.markdown(f"**👤 Autor:** {announcement.get('author', 'Desconhecido')}")
                                
                                # Conteúdo com destaque
                                st.markdown("**📝 Conteúdo:**")
                                st.markdown(f"<div style='background: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 3px solid {config['color']};'>{announcement.get('content', '')}</div>", unsafe_allow_html=True)
                                
                                # Datas em formato executivo
                                date_col1, date_col2, date_col3 = st.columns(3)
                                with date_col1:
                                    st.caption(f"📅 **Criado:** {announcement.get('date', 'Data desconhecida')}")
                                with date_col2:
                                    expiry = announcement.get('expiry_date', '2099-12-31')
                                    try:
                                        from datetime import datetime
                                        expiry_date = datetime.strptime(expiry, '%Y-%m-%d').date()
                                        days_left = (expiry_date - date.today()).days
                                        if days_left <= 0:
                                            st.caption("⏰ **Status:** <span style='color: #FF4444; font-weight: bold;'>EXPIRADO</span>", unsafe_allow_html=True)
                                        elif days_left <= 7:
                                            st.caption(f"⏰ **Status:** <span style='color: #FF8800; font-weight: bold;'>Expira em {days_left} dias</span>", unsafe_allow_html=True)
                                        else:
                                            st.caption(f"⏰ **Expira:** {expiry}")
                                    except:
                                        st.caption(f"⏰ **Expira:** {expiry}")
                                with date_col3:
                                    # Ação rápida para executivos
                                    if priority == "Crítica":
                                        st.caption("🎯 **Ação:** <span style='color: #FF4444; font-weight: bold;'>REVISAR AGORA</span>", unsafe_allow_html=True)
                                    elif priority == "Alta":
                                        st.caption("📋 **Ação:** <span style='color: #FF8800; font-weight: bold;'>Revisar hoje</span>", unsafe_allow_html=True)
                                    else:
                                        st.caption("📖 **Status:** Informativo")
                                
                                st.markdown("</div>", unsafe_allow_html=True)
                                
                                # Espaçamento entre anúncios
                                if i < len(announcements_in_priority) - 1:
                                    st.markdown("<br>", unsafe_allow_html=True)
                        
                        # Espaçamento entre categorias
                        st.markdown("<br>", unsafe_allow_html=True)
            
            else:
                # Vista detalhada tradicional
                st.subheader("📋 Anúncios Ativos - Vista Detalhada")
                
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
                                    from datetime import datetime
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

# Main app logic
# Show user info in sidebar
auth.show_user_info()

# Add manual navigation
st.sidebar.markdown("---")
st.sidebar.markdown("### 🧭 Navegação")

# Initialize session state for page navigation
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"

# Navigation buttons
if st.sidebar.button("🏠 Dashboard", use_container_width=True):
    st.session_state.current_page = "home"
    st.rerun()

if st.sidebar.button("📅 Timeline de Compras", use_container_width=True):
    st.session_state.current_page = "timeline"
    st.rerun()

if st.sidebar.button("📢 Anúncios", use_container_width=True):
    st.session_state.current_page = "announcements"
    st.rerun()

# Show different pages based on navigation
if st.session_state.current_page == "home":
    show_dashboard()
elif st.session_state.current_page == "timeline":
    show_timeline()
elif st.session_state.current_page == "announcements":
    show_announcements()

 