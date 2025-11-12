# Customer Engagement Platform with LLM-Powered Knowledge Base
## Architecture Recommendation for DocEX

## Executive Summary

This document provides architectural recommendations for building a customer engagement platform with an LLM-powered knowledge base on top of DocEX. The platform will store and manage various customer engagement documents (meeting transcripts, emails, documents, etc.) and enable intelligent search, insights, and knowledge extraction.

---

## 1. Platform Architecture Overview

### 1.1 High-Level Architecture (Leveraging DocEX)

**Key Principle:** Build LLM capabilities as DocEX processors, leveraging DocEX's built-in infrastructure.

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   REST API   │  │  GraphQL API │  │  Web UI      │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    DocEX + LLM Layer (Integrated)              │
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
│                    │  - Baskets     │                        │
│                    └─────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    DocEX Storage Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  S3 Storage  │  │  PostgreSQL  │  │  pgvector    │       │
│  │  (DocEX)     │  │  (DocEX)     │  │  (Extension)  │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

**Key Difference:** LLM capabilities are built as DocEX processors, not separate services. This leverages DocEX's operation tracking, metadata management, and event logging.

---

## 2. Core Components to Build

### 2.1 Custom Processors for Customer Engagement

#### A. Meeting Transcript Processor
**Purpose:** Extract structured information from meeting transcripts

**Features:**
- Extract participants, topics, action items, decisions
- Identify customer sentiment and engagement level
- Extract key dates and deadlines
- Link to related documents and emails

**Implementation:**
```python
class MeetingTranscriptProcessor(BaseProcessor):
    def can_process(self, document: Document) -> bool:
        return document.content_type == 'text/transcript' or \
               'meeting' in document.get_metadata().get('document_type', '').lower()
    
    def process(self, document: Document) -> ProcessingResult:
        # Use LLM to extract structured data
        # Extract: participants, topics, action items, sentiment
        # Store as metadata
        pass
```

#### B. Email Processor
**Purpose:** Process emails and extract engagement data

**Features:**
- Extract sender, recipient, subject, thread
- Extract attachments and link to documents
- Identify email type (support, sales, follow-up)
- Extract sentiment and urgency

**Implementation:**
```python
class EmailProcessor(BaseProcessor):
    def can_process(self, document: Document) -> bool:
        return document.content_type == 'message/rfc822' or \
               document.name.endswith('.eml')
    
    def process(self, document: Document) -> ProcessingResult:
        # Parse email headers and body
        # Extract metadata: from, to, subject, date, thread_id
        # Process attachments
        # Extract sentiment
        pass
```

#### C. Document Content Extractor
**Purpose:** Extract text and structure from various document types

**Features:**
- Support PDF, DOCX, PPTX, TXT, HTML
- Extract tables, images, metadata
- Preserve document structure
- Generate summaries

**Implementation:**
```python
class UniversalDocumentProcessor(BaseProcessor):
    def can_process(self, document: Document) -> bool:
        # Support multiple formats
        return True
    
    def process(self, document: Document) -> ProcessingResult:
        # Use appropriate library for each format
        # Extract text, structure, metadata
        # Generate summary
        pass
```

---

### 2.2 LLM Integration as DocEX Processors

**Key Insight:** Build LLM capabilities as DocEX processors to leverage DocEX's built-in infrastructure.

#### A. Base LLM Adapter (Extends BaseProcessor)
**Purpose:** Abstract base class for LLM provider adapters

**Leverages DocEX:**
- ✅ Operation tracking (via `_record_operation`)
- ✅ Metadata management (via `MetadataService`)
- ✅ Event logging (automatic)
- ✅ Processor registration (via `ProcessorFactory`)

**Implementation:**
```python
from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document

class BaseLLMAdapter(BaseProcessor):
    """Base class for LLM provider adapters - extends DocEX BaseProcessor"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)  # Initialize DocEX processor
        self.provider = config.get('provider', 'openai')
        self.model = config.get('model', 'gpt-4')
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
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Process document using LLM
        
        DocEX automatically tracks operations and metadata!
        """
        try:
            # DocEX tracks operation start
            operation = self._record_operation(
                document,
                status='in_progress',
                input_metadata={'document_id': document.id}
            )
            
            # Get document content (DocEX method)
            text_content = self.get_document_text(document)
            
            # Process with LLM
            result = self._process_with_llm(document, text_content)
            
            # Store results as DocEX metadata
            if result.metadata:
                from docex.services.metadata_service import MetadataService
                MetadataService().update_metadata(document.id, result.metadata)
            
            # DocEX tracks operation success
            self._record_operation(document, status='success')
            
            return result
        except Exception as e:
            # DocEX tracks operation failure
            self._record_operation(document, status='failed', error=str(e))
            return ProcessingResult(success=False, error=str(e))
```

