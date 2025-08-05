"""
Optimized Snowflake Upload
Reduces connections by combining version creation and upload into one connection
"""

import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from .snowflake_connection import get_snowflake_connection
from .snowflake_tables import create_tables
from .column_mapping import apply_column_remap

def upload_excel_to_snowflake_optimized(df, arquivo_nome, empresa="MINIPA", usuario="minipa", table_type="TIMELINE", description=""):
    """
    Optimized upload that creates version and uploads data in ONE connection.
    This prevents multiple Duo authentication prompts.
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    start_time = datetime.now()
    
    try:
        cursor = conn.cursor()
        
        # 1. Generate version info WITHOUT creating a new connection
        upload_version = str(uuid.uuid4())
        
        # Get next version ID
        cursor.execute("""
        SELECT COALESCE(MAX(version_id), 0) + 1 
        FROM CONFIG.VERSIONS 
        WHERE empresa = %s AND table_type = %s
        """, (empresa, table_type))
        
        version_id = cursor.fetchone()[0]
        
        # Create version record
        st.info(f"🔄 Criando nova versão para {empresa} - {table_type}...")
        cursor.execute("""
        INSERT INTO CONFIG.VERSIONS 
        (empresa, upload_version, version_id, table_type, created_by, description, arquivo_origem)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (empresa, upload_version, version_id, table_type, usuario, description, arquivo_nome))
        
        st.success(f"✅ Nova versão criada: v{version_id} ({upload_version})")
        
        # 2. Deactivate all previous versions
        st.info(f"🔄 Desativando versões anteriores para {empresa} - {table_type}...")
        
        # Deactivate in data tables
        if table_type == "TIMELINE":
            cursor.execute("""
            UPDATE ESTOQUE.PRODUTOS 
            SET is_active = FALSE 
            WHERE empresa = %s AND table_type = %s
            """, (empresa, table_type))
        elif table_type == "ANALYTICS":
            cursor.execute("""
            UPDATE ESTOQUE.ANALYTICS_DATA 
            SET is_active = FALSE 
            WHERE empresa = %s
            """, (empresa,))
        
        # Deactivate in version control table
        cursor.execute("""
        UPDATE CONFIG.VERSIONS 
        SET is_active = FALSE 
        WHERE empresa = %s AND table_type = %s
        """, (empresa, table_type))
        
        # Set the new version as active
        cursor.execute("""
        UPDATE CONFIG.VERSIONS 
        SET is_active = TRUE 
        WHERE empresa = %s AND upload_version = %s AND table_type = %s
        """, (empresa, upload_version, table_type))
        
        conn.commit()
        st.success(f"✅ Versão v{version_id} definida como ativa para {empresa}")
        
        # 3. Prepare data for upload
        df_clean = df.copy()
        df_clean = df_clean.dropna(how='all')
        df_clean, _ = apply_column_remap(df_clean)
        
        # 4. Upload data based on table type
        st.info(f"📤 Enviando {len(df_clean)} produtos para {table_type}...")
        
        if table_type == "TIMELINE":
            # Prepare timeline data columns
            timeline_columns = {
                'empresa': empresa,
                'item': 'Item',
                'modelo': 'Modelo',
                'fornecedor': 'Fornecedor',
                'qtd_atual': 'QTD',
                'preco_unitario': 'Preco_Unitario',
                'estoque_total': 'Estoque_Total',
                'in_transit': 'In_Transit',
                'vendas_medias': 'Vendas_Medias',
                'cbm': 'CBM',
                'moq': 'MOQ',
                'data_upload': datetime.now(),
                'upload_version': upload_version,
                'version_id': version_id,
                'table_type': 'TIMELINE',
                'is_active': True
            }
            
            # Map dataframe columns to database columns
            insert_data = []
            for _, row in df_clean.iterrows():
                row_data = [empresa]
                for db_col, df_col in timeline_columns.items():
                    if db_col == 'empresa':
                        continue  # Already added
                    elif db_col in ['data_upload', 'upload_version', 'version_id', 'table_type', 'is_active']:
                        # Use fixed values
                        if db_col == 'data_upload':
                            row_data.append(datetime.now())
                        elif db_col == 'upload_version':
                            row_data.append(upload_version)
                        elif db_col == 'version_id':
                            row_data.append(version_id)
                        elif db_col == 'table_type':
                            row_data.append('TIMELINE')
                        elif db_col == 'is_active':
                            row_data.append(True)
                    else:
                        # Get value from dataframe
                        value = row.get(df_col, None)
                        if pd.isna(value):
                            value = None
                        row_data.append(value)
                
                insert_data.append(row_data)
            
            # Batch insert
            cursor.executemany("""
            INSERT INTO ESTOQUE.PRODUTOS 
            (empresa, item, modelo, fornecedor, qtd_atual, preco_unitario, estoque_total, 
             in_transit, vendas_medias, cbm, moq, data_upload, upload_version, version_id, 
             table_type, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, insert_data)
            
        elif table_type == "ANALYTICS":
            # Prepare analytics data columns
            analytics_columns = {
                'empresa': empresa,
                'produto': 'Produto',
                'estoque': 'Estoque',
                'media_6_meses': 'Média 6 Meses',
                'consumo_6_meses': 'Consumo 6 Meses',
                'estoque_cobertura': 'Estoque Cobertura',
                'moq': 'MOQ',
                'ultimo_fornecedor': 'UltimoFornecedor',
                'qtde_tot_compras': 'Qtde Tot Compras',
                'compras_ate_30_dias': 'Compras Até 30 Dias',
                'compras_31_60_dias': 'Compras 31 a 60 Dias',
                'compras_61_90_dias': 'Compras 61 a 90 Dias',
                'compras_mais_90_dias': 'Compras > 90 Dias',
                'qtde_embarque': 'Qtde Embarque',
                'preco_unitario': 'preco_unitario',
                'data_upload': datetime.now(),
                'upload_version': upload_version,
                'version_id': version_id,
                'is_active': True,
                # Merged Excel specific columns
                'criticality': 'criticality',
                'priority_score': 'priority_score',
                'relevance_class': 'relevance_class',
                'monthly_volume': 'monthly_volume'
            }
            
            # Map dataframe columns to database columns
            insert_data = []
            for _, row in df_clean.iterrows():
                row_data = [empresa]
                for db_col, df_col in analytics_columns.items():
                    if db_col == 'empresa':
                        continue  # Already added
                    elif db_col in ['data_upload', 'upload_version', 'version_id', 'is_active']:
                        # Use fixed values
                        if db_col == 'data_upload':
                            row_data.append(datetime.now())
                        elif db_col == 'upload_version':
                            row_data.append(upload_version)
                        elif db_col == 'version_id':
                            row_data.append(version_id)
                        elif db_col == 'is_active':
                            row_data.append(True)
                    else:
                        # Get value from dataframe
                        value = row.get(df_col, None)
                        if pd.isna(value):
                            value = None
                        row_data.append(value)
                
                insert_data.append(row_data)
            
            # Batch insert
            cursor.executemany("""
            INSERT INTO ESTOQUE.ANALYTICS_DATA 
            (empresa, produto, estoque, media_6_meses, consumo_6_meses, estoque_cobertura,
             moq, ultimo_fornecedor, qtde_tot_compras, compras_ate_30_dias, compras_31_60_dias,
             compras_61_90_dias, compras_mais_90_dias, qtde_embarque, preco_unitario,
             data_upload, upload_version, version_id, is_active, 
             criticality, priority_score, relevance_class, monthly_volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, insert_data)
        
        # 5. Update version record with row count
        cursor.execute("""
        UPDATE CONFIG.VERSIONS 
        SET linhas_processadas = %s, status = 'COMPLETED', upload_date = CURRENT_TIMESTAMP
        WHERE empresa = %s AND upload_version = %s
        """, (len(df_clean), empresa, upload_version))
        
        conn.commit()
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        st.success(f"✅ Upload concluído em {execution_time:.1f} segundos")
        st.info(f"📊 {len(df_clean)} linhas processadas com sucesso")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"❌ Erro durante upload: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()
        return False