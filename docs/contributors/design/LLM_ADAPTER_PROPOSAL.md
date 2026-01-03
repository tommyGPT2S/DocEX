# LLM Provider Adapter Proposal for DocEX

## Executive Summary

This document proposes building LLM provider adapters that integrate seamlessly with DocEX's existing processor architecture. The adapters will enable LLM-powered document processing while leveraging DocEX's built-in features for operation tracking, metadata management, and event logging.

---

## 1. Current DocEX Capabilities to Leverage

### 1.1 Built-in Features We Should Use More

**Document Management:**
- ✅ Document storage (S3/filesystem)
- ✅ Metadata management (flexible key-value)
- ✅ Document operations tracking
- ✅ File history tracking
- ✅ Duplicate detection
- ✅ Event tracking (DocEvent)

**Processing Infrastructure:**
- ✅ Processor registration system
- ✅ Processor factory
- ✅ Processing operation tracking
- ✅ Operation dependencies
- ✅ Status tracking

**Basket Organization:**
- ✅ Per-basket storage configuration
- ✅ Basket-level metadata
- ✅ Document grouping

**Services:**
- ✅ MetadataService - Rich metadata management
- ✅ DocumentService - Document lifecycle management
- ✅ StorageService - Storage abstraction

---

## 2. Proposed LLM Adapter Architecture

### 2.1 LLM Adapter Design

Instead of building separate services, we should build **LLM adapters that integrate with DocEX's processor system**. This leverages DocEX's existing infrastructure.

```
┌─────────────────────────────────────────────────────────────┐
│                    DocEX Processor Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  LLM Adapter │  │  LLM Adapter │  │  LLM Adapter │       │
│  │  (OpenAI)    │  │  (Anthropic) │  │  (Local)     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            │                                 │
│                    ┌───────▼────────┐                        │
│                    │  BaseLLMAdapter │                        │
│                    │  (Abstract)     │                        │
│                    └───────┬────────┘                        │
│                            │                                 │
│                    ┌───────▼────────┐                        │
│                    │  BaseProcessor  │                        │
│                    │  (DocEX)        │                        │
│                    └─────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    DocEX Core Services                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Metadata    │  │  Operations  │  │  Events      │       │
│  │  Service     │  │  Tracking    │  │  Tracking    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Implementation Plan

### 3.1 Base LLM Adapter

Create an abstract base class that extends `BaseProcessor`:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document

class BaseLLMAdapter(BaseProcessor):
    """
    Base class for LLM provider adapters
    
    Extends DocEX's BaseProcessor to integrate LLM capabilities
    while leveraging DocEX's operation tracking and metadata management.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider = config.get('provider', 'openai')
        self.model = config.get('model', 'gpt-4')
        self.api_key = config.get('api_key') or os.getenv(f'{self.provider.upper()}_API_KEY')
        self.client = self._initialize_client()
    
    @abstractmethod
    def _initialize_client(self):
        """Initialize LLM client"""
        pass
    
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        pass
    
    @abstractmethod
    def generate_completion(self, prompt: str, **kwargs) -> str:
        """Generate text completion"""
        pass
    
    def process(self, document: Document) -> ProcessingResult:
        """
        Process document using LLM
        
        This method is called by DocEX's processor system.
        It automatically tracks operations and metadata.
        """
        try:
            # Record processing start
            operation = self._record_operation(
                document,
                status='in_progress',
                input_metadata={'document_id': document.id, 'document_type': document.document_type}
            )
            
            # Get document content
            text_content = self.get_document_text(document)
            
            # Process with LLM (subclass implements this)
            result = self._process_with_llm(document, text_content)
            
            # Update metadata
            if result.metadata:
                from docex.services.metadata_service import MetadataService
                metadata_service = MetadataService()
                metadata_service.update_metadata(document.id, result.metadata)
            
            # Record success
            self._record_operation(
                document,
                status='success',
                output_metadata=result.metadata_dict()
            )
            
            return result
            
        except Exception as e:
            # Record failure
            self._record_operation(
                document,
                status='failed',
                error=str(e)
            )
            return ProcessingResult(success=False, error=str(e))
    
    @abstractmethod
    def _process_with_llm(self, document: Document, text: str) -> ProcessingResult:
        """Subclass implements LLM processing logic"""
        pass
```

### 3.2 Provider-Specific Adapters

#### A. OpenAI Adapter