#### B. Vector Indexing Processor (DocEX Processor with pgvector)
**Purpose:** Index documents in pgvector (PostgreSQL extension) as part of DocEX processing pipeline

**Recommended: pgvector** - PostgreSQL extension for vector similarity search
- ✅ **No additional infrastructure** - Uses existing PostgreSQL
- ✅ **ACID transactions** - Vectors stored alongside document metadata
- ✅ **SQL queries** - Join vectors with documents, metadata, operations
- ✅ **Simple integration** - Just add a column to existing tables
- ✅ **Cost-effective** - No additional service costs
- ✅ **Good performance** - Suitable for up to millions of vectors

**Leverages DocEX:**
- ✅ Processor registration
- ✅ Operation tracking
- ✅ Metadata storage (embeddings stored in same database)
- ✅ Event logging
- ✅ ACID transactions (vectors and documents in same transaction)

**Implementation:**
```python
from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document
from docex.db.models import Document as DocumentModel
from sqlalchemy import update
from pgvector.sqlalchemy import Vector

class VectorIndexingProcessor(BaseProcessor):
    """DocEX processor that indexes documents in pgvector"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.llm_adapter = OpenAIAdapter(config)
        self.embedding_dim = config.get('embedding_dim', 1536)
    
    def can_process(self, document: Document) -> bool:
        # Process all documents for indexing
        return True
    
    async def process(self, document: Document) -> ProcessingResult:
        """Index document in pgvector - DocEX tracks this operation"""
        try:
            # Get content via DocEX
            text = self.get_document_text(document)
            
            # Generate embedding
            embedding = self.llm_adapter.generate_embedding(text)
            
            # Store in same database as document (ACID transaction)
            with self.db.transaction() as session:
                session.execute(
                    update(DocumentModel)
                    .where(DocumentModel.id == document.id)
                    .values(embedding=embedding)
                )
                session.commit()
            
            # Store in DocEX metadata
            from docex.services.metadata_service import MetadataService
            MetadataService().update_metadata(document.id, {
                'vector_indexed': True,
                'embedding_model': self.llm_adapter.model,
                'embedding_dim': self.embedding_dim
            })
            
            return ProcessingResult(success=True, metadata={'vector_indexed': True})
        except Exception as e:
            return ProcessingResult(success=False, error=str(e))
```

**Database Schema Setup:**
```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to documents table
ALTER TABLE documents ADD COLUMN embedding vector(1536);

-- Create index for similarity search
CREATE INDEX documents_embedding_idx ON documents 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);
```

#### C. Semantic Search Service (Leverages DocEX + pgvector)
**Purpose:** Semantic search using pgvector and DocEX for document retrieval

**Leverages DocEX:**
- ✅ Document retrieval via DocEX
- ✅ Metadata filtering via DocEX
- ✅ Basket organization via DocEX
- ✅ SQL queries join vectors with documents
- ✅ ACID transactions ensure consistency

