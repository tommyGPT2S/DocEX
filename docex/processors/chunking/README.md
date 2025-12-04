# Chunking Strategies for DocEX RAG System

Comprehensive implementation of 8 chunking strategies optimized for different document types and RAG use cases.

## 📊 Overview

This module implements state-of-the-art text chunking strategies based on the industry-standard approaches used by LangChain, LlamaIndex, and other RAG frameworks.

### Why Chunking Matters for RAG

Proper chunking is critical for RAG system performance:
- **Too large**: Exceeds embedding model limits, dilutes semantic meaning
- **Too small**: Loses context, increases storage costs
- **Poor boundaries**: Splits related concepts, degrades retrieval quality

## 🎯 Available Strategies

| Strategy | Complexity | Semantic Aware | Best For |
|----------|-----------|----------------|----------|
| **Fixed-Size** | Low | ❌ | Speed-critical tasks, emails, FAQs |
| **Recursive** | Low-Medium | Partial | Structured documents with hierarchy |
| **Document-Based** | Low | ❌ | Articles, docs with clear sections |
| **Semantic** | Medium | ✅ | Research papers, textbooks, narratives |
| **LLM-Based** | Medium-High | ✅ | Legal briefs, medical records, reports |
| **Agentic** | High | ✅ | Regulatory filings, complex policies |
| **Late Chunking** | High | ✅ | Case studies, long-form analyses |
| **Hierarchical** | Medium | Partial | Handbooks, regulations, manuals |

## 🚀 Quick Start

### Basic Usage

```python
from docex.processors.chunking import ChunkingFactory, ChunkingConfig

# Create chunking strategy
config = ChunkingConfig(
    chunk_size=512,
    chunk_overlap=50,
    min_chunk_size=100
)

chunker = ChunkingFactory.create('recursive', config)

# Chunk text
chunks = await chunker.chunk(text)

# Access chunks
for chunk in chunks:
    print(f"Chunk {chunk.id}: {len(chunk.content)} chars")
    print(chunk.content)
```

### Auto-Select Strategy

```python
# Automatically select optimal strategy
chunker = ChunkingFactory.create_optimal(
    text=document_text,
    metadata={'type': 'research_paper'}
)

chunks = await chunker.chunk(document_text)
```

## 📖 Strategy Details

### 1. Fixed-Size Chunking

**When to use**: Speed is critical, document structure doesn't matter

```python
from docex.processors.chunking import FixedSizeChunking

chunker = FixedSizeChunking(config, use_tokens=True)
chunks = await chunker.chunk(text)
```

**Technical Details**:
- O(n) complexity
- No semantic analysis
- Configurable overlap for context
- Can count by tokens or characters

### 2. Recursive Chunking

**When to use**: Documents with natural hierarchy (paragraphs, sections)

```python
from docex.processors.chunking import RecursiveChunking

chunker = RecursiveChunking(config)
chunks = await chunker.chunk(text)
```

**Technical Details**:
- Splits at: paragraphs → sentences → clauses → words
- Preserves structure when possible
- Combines small segments intelligently

### 3. Document-Based Chunking

**When to use**: Well-structured documents with headers/sections

```python
from docex.processors.chunking import DocumentBasedChunking

chunker = DocumentBasedChunking(config)
chunks = await chunker.chunk(text, metadata={'format': 'markdown'})
```

