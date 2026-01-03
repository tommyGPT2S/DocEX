# DocEX Dependency Optimization

## Overview

DocEX has been optimized to support lightweight installations without heavy dependencies. The package now uses optional dependency groups, allowing users to install only what they need.

## Installation Options

### Lightweight Base Installation (Recommended for Basic Use)

```bash
pip install docex
```

This installs only the core dependencies:
- `sqlalchemy` - Database ORM
- `pyyaml` - Configuration management
- `pydantic` - Data validation
- `python-dotenv` - Environment variable management
- `click` - CLI framework
- `jinja2` - Template engine
- `python-docx` - Word document processing

**Note**: This base installation uses SQLite by default and does not include:
- PostgreSQL support
- Vector indexing/semantic search
- LLM/embedding capabilities
- S3 storage
- HTTP/SFTP transport
- PDF processing

### Full Installation (All Features)

```bash
pip install docex[all]
```

This installs all optional dependencies including:
- PostgreSQL support (`psycopg2-binary`)
- Vector indexing (`numpy`, `pgvector`)
- LLM support (`openai`)
- S3 storage (`boto3`)
- HTTP transport (`aiohttp`)
- SFTP transport (`paramiko`)
- PDF processing (`pdfminer.six`)

### Selective Installation

Install only the features you need:

```bash
# PostgreSQL support
pip install docex[postgres]

# Vector indexing and semantic search
pip install docex[vector]

# LLM/Embedding support
pip install docex[llm]

# S3 storage
pip install docex[storage-s3]

# HTTP transport
pip install docex[transport-http]

# SFTP transport
pip install docex[transport-sftp]

# PDF processing
pip install docex[pdf]

# Combine multiple features
pip install docex[postgres,vector,llm]
```

## Database Schema Files

The database schema files (`schema.sql` and migration files) are now included in the PyPI package and accessible after installation. The code automatically locates these files using:

```python
from pathlib import Path
schema_path = Path(__file__).parent / "schema.sql"
```

This ensures that database initialization works correctly whether installed from PyPI or run from source.

## Graceful Error Handling

The codebase now handles missing optional dependencies gracefully:

### Storage Backends

```python
from docex.storage.storage_factory import StorageFactory

# S3 storage will raise a helpful error if boto3 is not installed
try:
    storage = StorageFactory.create_storage({'type': 's3', ...})
except ValueError as e:
    # Error message: "S3 storage requires 'boto3' package. Install it with: pip install docex[storage-s3]"
    print(e)
```

### Transport Methods

```python
from docex.transport.transporter_factory import TransporterFactory

# HTTP/SFTP transports will raise helpful errors if dependencies are missing
try:
    transporter = TransporterFactory.create_transporter(http_config)
except ValueError as e:
    # Error message includes installation instructions
    print(e)
```

### Database Types

```python
from docex.db.database_factory import DatabaseFactory

# PostgreSQL will raise a helpful error if psycopg2-binary is not installed
try:
    db = DatabaseFactory.create_database(config)  # config.type = 'postgres'
except ValueError as e:
    # Error message: "PostgreSQL support requires 'psycopg2-binary' package. Install it with: pip install docex[postgres]"
    print(e)
```

### PDF Processing

```python
from docex.processors.pdf_to_text import PDFToTextProcessor

# PDF processing will raise a helpful error if pdfminer.six is not installed
try:
    processor = PDFToTextProcessor(config)
    result = processor.process(document)
except ImportError as e:
    # Error message includes installation instructions
    print(e)
```

### Vector Operations

Vector operations (numpy) are already handled gracefully with try/except blocks:

```python
# In semantic_search_service.py
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    # Falls back to pure Python cosine similarity
```

## Migration Guide

### For Existing Users

If you're upgrading from a previous version, you may need to install optional dependencies:

```bash
# If you use PostgreSQL
pip install docex[postgres]

# If you use vector indexing
pip install docex[vector,llm]

# If you use S3 storage
pip install docex[storage-s3]

# If you use HTTP/SFTP transport
pip install docex[transport-http,transport-sftp]

# If you process PDFs
pip install docex[pdf]
```

### For New Users

Start with the lightweight base installation and add optional dependencies as needed:

```bash
# Start minimal
pip install docex

# Add features as you need them
pip install docex[postgres]  # When you need PostgreSQL
pip install docex[vector,llm]  # When you need semantic search
```

## Dependency Groups Summary

| Group | Dependencies | Use Case |
|-------|-------------|----------|
| `postgres` | `psycopg2-binary>=2.9.0` | PostgreSQL database support |
| `vector` | `numpy>=1.24.0`, `pgvector>=0.2.0` | Vector indexing and semantic search |
| `llm` | `openai>=1.0.0` | LLM/embedding capabilities |
| `storage-s3` | `boto3>=1.26.0` | Amazon S3 storage backend |
| `transport-http` | `aiohttp>=3.9.0` | HTTP transport method |
| `transport-sftp` | `paramiko>=3.4.0` | SFTP transport method |
| `pdf` | `pdfminer.six>=20221105` | PDF text extraction |
| `all` | All above dependencies | Full feature set |
| `dev` | `pytest`, `moto`, `black`, `isort`, `mypy` | Development tools |

## Benefits

1. **Reduced Installation Size**: Base installation is much lighter (~10MB vs ~100MB+)
2. **Faster Installation**: Fewer dependencies to download and install
3. **Clearer Dependencies**: Users only install what they need
4. **Better Error Messages**: Helpful installation instructions when optional features are used
5. **Schema Files Included**: Database initialization works out of the box from PyPI

## Testing

To test the lightweight installation:

```bash
# Create a fresh virtual environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install base package only
pip install docex

# Test basic functionality
python -c "from docex import DocEX; print('Base installation works!')"

# Try using optional features (should get helpful errors)
python -c "from docex.db.database_factory import DatabaseFactory; from docex.config.config_manager import ConfigManager; config = ConfigManager(); config.set('database.type', 'postgres'); DatabaseFactory.create_database(config)"
```

