# DocEX RAG Implementation

This document provides a comprehensive guide to the new RAG (Retrieval-Augmented Generation) functionality in DocEX, featuring advanced vector database integration with FAISS and Pinecone.

## 🎯 Overview

The DocEX RAG implementation provides three levels of functionality:

1. **Basic RAG Service** - Uses existing semantic search infrastructure
2. **Enhanced RAG Service** - Integrates FAISS and Pinecone vector databases  
3. **Advanced RAG Service** - Adds conversational capabilities and query expansion

## 🚀 Features

### Core Features
- **Multiple Vector Databases**: Support for FAISS (local) and Pinecone (cloud)
- **Hybrid Search**: Combines semantic search with vector similarity for better results
- **Intelligent Caching**: Configurable query result caching with TTL
- **Flexible Configuration**: Extensive configuration options for different use cases
- **Source Citations**: Automatic citation of source documents in answers
- **Confidence Scoring**: AI-powered confidence assessment for generated answers

### Advanced Features  
- **Conversational RAG**: Multi-turn conversations with context preservation
- **Query Expansion**: Automatic query enhancement using conversation history
- **Performance Optimization**: Batch processing, parallel search, and smart indexing
- **Multiple Answer Styles**: Concise, detailed, or bullet-point responses

## 📦 Installation

### Dependencies

Install the required dependencies:

```bash
pip install -r requirements.txt

# For FAISS (CPU version)
pip install faiss-cpu

# For FAISS with GPU support (optional)
pip install faiss-gpu

# For Pinecone
pip install pinecone-client
```

### Environment Variables

For Pinecone integration, set these environment variables:

```bash
export PINECONE_API_KEY=your_pinecone_api_key
export PINECONE_ENVIRONMENT=your_pinecone_environment
```

For Claude LLM integration:

```bash
export ANTHROPIC_API_KEY=your_claude_api_key
```

## 🏗️ Architecture

```
DocEX RAG Architecture

┌─────────────────────────────────────────────────┐
│                    RAG Service                  │
├─────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐             │
│  │   Query     │  │   Answer     │             │
│  │ Processing  │  │ Generation   │             │
│  └─────────────┘  └──────────────┘             │
├─────────────────────────────────────────────────┤
│              Hybrid Search Layer                │
│  ┌─────────────┐  ┌──────────────┐             │
│  │  Semantic   │  │   Vector     │             │
│  │   Search    │  │   Search     │             │
│  │ (DocEX)     │  │(FAISS/Pinecone)│           │
│  └─────────────┘  └──────────────┘             │
├─────────────────────────────────────────────────┤
│              Document Storage                   │
│  ┌─────────────┐  ┌──────────────┐             │
│  │   DocEX     │  │   Vector     │             │
│  │ Documents   │  │  Database    │             │
│  └─────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────┘
```

## 🔧 Configuration

### Basic RAG Configuration

```python
from docex.processors.rag import RAGService

rag_config = {
    'max_context_tokens': 4000,
    'top_k_documents': 5,
    'min_similarity': 0.7,
    'answer_style': 'detailed',  # 'concise', 'detailed', 'bullet_points'
    'include_citations': True,
    'temperature': 0.3,
    'max_answer_tokens': 500
}

rag_service = RAGService(
    semantic_search_service=semantic_search,
    llm_adapter=claude_adapter,
    config=rag_config
)
```

### Enhanced RAG Configuration

```python
from docex.processors.rag import EnhancedRAGService, EnhancedRAGConfig

# FAISS Configuration
faiss_config = {
    'dimension': 1536,  # OpenAI embedding dimension
    'index_type': 'flat',  # 'flat', 'ivf', 'hnsw'
    'metric': 'cosine',    # 'cosine', 'l2', 'inner_product'
    'storage_path': './storage/faiss_index.bin',
    'enable_gpu': False
}

# Pinecone Configuration  
pinecone_config = {
    'api_key': os.getenv('PINECONE_API_KEY'),
    'environment': os.getenv('PINECONE_ENVIRONMENT'), 
    'index_name': 'docex-rag',
    'dimension': 1536,
    'metric': 'cosine',
    'pod_type': 'p1.x1'
}

# Enhanced RAG Configuration
enhanced_config = EnhancedRAGConfig(
    vector_db_type='faiss',  # or 'pinecone'
    vector_db_config=faiss_config,  # or pinecone_config
    enable_hybrid_search=True,
    semantic_weight=0.6,
    vector_weight=0.4,
    enable_caching=True,
    cache_ttl_seconds=3600,
    batch_size=100,
    top_k_documents=5,
    min_similarity=0.75
)

rag_service = EnhancedRAGService(
    semantic_search_service=semantic_search,
    llm_adapter=claude_adapter,
    config=enhanced_config
)
```

