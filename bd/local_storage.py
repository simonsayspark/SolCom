"""
Local File Storage Module
Handles saving and loading data from local parquet files with version management
"""

import os
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import streamlit as st

# Base data directory
DATA_DIR = Path("data")

def get_data_path(empresa, table_type):
    """Get the directory path for a specific company and table type"""
    return DATA_DIR / empresa / table_type.lower()

def get_metadata_path(empresa, table_type):
    """Get the metadata JSON file path"""
    return get_data_path(empresa, table_type) / "metadata.json"

def ensure_directory(path):
    """Ensure directory exists"""
    path.mkdir(parents=True, exist_ok=True)

def load_metadata(empresa, table_type):
    """Load version metadata from JSON file"""
    metadata_path = get_metadata_path(empresa, table_type)
    
    if not metadata_path.exists():
        return []
    
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.warning(f"Erro ao carregar metadata: {str(e)}")
        return []

def save_metadata(empresa, table_type, metadata):
    """Save version metadata to JSON file"""
    metadata_path = get_metadata_path(empresa, table_type)
    
    try:
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar metadata: {str(e)}")
        return False

def save_uploaded_data(df, empresa, table_type, filename, description=""):
    """
    Save uploaded DataFrame to local parquet file with version management
    
    Args:
        df: DataFrame to save
        empresa: Company code (MINIPA, MINIPA_INDUSTRIA)
        table_type: Table type (ANALYTICS, TIMELINE)
        filename: Original filename
        description: Optional version description
        
    Returns:
        dict with success status and version_id
    """
    try:
        # Ensure directory exists
        data_path = get_data_path(empresa, table_type)
        ensure_directory(data_path)
        
        # Load existing metadata
        metadata = load_metadata(empresa, table_type)
        
        # Calculate next version_id
        if metadata:
            max_version = max(v.get('version_id', 0) for v in metadata)
            new_version_id = max_version + 1
        else:
            new_version_id = 1
        
        # Deactivate all previous versions for this company/table_type
        for v in metadata:
            v['is_active'] = False
        
        # Create new version entry
        new_version = {
            'version_id': new_version_id,
            'upload_date': datetime.now().isoformat(),
            'description': description or f"Upload {table_type} - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            'arquivo_origem': filename,
            'is_active': True,
            'row_count': len(df)
        }
        
        metadata.append(new_version)
        
        # Save parquet file
        parquet_path = data_path / f"version_{new_version_id}.parquet"
        df.to_parquet(parquet_path, index=False, engine='pyarrow')
        
        # Save metadata
        if save_metadata(empresa, table_type, metadata):
            return {
                'success': True,
                'version_id': new_version_id,
                'message': f"Dados salvos como versão {new_version_id}"
            }
        else:
            return {
                'success': False,
                'message': 'Erro ao salvar metadata'
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Erro ao salvar dados: {str(e)}'
        }

def load_data(empresa, table_type, version_id=None):
    """
    Load data from local parquet file
    
    Args:
        empresa: Company code (MINIPA, MINIPA_INDUSTRIA)
        table_type: Table type (ANALYTICS, TIMELINE)
        version_id: Specific version ID (None for active version)
        
    Returns:
        DataFrame or None
    """
    try:
        data_path = get_data_path(empresa, table_type)
        
        if version_id is None:
            # Load active version
            metadata = load_metadata(empresa, table_type)
            active_versions = [v for v in metadata if v.get('is_active', False)]
            
            if not active_versions:
                return None
            
            # Get the most recent active version
            active_version = max(active_versions, key=lambda x: x.get('version_id', 0))
            version_id = active_version['version_id']
        
        # Load parquet file
        parquet_path = data_path / f"version_{version_id}.parquet"
        
        if not parquet_path.exists():
            return None
        
        df = pd.read_parquet(parquet_path, engine='pyarrow')
        return df
        
    except Exception as e:
        st.warning(f"Erro ao carregar dados: {str(e)}")
        return None

