# DocEX

<!-- Badges -->
![License](https://img.shields.io/github/license/tommyGPT2S/DocEX)
![Python](https://img.shields.io/pypi/pyversions/docex)
![Build](https://github.com/tommyGPT2S/DocEX/actions/workflows/ci.yml/badge.svg)
<!-- Add PyPI badge here when ready -->

![DocEX Architecture](docs/DocEX_Architecture.jpeg)

**DocEX** is a robust, extensible document management and transport system for Python. It supports multiple storage backends, metadata management, and operation tracking, with a unified API for local, SFTP, HTTP, and other protocols. **Version 2.2.0** introduces database-level multi-tenancy, enhanced security with UserContext, and LLM-powered document processing capabilities.

## Features

- 📁 Document storage and metadata management
- 🔄 Transport layer with pluggable protocols (local, SFTP, HTTP, etc.)
- 🛣️ Configurable transport routes and routing rules
- 📝 Operation and audit tracking
- 🧩 Extensible architecture for new protocols and workflows
- 🤖 **LLM adapter integration** - Process documents with OpenAI and other LLM providers
- 📋 **Prompt management** - YAML-based prompt templates with Jinja2 support
- 🔍 **Structured data extraction** - Extract structured data from documents using LLMs
- 📊 **Vector indexing & semantic search** - Generate embeddings and perform similarity search
- 🔎 **RAG support** - Build retrieval-augmented generation applications
- ☁️ **S3 storage support** - Store documents in Amazon S3
- 🏢 **Multi-tenancy support** - Database-level isolation for secure multi-tenant deployments
- 🔐 **Enhanced security** - UserContext for audit logging and tenant routing

## Installation

Install from PyPI:

```sh
pip install docex
```

### Optional Dependencies

For PDF processing features:
```sh
pip install pdfminer.six
```

For LLM features (included by default in 2.2.0+):
- `openai>=1.0.0` - OpenAI API integration
- `jinja2>=3.1.0` - Prompt templating

## Quick Start

Before using DocEX in your code, you must initialize the system using the CLI:

```sh
# Run this once to set up configuration and database
$ docex init
```

Then you can use the Python API (minimal example):

```python
from docex import DocEX
from pathlib import Path

# Create DocEX instance (will check initialization internally)
docEX = DocEX()

# Create a basket
basket = docEX.create_basket('mybasket')

# Create a simple text file
hello_file = Path('hello.txt')
hello_file.write_text('Hello scos.ai!')

# Add the document to the basket
doc = basket.add(str(hello_file))

# Print document details
print(doc.get_details())

hello_file.unlink()
```

### Security and Multi-Tenancy

DocEX 2.2.0+ includes enhanced security features and multi-tenancy support:

```python
from docex import DocEX
from docex.context import UserContext

# Create UserContext for audit logging and multi-tenancy
user_context = UserContext(
    user_id="alice",
    user_email="alice@example.com",
    tenant_id="tenant1",  # For multi-tenant applications
    roles=["admin"]
)

# Initialize DocEX with UserContext (enables audit logging)
docEX = DocEX(user_context=user_context)

# All operations are logged with user context
basket = docEX.create_basket("invoices")
```

**Multi-Tenancy Models:**
- **Database-Level Isolation** (Model B) - Each tenant has separate database/schema (✅ Implemented in 2.2.0)
- **Row-Level Isolation** (Model A) - Shared database with tenant_id columns (Proposed)

See [Multi-Tenancy Guide](docs/MULTI_TENANCY_GUIDE.md) and [Security Best Practices](examples/SECURITY_BEST_PRACTICES.md) for details.

### LLM-Powered Document Processing

DocEX 2.2.0+ includes LLM adapters for intelligent document processing:

```python
from docex import DocEX
from docex.processors.llm import OpenAIAdapter
import asyncio
import os

# Initialize DocEX
docEX = DocEX()

# Create a basket
basket = docEX.create_basket('my_basket')

# Add a document
document = basket.add('invoice.pdf', metadata={'biz_doc_type': 'invoice'})

# Create LLM adapter
adapter = OpenAIAdapter({
    'api_key': os.getenv('OPENAI_API_KEY'),
    'model': 'gpt-4o',
    'prompt_name': 'invoice_extraction',  # Uses prompts from docex/prompts/
    'generate_summary': True,
    'generate_embedding': True
})

# Process document with LLM
result = await adapter.process(document)

if result.success:
    # Access extracted data
    metadata = document.get_metadata_dict()
    print(f"Invoice Number: {metadata.get('invoice_number')}")
    print(f"Total Amount: {metadata.get('total_amount')}")
    print(f"Summary: {metadata.get('llm_summary')}")
```

**Available Prompts:**
- `invoice_extraction` - Extract invoice data (number, amounts, dates, line items)
- `product_extraction` - Extract product information
- `document_summary` - Generate document summaries
- `generic_extraction` - Generic structured data extraction

**Custom Prompts:**
Create your own prompt files in YAML format in `docex/prompts/`:

```yaml
name: my_custom_prompt
description: Custom extraction prompt
version: 1.0

system_prompt: |
  You are an expert data extraction system.
  Extract the following information...

user_prompt_template: |
  Please extract data from this text:
  
  {{ text }}
```

### Vector Indexing and Semantic Search

DocEX 2.2.0+ includes vector indexing and semantic search capabilities:

```python
from docex import DocEX
from docex.processors.llm import OpenAIAdapter
from docex.processors.vector import VectorIndexingProcessor, SemanticSearchService
import asyncio

# Initialize DocEX
docEX = DocEX()
basket = docEX.create_basket('my_basket')

# Add and index documents
document = basket.add('document.pdf')

# Create vector indexing processor
llm_adapter = OpenAIAdapter({
    'api_key': os.getenv('OPENAI_API_KEY'),
    'model': 'gpt-4o'
})

vector_processor = VectorIndexingProcessor({
    'llm_adapter': llm_adapter,
    'vector_db_type': 'memory'  # Use 'pgvector' for production
})

# Index document
await vector_processor.process(document)

# Perform semantic search
search_service = SemanticSearchService(
    doc_ex=docEX,
    llm_adapter=llm_adapter,
    vector_db_type='memory',
    vector_db_config={'vectors': vector_processor.vector_db['vectors']}
)

results = await search_service.search(
    query="What is machine learning?",
    top_k=5
)

for result in results:
    print(f"{result.document.name}: {result.similarity_score:.4f}")
```

**Vector Database Options:**
- **Memory** - For testing/development (no setup required)
- **pgvector** - PostgreSQL extension (recommended for production, handles up to 100M vectors)

See [Vector Search Guide](docs/VECTOR_SEARCH_GUIDE.md) for detailed documentation.

Additional examples can be found in the `examples/` folder.

## Configuration

Configure routes and storage in `default_config.yaml`:

```yaml
transport_config:
  routes:
    - name: local_backup
      purpose: backup
      protocol: local
      config:
        type: local
        name: local_backup_transport
        base_path: /path/to/backup
        create_dirs: true
      can_upload: true
      can_download: true
      enabled: true
  default_route: local_backup
```

## Documentation

- [Developer Guide](docs/Developer_Guide.md)
- [Design Document](docs/DocEX_Design.md)
- [Multi-Tenancy Guide](docs/MULTI_TENANCY_GUIDE.md)
- [Security Best Practices](examples/SECURITY_BEST_PRACTICES.md)
- [LLM Adapter Implementation](docs/LLM_ADAPTER_IMPLEMENTATION.md)
- [LLM Adapter Proposal](docs/LLM_ADAPTER_PROPOSAL.md)
- [Vector Search Guide](docs/VECTOR_SEARCH_GUIDE.md)
- [API Reference](docs/API_Reference.md)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT License](LICENSE)