## 📚 Usage Examples

### Basic RAG Query

```python
import asyncio
from docex.processors.rag import RAGService

async def basic_example():
    # Initialize services (semantic search, LLM adapter)
    # ... initialization code ...
    
    # Create RAG service
    rag_service = RAGService(semantic_search, llm_adapter)
    
    # Query with RAG
    result = await rag_service.query(
        question="What is machine learning?",
        basket_id="my_basket",
        filters={'category': 'educational'}
    )
    
    print(f"Answer: {result.answer}")
    print(f"Confidence: {result.confidence_score}")
    print(f"Sources: {len(result.sources)}")
    
    # Access source documents
    for source in result.sources:
        print(f"- {source.document.name} (similarity: {source.similarity_score})")

asyncio.run(basic_example())
```

### Enhanced RAG with Vector Databases

```python
from docex.processors.rag import EnhancedRAGService, EnhancedRAGConfig

async def enhanced_example():
    # Configure for FAISS
    config = EnhancedRAGConfig(
        vector_db_type='faiss',
        vector_db_config={'dimension': 1536, 'index_type': 'flat'},
        enable_hybrid_search=True
    )
    
    # Create enhanced service
    rag_service = EnhancedRAGService(semantic_search, llm_adapter, config)
    
    # Initialize vector database
    await rag_service.initialize_vector_db()
    
    # Add documents to vector database
    await rag_service.add_documents_to_vector_db(documents)
    
    # Enhanced query with hybrid search
    result = await rag_service.query("Explain deep learning architectures")
    
    # Check search method used
    search_method = result.metadata.get('search_method')
    print(f"Search method: {search_method}")  # 'hybrid', 'vector', or 'semantic'

asyncio.run(enhanced_example())
```

### Conversational RAG

```python
from docex.processors.rag import AdvancedRAGService

async def conversational_example():
    advanced_rag = AdvancedRAGService(semantic_search, llm_adapter)
    
    conversation_id = "user_session_1"
    
    # First question
    result1 = await advanced_rag.conversational_query(
        question="What is machine learning?",
        conversation_id=conversation_id
    )
    print(f"Q1: {result1.answer}")
    
    # Follow-up question (will use context from previous)
    result2 = await advanced_rag.conversational_query(
        question="What are some popular algorithms?",
        conversation_id=conversation_id
    )
    print(f"Q2: {result2.answer}")

asyncio.run(conversational_example())
```

## 🔍 Vector Database Details

### FAISS Integration

FAISS (Facebook AI Similarity Search) provides high-performance vector search:

```python
faiss_config = {
    'dimension': 1536,
    'index_type': 'flat',     # Simple exact search
    # 'index_type': 'ivf',    # Inverted file index (faster, approximate)
    # 'index_type': 'hnsw',   # Hierarchical NSW (memory efficient)
    'metric': 'cosine',       # Similarity metric
    'nlist': 100,             # Clusters for IVF index
    'storage_path': './faiss_index.bin',  # Persistence
    'enable_gpu': False       # GPU acceleration
}
```

**FAISS Index Types:**
- `flat`: Exact search, best accuracy, slower for large datasets
- `ivf`: Approximate search with clustering, good speed/accuracy tradeoff
- `hnsw`: Graph-based search, memory efficient, very fast queries

### Pinecone Integration

Pinecone provides managed cloud vector search:

```python
pinecone_config = {
    'api_key': 'your_api_key',
    'environment': 'us-west1-gcp',  # Your Pinecone environment
    'index_name': 'docex-vectors',
    'dimension': 1536,
    'metric': 'cosine',
    'pod_type': 'p1.x1',           # Pod size
    'replicas': 1                   # Number of replicas
}
```

