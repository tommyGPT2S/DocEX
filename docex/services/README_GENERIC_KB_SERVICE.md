# Generic Knowledge Base Service

## Overview

The Generic Knowledge Base Service is a **domain-agnostic** RAG-powered service for building knowledge bases on top of DocEX. Unlike the domain-specific Knowledge Base Service (which is tailored for chargeback automation), this service can be configured for **any document type and use case**.

## Key Features

- **Domain-Agnostic**: Works with any document type (policies, contracts, guides, specifications, etc.)
- **RAG-Powered Querying**: Natural language queries with semantic search and LLM generation
- **Structured Data Extraction**: Configurable JSON extraction schemas for different document types
- **Version Control**: Document version tracking and change management
- **Configurable**: Define your own document types and extraction schemas
- **Built on DocEX**: Leverages DocEX's RAG, storage, and processing capabilities

## Architecture

```
Generic Knowledge Base Service
├── EnhancedRAGService (FAISS/Pinecone)
├── Semantic Search Service
├── LLM Adapters (OpenAI/Claude/Local)
└── DocBasket (Document Storage)

Generic KB Processor
├── Document type detection (optional)
├── Structured data extraction (configurable)
└── Metadata enrichment
```

## Components

### 1. GenericKnowledgeBaseService

Core service that provides generic knowledge base capabilities.

**Key Methods:**
- `ingest_document()` - Ingest documents with vector indexing
- `query()` - Natural language query with RAG
- `search()` - Semantic search across documents
- `list_documents()` - List all documents in knowledge base
- `get_document_version()` - Get version information for document type

**Location:** `docex/services/generic_knowledge_base_service.py`

### 2. GenericKBProcessor

Generic processor for ingesting documents into the knowledge base.

**Features:**
- Automatic document type detection (optional)
- Configurable structured data extraction
- Metadata enrichment

**Location:** `docex/processors/kb/generic_kb_processor.py`

## Usage

### Basic Setup

```python
from docex import DocEX
from docex.processors.rag.enhanced_rag_service import EnhancedRAGService, EnhancedRAGConfig
from docex.processors.vector.semantic_search_service import SemanticSearchService
from docex.processors.llm.openai_adapter import OpenAIAdapter
from docex.services.generic_knowledge_base_service import GenericKnowledgeBaseService

# Initialize DocEX
docEX = DocEX()
basket = docEX.create_basket('kb_documents')

# Initialize components
semantic_search = SemanticSearchService(doc_ex=docEX, llm_adapter=llm_adapter, ...)
await semantic_search.initialize()

llm_adapter = OpenAIAdapter({...})
rag_service = EnhancedRAGService(semantic_search, llm_adapter, config)
await rag_service.initialize_vector_db()

# Configure KB service
kb_config = {
    'document_types': {
        'policy': {'description': 'Company policies'},
        'contract': {'description': 'Legal contracts'},
        'guide': {'description': 'User guides'}
    },
    'extraction_schemas': {
        'policy': {
            'description': 'Extract policy information',
            'fields': ['title', 'summary', 'key_points', 'effective_date']
        }
    }
}

# Create KB service
kb_service = GenericKnowledgeBaseService(
    rag_service=rag_service,
    llm_adapter=llm_adapter,
    basket=basket,
    config=kb_config
)
```

### Ingest Documents

```python
# Add document to basket
document = basket.add('policy_document.pdf')

# Ingest into knowledge base
await kb_service.ingest_document(
    document=document,
    doc_type='policy',
    version='1.0',
    extract_structured=True
)
```

### Query Knowledge Base

```python
# Natural language query
result = await kb_service.query(
    question="What is the refund policy?",
    doc_type='policy',  # Optional: filter by document type
    extract_structured=True
)

print(result['answer'])
print(result['structured_data'])
print(f"Confidence: {result['confidence_score']}")
```

### Semantic Search

```python
# Search across documents
results = await kb_service.search(
    query="refund procedures",
    doc_type='policy',  # Optional: filter by type
    top_k=10
)

for result in results:
    print(f"{result['document_name']}: {result['similarity_score']:.3f}")
```

