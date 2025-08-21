"""Centralized column remapping utilities."""

COLUMN_REMAP = {
    # Price columns
    'Preço FOB\nUnitário': 'Preco_Unitario',
    'Preço FOB Unitário': 'Preco_Unitario',
    'Preco FOB Unitario': 'Preco_Unitario',
    'Preço Unitário': 'Preco_Unitario',
    'Preço FOB': 'Preco_Unitario',
    'Preço Unit.': 'Preco_Unitario',
    'Price': 'Preco_Unitario',
    'preco_unitario': 'Preco_Unitario',

    # Standard columns
    'Fornecedor\n': 'Fornecedor',
    'QTD\n': 'QTD',
    'Modelo\n': 'Modelo',
    'Estoque Total': 'Estoque_Total',
    'Estoque Total\n': 'Estoque_Total',
    'Estoque\nTotal': 'Estoque_Total',
    'Estoque\nTotal ': 'Estoque_Total',
    'Estoque\r\nTotal': 'Estoque_Total',
    'In Transit\n': 'In_Transit',
    'In\nTransit': 'In_Transit',
    'Avg Sales\n': 'Vendas_Medias',
    'Avg Sales': 'Vendas_Medias',
    'Vendas Médias': 'Vendas_Medias',
    'CBM\n': 'CBM',
    'MOQ\n': 'MOQ',

    # Analytics specific columns
    'Estoque Cobertura': 'Estoque_Cobertura',
    'Consumo 6 Meses': 'Consumo_6_Meses',
    'Média 6 Meses': 'Media_6_Meses',
    'UltimoFor': 'ultimo_fornecedor',
    'UltimoFornecedor': 'ultimo_fornecedor',

    # New analytics backlog columns
    'Carteira': 'Carteira',
    'carteira': 'Carteira',
    'Carteira-Estoque': 'Carteira_Estoque',
    'carteira-estoque': 'Carteira_Estoque',
    'Carteira_Estoque': 'Carteira_Estoque',
    'carteira_estoque': 'Carteira_Estoque',
    'Estoque - Carteira': 'Estoque_Menos_Carteira',

    # Forecast columns
    'Previsão Total com New PO': 'Previsao_Total_New_Pos',
    'Previsão Total com New POs': 'Previsao_Total_New_Pos',
    'Previsão Total': 'Previsao_Total_New_Pos',
    'Previsao Total': 'Previsao_Total_New_Pos',
    'Previsão': 'Previsao',

    # Priority analysis columns
    'produto': 'Produto',
    'Qtde Embarque': 'Qtde_Embarque',
    'Compras Até 30 Dias': 'Compras_Ate_30_Dias',
    'Compras 31 a 60 Dias': 'Compras_31_60_Dias',
    'Compras 61 a 90 Dias': 'Compras_61_90_Dias',
    'Compras > 90 Dias': 'Compras_Mais_90_Dias',
    'Qtde Tot Compras': 'Qtde_Tot_Compras',


        # Enhanced price column mappings
    'Preço FOB\nUnitário': 'Preco_Unitario',
    'Preço FOB Unitário': 'Preco_Unitario',
    'Preco FOB Unitario': 'Preco_Unitario',
    'Preço Unitário': 'Preco_Unitario',
    'Preço FOB': 'Preco_Unitario',
    'Preço Unit.': 'Preco_Unitario',
    'Price': 'Preco_Unitario',
    'preco_unitario': 'Preco_Unitario',
    'Preço FOB Unit': 'Preco_Unitario',  # Add this
    'FOB Unit': 'Preco_Unitario',        # Add this
    
    # Enhanced CBM mappings
    'CBM\n': 'CBM',
    'CBM ': 'CBM',
    'cbm': 'CBM',  # Add this
}


def apply_column_remap(df):
    """Rename columns in *df* using COLUMN_REMAP.

    Returns the updated dataframe and a list of (old, new) tuples for
    the applied mappings.
    """
    original_cols = list(df.columns)
    existing = set(original_cols)
    target_cols = set()
    safe_rename = {}

    for old, new in COLUMN_REMAP.items():
        if old in existing:
            if new not in existing or old == new:
                if new not in target_cols:
                    safe_rename[old] = new
                    target_cols.add(new)

    if safe_rename:
        df = df.rename(columns=safe_rename)

    # Remove duplicated columns if renaming created any
    if len(df.columns) != len(set(df.columns)):
        df = df.loc[:, ~df.columns.duplicated()]

    changes = [(o, n) for o, n in safe_rename.items() if o != n]
    return df, changes