**Implementation:**
```python
from docex import DocEX
from sqlalchemy import select, func
from pgvector.sqlalchemy import Vector
from docex.db.models import Document as DocumentModel

class SemanticSearchService:
    """Semantic search using pgvector and DocEX"""
    
    def __init__(self, doc_ex: DocEX, llm_adapter):
        self.doc_ex = doc_ex
        self.llm_adapter = llm_adapter
        self.db = doc_ex.db
    
    def search(self, query: str, basket_id: str = None, top_k: int = 10):
        """Semantic search using pgvector"""
        # 1. Generate query embedding
        query_embedding = self.llm_adapter.generate_embedding(query)
        
        # 2. Search in same database as documents (SQL query)
        with self.db.transaction() as session:
            query_stmt = select(
                DocumentModel.id,
                DocumentModel.name,
                DocumentModel.basket_id,
                func.cosine_distance(DocumentModel.embedding, query_embedding).label('distance')
            ).where(
                DocumentModel.embedding.isnot(None)
            )
            
            if basket_id:
                query_stmt = query_stmt.where(DocumentModel.basket_id == basket_id)
            
            query_stmt = query_stmt.order_by(
                func.cosine_distance(DocumentModel.embedding, query_embedding)
            ).limit(top_k)
            
            results = session.execute(query_stmt).all()
        
        # 3. Retrieve full documents via DocEX
        documents = []
        for result in results:
            basket = self.doc_ex.get_basket_by_id(result.basket_id)
            doc = basket.get_document(result.id)
            documents.append({
                'document': doc,  # Full DocEX document
                'relevance_score': 1 - result.distance,  # Convert distance to similarity
                'distance': result.distance,
                'metadata': doc.get_metadata()  # DocEX metadata
            })
        
        return documents
    
    def hybrid_search(self, query: str, filters: Dict = None, top_k: int = 10):
        """Hybrid search: vector similarity + metadata filtering"""
        # 1. Generate query embedding
        query_embedding = self.llm_adapter.generate_embedding(query)
        
        # 2. Build query with metadata filters
        with self.db.transaction() as session:
            from docex.db.models import DocumentMetadata
            
            query_stmt = select(
                DocumentModel.id,
                DocumentModel.basket_id,
                func.cosine_distance(DocumentModel.embedding, query_embedding).label('distance')
            ).where(
                DocumentModel.embedding.isnot(None)
            )
            
            # Add metadata filters
            if filters:
                query_stmt = query_stmt.join(
                    DocumentMetadata,
                    DocumentMetadata.document_id == DocumentModel.id
                )
                
                for key, value in filters.items():
                    query_stmt = query_stmt.where(
                        DocumentMetadata.key == key,
                        DocumentMetadata.value == str(value)
                    )
            
            query_stmt = query_stmt.order_by(
                func.cosine_distance(DocumentModel.embedding, query_embedding)
            ).limit(top_k)
            
            results = session.execute(query_stmt).all()
        
        # 3. Retrieve documents via DocEX
        return [self._get_document(result) for result in results]
```

#### D. RAG Query Processor (DocEX Processor with pgvector)
**Purpose:** Answer questions using RAG with pgvector, tracked as DocEX operations

**Leverages DocEX:**
- ✅ Document retrieval via pgvector (same database)
- ✅ Operation tracking
- ✅ Metadata storage (queries and answers)
- ✅ Event logging
- ✅ ACID transactions

**Implementation:**
```python
class RAGQueryProcessor(BaseProcessor):
    """DocEX processor for RAG-based Q&A using pgvector"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.llm_adapter = OpenAIAdapter(config)
        self.doc_ex = DocEX()
        self.search_service = SemanticSearchService(self.doc_ex, self.llm_adapter)
    
    async def process(self, document: Document) -> ProcessingResult:
        """Process query document - DocEX tracks this"""
        try:
            # Get query from document
            query = self.get_document_text(document)
            
            # Search relevant documents using pgvector (via DocEX)
            relevant_docs = self.search_service.search(query, top_k=5)
            
            # Build context from DocEX documents
            context = self._build_context([r['document'] for r in relevant_docs])
            
            # Generate answer
            answer = self.llm_adapter.generate_completion(
                self._build_rag_prompt(query, context)
            )
            
            # Store answer as DocEX metadata
            from docex.services.metadata_service import MetadataService
            MetadataService().update_metadata(document.id, {
                'answer': answer,
                'sources': [r['document'].id for r in relevant_docs],
                'query': query,
                'relevance_scores': [r['relevance_score'] for r in relevant_docs]
            })
            
            return ProcessingResult(
                success=True,
                content=answer,
                metadata={'answer': answer, 'sources': relevant_docs}
            )
        except Exception as e:
            return ProcessingResult(success=False, error=str(e))
```

---

### 2.3 Customer Engagement Service

#### A. Engagement Tracking
**Purpose:** Track and analyze customer interactions

**Features:**
- Track all touchpoints (emails, meetings, calls, documents)
- Calculate engagement scores
- Identify engagement trends
- Alert on low engagement

**Data Model:**
```python
# Custom metadata keys for customer engagement
CUSTOMER_ID = "customer_id"
ENGAGEMENT_TYPE = "engagement_type"  # email, meeting, call, document
ENGAGEMENT_DATE = "engagement_date"
ENGAGEMENT_SCORE = "engagement_score"
PARTICIPANTS = "participants"
TOPICS = "topics"
ACTION_ITEMS = "action_items"
SENTIMENT = "sentiment"
```

