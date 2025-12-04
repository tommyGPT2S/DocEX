# Knowledge Base Service

## Overview

The Knowledge Base (KB) Service is a RAG-powered service for querying rule books (GPO Rosters, DDD Matrix, Eligibility Guides) in chargeback automation workflows.

This implementation follows the specifications in `KB_Implementation_Proposal.html` and provides:

- **RAG-Powered Querying**: Natural language queries with semantic search and LLM generation
- **Structured Data Extraction**: JSON extraction for programmatic use
- **Workflow Integration**: Processors for Steps 3, 4, and 6 of the chargeback workflow
- **Version Control**: Rule book version tracking and change management

## Architecture

```
Knowledge Base Service
├── EnhancedRAGService (FAISS/Pinecone)
├── Semantic Search Service
├── LLM Adapters (OpenAI/Claude/Local)
└── DocBasket (Document Storage)

Rule Book Processors
├── GPORosterProcessor
├── DDDMatrixProcessor
└── EligibilityGuideProcessor

Workflow Processors
├── ContractEligibilityProcessor (Step 3)
└── COTDeterminationProcessor (Step 6)
```

## Components

### 1. KnowledgeBaseService

Core service that wraps RAG capabilities for KB-specific queries.

**Key Methods:**
- `ingest_rule_book()` - Ingest rule books with vector indexing
- `query_rule_book()` - Natural language query with RAG
- `validate_contract_eligibility()` - Step 3: Contract eligibility validation
- `validate_gpo_roster()` - Step 4: GPO Roster validation
- `get_class_of_trade()` - Step 6: COT determination
- `get_rule_book_version()` - Get version information

**Location:** `docex/services/knowledge_base_service.py`

### 2. Rule Book Processors

Processors for ingesting and extracting structured data from rule books.

**Processors:**
- `RuleBookProcessor` - Base processor
- `GPORosterProcessor` - GPO Roster extraction
- `DDDMatrixProcessor` - DDD Matrix extraction
- `EligibilityGuideProcessor` - Eligibility Guide extraction

**Location:** `docex/processors/kb/`

### 3. Workflow Integration Processors

Processors that integrate KB service into the chargeback workflow.

**Processors:**
- `ContractEligibilityProcessor` - Step 3: Validates contract eligibility
- `COTDeterminationProcessor` - Step 6: Determines class-of-trade

**Location:** `docex/processors/kb/workflow_processors.py`

### 4. Prompts

YAML-based prompts for structured data extraction.

**Prompts:**
- `gpo_roster_extraction.yaml` - GPO Roster extraction
- `ddd_matrix_extraction.yaml` - DDD Matrix extraction
- `eligibility_guide_extraction.yaml` - Eligibility Guide extraction

**Location:** `docex/prompts/`

## Usage

### Basic Setup

```python
from docex.docbasket import DocBasket
from docex.processors.rag.enhanced_rag_service import EnhancedRAGService, EnhancedRAGConfig
from docex.processors.vector.semantic_search_service import SemanticSearchService
from docex.processors.llm.openai_adapter import OpenAIAdapter
from docex.services.knowledge_base_service import KnowledgeBaseService

# Initialize components
basket = DocBasket()
semantic_search = SemanticSearchService(config={...})
await semantic_search.initialize()

llm_adapter = OpenAIAdapter({...})
rag_service = EnhancedRAGService(semantic_search, llm_adapter, config)
await rag_service.initialize_vector_db()

# Create KB service
kb_service = KnowledgeBaseService(rag_service, llm_adapter, basket)
```

### Ingest Rule Books

```python
from docex.processors.kb import GPORosterProcessor

# Process and ingest GPO Roster
processor = GPORosterProcessor(config, llm_adapter)
result = await processor.process(document)

# Ingest into KB
await kb_service.ingest_rule_book(
    document=document,
    rule_book_type='gpo_roster',
    version='1.0'
)
```

### Query Rule Books

