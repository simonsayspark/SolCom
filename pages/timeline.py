import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

def detect_excel_headers(uploaded_file):
    """Smart detection of Excel headers for different file formats"""
    try:
        # Read the Excel file to understand structure
        xl_file = pd.ExcelFile(uploaded_file)
        sheets = xl_file.sheet_names
        
        # Try different sheets and header positions
        best_sheet = None
        best_header_row = 9  # Default for MINIPA
        best_df = None
        best_score = 0
        
        # Try different starting rows to find headers
        for sheet in sheets[:3]:  # Check first 3 sheets
            for header_row in [0, 8, 9, 10, 7, 6, 11, 12]:
                try:
                    df_sample = pd.read_excel(uploaded_file, sheet_name=sheet, header=header_row, nrows=20)
                    
                    # Check if we found real headers (not None or Unnamed)
                    valid_columns = 0
                    real_headers = []
                    
                    for col in df_sample.columns:
                        col_str = str(col).strip()
                        if (col_str != 'None' and 
                            not col_str.startswith('Unnamed') and 
                            col_str != 'nan' and
                            len(col_str) > 0):
                            valid_columns += 1
                            real_headers.append(col_str)
                    
                    # Score this attempt (prioritize files with expected timeline columns)
                    expected_cols = ['Item', 'Modelo', 'Fornecedor', 'QTD', 'MOQ', 'Estoque']
                    timeline_score = sum(1 for expected in expected_cols if any(expected.lower() in col.lower() for col in real_headers))
                    data_rows = len(df_sample.dropna(how='all'))
                    score = valid_columns * data_rows + timeline_score * 10
                    
                    if score > best_score and valid_columns >= 3 and data_rows >= 3:
                        best_score = score
                        best_sheet = sheet
                        best_header_row = header_row
                        best_df = df_sample
                        
                except Exception as e:
                    continue
        
        if best_df is not None:
            # Load the full dataset
            df_full = pd.read_excel(uploaded_file, sheet_name=best_sheet, header=best_header_row)
            df_full = df_full.dropna(how='all')  # Remove completely empty rows
            st.info(f"🔍 Header detectado: planilha '{best_sheet}', linha {best_header_row + 1}")
            return df_full
        else:
            st.warning("⚠️ Usando detecção padrão: linha 10")
            return pd.read_excel(uploaded_file, header=9)
                        
    except Exception as e:
        st.error(f"❌ Erro na detecção: {str(e)}")
        # Fallback to default
        return pd.read_excel(uploaded_file, header=9)

@st.cache_data
def carregar_dados(uploaded_file=None):
    """Load data from uploaded file"""
    try:
        if uploaded_file is not None:
            df = detect_excel_headers(uploaded_file)
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

