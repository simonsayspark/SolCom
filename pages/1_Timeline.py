import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path to import auth
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import auth

# Check authentication
if not auth.require_auth():
    st.stop()

st.set_page_config(page_title="Timeline", page_icon="📅", layout="wide")

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
            # Tentar carregar arquivo local (para desenvolvimento)
            try:
                df = pd.read_excel("Solicitação 05 JOI & SP (3).xlsx", header=9)
            except FileNotFoundError:
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

# Interface principal
# Show user info
auth.show_user_info()

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
    st.error("Não foi possível carregar os dados") 