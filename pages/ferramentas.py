import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime
import tempfile
import os
from pathlib import Path

def normalize_product_name(name):
    """Normalize product names for better matching"""
    if pd.isna(name):
        return ""
    return str(name).strip().replace(" ", "").replace("-", "").upper()

def get_relevance_criteria(volume_column='media'):
    """Fallback configuration for relevance criteria"""
    return {
        'volume_threshold': 5.0,
        'impact_threshold': 2000.0,
        'statistical_volume': 12.0,
        'statistical_impact': 2500.0,
        'business_low': 1000,
        'business_medium': 5000,
        'business_high': 25000,
    }

def merge_inventory_with_prices(inventory_df, pricing_df):
    """
    Merge inventory data with pricing database
    """
    
    # Clean up the inventory data - remove invalid rows
    original_count = len(inventory_df)
    
    # Find product column first
    product_col = None
    for col in inventory_df.columns:
        if any(keyword in col.lower() for keyword in ['produto', 'product', 'modelo', 'item']):
            product_col = col
            break
    
    if product_col:
        # Remove rows with invalid product names
        valid_mask = (
            inventory_df[product_col].notna() &  # Not NaN
            (inventory_df[product_col].astype(str).str.strip() != '') &  # Not empty
            (~inventory_df[product_col].astype(str).str.lower().str.contains('filtros aplicados', na=False)) &  # No filter text
            (~inventory_df[product_col].astype(str).str.lower().str.contains('situação é ativo', na=False)) &  # No filter text
            (~inventory_df[product_col].astype(str).str.lower().str.contains('grupofiltro', na=False)) &  # No filter text
            (~inventory_df[product_col].astype(str).str.lower().str.contains('tipo de produto', na=False)) &  # No filter text
            (inventory_df[product_col].astype(str).str.len() > 0) &  # Has actual content
            (inventory_df[product_col].astype(str) != 'nan')  # Not string 'nan'
        )
        
        inventory_df = inventory_df[valid_mask].copy()
        removed_count = original_count - len(inventory_df)
        
        st.info(f"🗑️ Removidas {removed_count} linhas inválidas/vazias")
        st.success(f"✅ Dados limpos: {len(inventory_df)} produtos válidos")
    
    # Detect key columns
    st.write("🔍 **Detectando colunas principais...**")
    
    # Find product column in inventory
    inventory_product_col = None
    for col in inventory_df.columns:
        if any(keyword in col.lower() for keyword in ['produto', 'product', 'modelo', 'item']):
            inventory_product_col = col
            break
    
    if not inventory_product_col:
        st.error("❌ Não foi possível encontrar a coluna de produto nos dados do inventário")
        st.info("💡 Procurando por colunas que contenham: produto, product, modelo, item")
        return None
    
    # Find product column in pricing (prioritize MODELO over MODELO DO FORNECEDOR)
    pricing_product_col = None
    # First try to find the exact MODELO column
    for col in pricing_df.columns:
        if col.upper() == 'MODELO':
            pricing_product_col = col
            break
    
    # If not found, look for any model/product column
    if not pricing_product_col:
        for col in pricing_df.columns:
            if any(keyword in col.lower() for keyword in ['modelo', 'product', 'produto', 'item']):
                pricing_product_col = col
                break
    
    if not pricing_product_col:
        st.error("❌ Não foi possível encontrar a coluna de produto nos dados de preços")
        st.info("💡 Procurando por colunas que contenham: modelo, product, produto, item")
        return None
    
    # Find price column in pricing (prioritize current FOB)
    pricing_price_col = None
    # First try to find the current FOB column
    for col in pricing_df.columns:
        if 'fob atual' in col.lower():
            pricing_price_col = col
            break
    
    # If not found, look for any FOB or price column
    if not pricing_price_col:
        for col in pricing_df.columns:
            if any(keyword in col.lower() for keyword in ['fob', 'price', 'preco', 'preço', 'valor']):
                pricing_price_col = col
                break
    
    if not pricing_price_col:
        st.error("❌ Não foi possível encontrar a coluna de preço nos dados de preços")
        st.info("💡 Procurando por colunas que contenham: fob, price, preco, preço, valor")
        return None
    
    st.success(f"✅ Coluna produto inventário: '{inventory_product_col}'")
    st.success(f"✅ Coluna produto preços: '{pricing_product_col}'")
    st.success(f"✅ Coluna preço: '{pricing_price_col}'")
    
    # Prepare data for merge
    st.write("🔄 **Preparando dados para fusão...**")
    
    # Clean product names for better matching
    inventory_df['produto_clean'] = inventory_df[inventory_product_col].astype(str).str.strip().str.upper()
    pricing_df['produto_clean'] = pricing_df[pricing_product_col].astype(str).str.strip().str.upper()
    
    # Rename price column to standard name
    pricing_df['preco_unitario'] = pricing_df[pricing_price_col]
    
    # Perform the merge
    st.write("🔗 **Fundindo dados...**")
    merged_df = inventory_df.merge(
        pricing_df[['produto_clean', 'preco_unitario']],
        on='produto_clean',
        how='left'
    )
    
    # Remove the temporary clean column
    merged_df = merged_df.drop('produto_clean', axis=1)
    
    # Show merge statistics
    total_products = len(merged_df)
    products_with_prices = merged_df['preco_unitario'].notna().sum()
    products_without_prices = total_products - products_with_prices
    merge_rate = (products_with_prices / total_products) * 100 if total_products > 0 else 0
    
    st.write("📊 **Estatísticas da fusão:**")
    st.write(f"   • Total de produtos: {total_products}")
    st.write(f"   • Produtos com preços: {products_with_prices}")
    st.write(f"   • Produtos sem preços: {products_without_prices}")
    st.write(f"   • Taxa de correspondência: {merge_rate:.1f}%")
    
    return merged_df

