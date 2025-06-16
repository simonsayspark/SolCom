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
        
        # Convert numeric columns - support multiple column name variations
        colunas_numericas = ['QTD', 'Preço FOB\nUnitário', 'Preço FOB Unitário', 'Preco FOB Unitario',
                           'Estoque\nTotal ', 'Estoque Total', 'In Transit\nShipt', 'In Transit Shipt',
                           'Avg Sales\n', 'Avg Sales', 'CBM', 'MOQ', 'Preço FOB TOTAL', 'Preço FOB\nTOTAL']
        
        for col in colunas_numericas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Rename columns - support multiple variations
        df = df.rename(columns={
            'Preço FOB\nUnitário': 'Preco_Unitario',
            'Preço FOB Unitário': 'Preco_Unitario',
            'Preco FOB Unitario': 'Preco_Unitario',
            'Estoque\nTotal ': 'Estoque_Total',
            'Estoque Total': 'Estoque_Total',
            'In Transit\nShipt': 'In_Transit',
            'In Transit Shipt': 'In_Transit',
            'Avg Sales\n': 'Vendas_Medias',
            'Avg Sales': 'Vendas_Medias',
            'Previsão Total com New PO': 'Previsao_Total_New_Pos',
            'Previsão Total com New Pos': 'Previsao_Total_New_Pos'
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
    
    # Check if we have any data
    if df.empty:
        st.warning("⚠️ DataFrame vazio - nenhum dado para calcular timeline")
        return []
    
    # Debug columns moved to main function
    
    # Debug: Track filtering process
    total_rows = len(df)
    filtered_out = 0
    product_rows = 0
    
    for idx, row in df.iterrows():
        # FILTER OUT SUMMARY/TOTAL ROWS
        item_name = str(row.get('Item', '')).strip().upper()
        modelo = str(row.get('Modelo', '')).strip()
        
        # Skip summary rows like "TOTAL GERAL", empty rows, or rows without valid product names
        if (item_name in ['TOTAL GERAL', 'TOTAL', 'SUBTOTAL', 'GRAND TOTAL', ''] or
            modelo == '' or
            pd.isna(row.get('Modelo')) or
            item_name.startswith('TOTAL')):
            filtered_out += 1
            continue
        
        product_rows += 1
        
        # Safely access columns with fallbacks - handle NaN values properly
        produto = modelo if modelo else f'Produto_{idx}'
        fornecedor = str(row.get('Fornecedor', 'Fornecedor Desconhecido')) if pd.notna(row.get('Fornecedor')) else 'Fornecedor Desconhecido'
        
        # Handle numeric columns properly - convert NaN to 0
        estoque_atual = (pd.to_numeric(row.get('Estoque_Total', 0), errors='coerce') or 0) + (pd.to_numeric(row.get('In_Transit', 0), errors='coerce') or 0)
        vendas_mensais = pd.to_numeric(row.get('Vendas_Medias', 0), errors='coerce') or 0
        moq = pd.to_numeric(row.get('MOQ', 0), errors='coerce') or 0
        
        # 🔧 FIX: Get Excel QTD for correct total value calculation
        excel_qtd = pd.to_numeric(row.get('QTD', 0), errors='coerce') or 0
        
        # Try multiple column name variations for price
        preco = 0
        price_columns = [
            'Preco_Unitario',           # Standard renamed column
            '"Preco_Unitario"',         # Snowflake quoted column  
            'Preço FOB Unitário',       # Excel direct
            'Preço FOB\nUnitário',      # Excel with newline
            'preco_unitario',           # Database column
            'Preco_FOB_Unitario'        # Alternative naming
        ]
        for col in price_columns:
            if col in row and pd.notna(row[col]):
                preco = pd.to_numeric(row[col], errors='coerce') or 0
                if preco > 0:
                    break
        
        # Also try accessing by exact column names from the dataframe
        if preco == 0:
            for col in df.columns:
                if 'preco' in col.lower() and ('unit' in col.lower() or 'fob' in col.lower()):
                    if pd.notna(row[col]):
                        try:
                            preco = pd.to_numeric(row[col], errors='coerce') or 0
                            if preco > 0:
                                break
                        except Exception as e:
                            continue  # Skip problematic columns
        
        cbm = pd.to_numeric(row.get('CBM', 0), errors='coerce') or 0
        
        # 🔧 FIX: Get Previsão Total directly from Excel if available - with debugging
        excel_previsao_total = 0
        previsao_columns = ['Previsao_Total_New_Pos', 'Previsão Total com New PO', 'Previsão Total com New Pos', 'Previsão Total']

        # Try different column variations
        for col in previsao_columns:
            if col in row and pd.notna(row[col]):
                excel_previsao_total = pd.to_numeric(row[col], errors='coerce') or 0
                if excel_previsao_total > 0:
                    break

        # Also check exact column names in dataframe
        if excel_previsao_total == 0:
            for col in df.columns:
                if 'previsao' in col.lower() or 'previsão' in col.lower():
                    if pd.notna(row[col]):
                        excel_previsao_total = pd.to_numeric(row[col], errors='coerce') or 0
                        if excel_previsao_total > 0:
                            break
        

        
        # 🔧 DEBUG: Track what happens to each product
        debug_info = f"Produto: {produto} | Fornecedor: {fornecedor} | Vendas: {vendas_mensais} | Estoque: {estoque_atual} | MOQ: {moq} | Preço: {preco}"
        
        # Process all products with proper data - exactly like MINIPA
        if vendas_mensais > 0:
            meses_ate_zerar = estoque_atual / vendas_mensais
            data_esgotamento = hoje + timedelta(days=int(meses_ate_zerar * 30))
            data_pedido = data_esgotamento - timedelta(days=45)
            if data_pedido < hoje:
                data_pedido = hoje
            
            qtd_otimizada = otimizar_quantidade_moq(vendas_mensais, moq, meta_meses)
            
            # 🔧 FIX: Use Excel QTD for total value, not optimized quantity
            valor_pedido = excel_qtd * preco if excel_qtd > 0 else qtd_otimizada * preco
            
            # 🔧 FIX: Use Excel CBM value directly instead of calculating CBM per quantity
            # CBM should be the total CBM value from Excel, not CBM per unit * quantity
            cbm_pedido = cbm if cbm > 0 else (qtd_otimizada * 0.01)  # fallback to small CBM if zero
            
            # 🔧 FIX: Use Excel Previsão Total value directly if available, otherwise calculate
            if excel_previsao_total > 0:
                previsao_total_new_pos = excel_previsao_total
            else:
                # Fallback calculation if Excel doesn't have the value
                previsao_total_new_pos = qtd_otimizada / vendas_mensais if vendas_mensais > 0 else 0
            
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
                'Previsao_Total_New_Pos': previsao_total_new_pos,
                'Preco_Unitario': preco,
                'Cor': cor,
                'Urgencia': urgencia
            })
        elif (estoque_atual > 0 or moq > 0 or excel_qtd > 0) and produto != 'nan':
            # 🔧 FIX: Include products with QTD even if no stock/MOQ/sales
            # Products without sales but with stock/MOQ data - show as monitoring
            qtd_otimizada = max(moq, 50) if moq > 0 else 50
            
            # 🔧 FIX: Use Excel QTD for monitoring products too
            valor_pedido = excel_qtd * preco if excel_qtd > 0 else qtd_otimizada * preco
            
            # 🔧 FIX: Use Excel CBM value directly for monitoring products too
            cbm_pedido = cbm if cbm > 0 else (qtd_otimizada * 0.01)  # fallback
            
            # 🔧 FIX: Use Excel Previsão Total if available for monitoring products
            previsao_total_new_pos = excel_previsao_total if excel_previsao_total > 0 else 0
            
            cor = '#87CEEB'  # Light blue
            urgencia = 'MONITORAR'
            dias_restantes = 999
            
            timeline_data.append({
                'Produto': produto,
                'Fornecedor': fornecedor,
                'Dias_Restantes': dias_restantes,
                'Estoque_Atual': estoque_atual,
                'Vendas_Mensais': vendas_mensais,
                'MOQ': moq,
                'Qtd_Otimizada': qtd_otimizada,
                'Valor_Pedido': valor_pedido,
                'CBM_Pedido': cbm_pedido,
                'Previsao_Total_New_Pos': previsao_total_new_pos,
                'Preco_Unitario': preco,
                'Cor': cor,
                'Urgencia': urgencia
            })
        else:
            # 🔧 FIX: Catch-all for products that don't meet main conditions but should still appear
            if preco > 0 or excel_qtd > 0:  # At least has price or quantity
                qtd_otimizada = excel_qtd if excel_qtd > 0 else (moq if moq > 0 else 1)
                valor_pedido = excel_qtd * preco if excel_qtd > 0 else preco
                cbm_pedido = cbm if cbm > 0 else 0.01
                previsao_total_new_pos = excel_previsao_total if excel_previsao_total > 0 else 0
                
                timeline_data.append({
                    'Produto': produto,
                    'Fornecedor': fornecedor,
                    'Dias_Restantes': 999,  # No urgency calculation possible
                    'Estoque_Atual': estoque_atual,
                    'Vendas_Mensais': vendas_mensais,
                    'MOQ': moq,
                    'Qtd_Otimizada': qtd_otimizada,
                    'Valor_Pedido': valor_pedido,
                    'CBM_Pedido': cbm_pedido,
                    'Previsao_Total_New_Pos': previsao_total_new_pos,
                    'Preco_Unitario': preco,
                    'Cor': '#D3D3D3',  # Light gray
                    'Urgencia': 'REVISAR'
                })
    
    # Store debug info for main function
    if hasattr(st.session_state, 'debug_info') or True:
        # Count different categories
        products_with_sales = len([x for x in timeline_data if x['Vendas_Mensais'] > 0])
        products_monitoring = len([x for x in timeline_data if x['Urgencia'] == 'MONITORAR'])
        products_revisar = len([x for x in timeline_data if x['Urgencia'] == 'REVISAR'])
        
        st.session_state.debug_info = {
            'total_rows': total_rows,
            'filtered_out': filtered_out,
            'product_rows': product_rows,
            'timeline_items': len(timeline_data),
            'products_with_sales': products_with_sales,
            'products_monitoring': products_monitoring,
            'products_revisar': products_revisar,
            'missing_from_timeline': product_rows - len(timeline_data)
        }
    
    # If no valid timeline data after filtering, show warning
    if len(timeline_data) == 0 and product_rows > 0:
        st.warning(f"⚠️ Found {product_rows} product rows but no valid timeline data. Check sales data and stock levels.")
    elif len(timeline_data) == 0:
        st.warning(f"⚠️ No product rows found after filtering {filtered_out} summary/empty rows from {total_rows} total rows.")
    
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
                    f"Estoque Atual: {item['Estoque_Atual']:.0f} un.<br>" +
                    f"Vendas Mensais: {item['Vendas_Mensais']:.1f} un.<br>" +
                    f"Dias Restantes: {item['Dias_Restantes']}<br>" +
                    f"MOQ: {item['MOQ']:.0f} un.<br>" +
                    f"Preço FOB Unit.: R$ {item['Preco_Unitario']:.2f}<br>" +
                    f"Total FOB: R$ {item['Valor_Pedido']:,.2f}<br>" +
                    f"Urgência: {item['Urgencia']}<br>" +
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
                    f"Fornecedor: {item['Fornecedor']}<br>" +
                    f"Quantidade MOQ: {item['Qtd_Otimizada']:.0f} un.<br>" +
                    f"Preço FOB Unitário: R$ {item['Preco_Unitario']:.2f}<br>" +
                    f"Total FOB: R$ {item['Valor_Pedido']:,.2f}<br>" +
                    f"CBM Total: {item['CBM_Pedido']:.2f}<br>" +
                    f"Previsão Cobertura: {item['Previsao_Total_New_Pos']:.1f} meses<br>" +
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