#### B. Customer Profile Aggregation
**Purpose:** Build comprehensive customer profiles

**Features:**
- Aggregate all documents per customer
- Extract customer preferences and pain points
- Track customer journey
- Generate customer insights

**Implementation:**
```python
class CustomerProfileService:
    def __init__(self, doc_ex):
        self.doc_ex = doc_ex
    
    def get_customer_profile(self, customer_id: str):
        """Build comprehensive customer profile"""
        # Get all baskets for customer
        baskets = self._get_customer_baskets(customer_id)
        
        # Aggregate documents
        all_docs = []
        for basket in baskets:
            all_docs.extend(basket.list())
        
        # Extract insights using LLM
        profile = {
            'customer_id': customer_id,
            'total_interactions': len(all_docs),
            'engagement_timeline': self._build_timeline(all_docs),
            'topics': self._extract_topics(all_docs),
            'sentiment_analysis': self._analyze_sentiment(all_docs),
            'action_items': self._extract_action_items(all_docs),
            'preferences': self._extract_preferences(all_docs)
        }
        
        return profile
```

---

### 2.4 Knowledge Base Service

#### A. Knowledge Graph Builder
**Purpose:** Build relationships between documents, customers, topics

**Features:**
- Entity extraction (customers, products, topics, people)
- Relationship mapping
- Graph database integration (Neo4j, ArangoDB)
- Visual knowledge graph

**Implementation:**
```python
class KnowledgeGraphService:
    def __init__(self, graph_db):
        self.graph = graph_db
    
    def build_graph(self, documents: List[Document]):
        """Build knowledge graph from documents"""
        for doc in documents:
            # Extract entities
            entities = self._extract_entities(doc)
            
            # Create nodes
            for entity in entities:
                self.graph.create_node(entity)
            
            # Create relationships
            relationships = self._extract_relationships(doc, entities)
            for rel in relationships:
                self.graph.create_relationship(rel)
    
    def query_graph(self, query: str):
        """Query knowledge graph"""
        # Cypher or Gremlin query
        pass
```

#### B. Knowledge Base API
**Purpose:** Expose knowledge base functionality

**Endpoints:**
- `GET /api/kb/search?q=...` - Semantic search
- `GET /api/kb/query?q=...` - LLM-powered Q&A
- `GET /api/kb/customer/{id}/insights` - Customer insights
- `GET /api/kb/topics` - Extract topics
- `GET /api/kb/relationships` - Knowledge graph queries

---

## 3. Recommended Technology Stack

### 3.1 Core Platform
- **DocEX** - Document management foundation
- **PostgreSQL** - Primary database (for DocEX)
- **S3** - Document storage (using our new S3 implementation)

### 3.2 LLM & AI
- **OpenAI API** or **Anthropic Claude** - LLM for Q&A and extraction
- **OpenAI Embeddings** or **Cohere** - Vector embeddings
- **pgvector** (PostgreSQL extension) ⭐ **RECOMMENDED** - Vector database
  - ✅ No additional infrastructure (uses existing PostgreSQL)
  - ✅ ACID transactions (vectors stored with documents)
  - ✅ SQL queries (join vectors with documents, metadata)
  - ✅ Cost-effective (no additional service costs)
  - ✅ Good performance (suitable for up to millions of vectors)
- **Pinecone** or **Weaviate** - Alternative vector databases (for very large scale)
- **LangChain** or **LlamaIndex** - LLM orchestration framework (optional)

### 3.3 Additional Services
- **Neo4j** or **ArangoDB** - Knowledge graph (optional)
- **Redis** - Caching and session management
- **Celery** or **RQ** - Background job processing
- **FastAPI** or **Flask** - REST API layer
- **React** or **Vue.js** - Frontend UI

### 3.4 Processing Libraries
- **pdfminer.six** - PDF text extraction
- **python-docx** - Word document processing
- **python-pptx** - PowerPoint processing
- **beautifulsoup4** - HTML/email parsing
- **whisper** or **AssemblyAI** - Audio transcription (for meeting recordings)

---

## 4. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
1. **Set up DocEX with S3 storage**
   - Configure S3 buckets per customer or tenant
   - Set up basket structure (one basket per customer)
   - Configure metadata schema for customer engagement