def load_page():
    # Header with company selector
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title("📅 TIMELINE INTERATIVA DE COMPRAS")
        st.markdown("### 🎯 Visualização interativa com MOQ otimizado")
    
    with col2:
        # Company selector
        empresa_selecionada = st.selectbox(
            "🏢 Empresa:",
            ["MINIPA", "MINIPA INDUSTRIA"],
            key="empresa_selector_timeline",
            help="Selecione a empresa para visualizar os dados"
        )
        empresa_code = "MINIPA" if empresa_selecionada == "MINIPA" else "MINIPA_INDUSTRIA"
        
        # Store in session state for persistence
        st.session_state.current_empresa = empresa_code
    
    with col3:
        if st.button("🔄 Forçar Atualização", 
                    help="Atualizar dados do Snowflake (normalmente cache por 30 dias)",
                    use_container_width=True):
            from bd.snowflake_config import load_data_with_history
            load_data_with_history.clear()  # Clear specific function cache only
            st.success("✅ Cache da Timeline limpo! Dados atualizados.")
            st.rerun()

    # Try to load data from Snowflake first
    try:
        from bd.snowflake_config import load_data_with_history, get_upload_versions
        
        # Get available versions for the selected company
        versions = get_upload_versions(empresa_code, "TIMELINE", limit=20)
        
        # Version selector
        if versions:
            st.subheader(f"📦 Seleção de Versão - {empresa_selecionada}")
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Create options for version selector
                version_options = [{"id": None, "label": "🟢 Versão Ativa (Atual)", "description": "Versão atualmente ativa"}]
                for v in versions:
                    status_icon = "🟢" if v['is_active'] else "⚪"
                    version_options.append({
                        "id": v['version_id'],
                        "label": f"{status_icon} Versão {v['version_id']}",
                        "description": f"{v['upload_date']} - {v.get('description', 'Sem descrição')}"
                    })
                
                selected_version_idx = st.selectbox(
                    "Escolha a versão:",
                    range(len(version_options)),
                    format_func=lambda x: version_options[x]["label"],
                    key="version_selector_timeline",
                    help="Selecione qual versão dos dados você quer visualizar"
                )
                
                selected_version_id = version_options[selected_version_idx]["id"]
                
                # Show version info
                st.info(f"📋 {version_options[selected_version_idx]['description']}")
            
            with col2:
                st.metric("📊 Versões Disponíveis", len(versions))
                active_versions = len([v for v in versions if v['is_active']])
                st.metric("🟢 Versão Ativa", f"{active_versions}/1")
        else:
            selected_version_id = None
            st.info(f"💡 Nenhuma versão encontrada para {empresa_selecionada}")
        
        # Load data with company and version selection
        df = load_data_with_history(empresa=empresa_code, version_id=selected_version_id)
        
        if df is not None and len(df) > 0:
            version_text = f"v{selected_version_id}" if selected_version_id else "ativa"
            st.success(f"✅ {empresa_selecionada} - Versão {version_text}: {len(df)} produtos carregados")
            
            # Convert data upload column to string for display
            if 'data_upload' in df.columns:
                st.info(f"📅 Data do upload: {df['data_upload'].max()}")
        else:
            st.info(f"💡 Nenhum dado encontrado para {empresa_selecionada}.")
            st.markdown("👉 **Vá para 'Upload de Dados' para enviar dados para esta empresa primeiro.**")
            df = None
            
    except ImportError:
        st.warning("⚠️ Snowflake não configurado. Usando upload local temporário.")
        df = None
        empresa_code = "MINIPA"  # Default for fallback
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados para {empresa_selecionada}: {str(e)}")
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
        # Sidebar controls with company context
        st.sidebar.header(f"🎛️ Controles - {empresa_selecionada}")
        st.sidebar.info(f"📊 Empresa: {empresa_selecionada}")
        
        # Show version info in sidebar
        if 'selected_version_id' in locals() and selected_version_id:
            st.sidebar.info(f"📦 Versão: v{selected_version_id}")
        else:
            st.sidebar.info("📦 Versão: Ativa")
        
        meta_meses = st.sidebar.slider("🎯 Meta (meses)", 3, 12, 6)
        
        # Calculate timeline data
        timeline_data = calcular_timeline(df, meta_meses)
        
        if timeline_data:
            urgencias = ["Todos"] + sorted(list(set(item['Urgencia'] for item in timeline_data)))
            filtro = st.sidebar.selectbox("🔍 Filtrar", urgencias)
            
            # Show company-specific metrics
            st.subheader(f"📊 Métricas - {empresa_selecionada}")
            col1, col2, col3, col4 = st.columns(4)
            criticos = len([x for x in timeline_data if x['Urgencia'] == 'CRÍTICO'])
            medios = len([x for x in timeline_data if x['Urgencia'] == 'MÉDIO'])
            atencao = len([x for x in timeline_data if x['Urgencia'] == 'ATENÇÃO'])
            ok = len([x for x in timeline_data if x['Urgencia'] == 'OK'])
            
            col1.metric("🔴 Críticos", criticos)
            col2.metric("🟠 Médios", medios)
            col3.metric("🟡 Atenção", atencao)
            col4.metric("🟢 OK", ok)
            
            # Show total investment with company context
            valor_total = sum(item['Valor_Pedido'] for item in timeline_data)
            st.metric(f"💰 Investimento Total - {empresa_selecionada}", f"R$ {valor_total:,.0f}")
            
            # Create and display chart with company title
            fig = criar_grafico_interativo(timeline_data, filtro)
            if fig:
                # Update chart title to include company name
                fig.update_layout(
                    title=f"Timeline de Compras - {empresa_selecionada} ({len([x for x in timeline_data if filtro == 'Todos' or x['Urgencia'] == filtro])} produtos)",
                    title_x=0.5
                )
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown(f"""
                **💡 Como usar o Timeline de {empresa_selecionada}:**
                - 🖱️ **Zoom**: Ferramentas no canto superior direito
                - 👆 **Hover**: Passe o mouse para ver detalhes do produto
                - 🔍 **Filtrar**: Use a sidebar para filtrar por urgência
                - 🏢 **Trocar Empresa**: Use o seletor no topo da página
                - 📦 **Trocar Versão**: Use o seletor de versão para ver dados históricos
                """)
            else:
                st.warning("📊 Nenhum dado válido encontrado para o filtro selecionado.")
        else:
            st.warning(f"📊 Nenhum dado válido encontrado para criar o timeline de {empresa_selecionada}.")
            st.info("💡 Verifique se os dados foram importados corretamente ou tente uma versão diferente.")

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