```python
# Natural language query
result = await kb_service.query_rule_book(
    question="What customers are eligible for Premier contracts?",
    rule_book_type='gpo_roster',
    extract_structured=True
)

print(result['answer'])
print(result['structured_data'])
```

### Workflow Integration

```python
from docex.processors.kb.workflow_processors import ContractEligibilityProcessor

# Step 3: Contract Eligibility
processor = ContractEligibilityProcessor(config, kb_service)
result = await processor.process(chargeback_document)

if result.metadata['eligible']:
    print("Customer is eligible - continuing workflow")
else:
    print("Routing to exception queue")
```

## Demo

Run the end-to-end demo:

```bash
python examples/kb_service_demo.py
```

The demo demonstrates:
1. Rule book ingestion
2. Natural language querying
3. Structured data extraction
4. Workflow integration (Steps 3 & 6)
5. Version tracking

## Integration with 8-Step Chargeback Workflow

The KB service integrates with the chargeback workflow at:

- **Step 3**: Contract Eligibility Validation
  - Queries: GPO Roster, Eligibility Guide
  - Processor: `ContractEligibilityProcessor`
  - Result: 99.9% eligible, 0.1% rejected

- **Step 4**: GPO Roster Validation
  - Queries: GPO Roster
  - Method: `validate_gpo_roster()`

- **Step 6**: Class-of-Trade Determination
  - Queries: DDD Matrix
  - Processor: `COTDeterminationProcessor`
  - Uses: Customer info + Federal DB results

## Configuration

### LLM Adapter

Supports multiple LLM adapters:
- OpenAI (GPT-4o, GPT-4o-mini)
- Claude (claude-3-haiku, claude-3-sonnet)
- Local LLM (Ollama)

Set environment variables:
- `OPENAI_API_KEY` for OpenAI
- `ANTHROPIC_API_KEY` for Claude
- Local LLM runs on `http://localhost:11434`

### Vector Database

Supports:
- FAISS (local, default)
- Pinecone (cloud)

Configure in `EnhancedRAGConfig`:
```python
config = EnhancedRAGConfig(
    vector_db_type='faiss',  # or 'pinecone'
    enable_hybrid_search=True
)
```

## Requirements

- DocEX platform
- EnhancedRAGService
- LLM adapter (OpenAI/Claude/Local)
- Vector database (FAISS or Pinecone)
- Semantic search service

## Files Created

### Services
- `docex/services/knowledge_base_service.py` - Core KB service

### Processors
- `docex/processors/kb/__init__.py`
- `docex/processors/kb/rule_book_processor.py` - Base processor
- `docex/processors/kb/gpo_roster_processor.py` - GPO Roster processor
- `docex/processors/kb/ddd_matrix_processor.py` - DDD Matrix processor
- `docex/processors/kb/eligibility_guide_processor.py` - Eligibility Guide processor
- `docex/processors/kb/workflow_processors.py` - Workflow integration processors

### Prompts
- `docex/prompts/gpo_roster_extraction.yaml`
- `docex/prompts/ddd_matrix_extraction.yaml`
- `docex/prompts/eligibility_guide_extraction.yaml`

### Examples
- `examples/kb_service_demo.py` - End-to-end demo

## Next Steps

1. **Production Deployment**:
   - Set up G-Drive API integration for automated rule book updates
   - Configure production vector database (Pinecone)
   - Set up monitoring and observability

2. **Enhancements**:
   - Add caching for frequent queries
   - Implement query result analytics
   - Add support for more rule book types
   - Enhance structured data extraction accuracy

3. **Testing**:
   - Unit tests for all processors
   - Integration tests for workflow
   - Performance tests for query latency
   - Accuracy tests with real production data

## References

- `KB_Implementation_Proposal.html` - Full implementation proposal
- `docs/RAG_IMPLEMENTATION_GUIDE.md` - RAG service documentation
- `docs/LLM_ADAPTERS_GUIDE.md` - LLM adapter documentation

