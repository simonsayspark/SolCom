# 🗄️ Database Configuration (bd/)

This folder contains all database-related configurations for the MINIPA purchasing system.

## 📁 Folder Structure

```
bd/
├── __init__.py          # Package initialization
├── snowflake_config.py  # Snowflake connection and operations
└── README.md           # This file
```

## ❄️ Snowflake Setup

### 1. **Database Schema** (Recommended)
```sql
-- Main database
CREATE DATABASE COMPRAS_MINIPA;

-- Schemas
CREATE SCHEMA COMPRAS_MINIPA.ESTOQUE;      -- Inventory data
CREATE SCHEMA COMPRAS_MINIPA.TIMELINE;     -- Purchase timeline
CREATE SCHEMA COMPRAS_MINIPA.ANALYTICS;    -- Reports
CREATE SCHEMA COMPRAS_MINIPA.CONFIG;       -- Configuration
```

### 2. **Configuration File**
Create `.streamlit/secrets.toml` with your credentials:

```toml
[snowflake]
account = "your-organization-your-account"
user = "your_username"
password = "your_password"
role = "SYSADMIN"
warehouse = "COMPUTE_WH"
database = "COMPRAS_MINIPA"
schema = "ESTOQUE"
```

### 3. **Usage in App**
```python
from bd.snowflake_config import (
    test_connection,
    upload_excel_to_snowflake, 
    load_data_from_snowflake,
    create_tables
)

# Test connection
if test_connection():
    # Upload Excel data
    success = upload_excel_to_snowflake(df, "filename.xlsx")
    
    # Load data back
    df = load_data_from_snowflake()
```

## 🔒 Security Features

- ✅ **Credentials never in code** - Uses Streamlit secrets
- ✅ **Encrypted connections** - All data encrypted in transit
- ✅ **Role-based access** - Control who sees what
- ✅ **Audit trail** - Track all uploads and changes
- ✅ **Data isolation** - User-specific data separation

## 📊 Data Flow

1. **Upload**: Excel files → Snowflake tables
2. **Process**: Snowflake → Timeline analysis  
3. **Display**: Snowflake → Interactive charts
4. **Secure**: All data in cloud, zero local storage

## 🎯 Benefits

- **No more Excel files in repository**
- **Team collaboration** - Multiple users, same data
- **Version control** - Track data changes over time
- **Scalability** - Handle large datasets efficiently
- **Security** - Enterprise-grade data protection 