```python
import openai
from typing import List, Dict, Any
from .base_llm_adapter import BaseLLMAdapter
from docex.processors.base import ProcessingResult

class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI provider adapter"""
    
    def _initialize_client(self):
        return openai.OpenAI(api_key=self.api_key)
    
    def generate_embedding(self, text: str, model: str = "text-embedding-3-large") -> List[float]:
        """Generate embedding using OpenAI"""
        response = self.client.embeddings.create(
            model=model,
            input=text
        )
        return response.data[0].embedding
    
    def generate_completion(self, prompt: str, model: str = None, **kwargs) -> str:
        """Generate completion using OpenAI"""
        model = model or self.model
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return response.choices[0].message.content
    
    def _process_with_llm(self, document: Document, text: str) -> ProcessingResult:
        """Process document with OpenAI"""
        # Extract structured data
        extraction_prompt = self._build_extraction_prompt(text)
        extracted_data = self.generate_completion(extraction_prompt)
        
        # Generate summary
        summary_prompt = f"Summarize the following document:\n\n{text[:2000]}"
        summary = self.generate_completion(summary_prompt)
        
        # Generate embedding
        embedding = self.generate_embedding(text)
        
        return ProcessingResult(
            success=True,
            content=text,
            metadata={
                'extracted_data': extracted_data,
                'summary': summary,
                'embedding': embedding,
                'llm_provider': 'openai',
                'llm_model': self.model
            }
        )
    
    def _build_extraction_prompt(self, text: str) -> str:
        """Build prompt for data extraction"""
        return f"""Extract structured information from the following document.
Return JSON format with keys: participants, topics, action_items, sentiment, key_points.

Document:
{text[:4000]}
"""
```

#### B. Anthropic Adapter

```python
import anthropic
from .base_llm_adapter import BaseLLMAdapter

class AnthropicAdapter(BaseLLMAdapter):
    """Anthropic Claude provider adapter"""
    
    def _initialize_client(self):
        return anthropic.Anthropic(api_key=self.api_key)
    
    def generate_embedding(self, text: str) -> List[float]:
        """Anthropic doesn't have embeddings API, use OpenAI or Cohere"""
        # Fallback to OpenAI for embeddings
        import openai
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.embeddings.create(
            model="text-embedding-3-large",
            input=text
        )
        return response.data[0].embedding
    
    def generate_completion(self, prompt: str, **kwargs) -> str:
        """Generate completion using Claude"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=kwargs.get('max_tokens', 1024),
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
```

#### C. Local LLM Adapter (Ollama, etc.)

```python
from .base_llm_adapter import BaseLLMAdapter

class LocalLLMAdapter(BaseLLMAdapter):
    """Local LLM adapter (Ollama, etc.)"""
    
    def _initialize_client(self):
        # Initialize local LLM client
        return self._setup_local_llm()
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using local model"""
        # Use local embedding model
        pass
    
    def generate_completion(self, prompt: str, **kwargs) -> str:
        """Generate completion using local model"""
        # Use local LLM
        pass
```

---

## 4. Leveraging DocEX Features

### 4.1 Use DocEX's Operation Tracking

**Instead of building custom tracking, use DocEX's built-in operation tracking:**

```python
class LLMProcessor(BaseLLMAdapter):
    def process(self, document: Document) -> ProcessingResult:
        # DocEX automatically tracks operations via _record_operation
        # No need to build custom tracking!
        return super().process(document)
```

**Benefits:**
- Automatic operation logging
- Status tracking (in_progress, success, failed)
- Error tracking
- Operation dependencies
- All stored in DocEX database

### 4.2 Use DocEX's Metadata System

**Store LLM results as metadata:**

```python
# After LLM processing
metadata_service = MetadataService()
metadata_service.update_metadata(document.id, {
    'llm_summary': summary,
    'llm_extracted_data': extracted_data,
    'llm_embedding': embedding,  # Store as JSON
    'llm_provider': 'openai',
    'llm_model': 'gpt-4',
    'llm_processed_at': datetime.now().isoformat()
})
```

**Benefits:**
- Searchable metadata
- Query by LLM results
- Track processing history
- Link related documents

### 4.3 Use DocEX's Event System

**Track LLM processing events:**

```python
from docex.db.models import DocEvent

# DocEX automatically creates events for operations
# But you can also create custom events:
event = DocEvent(
    basket_id=document.basket_id,
    document_id=document.id,
    event_type='LLM_PROCESSED',
    data={
        'provider': 'openai',
        'model': 'gpt-4',
        'summary': summary,
        'extracted_data': extracted_data
    }
)
```

### 4.4 Use DocEX's Basket Organization

**Organize by customer using baskets:**

```python
# One basket per customer
customer_basket = docEX.create_basket(
    f"customer_{customer_id}",
    storage_config={
        'type': 's3',
        's3': {
            'bucket': 'customer-engagement',
            'prefix': f'customers/{customer_id}/'
        }
    }
)

# All customer documents in one basket
# Easy to query, process, and manage
```

