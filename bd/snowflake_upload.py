"""
Snowflake Upload Functions
Handles Excel file upload and analysis
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from .snowflake_connection import get_snowflake_connection
from .snowflake_versions import create_new_version
from .snowflake_tables import create_tables

def analyze_excel_structure(uploaded_file):
    """
    Analyze Excel file structure and suggest best processing approach
    """
    try:
        # Try to read Excel file and detect structure
        xl_file = pd.ExcelFile(uploaded_file)
        sheets = xl_file.sheet_names
        
        st.info(f"📋 Planilhas encontradas: {sheets}")
        
        # Try different starting rows to find headers - expanded range
        for sheet in sheets[:5]:  # Check first 5 sheets
            st.subheader(f"📊 Análise da planilha: {sheet}")
            
            # Try more header positions, especially around row 8-9 where the user's data is
            for header_row in [0, 8, 9, 10, 7, 6, 11, 12]:
                try:
                    df_sample = pd.read_excel(uploaded_file, sheet_name=sheet, header=header_row, nrows=5)
                    
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
                    
                    # We need at least 3 valid columns with meaningful names
                    if valid_columns >= 3 and len(df_sample) > 0:
                        # Check if we have data in the rows (not all None)
                        data_found = False
                        for _, row in df_sample.iterrows():
                            non_null_values = row.count()
                            if non_null_values >= 3:
                                data_found = True
                                break
                        
                        if data_found:
                            st.success(f"✅ Estrutura detectada em linha {header_row + 1}")
                            st.info(f"🔍 Colunas válidas encontradas: {real_headers}")
                            st.dataframe(df_sample)
                            
                            # Show column info
                            st.write("**Mapeamento de colunas:**")
                            for i, col in enumerate(df_sample.columns):
                                col_type = df_sample[col].dtype
                                sample_val = df_sample[col].iloc[0] if len(df_sample) > 0 else "N/A"
                                st.write(f"{i+1}. `{col}` - Tipo: {col_type} - Exemplo: {sample_val}")
                            
                            return sheet, header_row
                except Exception as e:
                    continue
        
        # If no automatic detection worked, show manual options
        st.warning("⚠️ Detecção automática não funcionou. Mostrando opções manuais...")
        
        # Show raw data for manual inspection
        for sheet in sheets[:2]:
            st.write(f"**Dados brutos da planilha '{sheet}':**")
            try:
                df_raw = pd.read_excel(uploaded_file, sheet_name=sheet, header=None, nrows=15)
                st.dataframe(df_raw)
                
                # Suggest header row based on where we see most text
                for row_idx in range(min(15, len(df_raw))):
                    row_data = df_raw.iloc[row_idx]
                    text_count = sum(1 for val in row_data if isinstance(val, str) and len(str(val)) > 2)
                    if text_count >= 3:
                        st.info(f"💡 Possível cabeçalho na linha {row_idx + 1}: {list(row_data[:5])}")
                        return sheet, row_idx
            except:
                continue
        
        return None, 0
                        
    except Exception as e:
        st.error(f"❌ Erro ao analisar Excel: {str(e)}")
        return None, 0

def upload_excel_to_snowflake(df, arquivo_nome, empresa="MINIPA", usuario="minipa", table_type="TIMELINE", description=""):
    """
    Upload Excel data to Snowflake with multi-company versioning support
    Returns True if successful, False otherwise
    """
    conn = get_snowflake_connection()
    if not conn:
        return False
        
    start_time = datetime.now()
    
    try:
        cursor = conn.cursor()
        
        # Create new version for this upload
        st.info(f"🔄 Criando nova versão para {empresa} - {table_type}...")
        version_info = create_new_version(
            empresa=empresa, 
            table_type=table_type, 
            description=description, 
            created_by=usuario, 
            arquivo_origem=arquivo_nome
        )
        
        if not version_info:
            st.error("❌ Erro ao criar nova versão")
            return False
        
        upload_version = version_info['upload_version']
        version_id = version_info['version_id']
        
        st.success(f"✅ Nova versão criada: v{version_id} ({upload_version})")
        
        # Ensure tables exist
        st.info(f"🔧 Verificando estrutura das tabelas...")
        if not create_tables():
            st.warning("⚠️ Erro ao verificar/criar tabelas - continuando...")
        
        # Clean the dataframe - remove NaN and empty rows
        df_clean = df.copy()
        df_clean = df_clean.dropna(how='all')
        
        # Get actual column names from the dataframe
        available_columns = list(df_clean.columns)
        st.info(f"📊 Colunas encontradas: {available_columns}")
        
        success_count = 0
        error_count = 0
        
        # Helper functions for safe data conversion
        def safe_numeric(val, default=0):
            if pd.isna(val) or val == '' or str(val).lower() == 'nan':
                return default
            try:
                return int(float(str(val)))
            except:
                return default
        
        def safe_float(val, default=0.0):
            if pd.isna(val) or val == '' or str(val).lower() == 'nan':
                return default
            try:
                return float(val)
            except:
                return default
        
        # Insert new data row by row based on table type
        if table_type == "TIMELINE":
            st.info(f"📋 Processando {len(df_clean)} linhas para Timeline de {empresa}...")
            
            for idx, row in df_clean.iterrows():
                try:
                    # Extract values for timeline table
                    item = str(row.get('Item', '')) if 'Item' in row.index else ''
                    modelo = str(row.get('Modelo', '')) if 'Modelo' in row.index else ''
                    fornecedor = str(row.get('Fornecedor', '')) if 'Fornecedor' in row.index else ''
                    
                    qtd_atual = safe_numeric(row.get('QTD', 0))
                    preco_unitario = safe_float(row.get('Preco_Unitario', 0.0))
                    estoque_total = safe_numeric(row.get('Estoque_Total', 0)) 
                    in_transit = safe_numeric(row.get('In_Transit', 0))
                    vendas_medias = safe_float(row.get('Vendas_Medias', 0.0))
                    cbm = safe_float(row.get('CBM', 0.0))
                    moq = safe_numeric(row.get('MOQ', 0))
                    
                    # Skip completely empty rows
                    if not any([item, modelo, fornecedor]) and all(v == 0 for v in [qtd_atual, estoque_total]):
                        continue
                    
                    # Insert timeline data with versioning
                    cursor.execute("""
                    INSERT INTO ESTOQUE.PRODUTOS 
                    (empresa, upload_version, version_id, is_active, item, modelo, fornecedor, 
                     qtd_atual, preco_unitario, estoque_total, in_transit, vendas_medias, 
                     cbm, moq, usuario, table_type, version_description, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (empresa, upload_version, version_id, True, item, modelo, fornecedor, 
                          qtd_atual, preco_unitario, estoque_total, in_transit, vendas_medias, 
                          cbm, moq, usuario, table_type, description, usuario))
                    
                    success_count += 1
                    
                except Exception as row_error:
                    error_count += 1
                    if error_count <= 5:  # Show only first 5 errors
                        st.warning(f"⚠️ Erro na linha {idx + 1}: {str(row_error)}")
                    continue
                    
        else:  # ANALYTICS
            st.info(f"📊 Processando {len(df_clean)} linhas para Analytics de {empresa}...")
            
            for idx, row in df_clean.iterrows():
                try:
                    # Extract values for analytics table
                    produto = str(row.get('Produto', ''))
                    if not produto:  # Try alternative column names
                        produto = str(row.get('Item', '') or row.get('Modelo', ''))
                    
                    estoque = safe_numeric(row.get('Estoque', 0))
                    consumo_6_meses = safe_float(row.get('Consumo 6 Meses', 0.0))
                    media_6_meses = safe_float(row.get('Média 6 Meses', 0.0))
                    estoque_cobertura = safe_float(row.get('Estoque Cobertura', 0.0))
                    
                    # NEW: Handle MOQ and UltimoFornecedor columns
                    moq = safe_numeric(row.get('MOQ', 0))
                    ultimo_fornecedor = str(row.get('UltimoFor', '') or row.get('UltimoFornecedor', ''))
                    if not ultimo_fornecedor or ultimo_fornecedor.lower() in ['nan', 'none', '']:
                        ultimo_fornecedor = 'Brazil'  # Default value
                    
                    # Skip completely empty rows
                    if not produto and all(v == 0 for v in [estoque, consumo_6_meses, media_6_meses]):
                        continue
                    
                    # Insert analytics data with versioning - UPDATED WITH NEW COLUMNS
                    cursor.execute("""
                    INSERT INTO ESTOQUE.ANALYTICS_DATA 
                    (empresa, upload_version, version_id, is_active, produto, estoque, 
                     consumo_6_meses, media_6_meses, estoque_cobertura, moq, ultimo_fornecedor,
                     usuario, table_type, version_description, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (empresa, upload_version, version_id, True, produto, estoque, 
                          consumo_6_meses, media_6_meses, estoque_cobertura, moq, ultimo_fornecedor,
                          usuario, table_type, description, usuario))
                    
                    success_count += 1
                    
                except Exception as row_error:
                    error_count += 1
                    if error_count <= 5:  # Show only first 5 errors
                        st.warning(f"⚠️ Erro na linha {idx + 1}: {str(row_error)}")
                    continue
        
        # Calculate processing time
        end_time = datetime.now()
        processing_time = int((end_time - start_time).total_seconds())
        
        # Update version record with processing results
        try:
            cursor.execute("""
            UPDATE CONFIG.VERSIONS 
            SET linhas_processadas = %s, status = %s
            WHERE empresa = %s AND upload_version = %s AND table_type = %s
            """, (success_count, 'SUCCESS' if success_count > 0 else 'PARTIAL', empresa, upload_version, table_type))
        except Exception as version_update_error:
            st.warning(f"⚠️ Erro ao atualizar registro de versão: {str(version_update_error)}")
        
        # Log the upload
        try:
            cursor.execute("""
            INSERT INTO CONFIG.UPLOAD_LOG 
            (empresa, upload_version, version_id, nome_arquivo, linhas_processadas, 
             usuario, status, table_type, processing_time_seconds)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (empresa, upload_version, version_id, arquivo_nome, success_count, usuario, 
                  'SUCCESS' if success_count > 0 else 'PARTIAL', table_type, processing_time))
        except Exception as log_error:
            st.warning(f"⚠️ Erro ao registrar log: {str(log_error)}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Show results
        if success_count > 0:
            st.success(f"✅ {success_count} linhas processadas com sucesso para {empresa}!")
            if error_count > 0:
                st.warning(f"⚠️ {error_count} linhas com erro foram ignoradas")
            
            st.info(f"""
            🎯 **Resumo do Upload:**
            - 🏢 Empresa: {empresa}
            - 📊 Tipo: {table_type}
            - 📦 Versão: v{version_id}
            - ✅ Sucesso: {success_count} linhas
            - ⚠️ Erros: {error_count} linhas
            - ⏱️ Tempo: {processing_time}s
            """)
            return True
        else:
            st.error("❌ Nenhuma linha foi processada com sucesso")
            return False
        
    except Exception as e:
        st.error(f"❄️ Erro ao fazer upload: {str(e)}")
        st.error(f"📊 Detalhes do erro: {type(e).__name__}")
        
        # Log the error
        try:
            end_time = datetime.now()
            processing_time = int((end_time - start_time).total_seconds())
            
            cursor.execute("""
            INSERT INTO CONFIG.UPLOAD_LOG 
            (empresa, upload_version, version_id, nome_arquivo, linhas_processadas, 
             usuario, status, table_type, error_details, processing_time_seconds)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (empresa, version_info['upload_version'] if 'version_info' in locals() else 'ERROR', 
                  version_info['version_id'] if 'version_info' in locals() else 0, 
                  arquivo_nome, 0, usuario, 'ERROR', table_type, str(e), processing_time))
            conn.commit()
        except:
            pass  # Don't fail if logging fails
        
        # Show more helpful error message
        error_str = str(e)
        if "does not exist" in error_str:
            st.error("🔧 **Problema**: As tabelas não existem no Snowflake")
            st.info("💡 **Solução**: Vá para a página 'Snowflake' e clique em 'Criar Tabelas'")
        elif "UNIQUE constraint" in error_str:
            st.error("🔧 **Problema**: Dados duplicados detectados")
            st.info("💡 **Solução**: Verifique se os dados já foram importados para esta versão")
        
        return False 