2. **Build custom processors**
   - Email processor
   - Meeting transcript processor
   - Universal document processor
   - Register processors in DocEX

### Phase 2: LLM Integration (Weeks 3-4)
1. **Embedding service**
   - Implement text chunking
   - Set up embedding generation
   - Integrate with pgvector (PostgreSQL extension)

2. **pgvector setup** ⭐ **RECOMMENDED**
   - Install pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector;`
   - Add embedding column to documents table
   - Create index for similarity search
   - Implement indexing pipeline (as DocEX processor)
   - Build search service (using SQL queries)

### Phase 3: Knowledge Base (Weeks 5-6)
1. **LLM query service**
   - Implement RAG pipeline
   - Build context retrieval
   - Add citation tracking

2. **Knowledge graph** (optional)
   - Entity extraction
   - Relationship mapping
   - Graph queries

### Phase 4: Customer Engagement (Weeks 7-8)
1. **Engagement tracking**
   - Build engagement service
   - Implement scoring
   - Create dashboards

2. **Customer profiles**
   - Aggregate customer data
   - Generate insights
   - Build customer journey maps

### Phase 5: API & UI (Weeks 9-10)
1. **REST API**
   - Document management endpoints
   - Knowledge base endpoints
   - Customer engagement endpoints

2. **Frontend**
   - Document browser
   - Search interface
   - Customer dashboard
   - Knowledge graph visualization

---

## 5. Data Model & Basket Structure

### 5.1 Basket Organization Strategy

**Option 1: One basket per customer**
```
baskets/
  customer_001/
    emails/
    meetings/
    documents/
    notes/
```

**Option 2: One basket per engagement type per customer**
```
baskets/
  customer_001_emails/
  customer_001_meetings/
  customer_001_documents/
```

**Option 3: Time-based baskets**
```
baskets/
  customer_001_2024_q1/
  customer_001_2024_q2/
```

**Recommendation:** Use Option 1 with S3 prefixes for organization:
```python
# Create customer basket with S3 storage
basket = docEX.create_basket(
    f"customer_{customer_id}",
    storage_config={
        'type': 's3',
        's3': {
            'bucket': 'customer-engagement',
            'prefix': f'customers/{customer_id}/',
            'region': 'us-east-1'
        }
    }
)
```

### 5.2 Metadata Schema

**Standard Metadata:**
```python
{
    'customer_id': 'CUST-001',
    'engagement_type': 'meeting',  # email, meeting, call, document
    'engagement_date': '2024-01-15',
    'participants': ['john@example.com', 'jane@example.com'],
    'topics': ['product demo', 'pricing', 'integration'],
    'sentiment': 'positive',
    'action_items': ['Follow up on pricing', 'Schedule integration call'],
    'document_type': 'meeting_transcript',
    'source': 'zoom_recording',
    'language': 'en'
}
```

**Custom Metadata Keys:**
```python
# Add to metadata_keys.py
CUSTOMER_ID = "customer_id"
ENGAGEMENT_TYPE = "engagement_type"
ENGAGEMENT_DATE = "engagement_date"
ENGAGEMENT_SCORE = "engagement_score"
PARTICIPANTS = "participants"
TOPICS = "topics"
ACTION_ITEMS = "action_items"
SENTIMENT = "sentiment"
CUSTOMER_SEGMENT = "customer_segment"
ACCOUNT_MANAGER = "account_manager"
```

---

## 6. Example Implementation

### 6.1 Complete Workflow Example

```python
from docex import DocEX
from docex.models.metadata_keys import MetadataKey

# Initialize DocEX
docEX = DocEX()

# Create customer basket with S3 storage
customer_id = "CUST-001"
basket = docEX.create_basket(
    f"customer_{customer_id}",
    description=f"Customer engagement documents for {customer_id}",
    storage_config={
        'type': 's3',
        's3': {
            'bucket': 'customer-engagement-docs',
            'prefix': f'customers/{customer_id}/',
            'region': 'us-east-1'
        }
    }
)

# Add meeting transcript
meeting_doc = basket.add(
    'meeting_transcript_2024_01_15.txt',
    metadata={
        MetadataKey.CUSTOMER_ID.value: customer_id,
        'engagement_type': 'meeting',
        'engagement_date': '2024-01-15',
        'participants': ['john@example.com', 'jane@example.com'],
        'topics': ['product demo', 'pricing'],
        'document_type': 'meeting_transcript'
    }
)

