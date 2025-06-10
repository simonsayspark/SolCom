#!/usr/bin/env python3
"""
Comprehensive fix for all syntax errors in snowflake_config.py
"""

def fix_snowflake_config():
    # Read the file
    with open('bd/snowflake_config.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Apply multiple fixes in order
    fixes = [
        # Fix 1: Line 623 - return True indentation
        (
            '            """\n        return True\n        else:',
            '            """\n            return True\n        else:'
        ),
        
        # Fix 2: Fix try/except block around line 844-849
        (
            '''            else:
                cursor.execute("""
                SELECT COUNT(*) FROM ESTOQUE.PRODUTOS 
                WHERE empresa = %s AND table_type = %s AND version_id = %s
                """, version_params)
            
                total_records = cursor.fetchone()[0]
            
            except Exception as table_error:
            st.warning(f"⚠️ Erro ao verificar dados para {empresa}: {str(table_error)}")
                cursor.close()
                conn.close()
                return None''',
            '''            else:
                cursor.execute("""
                SELECT COUNT(*) FROM ESTOQUE.PRODUTOS 
                WHERE empresa = %s AND table_type = %s AND version_id = %s
                """, version_params)
            
            total_records = cursor.fetchone()[0]
            
        except Exception as table_error:
            st.warning(f"⚠️ Erro ao verificar dados para {empresa}: {str(table_error)}")
            cursor.close()
            conn.close()
            return None'''
        ),
        
        # Fix 3: Fix malformed query around line 961
        (
            '''        if version_id is None:
        query = """
        SELECT produto as "Produto", 
               estoque as "Estoque", 
               consumo_6_meses as "Consumo 6 Meses",
               media_6_meses as "Média 6 Meses", 
               estoque_cobertura as "Estoque Cobertura",
               data_upload,
                   upload_version,
                   version_id
        FROM ESTOQUE.ANALYTICS_DATA 
            WHERE empresa = %s 
            AND is_active = TRUE
        ORDER BY data_upload DESC
        """
            query_params = [empresa]''',
            '''        if version_id is None:
            query = """
            SELECT produto as "Produto", 
                   estoque as "Estoque", 
                   consumo_6_meses as "Consumo 6 Meses",
                   media_6_meses as "Média 6 Meses", 
                   estoque_cobertura as "Estoque Cobertura",
                   data_upload,
                   upload_version,
                   version_id
            FROM ESTOQUE.ANALYTICS_DATA 
            WHERE empresa = %s 
            AND is_active = TRUE
            ORDER BY data_upload DESC
            """
            query_params = [empresa]'''
        ),
    ]
    
    # Apply all fixes
    for old, new in fixes:
        content = content.replace(old, new)
    
    # Write the fixed file
    with open('bd/snowflake_config.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Applied comprehensive fixes to snowflake_config.py")

if __name__ == "__main__":
    fix_snowflake_config() 