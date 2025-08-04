"""
Snowflake Connection & Configuration
Handles basic connection and configuration for MINIPA purchasing system
"""

import streamlit as st
import snowflake.connector
from snowflake.snowpark import Session

# Multi-company database schema structure
DATABASE_SCHEMA = {
    "database": "COMPRAS_MINIPA",
    "companies": ["MINIPA", "MINIPA_INDUSTRIA"],
    "schemas": {
        "ESTOQUE": "Inventory and stock data (multi-company, versioned)",
        "TIMELINE": "Purchase timeline analysis (multi-company, versioned)", 
        "ANALYTICS": "Reports and analytics (multi-company, versioned)",
        "CONFIG": "Configuration, metadata, and version control"
    },
    "versioning": {
        "enabled": True,
        "snapshot_based": True,
        "retention_days": 365
    }
}

def get_snowflake_connection():
    """Return a cached Snowflake connection or create a new one.

    The connection is stored in ``st.session_state['snowflake_conn']`` so that
    it can be reused across reruns. A new connection is established only when
    one is not cached or the cached connection has been closed.
    """

    try:
        # Verify secrets configuration
        if (
            not hasattr(st, "secrets")
            or "connections" not in st.secrets
            or "snowflake" not in st.secrets.connections
        ):
            st.error("❄️ Snowflake não configurado. Configure em .streamlit/secrets.toml")
            st.info(
                "💡 Verifique se o arquivo .streamlit/secrets.toml está configurado corretamente."
            )
            return None

        # Reuse existing connection if it's still open
        cached_conn = st.session_state.get("snowflake_conn")
        if cached_conn and not cached_conn.is_closed():
            return cached_conn

        # Otherwise create a new connection
        snowflake_config = st.secrets.connections.snowflake
        conn = snowflake.connector.connect(
            account=snowflake_config.account,
            user=snowflake_config.user,
            password=snowflake_config.password,
            role=snowflake_config.role,
            warehouse=snowflake_config.warehouse,
            database=snowflake_config.database,
            schema=snowflake_config.schema,
        )
        st.session_state["snowflake_conn"] = conn
        return conn

    except Exception as e:
        st.error(f"❄️ Erro ao conectar com Snowflake: {str(e)}")
        st.info(
            "💡 Verifique se o arquivo .streamlit/secrets.toml está configurado corretamente."
        )
        return None

def get_snowpark_session():
    """
    Get Snowpark session for advanced operations
    """
    try:
        if "connections" not in st.secrets or "snowflake" not in st.secrets.connections:
            return None
            
        snowflake_config = st.secrets.connections.snowflake
        connection_parameters = {
            "ACCOUNT": snowflake_config.account,
            "USER": snowflake_config.user,
            "PASSWORD": snowflake_config.password,
            "ROLE": snowflake_config.role,
            "WAREHOUSE": snowflake_config.warehouse,
            "DATABASE": snowflake_config.database,
            "SCHEMA": snowflake_config.schema
        }
        
        session = Session.builder.configs(connection_parameters).create()
        return session
    except Exception as e:
        st.error(f"❄️ Erro ao criar sessão Snowpark: {str(e)}")
        return None

def test_connection():
    """
    Test Snowflake connection
    Returns True if successful
    """
    conn = get_snowflake_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT CURRENT_VERSION()")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            st.success(f"✅ Conectado ao Snowflake! Versão: {version}")
            return True
        except Exception as e:
            st.error(f"❄️ Erro no teste: {str(e)}")
            return False
    return False 