# Process document (extract structured data)
from custom_processors import MeetingTranscriptProcessor
processor = MeetingTranscriptProcessor()
result = processor.process(meeting_doc)

# Update metadata with extracted information
from docex.services.metadata_service import MetadataService
metadata_service = MetadataService()
metadata_service.update_metadata(meeting_doc.id, {
    'action_items': result.metadata.get('action_items', []),
    'sentiment': result.metadata.get('sentiment', 'neutral'),
    'key_points': result.metadata.get('key_points', [])
})

# Index in vector database for semantic search
from services.embedding_service import EmbeddingService
from services.vector_store_service import VectorStoreService

embedding_service = EmbeddingService()
vector_store = VectorStoreService()

# Generate embeddings
text_content = meeting_doc.get_content(mode='text')
embeddings = embedding_service.generate_embeddings(text_content)

# Index in vector database
vector_store.index_document(
    document_id=meeting_doc.id,
    embeddings=embeddings,
    metadata={
        'customer_id': customer_id,
        'document_type': 'meeting_transcript',
        'date': '2024-01-15',
        'basket_id': basket.id
    }
)

# Query knowledge base
from services.llm_query_service import LLMQueryService
kb_service = LLMQueryService(llm_client, vector_store, docEX)

answer = kb_service.query(
    "What were the main concerns discussed in recent meetings with CUST-001?",
    customer_id=customer_id
)

print(f"Answer: {answer['answer']}")
print(f"Sources: {answer['sources']}")
```

---

## 7. Best Practices

### 7.1 Document Organization
- Use baskets to organize by customer
- Use S3 prefixes for additional organization
- Implement consistent naming conventions
- Set up retention policies

### 7.2 Metadata Management
- Use standard metadata keys consistently
- Extract and store structured data
- Link related documents
- Track document lineage

### 7.3 Processing Pipeline
- Process documents asynchronously
- Implement retry logic for failures
- Track processing status
- Cache expensive operations

### 7.4 LLM Integration
- Chunk documents appropriately
- Use appropriate embedding models
- Implement hybrid search (semantic + keyword)
- Cache embeddings and queries
- Monitor LLM API costs

### 7.5 Security & Privacy
- Encrypt sensitive documents
- Implement access control per customer
- Audit all document access
- Comply with data privacy regulations
- Use S3 encryption at rest

---

## 8. Cost Considerations

### 8.1 Storage Costs
- **S3 Storage:** ~$0.023/GB/month (Standard)
- **Database:** PostgreSQL on RDS or managed service
- **Vector DB:** pgvector (free, PostgreSQL extension) ⭐ **RECOMMENDED**
  - Alternative: Pinecone (~$70/month for starter) or Weaviate (self-hosted) for very large scale

### 8.2 LLM API Costs
- **Embeddings:** ~$0.0001 per 1K tokens
- **Chat Completions:** ~$0.03 per 1K tokens (GPT-4)
- **Consider:** Batch processing, caching, using cheaper models for simple tasks

### 8.3 Infrastructure
- **Compute:** EC2 or container service for processing
- **API Gateway:** For REST API
- **CDN:** For document delivery

---

## 9. Next Steps

1. **Review and approve architecture**
2. **Set up development environment**
   - Configure DocEX with S3
   - Set up pgvector extension (PostgreSQL)
   - Add embedding column to documents table
   - Create similarity search index
   - Get LLM API keys
3. **Start Phase 1 implementation**
4. **Iterate based on feedback**

---

## 10. Additional Recommendations

### 10.1 Advanced Features (Future)
- **Real-time processing:** WebSocket for live document ingestion
- **Multi-language support:** Detect and process multiple languages
- **Voice integration:** Transcribe calls and meetings automatically
- **Analytics dashboard:** Customer engagement metrics and trends
- **Automated insights:** Proactive customer health scoring
- **Integration APIs:** Connect with CRM, email, calendar systems

### 10.2 Scalability Considerations
- **Horizontal scaling:** Process documents in parallel
- **Caching strategy:** Cache embeddings and frequent queries
- **Database optimization:** Index metadata fields for fast queries
- **CDN integration:** Serve documents via CDN for faster access

---

**Document Version:** 1.0  
**Last Updated:** 2024  
**Author:** DocEX Development Team

