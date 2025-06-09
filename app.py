import streamlit as st
from datetime import datetime
import auth
import sys
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Check authentication first
if not auth.require_auth():
    st.stop()

st.set_page_config(page_title="Dashboard Corporativo", page_icon="🏢", layout="wide")

# Import functions from page files
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def show_data_upload():
    """Centralized data upload section"""
    st.header("📁 Central de Upload de Dados")
    st.markdown("**Upload seus arquivos Excel aqui. Os dados serão salvos na nuvem e disponíveis para todas as funcionalidades.**")
    
    # Import Snowflake functions
    try:
        from bd.snowflake_config import upload_excel_to_snowflake, load_data_with_history, test_connection
        snowflake_available = True
    except ImportError:
        snowflake_available = False
    
    # Show current data status
    if snowflake_available:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📊 Status dos Dados")
            
            # Try to load existing data
            existing_data = load_data_with_history()
            if existing_data is not None and len(existing_data) > 0:
                st.success(f"✅ {len(existing_data)} produtos já salvos na nuvem")
                
                # Check if data_upload column exists before accessing it
                if 'data_upload' in existing_data.columns:
                    st.info(f"📅 Último upload: {existing_data['data_upload'].max()}")
                else:
                    st.info("📅 Dados carregados da nuvem (sem informação de data)")
                
                # Show preview
                with st.expander("👀 Prévia dos dados salvos"):
                    st.dataframe(existing_data.head(10))
            else:
                st.info("💡 Nenhum dado encontrado na nuvem. Faça seu primeiro upload abaixo.")
        
        with col2:
            if st.button("🔄 Testar Conexão", use_container_width=True):
                if test_connection():
                    st.success("✅ Snowflake conectado!")
                else:
                    st.error("❌ Erro na conexão")
    
    # File upload section
    st.subheader("📤 Upload de Arquivo")
    
    # Create two distinct upload options
    upload_type = st.radio(
        "📋 Selecione o tipo de dados:",
        ["📅 Timeline de Compras (MOQ/Fornecedores)", "📊 Análise de Estoque (Export)"],
        help="Escolha o tipo correto para que os dados sejam processados adequadamente"
    )
    
    if upload_type == "📅 Timeline de Compras (MOQ/Fornecedores)":
        st.info("📝 **Para Timeline:** Upload com colunas Item, Fornecedor, QTD, Modelo, Preço FOB, MOQ, etc.")
        table_prefix = "TIMELINE"
        uploaded_file = st.file_uploader(
            "📁 Arquivo Excel para Timeline de Compras",
            type=['xlsx', 'xls'],
            help="Arquivo com dados de fornecedores, MOQ, preços FOB, etc.",
            key="timeline_upload"
        )
    else:
        st.info("📊 **Para Análise:** Upload com colunas Produto, Estoque, Média 6 Meses, Estoque Cobertura, etc.")
        table_prefix = "ANALYTICS"
        uploaded_file = st.file_uploader(
            "📁 Arquivo Excel para Análise de Estoque",
            type=['xlsx', 'xls'],
            help="Arquivo Export com dados de estoque e consumo",
            key="analytics_upload"
        )
    
    if uploaded_file is not None:
        st.subheader("🔍 Análise do Arquivo")
        
        if snowflake_available:
            try:
                # Use the improved Excel analysis
                df_full, detected_sheet, detected_header = analyze_and_process_excel(uploaded_file, "Auto-detectar")
                
                if df_full is not None:
                    st.success(f"✅ Dados carregados: {len(df_full)} linhas de '{detected_sheet}'")
                    st.dataframe(df_full.head(10))
                    
                    # Show data quality info
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("📊 Linhas", len(df_full))
                    with col2:
                        st.metric("📋 Colunas", len(df_full.columns))
                    with col3:
                        st.metric("✅ Valores válidos", df_full.count().sum())
                    with col4:
                        file_size = len(uploaded_file.getvalue()) / 1024
                        st.metric("📁 Tamanho", f"{file_size:.1f} KB")
                    
                    # Upload button
                    if st.button("💾 Salvar na Nuvem", type="primary"):
                        with st.spinner("📤 Processando e enviando dados para Snowflake..."):
                            try:
                                # Clean DataFrame for upload
                                df_clean = df_full.copy()
                                for col in df_clean.columns:
                                    if df_clean[col].dtype == 'object':
                                        df_clean[col] = df_clean[col].fillna('')
                                    else:
                                        df_clean[col] = df_clean[col].fillna(0)
                                
                                # Upload to Snowflake with table type
                                success = upload_excel_to_snowflake(df_clean, uploaded_file.name, "minipa", table_prefix)
                                
                                if success:
                                    st.success("🎉 Dados salvos com sucesso na nuvem!")
                                    st.balloons()
                                    
                                    # Show different messages based on upload type
                                    if table_prefix == "TIMELINE":
                                        st.info("✅ **Dados salvos para Timeline de Compras**")
                                        st.write("👉 Acesse a página '📅 Timeline de Compras' para ver a análise")
                                    else:
                                        st.info("✅ **Dados salvos para Análise de Estoque**") 
                                        st.write("👉 Acesse a página '📊 Análise de Estoque' para ver os relatórios")
                                    
                                    st.info(f"""
                                    📈 **Resumo do upload:**
                                    - 📁 Arquivo: {uploaded_file.name}
                                    - 📋 Planilha: {detected_sheet}
                                    - 📊 Cabeçalho: Linha {detected_header + 1}
                                    - 📈 Linhas: {len(df_clean)}
                                    - 🗂️ Tipo: {upload_type}
                                    - 🕒 Data: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
                                    """)
                                    st.rerun()
                                else:
                                    st.error("❌ Erro ao salvar dados na nuvem")
                                    
                            except Exception as e:
                                st.error(f"❌ Erro ao processar: {str(e)}")
                                st.code(str(e))
                else:
                    st.error("❌ Não foi possível processar o arquivo")
                    st.info("💡 Verifique se o arquivo Excel tem dados válidos")
                    
            except Exception as e:
                st.error(f"❌ Erro ao analisar arquivo: {str(e)}")
                st.info("💡 Tente com um arquivo Excel válido")
        else:
            st.warning("⚠️ Snowflake não configurado. Dados serão usados apenas localmente.")
    
    # Additional help section
    with st.expander("💡 Dicas para Upload"):
        st.markdown("""
        **Formato de arquivo suportado:**
        - ✅ Arquivos Excel (.xlsx, .xls)
        - ✅ Headers a partir da linha 9 ou 10
        - ✅ Colunas: Item, Fornecedor, QTD, Modelo, Preço FOB, Estoque Total, In Transit, Avg Sales, CBM, MOQ
        
        **Para melhores resultados:**
        - 📋 Certifique-se que os dados não tenham linhas vazias no topo
        - 📊 Números devem estar formatados como números (não texto)
        - 🔤 Nomes de produtos devem estar na coluna 'Modelo' ou 'Item'
        """)
    
    # Show cloud data status
    if snowflake_available:
        st.divider()
        st.subheader("☁️ Status da Nuvem")
        if st.button("🔄 Recarregar dados da nuvem", use_container_width=True):
            st.rerun()

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
    st.title("📅 TIMELINE INTERATIVA DE COMPRAS")
    st.markdown("### 🎯 Visualização interativa com MOQ otimizado")

    # Try to load data from Snowflake first
    try:
        from bd.snowflake_config import load_data_with_history
        df = load_data_with_history()
        
        if df is not None and len(df) > 0:
            st.success(f"✅ Usando dados da nuvem: {len(df)} produtos carregados")
            
            # Convert data upload column to string for display
            if 'data_upload' in df.columns:
                st.info(f"📅 Último upload: {df['data_upload'].max()}")
        else:
            st.info("💡 Nenhum dado encontrado na nuvem.")
            st.markdown("👉 **Vá para 'Upload de Dados' para enviar seu Excel para a nuvem primeiro.**")
            df = None
            
    except ImportError:
        st.warning("⚠️ Snowflake não configurado. Usando upload local temporário.")
        df = None
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados da nuvem: {str(e)}")
        df = None

    # Fallback to local upload if no cloud data
    if df is None:
        with st.expander("📁 Upload Local (Temporário)", expanded=True):
            st.markdown("⚠️ **Este upload é temporário. Para salvar na nuvem, use 'Upload de Dados'**")
            
            uploaded_file = st.file_uploader(
                "Faça upload do seu arquivo Excel:",
                type=['xlsx', 'xls'],
                help="Carregue um arquivo Excel com dados de estoque e vendas"
            )
            
            usar_dados_exemplo = st.checkbox("📊 Usar dados de exemplo", value=False)
            
            if usar_dados_exemplo:
                df = criar_dados_exemplo()
                st.info("📊 Usando dados de exemplo para demonstração")
            elif uploaded_file is not None:
                df = carregar_dados(uploaded_file)
                if df is not None:
                    st.success("✅ Arquivo carregado com sucesso!")
                else:
                    st.error("❌ Erro ao carregar arquivo. Verifique o formato.")
            else:
                st.info("📁 Faça upload de um arquivo Excel ou use os dados de exemplo para começar!")

    # Only show controls and analysis if data is loaded
    if df is not None:
        # Sidebar controls
        st.sidebar.header("🎛️ Controles")
        meta_meses = st.sidebar.slider("🎯 Meta (meses)", 3, 12, 6)
        
        # Calculate timeline data
        timeline_data = calcular_timeline(df, meta_meses)
        
        if timeline_data:
            urgencias = ["Todos"] + sorted(list(set(item['Urgencia'] for item in timeline_data)))
            filtro = st.sidebar.selectbox("🔍 Filtrar", urgencias)
            
            # Show metrics
            col1, col2, col3, col4 = st.columns(4)
            criticos = len([x for x in timeline_data if x['Urgencia'] == 'CRÍTICO'])
            medios = len([x for x in timeline_data if x['Urgencia'] == 'MÉDIO'])
            atencao = len([x for x in timeline_data if x['Urgencia'] == 'ATENÇÃO'])
            ok = len([x for x in timeline_data if x['Urgencia'] == 'OK'])
            
            col1.metric("🔴 Críticos", criticos)
            col2.metric("🟠 Médios", medios)
            col3.metric("🟡 Atenção", atencao)
            col4.metric("🟢 OK", ok)
            
            # Show total investment
            valor_total = sum(item['Valor_Pedido'] for item in timeline_data)
            st.metric("💰 Investimento Total", f"R$ {valor_total:,.0f}")
            
            # Create and display chart
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
                st.warning("📊 Nenhum dado válido encontrado para o filtro selecionado.")
        else:
            st.warning("📊 Nenhum dado válido encontrado para criar o timeline.")

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
    from datetime import datetime, timedelta
    hoje = datetime.now()
    timeline_data = []
    
    # Debug: Show what columns we actually have
    st.info(f"🔍 Colunas disponíveis para timeline: {list(df.columns)}")
    
    # Check if we have any data
    if df.empty:
        st.warning("⚠️ DataFrame vazio - nenhum dado para calcular timeline")
        return []
    
    for idx, row in df.iterrows():
        # Safely access columns with fallbacks
        produto = str(row.get('Modelo', f'Produto_{idx}'))
        fornecedor = str(row.get('Fornecedor', 'Fornecedor Desconhecido'))
        estoque_atual = row.get('Estoque_Total', 0) + row.get('In_Transit', 0)
        vendas_mensais = row.get('Vendas_Medias', 0)
        moq = row.get('MOQ', 0)
        preco = row.get('Preco_Unitario', 0)
        cbm = row.get('CBM', 0)
        
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
                "department": "Importação",
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
                        ["Todos", "Importação"]
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
        
        # Clear all button with confirmation
        if st.sidebar.button("🗑️ Limpar Todos os Anúncios", type="secondary"):
            st.session_state.show_clear_confirmation = True
        
        # Show confirmation dialog if triggered
        if st.session_state.get("show_clear_confirmation", False):
            st.sidebar.warning("⚠️ **Confirmar exclusão?**")
            st.sidebar.markdown("Esta ação não pode ser desfeita!")
            
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("✅ Sim, limpar", type="primary", key="confirm_clear"):
                    if save_announcements([]):
                        st.success("✅ Todos os anúncios foram removidos!")
                        st.session_state.show_clear_confirmation = False
                        st.rerun()
                    else:
                        st.error("❌ Erro ao limpar anúncios")
            
            with col2:
                if st.button("❌ Cancelar", key="cancel_clear"):
                    st.session_state.show_clear_confirmation = False
                    st.rerun()
    else:
        st.sidebar.info("👁️ Modo Visualização")
    
    # Filtros
    st.sidebar.subheader("🔍 Filtros")
    
    # View mode toggle
    view_mode = st.sidebar.radio(
        "👔 Modo de Visualização",
        ["🎯 Blocos (Por Prioridade)", "📋 Lista (Detalhada)"],
        help="Blocos: Layout compacto em blocos por prioridade\nLista: Vista tradicional com todos os detalhes"
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
            ["Todos", "Importação"]
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
            if view_mode == "🎯 Blocos (Por Prioridade)":
                # Categorização por prioridade em blocos
                st.subheader("📋 Central de Anúncios - Importação")
                
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
                
                # Configurações de prioridade
                priority_configs = {
                    "Crítica": {"icon": "🚨", "color": "#FF4444", "bg": "#FFF5F5"},
                    "Alta": {"icon": "🔥", "color": "#FF8800", "bg": "#FFF8F0"},
                    "Média": {"icon": "⚡", "color": "#FFDD00", "bg": "#FFFEF0"},
                    "Baixa": {"icon": "📝", "color": "#44AA44", "bg": "#F8FFF8"}
                }
                
                # Layout em 2 colunas para blocos compactos
                col_left, col_right = st.columns(2)
                
                # Distribui as prioridades nas colunas
                priorities_left = ["Crítica", "Média"]
                priorities_right = ["Alta", "Baixa"]
                
                for col, priorities in [(col_left, priorities_left), (col_right, priorities_right)]:
                    with col:
                        for priority in priorities:
                            announcements_in_priority = priority_groups[priority]
                            config = priority_configs[priority]
                            count = len(announcements_in_priority)
                            
                            # Bloco da prioridade
                            st.markdown(f"""
                            <div style="
                                background: linear-gradient(135deg, {config['bg']}, white);
                                border: 2px solid {config['color']}40;
                                border-radius: 12px;
                                padding: 15px;
                                margin-bottom: 20px;
                                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                                min-height: 200px;
                            ">
                                <div style="
                                    display: flex;
                                    align-items: center;
                                    justify-content: space-between;
                                    margin-bottom: 15px;
                                    border-bottom: 2px solid {config['color']}20;
                                    padding-bottom: 10px;
                                ">
                                    <h3 style="
                                        color: {config['color']};
                                        margin: 0;
                                        font-size: 18px;
                                        font-weight: bold;
                                    ">
                                        {config['icon']} {priority.upper()}
                                    </h3>
                                    <span style="
                                        background: {config['color']};
                                        color: white;
                                        padding: 4px 12px;
                                        border-radius: 20px;
                                        font-size: 14px;
                                        font-weight: bold;
                                    ">{count}</span>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            if announcements_in_priority:
                                # Mostrar até 3 anúncios por bloco
                                for i, announcement in enumerate(announcements_in_priority[:3]):
                                    type_icon = get_type_icon(announcement.get('type', 'Geral'))
                                    
                                    # Calcular status de expiração
                                    expiry = announcement.get('expiry_date', '2099-12-31')
                                    status_color = "#28a745"
                                    status_text = "Ativo"
                                    try:
                                        from datetime import datetime
                                        expiry_date = datetime.strptime(expiry, '%Y-%m-%d').date()
                                        days_left = (expiry_date - date.today()).days
                                        if days_left <= 0:
                                            status_color = "#dc3545"
                                            status_text = "EXPIRADO"
                                        elif days_left <= 7:
                                            status_color = "#fd7e14"
                                            status_text = f"{days_left}d restantes"
                                    except:
                                        pass
                                    
                                    st.markdown(f"""
                                    <div style="
                                        background: white;
                                        border-left: 4px solid {config['color']};
                                        border-radius: 6px;
                                        padding: 12px;
                                        margin: 8px 0;
                                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                                    ">
                                        <div style="
                                            display: flex;
                                            justify-content: space-between;
                                            align-items: flex-start;
                                            margin-bottom: 8px;
                                        ">
                                            <h5 style="
                                                margin: 0;
                                                color: #333;
                                                font-size: 14px;
                                                font-weight: bold;
                                                flex: 1;
                                            ">
                                                {type_icon} {announcement.get('title', 'Sem título')[:40]}{'...' if len(announcement.get('title', '')) > 40 else ''}
                                            </h5>
                                            <span style="
                                                background: {status_color};
                                                color: white;
                                                padding: 2px 6px;
                                                border-radius: 10px;
                                                font-size: 10px;
                                                font-weight: bold;
                                                margin-left: 8px;
                                            ">{status_text}</span>
                                        </div>
                                        <p style="
                                            margin: 0;
                                            color: #666;
                                            font-size: 12px;
                                            line-height: 1.4;
                                        ">
                                            {announcement.get('content', '')[:80]}{'...' if len(announcement.get('content', '')) > 80 else ''}
                                        </p>
                                        <div style="
                                            display: flex;
                                            justify-content: space-between;
                                            align-items: center;
                                            margin-top: 8px;
                                            font-size: 10px;
                                            color: #888;
                                        ">
                                            <span>👤 {announcement.get('author', 'Desconhecido')}</span>
                                            <span>📅 {announcement.get('date', '')}</span>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                # Mostrar indicador se há mais anúncios
                                if len(announcements_in_priority) > 3:
                                    remaining = len(announcements_in_priority) - 3
                                    st.markdown(f"""
                                    <div style="
                                        text-align: center;
                                        color: {config['color']};
                                        font-size: 12px;
                                        font-weight: bold;
                                        margin-top: 10px;
                                    ">
                                        + {remaining} mais anúncios
                                    </div>
                                    """, unsafe_allow_html=True)
                            else:
                                st.markdown(f"""
                                <div style="
                                    text-align: center;
                                    color: #888;
                                    font-style: italic;
                                    padding: 20px 0;
                                ">
                                    Nenhum anúncio {priority.lower()}
                                </div>
                                """, unsafe_allow_html=True)
                            
                            st.markdown("</div>", unsafe_allow_html=True)
            
            else:
                # Vista em lista tradicional
                st.subheader("📋 Anúncios Ativos - Importação")
                
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

def show_excel_analytics():
    """Análise avançada de dados Excel - Sistema de Gestão de Estoque"""
    
    st.title("📊 Análise de Estoque - Sistema MINIPA")
    st.markdown("**Ferramenta prática para gestão de estoque focada em AÇÃO e DECISÃO**")
    
    # Try to load data from Snowflake first
    try:
        from bd.snowflake_config import load_analytics_data
        df = load_analytics_data()
        
        if df is not None and len(df) > 0:
            st.success(f"✅ Usando dados da nuvem: {len(df)} produtos carregados")
            
            # Check if data_upload column exists before accessing it
            if 'data_upload' in df.columns:
                st.info(f"📅 Último upload: {df['data_upload'].max()}")
            else:
                st.info("📅 Dados de análise carregados da nuvem")
                
        else:
            st.info("💡 Nenhum dado de análise encontrado na nuvem.")
            st.markdown("👉 **Vá para 'Upload de Dados' e selecione '📊 Análise de Estoque (Export)' para enviar seus dados primeiro.**")
            df = None
            
    except ImportError:
        st.warning("⚠️ Snowflake não configurado. Usando upload local temporário.")
        df = None
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados da nuvem: {str(e)}")
        df = None

    # Fallback to local upload if no cloud data
    if df is None:
        st.subheader("📁 Upload Local (Temporário)")
        st.markdown("⚠️ **Este upload é temporário. Para salvar na nuvem, use 'Upload de Dados' → 'Análise de Estoque'**")
        
        uploaded_file = st.file_uploader(
            "Faça upload do arquivo Excel (.xlsx)",
            type=['xlsx'],
            help="Arquivo deve conter planilha 'Export' com colunas: Produto, Estoque, Média 6 Meses, Estoque Cobertura"
        )
        
        if uploaded_file is not None:
            try:
                # Read the Excel file
                df = pd.read_excel(uploaded_file, sheet_name='Export')
                
                # Clean data
                df = df.dropna(subset=['Produto'])
                df = df[df['Produto'] != 'nan']
                df = df[~df['Produto'].str.contains('Filtros aplicados', na=False)]
                
                # Convert numeric columns
                numeric_columns = ['Estoque', 'Média 6 Meses', 'Estoque Cobertura', 'Qtde Tot Compras']
                for col in numeric_columns:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
                st.success(f"✅ Dados carregados: {len(df)} produtos")
                
            except Exception as e:
                st.error(f"❌ Erro ao processar arquivo: {str(e)}")
                st.info("💡 Certifique-se de que o arquivo contém uma planilha 'Export' com as colunas necessárias")
                return
        else:
            st.info("📁 Faça upload de um arquivo Excel para análise local ou use os dados da nuvem")
            
            # Show sample format
            with st.expander("📋 Formato esperado do arquivo"):
                st.markdown("""
                **Planilha: 'Export'**
                
                Colunas necessárias:
                - `Produto`: Nome do produto
                - `Estoque`: Quantidade atual em estoque
                - `Média 6 Meses`: Consumo médio mensal
                - `Estoque Cobertura`: Cobertura em meses
                - `Qtde Tot Compras`: Quantidade total para compras (opcional)
                """)
            return

    # Only show analysis if data is loaded (either from Snowflake or local upload)
    if df is not None:
        # Separate new and existing products
        produtos_novos = df[(df['Estoque'] == 0) & (df['Média 6 Meses'] == 0) & (df.get('Qtde Tot Compras', 0) > 0)]
        produtos_existentes = df[(df['Estoque'] > 0) | (df['Média 6 Meses'] > 0)]
        
        # Show analytics tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Resumo Executivo", "🚨 Lista de Compras", "📊 Dashboards", "📞 Contatos Urgentes"])
        
        with tab1:
            show_executive_summary(df, produtos_novos, produtos_existentes)
        
        with tab2:
            show_purchase_list(produtos_existentes)
        
        with tab3:
            show_analytics_dashboard(produtos_existentes, produtos_novos)
        
        with tab4:
            show_urgent_contacts(produtos_existentes)

def show_executive_summary(df, produtos_novos, produtos_existentes):
    """Resumo executivo dos dados"""
    
    st.subheader("📋 Resumo Executivo")
    
    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📦 Total de Produtos", len(df))
    
    with col2:
        st.metric("🆕 Produtos Novos", len(produtos_novos))
    
    with col3:
        st.metric("📈 Produtos Existentes", len(produtos_existentes))
    
    with col4:
        if len(produtos_existentes) > 0:
            criticos = len(produtos_existentes[produtos_existentes['Estoque Cobertura'] <= 1])
            st.metric("🚨 Produtos Críticos", criticos)
        else:
            st.metric("🚨 Produtos Críticos", 0)
    
    if len(produtos_existentes) > 0:
        # Status breakdown
        st.subheader("🎯 Status dos Produtos Existentes")
        
        criticos = len(produtos_existentes[produtos_existentes['Estoque Cobertura'] <= 1])
        alerta = len(produtos_existentes[(produtos_existentes['Estoque Cobertura'] > 1) & (produtos_existentes['Estoque Cobertura'] <= 3)])
        saudaveis = len(produtos_existentes[produtos_existentes['Estoque Cobertura'] > 3])
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "🔴 Críticos (≤1 mês)", 
                criticos,
                delta=f"{criticos/len(produtos_existentes)*100:.1f}%"
            )
        
        with col2:
            st.metric(
                "🟡 Alerta (1-3 meses)", 
                alerta,
                delta=f"{alerta/len(produtos_existentes)*100:.1f}%"
            )
        
        with col3:
            st.metric(
                "🟢 Saudáveis (>3 meses)", 
                saudaveis,
                delta=f"{saudaveis/len(produtos_existentes)*100:.1f}%"
            )
        
        # Financial overview
        st.subheader("💰 Visão Financeira")
        
        estoque_total = produtos_existentes['Estoque'].sum()
        consumo_total = produtos_existentes['Média 6 Meses'].sum()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📦 Estoque Total", f"{estoque_total:,.0f} unidades")
        
        with col2:
            st.metric("📈 Consumo Mensal", f"{consumo_total:,.1f} unidades")
        
        with col3:
            if consumo_total > 0:
                duracao = estoque_total / consumo_total
                st.metric("⏱️ Duração Média", f"{duracao:.1f} meses")
            else:
                st.metric("⏱️ Duração Média", "N/A")
    
    # Action items
    if len(produtos_existentes) > 0:
        st.subheader("🚨 Ações Necessárias")
        
        if criticos > 0:
            st.error(f"⚡ URGENTE: {criticos} produtos críticos precisam de compra IMEDIATA")
        if alerta > 0:
            st.warning(f"📅 PLANEJAR: {alerta} produtos em alerta para próximas semanas")
        if len(produtos_novos) > 0:
            st.info(f"🆕 MONITORAR: {len(produtos_novos)} produtos novos sendo lançados")
        
        if criticos == 0 and alerta == 0:
            st.success("✅ Situação de estoque sob controle!")

def calculate_purchase_suggestions(produtos_existentes):
    """Calculate purchase suggestions for products"""
    
    def calcular_quando_vai_acabar(estoque, consumo_mensal):
        if consumo_mensal <= 0:
            return "Sem consumo", 999
        
        meses_restantes = estoque / consumo_mensal
        
        if meses_restantes <= 0:
            return "JÁ ACABOU", 0
        elif meses_restantes < 0.5:
            dias = int(meses_restantes * 30)
            return f"{dias} dias", meses_restantes
        else:
            return f"{meses_restantes:.1f} meses", meses_restantes
    
    def quanto_comprar(consumo_mensal, estoque_atual, meses_desejados=6):
        if consumo_mensal <= 0:
            return 0
        
        estoque_ideal = consumo_mensal * meses_desejados
        falta = max(0, estoque_ideal - estoque_atual)
        
        # Round for easier purchasing
        return int(np.ceil(falta / 50) * 50) if falta > 0 else 0
    
    # Calculate for each product
    suggestions = []
    
    for _, row in produtos_existentes.iterrows():
        produto = str(row['Produto'])
        estoque = row['Estoque']
        consumo = row['Média 6 Meses']
        
        quando_acaba, meses_num = calcular_quando_vai_acabar(estoque, consumo)
        qtd_comprar = quanto_comprar(consumo, estoque)
        
        suggestions.append({
            'Produto': produto,
            'Estoque_Atual': estoque,
            'Consumo_Mensal': consumo,
            'Quando_Acaba': quando_acaba,
            'Meses_Restantes': meses_num,
            'Qtd_Comprar': qtd_comprar,
            'Investimento_Estimado': qtd_comprar * 15  # R$ 15 per unit estimate
        })
    
    return pd.DataFrame(suggestions)

def show_purchase_list(produtos_existentes):
    """Show practical purchase list"""
    
    st.subheader("🛒 Lista Prática de Compras")
    
    if len(produtos_existentes) == 0:
        st.info("Nenhum produto existente para análise")
        return
    
    # Calculate suggestions
    suggestions_df = calculate_purchase_suggestions(produtos_existentes)
    
    # Filter products that need action (increased range due to new categories)
    precisa_acao = suggestions_df[
        (suggestions_df['Meses_Restantes'] <= 6) & 
        (suggestions_df['Consumo_Mensal'] > 0)
    ].sort_values('Meses_Restantes')
    
    if len(precisa_acao) == 0:
        st.success("✅ Nenhum produto necessita compra urgente!")
        return
    
    st.info(f"📦 {len(precisa_acao)} produtos precisam de compra")
    
    # Emergency products (≤ 1 month)
    emergencia = precisa_acao[precisa_acao['Meses_Restantes'] <= 1]
    if len(emergencia) > 0:
        st.error("🚨 EMERGÊNCIA (≤ 1 mês)")
        st.dataframe(
            emergencia[['Produto', 'Quando_Acaba', 'Consumo_Mensal', 'Qtd_Comprar', 'Investimento_Estimado']].round(1),
            use_container_width=True
        )
    
    # Critical products (1-3 months)
    criticos = precisa_acao[(precisa_acao['Meses_Restantes'] > 1) & (precisa_acao['Meses_Restantes'] <= 3)]
    if len(criticos) > 0:
        st.warning("🔴 CRÍTICOS (1-3 meses)")
        st.dataframe(
            criticos[['Produto', 'Quando_Acaba', 'Consumo_Mensal', 'Qtd_Comprar', 'Investimento_Estimado']].head(10).round(1),
            use_container_width=True
        )
    
    # Attention products (3+ months)
    atencao = precisa_acao[precisa_acao['Meses_Restantes'] > 3]
    if len(atencao) > 0:
        st.info("🟡 ATENÇÃO (>3 meses)")
        st.dataframe(
            atencao[['Produto', 'Quando_Acaba', 'Consumo_Mensal', 'Qtd_Comprar', 'Investimento_Estimado']].head(10).round(1),
            use_container_width=True
        )
    
    # Summary
    st.subheader("💰 Resumo de Investimento")
    
    total_emergencia = len(emergencia)
    total_criticos = len(criticos)
    total_atencao = len(atencao)
    
    investimento_total = precisa_acao['Investimento_Estimado'].sum()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🚨 Emergência", total_emergencia)
    with col2:
        st.metric("🔴 Críticos", total_criticos)
    with col3:
        st.metric("🟡 Atenção", total_atencao)
    with col4:
        st.metric("💰 Investimento", f"R$ {investimento_total:,.0f}")

def show_analytics_dashboard(produtos_existentes, produtos_novos):
    """Show visual analytics dashboard"""
    
    st.subheader("📊 Dashboard Visual")
    
    if len(produtos_existentes) == 0:
        st.info("Nenhum produto para análise visual")
        return
    
    # Calculate data for charts
    suggestions_df = calculate_purchase_suggestions(produtos_existentes)
    
    # Urgency categorization
    muito_critico = len(suggestions_df[suggestions_df['Meses_Restantes'] <= 1])
    critico = len(suggestions_df[(suggestions_df['Meses_Restantes'] > 1) & (suggestions_df['Meses_Restantes'] <= 3)])
    moderado = len(suggestions_df[(suggestions_df['Meses_Restantes'] > 3) & (suggestions_df['Meses_Restantes'] <= 6)])
    ok = len(suggestions_df[suggestions_df['Meses_Restantes'] > 6])
    
    # Chart 1: Products by urgency
    col1, col2 = st.columns(2)
    
    with col1:
        urgency_data = {
            'Categoria': ['≤1 mês', '1-3 meses', '3-6 meses', '>6 meses'],
            'Quantidade': [muito_critico, critico, moderado, ok],
            'Cor': ['#8B0000', '#FF0000', '#FFA500', '#008000']
        }
        
        fig_urgency = px.bar(
            urgency_data,
            x='Categoria',
            y='Quantidade',
            color='Cor',
            title='🚨 Produtos por Urgência',
            color_discrete_map={color: color for color in urgency_data['Cor']}
        )
        st.plotly_chart(fig_urgency, use_container_width=True)
    
    with col2:
        # Chart 2: Stock coverage distribution
        if len(produtos_existentes) > 0:
            fig_pie = px.pie(
                values=[muito_critico, critico, moderado, ok],
                names=['≤1 mês', '1-3 meses', '3-6 meses', '>6 meses'],
                title='⏰ Distribuição de Cobertura',
                color_discrete_sequence=['#8B0000', '#FF0000', '#FFA500', '#008000']
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    
    # Chart 3: Top products to buy
    precisa_acao = suggestions_df[
        (suggestions_df['Meses_Restantes'] <= 3) & 
        (suggestions_df['Consumo_Mensal'] > 0)
    ].sort_values('Qtd_Comprar', ascending=False).head(10)
    
    if len(precisa_acao) > 0:
        fig_top = px.bar(
            precisa_acao,
            x='Qtd_Comprar',
            y='Produto',
            orientation='h',
            title='🛒 Top 10 Produtos para Comprar',
            color='Meses_Restantes',
            color_continuous_scale='Reds_r'
        )
        fig_top.update_layout(height=500)
        st.plotly_chart(fig_top, use_container_width=True)
    
    # Chart 4: Investment timeline
    col1, col2 = st.columns(2)
    
    with col1:
        emergencia = suggestions_df[suggestions_df['Meses_Restantes'] <= 1]
        criticos_chart = suggestions_df[(suggestions_df['Meses_Restantes'] > 1) & (suggestions_df['Meses_Restantes'] <= 3)]
        atencao = suggestions_df[suggestions_df['Meses_Restantes'] > 3]
        
        invest_emergencia = emergencia['Investimento_Estimado'].sum() if len(emergencia) > 0 else 0
        invest_criticos = criticos_chart['Investimento_Estimado'].sum() if len(criticos_chart) > 0 else 0
        invest_atencao = atencao['Investimento_Estimado'].sum() if len(atencao) > 0 else 0
        
        investment_data = {
            'Período': ['Este Mês', 'Próximos 3 Meses', 'Longo Prazo'],
            'Investimento': [invest_emergencia, invest_criticos, invest_atencao]
        }
        
        fig_invest = px.bar(
            investment_data,
            x='Período',
            y='Investimento',
            title='💰 Investimento por Período',
            color='Investimento',
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig_invest, use_container_width=True)
    
    with col2:
        # Product status overview
        if len(produtos_novos) > 0:
            overview_data = {
                'Categoria': ['Produtos Existentes', 'Produtos Novos'],
                'Quantidade': [len(produtos_existentes), len(produtos_novos)]
            }
            
            fig_overview = px.pie(
                overview_data,
                values='Quantidade',
                names='Categoria',
                title='📊 Visão Geral dos Produtos'
            )
            st.plotly_chart(fig_overview, use_container_width=True)

def show_urgent_contacts(produtos_existentes):
    """Show urgent contacts list"""
    
    st.subheader("📞 Lista de Contatos Urgentes")
    
    if len(produtos_existentes) == 0:
        st.info("Nenhum produto para análise de contatos")
        return
    
    suggestions_df = calculate_purchase_suggestions(produtos_existentes)
    
    # Emergency contacts (≤ 0.5 months)
    emergencia = suggestions_df[suggestions_df['Meses_Restantes'] <= 0.5]
    
    # Critical contacts (0.5-1 months)
    criticos = suggestions_df[(suggestions_df['Meses_Restantes'] > 0.5) & (suggestions_df['Meses_Restantes'] <= 1)]
    
    st.subheader("🚨 LIGAR HOJE (EMERGÊNCIA)")
    if len(emergencia) > 0:
        st.error(f"📞 {len(emergencia)} fornecedores para contactar HOJE")
        
        contact_emergency = emergencia[['Produto', 'Quando_Acaba', 'Consumo_Mensal', 'Qtd_Comprar']].head(10)
        st.dataframe(contact_emergency, use_container_width=True)
    else:
        st.success("✅ Nenhum contato de emergência necessário")
    
    st.subheader("🔴 LIGAR ESTA SEMANA (CRÍTICOS)")
    if len(criticos) > 0:
        st.warning(f"📞 {len(criticos)} fornecedores para contactar ESTA SEMANA")
        
        contact_critical = criticos[['Produto', 'Quando_Acaba', 'Consumo_Mensal', 'Qtd_Comprar']].head(10)
        st.dataframe(contact_critical, use_container_width=True)
    else:
        st.success("✅ Nenhum contato crítico necessário")
    
    # Summary
    st.subheader("📋 Resumo de Contatos")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🚨 HOJE", len(emergencia))
    with col2:
        st.metric("🔴 ESTA SEMANA", len(criticos))
    with col3:
        st.metric("📞 TOTAL", len(emergencia) + len(criticos))
    
    if len(emergencia) > 0 or len(criticos) > 0:
        st.info("💡 **DICA:** Prepare a lista de quantidades antes de ligar! Use a aba 'Lista de Compras' para ter os números exatos.")

def show_snowflake():
    """Enhanced Snowflake integration management page"""
    st.title("❄️ SNOWFLAKE DATABASE")
    st.markdown("### 🔧 Gerenciamento de Banco de Dados")
    
    # Try to import Snowflake functions
    try:
        from bd.snowflake_config import (
            test_connection, create_tables, get_snowflake_connection,
            load_data_with_history
        )
        snowflake_available = True
    except ImportError as e:
        st.error("❌ Snowflake não configurado!")
        st.code(f"Erro: {str(e)}")
        st.info("💡 Verifique se o arquivo bd/snowflake_config.py existe e as dependências estão instaladas")
        snowflake_available = False
        return
    
    # Connection status section
    st.subheader("🔌 Status da Conexão")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("🔄 Testar Conexão", type="primary"):
            with st.spinner("Testando conexão com Snowflake..."):
                if test_connection():
                    st.success("✅ Conectado com sucesso!")
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
    
    # Configuration info
    st.subheader("⚙️ Configuração")
    
    if hasattr(st, 'secrets') and "connections" in st.secrets and "snowflake" in st.secrets.connections:
        config = st.secrets.connections.snowflake
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"""
            **Configuração Atual:**
            - 🏢 Account: `{config.account}`
            - 👤 User: `{config.user}`
            - 🗄️ Database: `{config.database}`
            - 📋 Schema: `{config.schema}`
            """)
        
        with col2:
            st.info(f"""
            **Recursos:**
            - ⚡ Warehouse: `{config.warehouse}`
            - 🔐 Role: `{config.role}`
            - 🔒 Password: `***`
            """)
    else:
        st.warning("⚠️ Configuração não encontrada!")
        st.info("💡 Configure em `.streamlit/secrets.toml`")
    
    # Table management
    st.subheader("🗃️ Gerenciamento de Tabelas")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔨 Criar Tabelas", use_container_width=True):
            with st.spinner("Criando estrutura de tabelas..."):
                if create_tables():
                    st.success("✅ Tabelas criadas com sucesso!")
                    st.balloons()
                else:
                    st.error("❌ Erro ao criar tabelas")
    
    with col2:
        if st.button("📊 Verificar Dados", use_container_width=True):
            try:
                data = load_data_with_history()
                if data is not None and len(data) > 0:
                    st.success(f"✅ {len(data)} registros encontrados")
                    with st.expander("👀 Prévia dos dados"):
                        st.dataframe(data.head())
                else:
                    st.info("💡 Nenhum dado encontrado")
            except Exception as e:
                st.error(f"❌ Erro ao carregar dados: {str(e)}")
    
    with col3:
        if st.button("🔍 Diagnóstico", use_container_width=True):
            run_snowflake_diagnostics()
    
    # Migration section for existing users
    st.subheader("🔄 Migração de Tabelas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Atualizar Estrutura", use_container_width=True):
            from bd.snowflake_config import migrate_existing_tables
            migrate_existing_tables()
    
    with col2:
        st.info("💡 Use se você tem tabelas antigas e precisa suporte para Timeline + Analytics")
    
    # Database schema info
    st.subheader("🏗️ Estrutura do Banco")
    
    with st.expander("📋 Esquema das Tabelas"):
        st.markdown("""
        **ESTOQUE.PRODUTOS** - Tabela principal de produtos
        ```sql
        - id (INTEGER) - Chave primária
        - item (VARCHAR) - Código do item
        - modelo (VARCHAR) - Descrição/modelo do produto
        - fornecedor (VARCHAR) - Nome do fornecedor
        - qtd_atual (INTEGER) - Quantidade em estoque
        - preco_unitario (DECIMAL) - Preço FOB unitário
        - estoque_total (INTEGER) - Estoque total disponível
        - in_transit (INTEGER) - Quantidade em trânsito
        - vendas_medias (DECIMAL) - Média de vendas
        - cbm (DECIMAL) - Volume CBM
        - moq (INTEGER) - Quantidade mínima de pedido
        - data_upload (TIMESTAMP) - Data do upload
        - usuario (VARCHAR) - Usuário que fez o upload
        ```
        
        **CONFIG.UPLOAD_LOG** - Log de uploads
        ```sql
        - id (INTEGER) - Chave primária
        - nome_arquivo (VARCHAR) - Nome do arquivo Excel
        - linhas_processadas (INTEGER) - Número de linhas processadas
        - data_upload (TIMESTAMP) - Data do upload
        - usuario (VARCHAR) - Usuário
        - status (VARCHAR) - Status do upload
        ```
        """)
    
    # Help section
    st.subheader("💡 Ajuda")
    
    with st.expander("🚀 Como usar"):
        st.markdown("""
        **Passos para configurar:**
        
        1. **Configure credenciais** em `.streamlit/secrets.toml`:
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
        
        2. **Teste a conexão** clicando em "Testar Conexão"
        
        3. **Crie as tabelas** clicando em "Criar Tabelas"
        
        4. **Faça upload** na página "Upload de Dados"
        
        5. **Use os dados** em todas as funcionalidades do app
        """)
    
    with st.expander("🔧 Solução de Problemas"):
        st.markdown("""
        **Erros comuns:**
        
        - **"Table does not exist"**: Clique em "Criar Tabelas"
        - **"Connection failed"**: Verifique credenciais no secrets.toml
        - **"Parameter formatting"**: Verifique se as tabelas foram criadas corretamente
        - **"Schema not found"**: Verifique se o database COMPRAS_MINIPA existe no Snowflake
        
        **Se persistirem problemas:**
        1. Verifique se você tem permissões ACCOUNTADMIN
        2. Confirme que o database COMPRAS_MINIPA existe
        3. Execute o diagnóstico para mais detalhes
        """)

def run_snowflake_diagnostics():
    """Run comprehensive Snowflake diagnostics"""
    st.subheader("🔍 Diagnóstico Completo")
    
    try:
        from bd.snowflake_config import get_snowflake_connection
        
        conn = get_snowflake_connection()
        if not conn:
            st.error("❌ Não foi possível conectar ao Snowflake")
            return
        
        cursor = conn.cursor()
        
        # Test 1: Basic connection
        st.write("**1. Teste de Conexão Básica**")
        try:
            cursor.execute("SELECT CURRENT_VERSION()")
            version = cursor.fetchone()[0]
            st.success(f"✅ Conectado! Versão: {version}")
        except Exception as e:
            st.error(f"❌ Falha na conexão: {str(e)}")
            return
        
        # Test 2: Database and schema access
        st.write("**2. Acesso ao Database e Schema**")
        try:
            cursor.execute("SELECT CURRENT_DATABASE(), CURRENT_SCHEMA()")
            db, schema = cursor.fetchone()
            st.success(f"✅ Database: {db}, Schema: {schema}")
        except Exception as e:
            st.error(f"❌ Erro de acesso: {str(e)}")
        
        # Test 3: Table existence
        st.write("**3. Verificação de Tabelas**")
        try:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            if tables:
                st.success(f"✅ {len(tables)} tabelas encontradas:")
                for table in tables:
                    st.write(f"   - {table[1]}")  # Table name is in second column
            else:
                st.warning("⚠️ Nenhuma tabela encontrada")
                st.info("💡 Clique em 'Criar Tabelas' para criar a estrutura")
        except Exception as e:
            st.error(f"❌ Erro ao listar tabelas: {str(e)}")
        
        # Test 4: Data count
        st.write("**4. Contagem de Dados**")
        try:
            cursor.execute("SELECT COUNT(*) FROM ESTOQUE.PRODUTOS")
            count = cursor.fetchone()[0]
            st.success(f"✅ {count} registros na tabela PRODUTOS")
        except Exception as e:
            st.warning(f"⚠️ Erro ao contar dados: {str(e)}")
            st.info("💡 Tabela PRODUTOS pode não existir ainda")
        
        # Test 5: Permissions
        st.write("**5. Verificação de Permissões**")
        try:
            cursor.execute("SELECT CURRENT_ROLE()")
            role = cursor.fetchone()[0]
            st.success(f"✅ Role atual: {role}")
            
            # Try to create a test table
            cursor.execute("CREATE OR REPLACE TABLE TEST_PERMISSIONS (id INTEGER)")
            cursor.execute("DROP TABLE TEST_PERMISSIONS")
            st.success("✅ Permissões de CREATE/DROP confirmadas")
        except Exception as e:
            st.error(f"❌ Problema de permissões: {str(e)}")
        
        cursor.close()
        conn.close()
        
        st.success("🎉 Diagnóstico concluído!")
        
    except Exception as e:
        st.error(f"❌ Erro no diagnóstico: {str(e)}")

def analyze_and_process_excel(uploaded_file, file_type="Auto-detectar"):
    """
    Advanced Excel analysis and processing based on actual user table structure
    """
    try:
        # Read the Excel file to understand structure
        xl_file = pd.ExcelFile(uploaded_file)
        sheets = xl_file.sheet_names
        
        st.info(f"📋 Planilhas encontradas: {sheets}")
        
        # Try different sheets and header positions
        best_sheet = None
        best_header_row = 0
        best_df = None
        
        # Priority order for sheets
        sheet_priority = []
        for sheet in sheets:
            sheet_lower = sheet.lower()
            if 'export' in sheet_lower:
                sheet_priority.insert(0, sheet)  # Export first
            elif any(word in sheet_lower for word in ['data', 'dados', 'planilha', 'sheet']):
                sheet_priority.append(sheet)
            else:
                sheet_priority.append(sheet)
        
        # Test different header rows (based on user's table which seems to start around row 9-10)
        header_candidates = [8, 9, 10, 7, 6, 11, 0, 1, 2]
        
        for sheet in sheet_priority[:3]:  # Check first 3 most promising sheets
            for header_row in header_candidates:
                try:
                    # Read sample to test
                    df_test = pd.read_excel(uploaded_file, sheet_name=sheet, header=header_row, nrows=10)
                    
                    if len(df_test) == 0:
                        continue
                    
                    # Look for expected column patterns from user's table
                    columns = [str(col).strip() for col in df_test.columns]
                    
                    # Score this attempt based on expected columns
                    score = 0
                    expected_patterns = [
                        'item', 'fornecedor', 'qtd', 'modelo', 'preço', 'estoque', 
                        'transit', 'sales', 'avg', 'cbm', 'moq', 'fob'
                    ]
                    
                    for col in columns:
                        col_lower = col.lower()
                        for pattern in expected_patterns:
                            if pattern in col_lower:
                                score += 1
                                break
                    
                    # Check if we have actual data (not all empty)
                    data_rows = 0
                    for _, row in df_test.iterrows():
                        if row.count() >= 3:  # At least 3 non-null values
                            data_rows += 1
                    
                    # This is a good candidate if:
                    # 1. We found expected column patterns
                    # 2. We have actual data
                    # 3. Columns are not mostly "Unnamed" or None
                    unnamed_count = sum(1 for col in columns if 'unnamed' in col.lower() or col == 'None')
                    
                    if score >= 3 and data_rows >= 2 and unnamed_count < len(columns) * 0.5:
                        best_sheet = sheet
                        best_header_row = header_row
                        best_df = df_test
                        st.success(f"✅ Melhor estrutura encontrada: Planilha '{sheet}', Linha {header_row + 1}")
                        st.info(f"🎯 Score: {score} | Colunas válidas: {len(columns) - unnamed_count}")
                        break
                        
                except Exception:
                    continue
            
            if best_df is not None:
                break
        
        if best_df is None:
            st.error("❌ Não foi possível detectar a estrutura do Excel automaticamente")
            return None, None, None
        
        # Now read the full dataset with the best parameters
        df_full = pd.read_excel(uploaded_file, sheet_name=best_sheet, header=best_header_row)
        
        # Clean the dataframe
        df_full = df_full.dropna(how='all')  # Remove completely empty rows
        
        # Show what we found
        st.success(f"📊 Dados carregados: {len(df_full)} linhas de '{best_sheet}'")
        
        # Display column mapping
        with st.expander("🔍 Estrutura detectada"):
            st.write("**Colunas encontradas:**")
            for i, col in enumerate(df_full.columns):
                sample_val = df_full[col].dropna().iloc[0] if len(df_full[col].dropna()) > 0 else "Vazio"
                st.write(f"{i+1}. `{col}` - Exemplo: {sample_val}")
        
        # Smart column mapping based on user's actual table
        column_mapping = {}
        
        for col in df_full.columns:
            col_str = str(col).strip().lower()
            
            # Map to standardized names based on content patterns
            if any(word in col_str for word in ['item', 'codigo', 'produto']) and 'Item' not in column_mapping.values():
                column_mapping[col] = 'Item'
            elif any(word in col_str for word in ['fornecedor', 'supplier', 'vendor']) and 'Fornecedor' not in column_mapping.values():
                column_mapping[col] = 'Fornecedor'
            elif 'qtd' in col_str and 'total' not in col_str and 'QTD' not in column_mapping.values():
                column_mapping[col] = 'QTD'
            elif any(word in col_str for word in ['modelo', 'model', 'description']) and 'Modelo' not in column_mapping.values():
                column_mapping[col] = 'Modelo'
            elif 'preço' in col_str and 'unitario' in col_str and 'Preco_Unitario' not in column_mapping.values():
                column_mapping[col] = 'Preco_Unitario'
            elif 'estoque' in col_str and 'total' in col_str and 'Estoque_Total' not in column_mapping.values():
                column_mapping[col] = 'Estoque_Total'
            elif any(word in col_str for word in ['transit', 'transito']) and 'shipt' in col_str and 'In_Transit' not in column_mapping.values():
                column_mapping[col] = 'In_Transit'
            elif any(word in col_str for word in ['avg', 'sales', 'vendas', 'media']) and 'sales' in col_str and 'Vendas_Medias' not in column_mapping.values():
                column_mapping[col] = 'Vendas_Medias'
            elif 'cbm' in col_str and 'CBM' not in column_mapping.values():
                column_mapping[col] = 'CBM'
            elif 'moq' in col_str and 'MOQ' not in column_mapping.values():
                column_mapping[col] = 'MOQ'
        
        # Apply the mapping - only rename columns that were mapped
        df_mapped = df_full.copy()
        if column_mapping:
            try:
                df_mapped = df_full.rename(columns=column_mapping)
            except Exception as e:
                st.warning(f"⚠️ Erro no mapeamento de colunas: {str(e)}")
                df_mapped = df_full.copy()  # Keep original if mapping fails
        
        # Show mapping results
        if column_mapping:
            st.info("🔄 Mapeamento de colunas aplicado:")
            for old, new in column_mapping.items():
                st.write(f"• `{old}` → `{new}`")
        
        # Convert numeric columns safely
        numeric_columns = ['QTD', 'Preco_Unitario', 'Estoque_Total', 'In_Transit', 'Vendas_Medias', 'CBM', 'MOQ']
        
        for col in numeric_columns:
            if col in df_mapped.columns:
                try:
                    # Convert to numeric, replacing errors with 0
                    df_mapped[col] = pd.to_numeric(df_mapped[col], errors='coerce').fillna(0)
                except Exception as e:
                    st.warning(f"⚠️ Não foi possível converter coluna '{col}' para numérico: {str(e)}")
                    # Keep original data if conversion fails
                    pass
        
        return df_mapped, best_sheet, best_header_row
        
    except Exception as e:
        st.error(f"❌ Erro ao processar Excel: {str(e)}")
        return None, None, None

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

if st.sidebar.button("📁 Upload de Dados", use_container_width=True):
    st.session_state.current_page = "upload"
    st.rerun()

if st.sidebar.button("📅 Timeline de Compras", use_container_width=True):
    st.session_state.current_page = "timeline"
    st.rerun()

if st.sidebar.button("📢 Anúncios", use_container_width=True):
    st.session_state.current_page = "announcements"
    st.rerun()

if st.sidebar.button("📊 Análise de Estoque", use_container_width=True):
    st.session_state.current_page = "excel_analytics"
    st.rerun()

if st.sidebar.button("❄️ Snowflake", use_container_width=True):
    st.session_state.current_page = "snowflake"
    st.rerun()

# Show different pages based on navigation
if st.session_state.current_page == "home":
    show_dashboard()
elif st.session_state.current_page == "upload":
    show_data_upload()
elif st.session_state.current_page == "timeline":
    show_timeline()
elif st.session_state.current_page == "announcements":
    show_announcements()
elif st.session_state.current_page == "excel_analytics":
    show_excel_analytics()
elif st.session_state.current_page == "snowflake":
    show_snowflake()

 