**Pinecone Benefits:**
- Managed service (no infrastructure setup)
- Automatic scaling
- High availability and reliability
- Real-time updates
- Global distribution options

## ⚙️ Performance Optimization

### Caching Strategy

```python
config = EnhancedRAGConfig(
    enable_caching=True,
    cache_ttl_seconds=3600,  # 1 hour cache
    # Cache reduces latency for repeated queries
)
```

### Batch Processing

```python
# Add documents in batches for better performance
config = EnhancedRAGConfig(
    batch_size=100  # Process 100 documents at a time
)

# Large document collections
await rag_service.add_documents_to_vector_db(large_document_list)
```

### Hybrid Search Tuning

```python
# Adjust weights based on your use case
config = EnhancedRAGConfig(
    semantic_weight=0.7,  # Higher weight for semantic understanding
    vector_weight=0.3,    # Lower weight for pure vector similarity
    
    # For technical documents, you might prefer:
    # semantic_weight=0.4,
    # vector_weight=0.6,
)
```

## 📊 Monitoring and Analytics

### Getting Statistics

```python
# Vector database statistics
stats = await rag_service.get_vector_db_stats()
print(f"Total documents: {stats['total_documents']}")
print(f"Index type: {stats['index_type']}")
print(f"Cache size: {stats['cache_size']}")

# Query result analysis
result = await rag_service.query("Your question")
print(f"Processing time: {result.processing_time}")
print(f"Context tokens: {result.metadata['context_tokens']}")
print(f"Search method: {result.metadata['search_method']}")
```

### Performance Metrics

Track these metrics for optimization:

- **Query Response Time**: Time to generate answers
- **Retrieval Accuracy**: Relevance of retrieved documents  
- **Cache Hit Rate**: Percentage of cached responses
- **Confidence Scores**: Quality indicator for answers
- **Token Usage**: Cost monitoring for LLM calls

## 🚨 Troubleshooting

### Common Issues

**1. FAISS Installation Problems**

```bash
# For Mac with ARM chips
conda install faiss-cpu -c pytorch

# For Linux/Windows
pip install faiss-cpu
```

**2. Pinecone Connection Issues**

```python
# Verify credentials
import pinecone
pinecone.init(api_key="your_key", environment="your_env")
print(pinecone.list_indexes())  # Should list your indexes
```

**3. Memory Issues with Large Documents**

```python
# Reduce batch size and context tokens
config = EnhancedRAGConfig(
    batch_size=50,           # Smaller batches
    max_context_tokens=2000  # Less context per query
)
```

**4. Poor Answer Quality**

```python
# Adjust similarity threshold and top-k
config = EnhancedRAGConfig(
    min_similarity=0.8,      # Higher threshold
    top_k_documents=3,       # Fewer, more relevant docs
    temperature=0.1          # More focused LLM responses
)
```

## 🔮 Future Enhancements

Planned improvements for DocEX RAG:

1. **Additional Vector Databases**: Qdrant, Weaviate, Milvus support
2. **Multi-Modal RAG**: Support for images, audio, and video content
3. **Advanced Reranking**: Learning-to-rank models for result optimization
4. **Streaming Responses**: Real-time answer generation
5. **Evaluation Framework**: Automated answer quality assessment
6. **Multi-Language Support**: Non-English document processing

## 📖 Examples

See the `/examples` directory for complete working examples:

- `rag_basic_example.py` - Basic RAG functionality
- `rag_enhanced_example.py` - FAISS and Pinecone integration
- `rag_performance_test.py` - Performance benchmarking
- `rag_conversational_demo.py` - Multi-turn conversations

## 🤝 Contributing

To contribute to DocEX RAG:

1. Implement new vector database adapters in `docex/processors/rag/vector_databases.py`
2. Extend RAG service functionality in `docex/processors/rag/rag_service.py`
3. Add comprehensive tests in `tests/test_rag_*.py`
4. Update documentation and examples

## 📄 License

This RAG implementation is part of DocEX and follows the same license terms.