### 4.5 Use DocEX's Processor Registration

**Register LLM processors via CLI:**

```bash
# Register OpenAI processor
docex processor register \
    --name OpenAIProcessor \
    --type llm_processor \
    --description "OpenAI-powered document processing" \
    --config '{"provider": "openai", "model": "gpt-4", "api_key": "${OPENAI_API_KEY}"}'

# Register Anthropic processor
docex processor register \
    --name AnthropicProcessor \
    --type llm_processor \
    --description "Anthropic Claude-powered processing" \
    --config '{"provider": "anthropic", "model": "claude-3-opus"}'
```

**Benefits:**
- Dynamic processor registration
- Configuration management
- Enable/disable processors
- Processor discovery

---

## 5. Recommended Architecture (Revised)

### 5.1 Leverage DocEX More

**Instead of building separate services, build on DocEX:**

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   REST API   │  │  GraphQL API │  │  Web UI      │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    DocEX + LLM Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  LLM         │  │  Vector      │  │  Knowledge   │       │
│  │  Processors  │  │  Indexing    │  │  Extraction  │       │
│  │  (DocEX)     │  │  Processor   │  │  Processor   │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            │                                 │
│                    ┌───────▼────────┐                        │
│                    │  DocEX Core    │                        │
│                    │  - Processors  │                        │
│                    │  - Metadata    │                        │
│                    │  - Operations  │                        │
│                    │  - Events      │                        │
│                    └─────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    DocEX Storage Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  S3 Storage  │  │  PostgreSQL   │  │  Vector DB   │       │
│  │  (DocEX)     │  │  (DocEX)      │  │  (External)  │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Key Differences from Original Plan

**Original Plan:**
- Build separate services (EmbeddingService, LLMQueryService, etc.)
- Custom operation tracking
- Custom metadata management

**Revised Plan (Leveraging DocEX):**
- ✅ Build LLM adapters as DocEX processors
- ✅ Use DocEX's operation tracking
- ✅ Use DocEX's metadata system
- ✅ Use DocEX's event system
- ✅ Use DocEX's basket organization
- ✅ Use DocEX's processor registration

---

## 6. Implementation Example

### 6.1 Complete LLM-Enabled Workflow

```python
from docex import DocEX
from docex.processors.llm import OpenAIAdapter
from docex.services.metadata_service import MetadataService

# Initialize DocEX
docEX = DocEX()

# Create customer basket
customer_id = "CUST-001"
basket = docEX.create_basket(
    f"customer_{customer_id}",
    storage_config={
        'type': 's3',
        's3': {
            'bucket': 'customer-engagement',
            'prefix': f'customers/{customer_id}/'
        }
    }
)

# Add meeting transcript
meeting_doc = basket.add(
    'meeting_transcript_2024_01_15.txt',
    metadata={
        'customer_id': customer_id,
        'engagement_type': 'meeting',
        'document_type': 'meeting_transcript'
    }
)

# Register and use LLM processor
from docex.processors.factory import factory

# Register OpenAI processor
factory.register(OpenAIAdapter)

# Process document (DocEX handles operation tracking automatically)
processor = OpenAIAdapter({
    'provider': 'openai',
    'model': 'gpt-4',
    'api_key': os.getenv('OPENAI_API_KEY')
})

result = await processor.process(meeting_doc)

# Metadata is automatically stored by DocEX
# Operations are automatically tracked by DocEX
# Events are automatically logged by DocEX

# Query using DocEX's metadata search
documents = basket.find_documents_by_metadata({
    'customer_id': customer_id,
    'engagement_type': 'meeting'
})

# Get processing history (DocEX tracks this)
operations = meeting_doc.get_operations()
for op in operations:
    print(f"{op.operation_type}: {op.status}")
```

---

## 7. Vector Database Integration

### 7.1 Vector Indexing Processor

**Build a processor that indexes documents in vector DB:**

```python
from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document
import pinecone

class VectorIndexingProcessor(BaseProcessor):
    """Processor that indexes documents in vector database"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.vector_db = pinecone.Pinecone(api_key=config.get('pinecone_api_key'))
        self.index_name = config.get('index_name', 'docex-documents')
        self.llm_adapter = OpenAIAdapter(config)
    
    def can_process(self, document: Document) -> bool:
        # Process all documents for indexing
        return True
    
    async def process(self, document: Document) -> ProcessingResult:
        """Index document in vector database"""
        try:
            # Get document content
            text = self.get_document_text(document)
            
            # Generate embedding
            embedding = self.llm_adapter.generate_embedding(text)
            
            # Get document metadata
            metadata = document.get_metadata()
            
            # Index in vector DB
            self.vector_db.Index(self.index_name).upsert(
                vectors=[{
                    'id': document.id,
                    'values': embedding,
                    'metadata': {
                        'document_id': document.id,
                        'basket_id': document.basket_id,
                        'customer_id': metadata.get('customer_id'),
                        'document_type': document.document_type,
                        'text': text[:1000],  # Store first 1000 chars
                        **metadata
                    }
                }]
            )
            
            # Update document metadata
            from docex.services.metadata_service import MetadataService
            MetadataService().update_metadata(document.id, {
                'vector_indexed': True,
                'vector_indexed_at': datetime.now().isoformat()
            })
            
            return ProcessingResult(
                success=True,
                content=text,
                metadata={'vector_indexed': True}
            )
        except Exception as e:
            return ProcessingResult(success=False, error=str(e))
```

