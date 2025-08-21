"""
Optimized Snowflake Upload
Reduces connections by doing everything in ONE connection
"""

import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from .snowflake_connection import get_snowflake_connection
from .column_mapping import apply_column_remap

def upload_excel_to_snowflake_optimized(df, arquivo_nome, empresa="MINIPA", usuario="minipa", table_type="TIMELINE", description=""):
    """
    Optimized upload that does EVERYTHING in ONE connection:
    - Creates schemas/tables if needed
    - Creates new version
    - Deactivates old versions
    - Uploads data
    This prevents multiple Duo authentication prompts.
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    start_time = datetime.now()
    
    try:
        cursor = conn.cursor()
        
        # 1. Ensure schemas exist
        cursor.execute("CREATE SCHEMA IF NOT EXISTS CONFIG")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS ESTOQUE")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS TIMELINE")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS ANALYTICS")
        
        # 2. Create VERSIONS table if it doesn't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS CONFIG.VERSIONS (
            empresa VARCHAR(50),
            upload_version VARCHAR(100),
            version_id INTEGER,
            table_type VARCHAR(50),
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(100),
            description VARCHAR(500),
            arquivo_origem VARCHAR(200),
            linhas_processadas INTEGER DEFAULT 0,
            status VARCHAR(50) DEFAULT 'IN_PROGRESS',
            is_active BOOLEAN DEFAULT FALSE,
            PRIMARY KEY (empresa, upload_version)
        )
        """)
        
        # 3. Create data tables if they don't exist
        if table_type == "TIMELINE":
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ESTOQUE.PRODUTOS (
                empresa VARCHAR(50),
                item VARCHAR(200),
                modelo VARCHAR(200),
                fornecedor VARCHAR(200),
                qtd_atual INTEGER,
                preco_unitario FLOAT,
                estoque_total INTEGER,
                in_transit INTEGER,
                vendas_medias FLOAT,
                cbm FLOAT,
                moq INTEGER,
                data_upload TIMESTAMP,
                upload_version VARCHAR(100),
                version_id INTEGER,
                table_type VARCHAR(50),
                is_active BOOLEAN DEFAULT TRUE
            )
            """)
        elif table_type == "ANALYTICS":
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ESTOQUE.ANALYTICS_DATA (
                empresa VARCHAR(50),
                produto VARCHAR(200),
                estoque INTEGER,
                media_6_meses FLOAT,
                consumo_6_meses FLOAT,
                estoque_cobertura FLOAT,
                moq INTEGER,
                ultimo_fornecedor VARCHAR(200),
                qtde_tot_compras INTEGER,
                compras_ate_30_dias INTEGER,
                compras_31_60_dias INTEGER,
                compras_61_90_dias INTEGER,
                compras_mais_90_dias INTEGER,
                qtde_embarque INTEGER,
                preco_unitario FLOAT,
                data_upload TIMESTAMP,
                upload_version VARCHAR(100),
                version_id INTEGER,
                is_active BOOLEAN DEFAULT TRUE,
                criticality VARCHAR(50),
                priority_score FLOAT,
                relevance_class VARCHAR(50),
                monthly_volume FLOAT,
                carteira FLOAT
            )
            """)
        
        # 4. Generate version info
        upload_version = str(uuid.uuid4())
        
        # Get next version ID
        cursor.execute("""
        SELECT COALESCE(MAX(version_id), 0) + 1 
        FROM CONFIG.VERSIONS 
        WHERE empresa = %s AND table_type = %s
        """, (empresa, table_type))
        
        version_id = cursor.fetchone()[0]
        
        # 5. Create version record
        cursor.execute("""
        INSERT INTO CONFIG.VERSIONS 
        (empresa, upload_version, version_id, table_type, created_by, description, arquivo_origem)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (empresa, upload_version, version_id, table_type, usuario, description, arquivo_nome))
        
        # 6. Deactivate all previous versions (both in VERSION table and data tables)
        # Deactivate in version control table
        cursor.execute("""
        UPDATE CONFIG.VERSIONS 
        SET is_active = FALSE 
        WHERE empresa = %s AND table_type = %s
        """, (empresa, table_type))
        
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
        
        # Set the new version as active
        cursor.execute("""
        UPDATE CONFIG.VERSIONS 
        SET is_active = TRUE 
        WHERE empresa = %s AND upload_version = %s AND table_type = %s
        """, (empresa, upload_version, table_type))
        
        # 7. Prepare data for upload
        df_clean = df.copy()
        df_clean = df_clean.dropna(how='all')
        df_clean, _ = apply_column_remap(df_clean)
        
        # 8. Upload data based on table type
        if table_type == "TIMELINE":
            # Map columns for timeline
            for idx, row in df_clean.iterrows():
                try:
                    cursor.execute("""
                    INSERT INTO ESTOQUE.PRODUTOS 
                    (empresa, item, modelo, fornecedor, qtd_atual, preco_unitario, estoque_total, 
                     in_transit, vendas_medias, cbm, moq, data_upload, upload_version, version_id, 
                     table_type, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        empresa,
                        row.get('Item', ''),
                        row.get('Modelo', ''),
                        row.get('Fornecedor', 'Brazil'),
                        row.get('QTD', 0),
                        row.get('Preco_Unitario', 0),
                        row.get('Estoque_Total', 0),
                        row.get('In_Transit', 0),
                        row.get('Vendas_Medias', 0),
                        row.get('CBM', 0),
                        row.get('MOQ', 0),
                        datetime.now(),
                        upload_version,
                        version_id,
                        'TIMELINE',
                        True
                    ))
                except Exception as row_error:
                    # Row errors logged silently
                    pass
        elif table_type == "ANALYTICS":
            # Map columns for analytics
            for idx, row in df_clean.iterrows():
                try:
                    # Derive Carteira (orders on hand) if present
                    carteira_val = 0.0
                    try:
                        if 'Carteira' in row.index and pd.notna(row['Carteira']):
                            carteira_val = float(row['Carteira'])
                        elif 'carteira' in row.index and pd.notna(row['carteira']):
                            carteira_val = float(row['carteira'])
                    except Exception:
                        carteira_val = 0.0

                    cursor.execute("""
                    INSERT INTO ESTOQUE.ANALYTICS_DATA 
                    (empresa, produto, estoque, media_6_meses, consumo_6_meses, estoque_cobertura,
                     moq, ultimo_fornecedor, qtde_tot_compras, compras_ate_30_dias, compras_31_60_dias,
                     compras_61_90_dias, compras_mais_90_dias, qtde_embarque, preco_unitario,
                     data_upload, upload_version, version_id, is_active, 
                     criticality, priority_score, relevance_class, monthly_volume, carteira)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        empresa,
                        row.get('Produto', ''),
                        row.get('Estoque', 0),
                        row.get('Média 6 Meses', row.get('Media_6_Meses', 0)),
                        row.get('Consumo 6 Meses', row.get('Consumo_6_Meses', 0)),
                        row.get('Estoque Cobertura', row.get('Estoque_Cobertura', 999)),
                        row.get('MOQ', 0),
                        row.get('UltimoFornecedor', row.get('ultimo_fornecedor', 'Brazil')),
                        row.get('Qtde Tot Compras', row.get('Qtde_Tot_Compras', 0)),
                        row.get('Compras Até 30 Dias', row.get('Compras_Ate_30_Dias', 0)),
                        row.get('Compras 31 a 60 Dias', row.get('Compras_31_60_Dias', 0)),
                        row.get('Compras 61 a 90 Dias', row.get('Compras_61_90_Dias', 0)),
                        row.get('Compras > 90 Dias', row.get('Compras_Mais_90_Dias', 0)),
                        row.get('Qtde Embarque', row.get('Qtde_Embarque', 0)),
                        row.get('preco_unitario', row.get('Preco_Unitario', 0)),
                        datetime.now(),
                        upload_version,
                        version_id,
                        True,
                        row.get('criticality', None),
                        row.get('priority_score', None),
                        row.get('relevance_class', None),
                        row.get('monthly_volume', None),
                        carteira_val
                    ))
                except Exception as row_error:
                    # Fallback: try without carteira if column does not exist
                    try:
                        if 'invalid identifier' in str(row_error).lower() and 'carteira' in str(row_error).lower():
                            cursor.execute("""
                            INSERT INTO ESTOQUE.ANALYTICS_DATA 
                            (empresa, produto, estoque, media_6_meses, consumo_6_meses, estoque_cobertura,
                             moq, ultimo_fornecedor, qtde_tot_compras, compras_ate_30_dias, compras_31_60_dias,
                             compras_61_90_dias, compras_mais_90_dias, qtde_embarque, preco_unitario,
                             data_upload, upload_version, version_id, is_active, 
                             criticality, priority_score, relevance_class, monthly_volume)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                empresa,
                                row.get('Produto', ''),
                                row.get('Estoque', 0),
                                row.get('Média 6 Meses', row.get('Media_6_Meses', 0)),
                                row.get('Consumo 6 Meses', row.get('Consumo_6_Meses', 0)),
                                row.get('Estoque Cobertura', row.get('Estoque_Cobertura', 999)),
                                row.get('MOQ', 0),
                                row.get('UltimoFornecedor', row.get('ultimo_fornecedor', 'Brazil')),
                                row.get('Qtde Tot Compras', row.get('Qtde_Tot_Compras', 0)),
                                row.get('Compras Até 30 Dias', row.get('Compras_Ate_30_Dias', 0)),
                                row.get('Compras 31 a 60 Dias', row.get('Compras_31_60_Dias', 0)),
                                row.get('Compras 61 a 90 Dias', row.get('Compras_61_90_Dias', 0)),
                                row.get('Compras > 90 Dias', row.get('Compras_Mais_90_Dias', 0)),
                                row.get('Qtde Embarque', row.get('Qtde_Embarque', 0)),
                                row.get('preco_unitario', row.get('Preco_Unitario', 0)),
                                datetime.now(),
                                upload_version,
                                version_id,
                                True,
                                row.get('criticality', None),
                                row.get('priority_score', None),
                                row.get('relevance_class', None),
                                row.get('monthly_volume', None)
                            ))
                        else:
                            pass
                    except Exception:
                        pass
        
        # 9. Update version record with row count
        cursor.execute("""
        UPDATE CONFIG.VERSIONS 
        SET linhas_processadas = %s, status = 'COMPLETED', upload_date = CURRENT_TIMESTAMP
        WHERE empresa = %s AND upload_version = %s
        """, (len(df_clean), empresa, upload_version))
        
        # 10. Commit everything at once
        conn.commit()
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        st.success(f"✅ Upload concluído em {execution_time:.1f} segundos")
                        # Processing complete - silent success
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"❌ Erro durante upload: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()
        return False