def show_timeline_visual(timeline_data, empresa_selecionada, filtro):
    """Tab 1: Enhanced Timeline Visual"""
    
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
    cbm_total = sum(item['CBM_Pedido'] for item in timeline_data)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(f"💰 Investimento Total", f"R$ {valor_total:,.0f}")
    with col2:
        st.metric(f"📦 CBM Total", f"{cbm_total:.1f} m³")
    
    # Create and display enhanced charts
    fig = criar_grafico_interativo(timeline_data, filtro)
    if fig:
        # Update chart title to include company name
        fig.update_layout(
            title=f"Timeline de Compras - {empresa_selecionada} ({len([x for x in timeline_data if filtro == 'Todos' or x['Urgencia'] == filtro])} produtos)",
            title_x=0.5
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown(f"""
        **💡 Como usar o Timeline Visual:**
        - 🖱️ **Zoom**: Ferramentas no canto superior direito
        - 👆 **Hover**: Informações detalhadas incluindo preços FOB e previsão de cobertura
        - 🔍 **Filtrar**: Use a sidebar para filtrar por urgência
        - 📊 **Gráfico Superior**: Quando o estoque vai acabar (em dias)
        - 📦 **Gráfico Inferior**: Quanto comprar (MOQ) com valores FOB e previsão
        """)
    else:
        st.warning("📊 Nenhum dado válido encontrado para o filtro selecionado.")

def show_purchase_planning(timeline_data, empresa_selecionada, filtro):
    """Tab 2: Purchase Planning and Management"""
    
    # Filter data based on selection
    if filtro != "Todos":
        filtered_data = [item for item in timeline_data if item['Urgencia'] == filtro]
    else:
        filtered_data = timeline_data
    
    if not filtered_data:
        st.warning("📊 Nenhum produto encontrado para o filtro selecionado.")
        return
    
    # Purchase Summary Cards
    st.subheader("📊 Resumo de Compras")
    col1, col2, col3, col4 = st.columns(4)
    
    # Calculate metrics
    total_value = sum(item['Valor_Pedido'] for item in filtered_data)
    critical_items = len([x for x in filtered_data if x['Urgencia'] == 'CRÍTICO'])
    total_cbm = sum(item['CBM_Pedido'] for item in filtered_data)
    suppliers = len(set(item['Fornecedor'] for item in filtered_data))
    
    col1.metric("💰 Valor Total", f"R$ {total_value:,.0f}")
    col2.metric("🔴 Itens Críticos", critical_items)
    col3.metric("📦 CBM Total", f"{total_cbm:.1f} m³")
    col4.metric("🏭 Fornecedores", suppliers)
    
    # Priority-based filtering
    st.subheader("🎯 Filtros Inteligentes")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        show_critical = st.button("🔴 Apenas Críticos", help="Itens que precisam ser pedidos imediatamente")
    with col2:
        show_high_value = st.button("💰 Alto Valor", help="Itens com valor > R$ 10.000")
    with col3:
        show_by_supplier = st.selectbox("🏭 Por Fornecedor", 
                                       ["Todos"] + sorted(list(set(item['Fornecedor'] for item in filtered_data))))
    
    # Apply additional filters
    display_data = filtered_data.copy()
    if show_critical:
        display_data = [x for x in display_data if x['Urgencia'] == 'CRÍTICO']
    if show_high_value:
        display_data = [x for x in display_data if x['Valor_Pedido'] > 10000]
    if show_by_supplier != "Todos":
        display_data = [x for x in display_data if x['Fornecedor'] == show_by_supplier]
    
    # Smart Purchase Table
    st.subheader("📋 Tabela de Planejamento de Compras")
    
    if display_data:
        # Convert to DataFrame for better display
        df_purchase = pd.DataFrame(display_data)
        
        # Add priority icons and action recommendations
        def get_priority_icon(urgencia):
            icons = {
                'CRÍTICO': '🔴 CRÍTICO',
                'MÉDIO': '🟡 MÉDIO', 
                'ATENÇÃO': '🟠 ATENÇÃO',
                'OK': '🟢 OK',
                'MONITORAR': '🔵 MONITORAR'
            }
            return icons.get(urgencia, urgencia)
        
        def get_action_recommendation(urgencia, dias):
            if urgencia == 'CRÍTICO' or dias <= 30:
                return "🚨 PEDIR AGORA"
            elif urgencia == 'MÉDIO' or dias <= 90:
                return "⚠️ MONITORAR"
            else:
                return "✅ OK"
        
        # Create display dataframe
        display_df = pd.DataFrame({
            'Produto': [item['Produto'] for item in display_data],
            'Fornecedor': [item['Fornecedor'] for item in display_data],
            'Prioridade': [get_priority_icon(item['Urgencia']) for item in display_data],
            'Dias Restantes': [item['Dias_Restantes'] for item in display_data],
            'MOQ': [f"{item['MOQ']:.0f}" for item in display_data],
            'Preço Unit. (R$)': [f"{item['Preco_Unitario']:.2f}" for item in display_data],
            'Investimento (R$)': [f"{item['Valor_Pedido']:,.0f}" for item in display_data],
            'CBM': [f"{item['CBM_Pedido']:.2f}" for item in display_data],
            'Cobertura (meses)': [f"{item['Previsao_Total_New_Pos']:.1f}" for item in display_data],
            'Ação': [get_action_recommendation(item['Urgencia'], item['Dias_Restantes']) for item in display_data]
        })
        
        # 🔧 FIX: Initialize session state for selections  
        if 'purchase_selections' not in st.session_state:
            st.session_state.purchase_selections = {}
        # Add counter for forcing checkbox refresh
        if 'clear_counter' not in st.session_state:
            st.session_state.clear_counter = 0

        # 🔧 FIX: Calculate selected items first to show Gerador above table
        selected_items = []
        # Get current selections from session state
        for i, item in enumerate(display_data):
            item_id = f"{item['Produto']}_{item['Fornecedor']}"
            if st.session_state.purchase_selections.get(item_id, False):
                selected_items.append(item)

        # 🛒 GERADOR DE PEDIDO DE COMPRA - MOVED ABOVE TABLE
        if selected_items:
            st.subheader("🛒 Gerador de Pedido de Compra")
            
            selected_value = sum(item['Valor_Pedido'] for item in selected_items)
            selected_cbm = sum(item['CBM_Pedido'] for item in selected_items)
            selected_suppliers = len(set(item['Fornecedor'] for item in selected_items))
            
            col1, col2, col3 = st.columns(3)
            col1.metric("📦 Itens Selecionados", len(selected_items))
            col2.metric("💰 Valor Total", f"R$ {selected_value:,.0f}")
            col3.metric("🏭 Fornecedores", selected_suppliers)
            
            # Group by supplier
            supplier_groups = {}
            for item in selected_items:
                supplier = item['Fornecedor']
                if supplier not in supplier_groups:
                    supplier_groups[supplier] = []
                supplier_groups[supplier].append(item)
            
            # Display grouped by supplier
            st.markdown("**📋 Agrupado por Fornecedor:**")
            for supplier, items in supplier_groups.items():
                with st.expander(f"🏭 {supplier} ({len(items)} itens - R$ {sum(x['Valor_Pedido'] for x in items):,.0f})"):
                    for item in items:
                        st.write(f"• {item['Produto']} - {item['MOQ']:.0f} un. - R$ {item['Valor_Pedido']:,.0f}")
            
            # Export functionality
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📊 Exportar para Excel", use_container_width=True):
                    # Create Excel export
                    export_df = pd.DataFrame({
                        'Item': [item['Produto'] for item in selected_items],
                        'Fornecedor': [item['Fornecedor'] for item in selected_items],
                        'QTD': [item['MOQ'] for item in selected_items],
                        'Preço FOB Unitário': [item['Preco_Unitario'] for item in selected_items],
                        'Preço FOB TOTAL': [item['Valor_Pedido'] for item in selected_items],
                        'CBM': [item['CBM_Pedido'] for item in selected_items],
                        'Previsão Total com New Pos': [item['Previsao_Total_New_Pos'] for item in selected_items],
                        'Urgência': [item['Urgencia'] for item in selected_items]
                    })
                    
                    st.download_button(
                        label="⬇️ Download Excel",
                        data=export_df.to_csv(index=False).encode('utf-8'),
                        file_name=f"pedido_compras_{empresa_selecionada}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            
            with col2:
                st.info(f"📋 {len(selected_items)} itens selecionados")
            
            st.divider()

        # Clear selection button BEFORE the table
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("**Selecione os itens para gerar pedido de compra:**")
        with col2:
            # 🔧 FIX: Better clear button with forced refresh
            if st.button("🔄 Limpar Seleção", use_container_width=True, key="clear_selection_btn"):
                # Clear all purchase selections completely
                st.session_state.purchase_selections = {}
                # Increment counter to force new checkbox keys
                st.session_state.clear_counter += 1
                # Force immediate refresh to clear all checkboxes
                st.rerun()
        
        # Add table header
        header_cols = st.columns([0.5, 2, 1.5, 1, 1, 1, 1.2, 0.8, 1, 1.5, 1.2])
        with header_cols[0]:
            st.markdown("**Sel**")
        with header_cols[1]:
            st.markdown("**Produto**")
        with header_cols[2]:
            st.markdown("**Fornecedor**")
        with header_cols[3]:
            st.markdown("**Prioridade**")
        with header_cols[4]:
            st.markdown("**Dias Rest.**")
        with header_cols[5]:
            st.markdown("**MOQ**")
        with header_cols[6]:
            st.markdown("**Preço Unit.**")
        with header_cols[7]:
            st.markdown("**Invest.**")
        with header_cols[8]:
            st.markdown("**CBM**")
        with header_cols[9]:
            st.markdown("**Cobertura**")
        with header_cols[10]:
            st.markdown("**Ação**")
        
        st.divider()
        
        # 🔧 FIX: Add selection checkboxes with session state persistence
        selected_items = []
        for i, (idx, row) in enumerate(display_df.iterrows()):
            cols = st.columns([0.5, 2, 1.5, 1, 1, 1, 1.2, 0.8, 1, 1.5, 1.2])
            
            with cols[0]:
                # Create unique identifier for this item
                item_id = f"{display_data[i]['Produto']}_{display_data[i]['Fornecedor']}"
                
                # Get previous state or default to False
                default_value = st.session_state.purchase_selections.get(item_id, False)
                
                # 🔧 FIX: Create checkbox with better unique key to prevent conflicts
                # Include clear counter to force refresh when clearing
                checkbox_key = f"purchase_checkbox_{i}_{hash(item_id) % 10000}_{st.session_state.clear_counter}"
                selected = st.checkbox(
                    "Sel", 
                    value=default_value,
                    key=checkbox_key, 
                    label_visibility="collapsed"
                )
                
                # Update session state
                st.session_state.purchase_selections[item_id] = selected
                
                # Add to selected items if checked
                if selected:
                    selected_items.append(display_data[i])
            
            with cols[1]:
                st.write(row['Produto'])
            with cols[2]:
                st.write(row['Fornecedor'])
            with cols[3]:
                st.write(row['Prioridade'])
            with cols[4]:
                st.write(row['Dias Restantes'])
            with cols[5]:
                st.write(row['MOQ'])
            with cols[6]:
                st.write(row['Preço Unit. (R$)'])
            with cols[7]:
                st.write(row['Investimento (R$)'])
            with cols[8]:
                st.write(row['CBM'])
            with cols[9]:
                st.write(row['Cobertura (meses)'])
            with cols[10]:
                st.write(row['Ação'])
        
        # Purchase Order Generator moved above table - this duplicate section removed
    
    else:
        st.info("📋 Nenhum item encontrado para os filtros selecionados.")

def load_page():
    # Header with company selector
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title("📅 TIMELINE DE COMPRAS")
        st.markdown("### 🎯 Análise completa de compras e MOQ")
    
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
        
        # Version selector with custom names and filenames
        if versions:
            st.subheader(f"📦 Seleção de Versão - {empresa_selecionada}")
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Create version options with custom names and filenames
                version_options = ["Versão Ativa (mais recente)"]
                version_mapping = {0: None}  # 0 = active version
                
                for i, v in enumerate(versions):
                    display_name = v.get('description', '').strip()
                    if not display_name:
                        display_name = f"Versão {v['version_id']}"
                    
                    filename_info = f" - 📁 {v.get('arquivo_origem', 'N/A')}" if v.get('arquivo_origem') else ""
                    option_text = f"{display_name} ({v['upload_date']}){filename_info}"
                    
                    version_options.append(option_text)
                    version_mapping[i + 1] = v['version_id']
                
                selected_option = st.selectbox(
                    "Escolha a versão dos dados:",
                    options=range(len(version_options)),
                    format_func=lambda x: version_options[x],
                    help="Selecione uma versão específica ou use a versão ativa"
                )
                
                selected_version_id = version_mapping[selected_option]
                
                if selected_version_id:
                    st.info(f"📊 Carregando versão específica: {version_options[selected_option]}")
                else:
                    st.info("📊 Carregando versão ativa (mais recente)")
            
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
        
        # MOVED DEBUG SECTIONS HERE - where sidebar is properly set up
        st.sidebar.subheader("🔧 Debug & Troubleshooting")
        st.sidebar.info("💡 Enable debug options below to troubleshoot price issues")
        
        # Debug: Show available columns
        if st.sidebar.checkbox("🔍 Debug Columns", value=True, help="Show available DataFrame columns"):
            with st.sidebar.expander("📋 Available Columns"):
                st.write("**Available Columns:**")
                st.write(list(df.columns))
                st.write("**Sample Row:**")
                if len(df) > 0:
                    sample_row = df.iloc[0]
                    st.write({col: sample_row[col] for col in df.columns[:10]})  # Show first 10 columns
                
                # Show all potential price columns and their values
                st.write("**All Potential Price Columns:**")
                first_row = df.iloc[0]
                for col in df.columns:
                    if any(keyword in col.lower() for keyword in ['preco', 'price', 'fob', 'unit']):
                        st.write(f"{col}: {first_row.get(col, 'N/A')}")
                
                # Show data filtering info
                if hasattr(st.session_state, 'debug_info'):
                    debug_info = st.session_state.debug_info
                    st.write("**🔍 Data Filtering Results:**")
                    st.write(f"📊 Total Rows in DF: {debug_info.get('total_rows', 'N/A')}")
                    st.write(f"❌ Filtered Out: {debug_info.get('filtered_out', 'N/A')} (totals/empty)")
                    st.write(f"✅ Product Rows: {debug_info.get('product_rows', 'N/A')}")
                    st.write(f"🎯 Timeline Items: {debug_info.get('timeline_items', 'N/A')}")
                
                # Show sample of rows being processed
                st.write("**📋 First 5 Rows to Process:**")
                for i in range(min(5, len(df))):
                    row = df.iloc[i]
                    item_name = str(row.get('Item', '')).strip()
                    modelo = str(row.get('Modelo', '')).strip()
                    preco = row.get('Preco_Unitario', 0)
                    st.write(f"{i+1}. Item: '{item_name}' | Modelo: '{modelo}' | Preço: {preco}")
                    if item_name.upper() in ['TOTAL GERAL', 'TOTAL'] or modelo == '':
                        st.write("   ❌ (Will be filtered out)")
                    else:
                        st.write("   ✅ (Will be processed)")
        
        # Calculate timeline data
        timeline_data = calcular_timeline(df, meta_meses)
        
        # IMMEDIATE PRICE ISSUE CHECK
        if timeline_data:
            items_with_zero_prices = len([x for x in timeline_data if x.get('Preco_Unitario', 0) == 0])
            if items_with_zero_prices > 0:
                st.sidebar.error(f"🚨 {items_with_zero_prices}/{len(timeline_data)} items have ZERO PRICES!")
                st.sidebar.warning("👆 Enable debug options above to troubleshoot")
            else:
                st.sidebar.success(f"✅ All {len(timeline_data)} items have valid prices")
        
        # Debug info for troubleshooting
        if timeline_data and st.sidebar.checkbox("🔧 Debug Calculations", value=True, help="Show data calculation details"):
            with st.sidebar.expander("🔍 Calculation Debug"):
                sample_item = timeline_data[0] if timeline_data else {}
                st.write("**📊 Sample Calculated Item:**")
                st.write(f"Produto: {sample_item.get('Produto', 'N/A')}")
                st.write(f"💰 Preço Unit.: R$ {sample_item.get('Preco_Unitario', 0):.2f}")
                st.write(f"💰 Total FOB: R$ {sample_item.get('Valor_Pedido', 0):,.2f}")
                st.write(f"📦 CBM: {sample_item.get('CBM_Pedido', 0):.2f}")
                st.write(f"📅 Previsão: {sample_item.get('Previsao_Total_New_Pos', 0):.1f} meses")
                st.write(f"📊 MOQ: {sample_item.get('MOQ', 0):.0f}")
                st.write(f"🎯 Qty Otimizada: {sample_item.get('Qtd_Otimizada', 0):.0f}")
                
                # Show if zero values detected
                if sample_item.get('Preco_Unitario', 0) == 0:
                    st.error("⚠️ PREÇO UNITÁRIO ZERO! Verificar colunas de preço.")
                if sample_item.get('Valor_Pedido', 0) == 0:
                    st.error("⚠️ VALOR PEDIDO ZERO! Problema no cálculo de preços.")
                
                # Show calculation summary for all items
                total_items = len(timeline_data)
                items_with_prices = len([x for x in timeline_data if x.get('Preco_Unitario', 0) > 0])
                items_zero_prices = total_items - items_with_prices
                
                st.write("**📈 Summary:**")
                st.write(f"Total Items: {total_items}")
                st.write(f"✅ With Prices: {items_with_prices}")
                st.write(f"❌ Zero Prices: {items_zero_prices}")
                
                if items_zero_prices > 0:
                    st.error(f"🚨 {items_zero_prices} items have zero prices!")
                else:
                    st.success("✅ All items have valid prices!")
        
        if timeline_data:
            urgencias = ["Todos"] + sorted(list(set(item['Urgencia'] for item in timeline_data)))
            filtro = st.sidebar.selectbox("🔍 Filtrar", urgencias)
            
            # TAB STRUCTURE IMPLEMENTATION
            tab1, tab2 = st.tabs(["📅 Timeline Visual", "🛒 Planejamento de Compras"])
            
            with tab1:
                show_timeline_visual(timeline_data, empresa_selecionada, filtro)
            
            with tab2:
                show_purchase_planning(timeline_data, empresa_selecionada, filtro)
                
        else:
            st.warning(f"📊 Nenhum dado válido encontrado para criar o timeline de {empresa_selecionada}.")
            st.info("💡 Verifique se os dados foram importados corretamente ou tente uma versão diferente.")

    # Instructions
    st.markdown("""
    ### 💡 Como usar a Timeline de Compras:
    
    **🏢 Configuração:**
    1. **Selecione a empresa** no menu superior (MINIPA ou MINIPA INDUSTRIA)
    2. **Escolha a versão** dos dados que quer visualizar
    3. **Ajuste a meta** de meses na sidebar (3-12 meses)
    4. **Aplique filtros** por urgência na sidebar
    
    **📅 Tab "Timeline Visual":**
    - Visualização interativa com gráficos aprimorados
    - Hover detalhado com preços FOB unitário e total
    - Previsão de cobertura em meses (Previsão Total com New Pos)
    - Métricas de investimento total e CBM
    
    **🛒 Tab "Planejamento de Compras":**
    - Tabela inteligente com prioridades e ações recomendadas
    - Filtros por criticidade, valor alto e fornecedor
    - Seleção de itens para pedido de compra
    - Agrupamento automático por fornecedor
    - Export para Excel no formato de solicitação
    
    **🎯 Funcionalidades Avançadas:**
    - **Previsão Total com New Pos**: Mostra quantos meses o MOQ vai durar
    - **Prioridades automáticas**: Crítico (≤30 dias), Médio, Atenção, OK
    - **Valores FOB completos**: Unitário e total com CBM
    - **Cache otimizado**: 30 dias para reduzir custos do Snowflake
    """) 