def run_priority_analysis(merged_df, volume_column='Média 6 Meses', volume_weight=0.85, price_weight=0.15):
    """
    Run priority analysis on merged data
    """
    
    # Handle produto column name variations
    if 'Produto' in merged_df.columns and 'produto' not in merged_df.columns:
        merged_df['produto'] = merged_df['Produto']  # Create lowercase version
    
    # Check which volume column exists and use it
    volume_column_alt = volume_column.lower()
    if volume_column not in merged_df.columns and volume_column_alt in merged_df.columns:
        volume_column = volume_column_alt
    elif volume_column not in merged_df.columns and volume_column_alt not in merged_df.columns:
        st.error(f"❌ ERRO: Nem '{volume_column}' nem '{volume_column_alt}' encontradas nos dados")
        st.error(f"Colunas disponíveis: {list(merged_df.columns)}")
        return None
    
    st.write(f"📊 Produtos com dados de uso ({volume_column}): {merged_df[volume_column].notna().sum()}")
    st.write(f"💰 Produtos com dados de preço: {merged_df['preco_unitario'].notna().sum()}")
    
    # Calculate priority scores
    df_analysis = merged_df.copy()
    
    # Normalize volume and price data
    volume_data = pd.to_numeric(df_analysis[volume_column], errors='coerce')
    price_data = pd.to_numeric(df_analysis['preco_unitario'], errors='coerce')
    
    # Calculate annual impact (volume * price * 12 months)
    df_analysis['annual_impact'] = volume_data * price_data * 12
    
    # Normalize scores for priority calculation
    max_volume = volume_data.max() if volume_data.max() > 0 else 1
    max_impact = df_analysis['annual_impact'].max() if df_analysis['annual_impact'].max() > 0 else 1
    
    # Calculate normalized scores
    df_analysis['volume_score'] = (volume_data / max_volume).fillna(0)
    df_analysis['impact_score'] = (df_analysis['annual_impact'] / max_impact).fillna(0)
    
    # Calculate weighted priority score
    df_analysis['priority_score'] = (
        df_analysis['volume_score'] * volume_weight + 
        df_analysis['impact_score'] * price_weight
    )
    
    # Assign priority categories
    def assign_priority(row):
        if pd.isna(row['preco_unitario']):
            return 'Sem Preço'
        elif row['priority_score'] >= 0.7:
            return 'Crítico'
        elif row['priority_score'] >= 0.4:
            return 'Alto'
        elif row['priority_score'] >= 0.2:
            return 'Médio'
        else:
            return 'Baixo'
    
    df_analysis['priority_category'] = df_analysis.apply(assign_priority, axis=1)
    
    # Sort by priority score (descending)
    df_analysis = df_analysis.sort_values('priority_score', ascending=False)
    
    return df_analysis

