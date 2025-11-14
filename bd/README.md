# 🗄️ Database Configuration (bd/)

This folder contains all database-related configurations for the MINIPA purchasing system.

## 📁 Folder Structure

```
bd/
├── __init__.py          # Package initialization
├── local_storage.py     # Local file storage operations
├── column_mapping.py    # Column name standardization
└── README.md           # This file
```

## 💾 Local File Storage

The system now uses local file storage instead of a cloud database. Data is stored in parquet files with version management.

### 1. **Data Directory Structure**

```
data/
├── MINIPA/
│   ├── analytics/
│   │   ├── version_1.parquet
│   │   ├── version_2.parquet
│   │   └── metadata.json
│   └── timeline/
│       ├── version_1.parquet
│       └── metadata.json
└── MINIPA_INDUSTRIA/
    └── (same structure)
```

### 2. **Usage in App**

```python
from bd.local_storage import (
    save_uploaded_data,
    load_data,
    get_versions,
    delete_version
)

# Save uploaded data
result = save_uploaded_data(
    df=df,
    empresa="MINIPA",
    table_type="ANALYTICS",
    filename="data.xlsx",
    description="Q4 2024 Update"
)

# Load data (active version)
df = load_data("MINIPA", "ANALYTICS")

# Load specific version
df = load_data("MINIPA", "ANALYTICS", version_id=2)

# Get version history
versions = get_versions("MINIPA", "ANALYTICS")

# Delete a version
result = delete_version("MINIPA", "ANALYTICS", version_id=1)
```

## 🎯 Benefits

- ✅ **No authentication required** - No database credentials needed
- ✅ **Faster loading** - Local file I/O, no network calls
- ✅ **Simpler deployment** - No database setup required
- ✅ **Data persists** - Files stored locally across sessions
- ✅ **Version history** - Full version control maintained
- ✅ **No external dependencies** - Works out of the box

## 📊 Data Flow

1. **Upload**: Excel files → Local parquet files
2. **Process**: Local files → Timeline analysis  
3. **Display**: Local files → Interactive charts
4. **Storage**: All data in local `data/` directory