### 7.2 Semantic Search Service

**Build on top of DocEX's metadata search:**

```python
class SemanticSearchService:
    """Semantic search service leveraging DocEX"""
    
    def __init__(self, doc_ex: DocEX, vector_db, llm_adapter):
        self.doc_ex = doc_ex
        self.vector_db = vector_db
        self.llm_adapter = llm_adapter
    
    def search(self, query: str, customer_id: str = None, filters: Dict = None):
        """Semantic search across documents"""
        # 1. Generate query embedding
        query_embedding = self.llm_adapter.generate_embedding(query)
        
        # 2. Search vector database
        vector_results = self.vector_db.Index('docex-documents').query(
            vector=query_embedding,
            filter={**filters, 'customer_id': customer_id} if customer_id else filters,
            top_k=10,
            include_metadata=True
        )
        
        # 3. Retrieve full documents from DocEX
        results = []
        for match in vector_results.matches:
            doc_id = match.metadata['document_id']
            # Use DocEX to get full document
            basket = self.doc_ex.get_basket_by_id(match.metadata['basket_id'])
            doc = basket.get_document(doc_id)
            
            results.append({
                'document': doc,
                'relevance_score': match.score,
                'metadata': match.metadata
            })
        
        return results
```

---

## 8. Revised Implementation Roadmap

### Phase 1: LLM Adapters (Weeks 1-2)
1. **Build BaseLLMAdapter**
   - Extends BaseProcessor
   - Integrates with DocEX operation tracking
   - Handles metadata storage

2. **Build Provider Adapters**
   - OpenAIAdapter
   - AnthropicAdapter
   - LocalLLMAdapter (optional)

3. **Register as DocEX Processors**
   - Use DocEX's processor registration
   - Configure via CLI or config

### Phase 2: Vector Indexing (Weeks 3-4)
1. **Build VectorIndexingProcessor**
   - Extends BaseProcessor
   - Indexes documents in vector DB
   - Stores embeddings in DocEX metadata

2. **Integrate with DocEX**
   - Use DocEX's processor pipeline
   - Track indexing operations
   - Store vector metadata

### Phase 3: Semantic Search (Weeks 5-6)
1. **Build SemanticSearchService**
   - Leverages DocEX document retrieval
   - Integrates with vector DB
   - Uses DocEX metadata for filtering

2. **Build RAG Service**
   - Uses DocEX for document retrieval
   - Uses LLM adapters for Q&A
   - Tracks queries as DocEX operations

### Phase 4: Customer Engagement (Weeks 7-8)
1. **Build Custom Processors**
   - MeetingTranscriptProcessor (uses LLM)
   - EmailProcessor (uses LLM)
   - All as DocEX processors

2. **Leverage DocEX Features**
   - Use baskets for customer organization
   - Use metadata for engagement tracking
   - Use events for engagement logging

---

## 9. Benefits of This Approach

### 9.1 Leverages DocEX Infrastructure
- ✅ Operation tracking (built-in)
- ✅ Metadata management (built-in)
- ✅ Event logging (built-in)
- ✅ Processor registration (built-in)
- ✅ Basket organization (built-in)
- ✅ Document lifecycle (built-in)

### 9.2 Consistent Architecture
- All processing goes through DocEX processors
- All operations tracked consistently
- All metadata stored consistently
- All events logged consistently

### 9.3 Easier Maintenance
- Single codebase for tracking
- Single metadata model
- Single operation model
- Single event model

### 9.4 Better Integration
- LLM results stored as DocEX metadata
- LLM operations tracked as DocEX operations
- LLM events logged as DocEX events
- Easy to query and search

---

## 10. Next Steps

1. **Review and approve adapter architecture**
2. **Implement BaseLLMAdapter**
3. **Implement OpenAIAdapter**
4. **Test with DocEX processor system**
5. **Build vector indexing processor**
6. **Build semantic search service**

---

**Document Version:** 1.0  
**Last Updated:** 2024