### List Documents

```python
# List all documents
docs = await kb_service.list_documents(doc_type='policy')

for doc in docs:
    print(f"{doc['name']} ({doc['type']}, v{doc['version']})")
```

## Configuration

### Document Types

Define the types of documents your knowledge base will contain:

```python
document_types = {
    'policy': {
        'description': 'Company policies and guidelines'
    },
    'contract': {
        'description': 'Legal contracts and agreements'
    },
    'guide': {
        'description': 'User guides and manuals'
    }
}
```

### Extraction Schemas

Define how structured data should be extracted from each document type:

```python
extraction_schemas = {
    'policy': {
        'description': 'Extract policy information',
        'fields': ['title', 'summary', 'key_points', 'effective_date', 'policy_number']
    },
    'contract': {
        'description': 'Extract contract information',
        'fields': ['parties', 'effective_date', 'expiry_date', 'key_terms', 'contract_value']
    }
}
```

### Full Configuration Example

```python
kb_config = {
    'document_types': {
        'policy': {'description': 'Company policies'},
        'contract': {'description': 'Legal contracts'},
        'guide': {'description': 'User guides'},
        'specification': {'description': 'Technical specifications'}
    },
    'extraction_schemas': {
        'policy': {
            'description': 'Extract policy information',
            'fields': ['title', 'summary', 'key_points', 'effective_date']
        },
        'contract': {
            'description': 'Extract contract information',
            'fields': ['parties', 'effective_date', 'expiry_date', 'key_terms']
        }
    },
    'default_extraction_schema': {
        'description': 'Extract key information from document',
        'fields': ['summary', 'key_points', 'metadata']
    }
}
```

## Using the Generic KB Processor

The processor can be used independently or as part of a processing pipeline:

```python
from docex.processors.kb.generic_kb_processor import GenericKBProcessor

# Create processor
processor = GenericKBProcessor(
    config={
        'doc_type': 'policy',  # or None for auto-detection
        'extract_structured': True,
        'extraction_schema': {
            'description': 'Extract policy information',
            'fields': ['title', 'summary', 'key_points']
        }
    },
    llm_processor=llm_adapter
)

# Process document
result = await processor.process(document)

if result.success:
    print(f"Extracted data: {result.metadata.get('extracted_data')}")
```

## Use Cases

The Generic Knowledge Base Service can be used for:

1. **Company Knowledge Base**: Policies, procedures, guides
2. **Legal Document Management**: Contracts, agreements, terms
3. **Technical Documentation**: Specifications, API docs, manuals
4. **Compliance Documentation**: Regulations, standards, requirements
5. **Customer Support**: FAQs, troubleshooting guides, product docs
6. **Research Knowledge Base**: Papers, articles, reference materials

## Comparison: Generic vs Domain-Specific KB Service

| Feature | Generic KB Service | Domain-Specific KB Service |
|---------|-------------------|---------------------------|
| **Domain** | Any | Chargeback automation (pharma) |
| **Document Types** | Configurable | Fixed (GPO Roster, DDD Matrix, etc.) |
| **Extraction Schemas** | Configurable | Fixed schemas |
| **Workflow Integration** | Generic | Specific workflow steps |
| **Use Case** | General knowledge base | Rule book querying |

## Examples

See `examples/generic_kb_example.py` for a complete working example.

## Requirements

- DocEX platform
- EnhancedRAGService
- LLM adapter (OpenAI/Claude/Local)
- Vector database (FAISS, Pinecone, or memory)
- Semantic search service

## Next Steps

1. **Customize for Your Domain**: Define document types and extraction schemas for your use case
2. **Production Deployment**: Configure production vector database (Pinecone, pgvector)
3. **Integration**: Integrate with your business workflows
4. **Monitoring**: Set up logging and monitoring for query performance

## References

- `docs/RAG_IMPLEMENTATION_GUIDE.md` - RAG service documentation
- `docs/LLM_ADAPTERS_GUIDE.md` - LLM adapter documentation
- `docex/services/README_KB_SERVICE.md` - Domain-specific KB service (for comparison)