**Supported Formats**:
- Markdown (headers: #, ##, ###)
- HTML (tags: h1, h2, h3, etc.)
- Plain text (paragraph boundaries)

### 4. Semantic Chunking

**When to use**: Topic-driven documents where meaning matters

```python
from docex.processors.chunking import SemanticChunking

# Requires embedding function
chunker = SemanticChunking(config, embedding_function=embed_func)
chunks = await chunker.chunk(text)
```

**Technical Details**:
- Uses embeddings to detect topic shifts
- Cosine similarity between sentences
- Adaptive threshold based on document statistics

### 5. LLM-Based Chunking

**When to use**: Complex documents requiring deep understanding

```python
from docex.processors.chunking import LLMBasedChunking

# Requires LLM service
chunker = LLMBasedChunking(config, llm_service=llm)
chunks = await chunker.chunk(text)
```

**How it works**:
1. LLM analyzes document structure
2. Identifies optimal semantic boundaries
3. Provides reasoning for each split

### 6. Agentic Chunking

**When to use**: Maximum quality for critical documents

```python
from docex.processors.chunking import AgenticChunking

chunker = AgenticChunking(
    config,
    llm_service=llm,
    task_requirements={'accuracy': 'high', 'context': 'legal'}
)
chunks = await chunker.chunk(text)
```

**Capabilities**:
- Analyzes document characteristics
- Selects optimal sub-strategy
- Iteratively refines chunks
- Task-specific optimization

### 7. Late Chunking

**When to use**: Document context critical for each chunk

```python
from docex.processors.chunking import LateChunking

chunker = LateChunking(config, embedding_function=embed_func)
chunks = await chunker.chunk(text)
```

**How it works**:
1. Embed entire document
2. Create preliminary chunks
3. Derive chunk embeddings with document context
4. Store both local and global embeddings

### 8. Hierarchical Chunking

**When to use**: Multi-resolution retrieval needed

```python
from docex.processors.chunking import HierarchicalChunking

chunker = HierarchicalChunking(config, max_levels=4)
chunks = await chunker.chunk(text)

# Get hierarchy info
hierarchy = chunker.get_chunk_hierarchy(chunk_id, chunks)
```

**Hierarchy Levels**:
- Level 0: Full document
- Level 1: Major sections
- Level 2: Subsections/paragraphs
- Level 3: Sentences

## ⚙️ Configuration

### ChunkingConfig Options

```python
from docex.processors.chunking import ChunkingConfig

config = ChunkingConfig(
    # Size parameters
    chunk_size=512,           # Target size in tokens
    chunk_overlap=50,         # Overlap between chunks
    min_chunk_size=100,       # Minimum chunk size
    max_chunk_size=2000,      # Maximum chunk size
    
    # Structure preservation
    preserve_structure=True,   # Try to keep semantic structure
    split_on_sentences=True,   # Split at sentence boundaries
    split_on_paragraphs=True,  # Split at paragraph boundaries
    
    # Semantic chunking
    similarity_threshold=0.8,  # For semantic boundary detection
    embedding_batch_size=32,   # Batch size for embeddings
    
    # Document-based
    header_tags=['h1', 'h2', 'h3'],
    section_markers=['#', '##', '###'],
    
    # Performance
    enable_caching=True,
    parallel_processing=True,
    
    # Metadata
    include_metadata=True,
    metadata_fields=['source', 'author', 'date']
)
```

## 🔄 Integration with RAG Pipeline

### With Vector Indexing

```python
from docex.processors.chunking import ChunkingFactory
from docex.processors.vector import VectorIndexingProcessor

# Chunk document
chunker = ChunkingFactory.create('semantic', config)
chunks = await chunker.chunk(document.get_content())

# Index each chunk
vector_processor = VectorIndexingProcessor(...)

for chunk in chunks:
    # Create mini-document for each chunk
    chunk_doc = Document()
    chunk_doc.content = chunk.content
    chunk_doc.metadata.update(chunk.metadata)
    
    # Index
    await vector_processor.process(chunk_doc)
```

### With Enhanced RAG Service

```python
from docex.processors.chunking import ChunkingFactory
from docex.processors.rag import EnhancedRAGService

# Add chunking to RAG pipeline
rag_service = EnhancedRAGService(...)

# Chunk documents before indexing
chunker = ChunkingFactory.create_optimal(document_text)
chunks = await chunker.chunk(document_text)

# Convert chunks to documents
chunk_documents = [
    create_document_from_chunk(chunk)
    for chunk in chunks
]

# Add to vector database
await rag_service.add_documents_to_vector_db(chunk_documents)
```

## 📈 Performance Comparison

| Strategy | Speed | Quality | Use Case |
|----------|-------|---------|----------|
| Fixed-Size | ⚡⚡⚡⚡⚡ | ⭐⭐ | High-throughput processing |
| Recursive | ⚡⚡⚡⚡ | ⭐⭐⭐ | General purpose |
| Document | ⚡⚡⚡⚡ | ⭐⭐⭐⭐ | Structured documents |
| Semantic | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | Quality-critical retrieval |
| LLM-Based | ⚡⚡ | ⭐⭐⭐⭐⭐ | Complex documents |
| Agentic | ⚡ | ⭐⭐⭐⭐⭐ | Maximum quality |
| Late | ⚡⚡ | ⭐⭐⭐⭐⭐ | Context-dependent |
| Hierarchical | ⚡⚡⚡ | ⭐⭐⭐⭐ | Multi-resolution search |

## 🧪 Testing

Run the example to see all strategies in action:

```bash
python examples/chunking_strategies_example.py
```

## 📚 Best Practices

### Choosing Chunk Size

- **Small chunks (128-256 tokens)**: Better for precise retrieval, more granular
- **Medium chunks (512-1024 tokens)**: Balanced approach, most common
- **Large chunks (2048+ tokens)**: More context, but may exceed model limits

### Overlap Configuration

- **No overlap (0)**: Maximum efficiency, potential context loss
- **Small overlap (10-20%)**: Good balance
- **Large overlap (30-50%)**: Maximum context preservation, storage overhead

### Strategy Selection Guide

1. **Start simple**: Try `recursive` or `document_based`
2. **Add intelligence**: Upgrade to `semantic` for quality boost
3. **Optimize**: Use `hierarchical` for multi-resolution
4. **Special cases**: Use `llm_based` or `agentic` for critical documents

## 🔗 Related Documentation

- [RAG Implementation Guide](../docs/RAG_IMPLEMENTATION_GUIDE.md)
- [Vector Database Best Practices](../docs/VECTOR_DATABASE_BEST_PRACTICES.md)
- [Semantic Search Guide](../docs/VECTOR_SEARCH_GUIDE.md)

## 📄 References

Based on research and best practices from:
- LangChain text splitters
- LlamaIndex node parsers
- Pinecone chunking strategies
- Industry RAG implementation patterns

## 🤝 Contributing

To add a new chunking strategy:

1. Extend `ChunkingStrategy` base class
2. Implement `chunk()` method
3. Add to `ChunkingFactory.STRATEGIES`
4. Update documentation
5. Add tests

## 📝 License

Part of DocEX - see main LICENSE file.