def get_versions(empresa, table_type):
    """
    Get version history for a company and table type
    
    Args:
        empresa: Company code (MINIPA, MINIPA_INDUSTRIA)
        table_type: Table type (ANALYTICS, TIMELINE)
        
    Returns:
        List of version dictionaries, sorted by version_id descending
    """
    metadata = load_metadata(empresa, table_type)
    
    # Sort by version_id descending (newest first)
    metadata.sort(key=lambda x: x.get('version_id', 0), reverse=True)
    
    return metadata

def delete_version(empresa, table_type, version_id):
    """
    Delete a specific version
    
    Args:
        empresa: Company code
        table_type: Table type
        version_id: Version ID to delete
        
    Returns:
        dict with success status
    """
    try:
        data_path = get_data_path(empresa, table_type)
        metadata = load_metadata(empresa, table_type)
        
        # Find and remove version from metadata
        version_to_delete = None
        for v in metadata:
            if v.get('version_id') == version_id:
                version_to_delete = v
                break
        
        if not version_to_delete:
            return {
                'success': False,
                'message': f'Versão {version_id} não encontrada'
            }
        
        # Don't allow deleting active version
        if version_to_delete.get('is_active', False):
            return {
                'success': False,
                'message': 'Não é possível deletar a versão ativa'
            }
        
        # Remove from metadata
        metadata = [v for v in metadata if v.get('version_id') != version_id]
        
        # Delete parquet file
        parquet_path = data_path / f"version_{version_id}.parquet"
        if parquet_path.exists():
            parquet_path.unlink()
        
        # Save updated metadata
        if save_metadata(empresa, table_type, metadata):
            return {
                'success': True,
                'message': f'Versão {version_id} deletada com sucesso'
            }
        else:
            return {
                'success': False,
                'message': 'Erro ao salvar metadata após deleção'
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Erro ao deletar versão: {str(e)}'
        }

def get_active_version(empresa, table_type):
    """
    Get the currently active version info
    
    Args:
        empresa: Company code
        table_type: Table type
        
    Returns:
        Version dict or None
    """
    metadata = load_metadata(empresa, table_type)
    active_versions = [v for v in metadata if v.get('is_active', False)]
    
    if not active_versions:
        return None
    
    # Return the most recent active version
    return max(active_versions, key=lambda x: x.get('version_id', 0))

def get_upload_page_data(empresa):
    """
    Get all data needed for upload page display
    Similar to get_cached_upload_page_data but for local storage
    
    Returns:
        dict with stats and versions
    """
    result = {
        'stats': {
            'timeline': {'count': 0, 'latest_upload': None},
            'analytics': {'count': 0, 'latest_upload': None}
        },
        'versions_timeline': [],
        'versions_analytics': []
    }
    
    # Get timeline stats
    timeline_versions = get_versions(empresa, 'TIMELINE')
    if timeline_versions:
        active_timeline = get_active_version(empresa, 'TIMELINE')
        if active_timeline:
            df = load_data(empresa, 'TIMELINE')
            if df is not None:
                result['stats']['timeline']['count'] = len(df)
                result['stats']['timeline']['latest_upload'] = active_timeline.get('upload_date')
        result['versions_timeline'] = timeline_versions
    
    # Get analytics stats
    analytics_versions = get_versions(empresa, 'ANALYTICS')
    if analytics_versions:
        active_analytics = get_active_version(empresa, 'ANALYTICS')
        if active_analytics:
            df = load_data(empresa, 'ANALYTICS')
            if df is not None:
                result['stats']['analytics']['count'] = len(df)
                result['stats']['analytics']['latest_upload'] = active_analytics.get('upload_date')
        result['versions_analytics'] = analytics_versions
    
    return result

def check_duplicate(empresa, table_type, filename, df_hash=None):
    """
    Check if a file with the same name or hash already exists
    
    Args:
        empresa: Company code
        table_type: Table type
        filename: Filename to check
        df_hash: Optional DataFrame hash for content comparison
        
    Returns:
        dict with is_duplicate flag and version_info if duplicate
    """
    metadata = load_metadata(empresa, table_type)
    
    # Check by filename
    for v in metadata:
        if v.get('arquivo_origem') == filename:
            return {
                'is_duplicate': True,
                'version_info': v,
                'reason': 'filename'
            }
    
    # TODO: Could add content hash comparison here if needed
    
    return {
        'is_duplicate': False,
        'version_info': None
    }