def show_ferramentas():
    """Main function to display the Ferramentas page"""
    
    st.title("🔧 Ferramentas")
    st.markdown("---")
    
    st.header("📊 Fusão de Dados e Análise de Prioridade")
    st.write("Esta ferramenta permite combinar dados de inventário com base de dados de preços para criar análise de prioridade otimizada.")
    
    # Create two columns for file uploads
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📁 Arquivo de Inventário")
        inventory_file = st.file_uploader(
            "Carregue o arquivo Excel do inventário",
            type=['xlsx', 'xls'],
            key="inventory_upload",
            help="Arquivo Excel contendo dados de inventário com colunas de produto e consumo"
        )
        
        if inventory_file:
            st.success(f"✅ Arquivo carregado: {inventory_file.name}")
    
    with col2:
        st.subheader("💰 Base de Dados de Preços")
        pricing_file = st.file_uploader(
            "Carregue o arquivo Excel da base de preços",
            type=['xlsx', 'xls'],
            key="pricing_upload",
            help="Arquivo Excel contendo dados de preços FOB com colunas de modelo e preço"
        )
        
        if pricing_file:
            st.success(f"✅ Arquivo carregado: {pricing_file.name}")
    
    # Configuration section
    st.header("⚙️ Configurações da Análise")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        volume_column_choice = st.selectbox(
            "Coluna de Volume",
            ["Média 6 Meses", "Consumo 6 Meses"],
            help="Escolha qual coluna usar para cálculo de volume"
        )
    
    with col2:
        volume_weight = st.slider(
            "Peso do Volume (%)",
            min_value=0,
            max_value=100,
            value=85,
            help="Peso dado ao volume na análise de prioridade"
        ) / 100
    
    with col3:
        price_weight = 1 - volume_weight
        st.metric("Peso do Preço (%)", f"{price_weight*100:.0f}")
    
    # Process files when both are uploaded
    if inventory_file and pricing_file:
        st.markdown("---")
        st.header("🔄 Processamento")
        
        if st.button("🚀 Executar Análise", type="primary", use_container_width=True):
            try:
                with st.spinner("Carregando arquivos..."):
                    # Load inventory data
                    inventory_df = pd.read_excel(inventory_file)
                    st.success(f"📊 Dados de inventário carregados: {len(inventory_df)} linhas")
                    
                    # Load pricing data
                    pricing_df = pd.read_excel(pricing_file)
                    st.success(f"💰 Dados de preços carregados: {len(pricing_df)} linhas")
                
                with st.spinner("Fundindo dados..."):
                    # Merge data
                    merged_df = merge_inventory_with_prices(inventory_df, pricing_df)
                    
                    if merged_df is not None:
                        st.success("✅ Dados fundidos com sucesso!")
                        
                        # Store merged data in session state
                        st.session_state['merged_data'] = merged_df
                        
                        with st.spinner("Executando análise de prioridade..."):
                            # Run priority analysis
                            analysis_df = run_priority_analysis(
                                merged_df, 
                                volume_column=volume_column_choice,
                                volume_weight=volume_weight,
                                price_weight=1-volume_weight
                            )
                            
                            if analysis_df is not None:
                                st.success("✅ Análise de prioridade concluída!")
                                
                                # Store analysis results in session state
                                st.session_state['analysis_results'] = analysis_df
                                
                                # Show results summary
                                st.markdown("---")
                                st.header("📈 Resumo dos Resultados")
                                
                                # Priority distribution
                                priority_counts = analysis_df['priority_category'].value_counts()
                                
                                col1, col2, col3, col4, col5 = st.columns(5)
                                
                                with col1:
                                    st.metric("🔴 Crítico", priority_counts.get('Crítico', 0))
                                with col2:
                                    st.metric("🟠 Alto", priority_counts.get('Alto', 0))
                                with col3:
                                    st.metric("🟡 Médio", priority_counts.get('Médio', 0))
                                with col4:
                                    st.metric("🟢 Baixo", priority_counts.get('Baixo', 0))
                                with col5:
                                    st.metric("⚪ Sem Preço", priority_counts.get('Sem Preço', 0))
                                
                                # Show top 10 critical products
                                st.subheader("🔝 Top 10 Produtos Críticos")
                                critical_products = analysis_df[analysis_df['priority_category'] == 'Crítico'].head(10)
                                
                                if not critical_products.empty:
                                    # Select relevant columns to display
                                    display_columns = []
                                    if 'produto' in critical_products.columns:
                                        display_columns.append('produto')
                                    elif 'Produto' in critical_products.columns:
                                        display_columns.append('Produto')
                                    
                                    display_columns.extend([
                                        volume_column_choice, 'preco_unitario', 'annual_impact', 
                                        'priority_score', 'priority_category'
                                    ])
                                    
                                    # Filter columns that actually exist
                                    display_columns = [col for col in display_columns if col in critical_products.columns]
                                    
                                    st.dataframe(
                                        critical_products[display_columns],
                                        use_container_width=True,
                                        hide_index=True
                                    )
                                else:
                                    st.info("Nenhum produto crítico encontrado.")
                                
                                # Download section
                                st.markdown("---")
                                st.header("💾 Download dos Resultados")
                                
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    # Create Excel file for merged data
                                    merged_buffer = io.BytesIO()
                                    with pd.ExcelWriter(merged_buffer, engine='xlsxwriter') as writer:
                                        merged_df.to_excel(writer, sheet_name='Dados Fundidos', index=False)
                                    
                                    st.download_button(
                                        label="📊 Download Dados Fundidos",
                                        data=merged_buffer.getvalue(),
                                        file_name=f"dados_fundidos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    )
                                
                                with col2:
                                    # Create Excel file for analysis results
                                    analysis_buffer = io.BytesIO()
                                    with pd.ExcelWriter(analysis_buffer, engine='xlsxwriter') as writer:
                                        analysis_df.to_excel(writer, sheet_name='Análise de Prioridade', index=False)
                                    
                                    st.download_button(
                                        label="🎯 Download Análise de Prioridade",
                                        data=analysis_buffer.getvalue(),
                                        file_name=f"analise_prioridade_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    )
                            
            except Exception as e:
                st.error(f"❌ Erro durante o processamento: {str(e)}")
                st.exception(e)
    
    # Show existing results if available
    if 'analysis_results' in st.session_state:
        st.markdown("---")
        st.header("📋 Resultados Anteriores")
        
        analysis_df = st.session_state['analysis_results']
        
        # Filter options
        st.subheader("🔍 Filtros")
        col1, col2 = st.columns(2)
        
        with col1:
            selected_categories = st.multiselect(
                "Categorias de Prioridade",
                options=analysis_df['priority_category'].unique(),
                default=analysis_df['priority_category'].unique()
            )
        
        with col2:
            min_annual_impact = st.number_input(
                "Impacto Anual Mínimo ($)",
                min_value=0.0,
                value=0.0,
                step=100.0
            )
        
        # Apply filters
        filtered_df = analysis_df[
            (analysis_df['priority_category'].isin(selected_categories)) &
            (analysis_df['annual_impact'].fillna(0) >= min_annual_impact)
        ]
        
        st.write(f"Mostrando {len(filtered_df)} de {len(analysis_df)} produtos")
        
        # Display filtered results
        if not filtered_df.empty:
            # Select relevant columns to display
            display_columns = []
            if 'produto' in filtered_df.columns:
                display_columns.append('produto')
            elif 'Produto' in filtered_df.columns:
                display_columns.append('Produto')
            
            # Add other relevant columns
            for col in ['Média 6 Meses', 'Consumo 6 Meses', 'preco_unitario', 'annual_impact', 'priority_score', 'priority_category']:
                if col in filtered_df.columns:
                    display_columns.append(col)
            
            st.dataframe(
                filtered_df[display_columns],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Nenhum produto encontrado com os filtros aplicados.")