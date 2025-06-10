import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

@st.cache_data
def carregar_dados(uploaded_file=None):
    """Load data from uploaded file"""
    try:
        if uploaded_file is not None:
            df = pd.read_excel(uploaded_file, header=9)
        else:
            return None
        
        df = df.dropna(subset=['Item'])
        df = df[df['Item'] != 'Item']
        
        # Convert numeric columns
        colunas_numericas = ['QTD', 'Preço FOB\nUnitário', 'Estoque\nTotal ', 
                           'In Transit\nShipt', 'Avg Sales\n', 'CBM', 'MOQ']
        
        for col in colunas_numericas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Rename columns
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
    """Create example data for demonstration"""
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
    """Optimize quantity based on MOQ"""
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
    """Calculate timeline data for products"""
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
    """Create interactive timeline charts"""
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
    
    # Chart 1: Timeline
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
    
    # Chart 2: Quantities
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

def show_timeline():
    """Timeline page with company support"""
    st.title("📅 TIMELINE INTERATIVA DE COMPRAS")
    st.markdown("### 🎯 Visualização interativa com MOQ otimizado")
    
    # Company selector
    col1, col2 = st.columns([3, 1])
    with col1:
        empresa_selecionada = st.selectbox(
            "🏢 Empresa:",
            ["MINIPA", "MINIPA INDUSTRIA"],
            key="empresa_selector_timeline"
        )
        empresa_code = "MINIPA" if empresa_selecionada == "MINIPA" else "MINIPA_INDUSTRIA"
    
    with col2:
        if st.button("🔄 Forçar Atualização", use_container_width=True):
            try:
                from bd.snowflake_config import load_data_with_history
                load_data_with_history.clear()
                st.success("✅ Cache limpo!")
                st.rerun()
            except ImportError:
                st.warning("⚠️ Snowflake não configurado")

    # Try to load data from Snowflake
    try:
        from bd.snowflake_config import load_data_with_history, get_upload_versions
        
        # Get available versions
        versions = get_upload_versions(empresa_code, "TIMELINE", limit=20)
        
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
                key="version_selector_timeline"
            )
            
            selected_version_id = version_options[selected_version_idx]["id"]
        else:
            selected_version_id = None
            st.info(f"💡 Nenhuma versão encontrada para {empresa_selecionada}")
        
        # Load data
        df = load_data_with_history(empresa=empresa_code, version_id=selected_version_id)
        
        if df is not None and len(df) > 0:
            version_text = f"v{selected_version_id}" if selected_version_id else "ativa"
            st.success(f"✅ {empresa_selecionada} - Versão {version_text}: {len(df)} produtos carregados")
            
            # Show data
            st.dataframe(df.head(20))
            
            # Basic metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 Total Produtos", len(df))
            with col2:
                if 'Estoque_Total' in df.columns:
                    st.metric("📦 Estoque Total", f"{df['Estoque_Total'].sum():,.0f}")
            with col3:
                if 'data_upload' in df.columns:
                    st.metric("📅 Última Atualização", str(df['data_upload'].max())[:10])
                    
        else:
            st.info(f"💡 Nenhum dado encontrado para {empresa_selecionada}.")
            st.markdown("👉 **Vá para 'Upload de Dados' para enviar dados para esta empresa primeiro.**")
            
    except ImportError:
        st.warning("⚠️ Snowflake não configurado. Use 'Upload de Dados' primeiro.")
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {str(e)}")
        
    # Instructions
    st.markdown("""
    ### 💡 Como usar:
    1. **Selecione a empresa** no menu superior
    2. **Escolha a versão** dos dados que quer visualizar
    3. **Analise os dados** na tabela abaixo
    4. Use **Forçar Atualização** se fez upload recente
    
    ### 🔄 Próximas melhorias:
    - Gráficos interativos de timeline
    - Cálculo automático de MOQ
    - Alertas de estoque baixo
    - Análise de fornecedores
    """) 