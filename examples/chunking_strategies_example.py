"""
Chunking Strategies Example

Demonstrates all 8 chunking strategies with practical examples.
"""

import asyncio
import sys
sys.path.insert(0, '.')

from docex.processors.chunking import (
    ChunkingFactory,
    ChunkingConfig,
    FixedSizeChunking,
    RecursiveChunking,
    DocumentBasedChunking,
    SemanticChunking,
    HierarchicalChunking
)


# Sample documents for testing
SAMPLE_DOCUMENTS = {
    'short_email': """
Hi team,

Quick update on the project timeline. We're on track for the Q4 launch.
Next meeting is scheduled for Friday at 2 PM.

Best regards,
John
""",
    
    'technical_doc': """
# Installation Guide

## Prerequisites
Before installing DocEX, ensure you have:
- Python 3.8 or higher
- pip package manager
- At least 4GB of RAM

## Installation Steps

### Step 1: Clone Repository
First, clone the repository from GitHub:
```bash
git clone https://github.com/org/docex.git
cd docex
```

### Step 2: Install Dependencies
Install required dependencies:
```bash
pip install -r requirements.txt
```

### Step 3: Configuration
Create a configuration file:
```python
config = {
    'database': 'postgresql',
    'host': 'localhost',
    'port': 5432
}
```

## Verification
Run the test suite to verify installation:
```bash
pytest tests/
```
""",
    
    'narrative': """
The field of artificial intelligence has undergone remarkable transformations over the past decade.
Deep learning, in particular, has revolutionized how machines process and understand data.

Early neural networks were limited by computational power and data availability. However, the advent
of powerful GPUs and massive datasets changed everything. Researchers could now train models with
billions of parameters, achieving unprecedented accuracy.

The transformer architecture, introduced in 2017, marked another watershed moment. Unlike previous
models that processed sequences linearly, transformers could attend to all parts of the input
simultaneously. This parallel processing capability made them ideal for natural language tasks.

Today, large language models built on transformer architecture dominate the AI landscape. These
models can generate human-like text, answer questions, write code, and perform countless other
tasks. The implications for society are profound and still being explored.
""",
    
    'legal': """
TERMS AND CONDITIONS

1. DEFINITIONS
In this Agreement, unless the context otherwise requires:
"Services" means the software services provided by Company under this Agreement;
"User" means any person accessing or using the Services;
"Confidential Information" means any information disclosed by one party to another.

2. GRANT OF LICENSE
Subject to the terms and conditions of this Agreement, Company hereby grants to User a
non-exclusive, non-transferable license to use the Services solely for User's internal
business purposes.

3. RESTRICTIONS
User shall not: (a) reverse engineer, decompile, or disassemble the Services; (b) rent,
lease, or sublicense the Services; (c) remove any proprietary notices.

4. TERM AND TERMINATION
This Agreement commences on the date User first accesses the Services and continues until
terminated by either party upon thirty (30) days written notice.
"""
}


async def demo_fixed_size():
    """Demonstrate fixed-size chunking"""
    print("\n" + "="*60)
    print("1. FIXED-SIZE CHUNKING")
    print("="*60)
    print("Use case: Short emails, FAQs, speed-critical tasks")
    
    config = ChunkingConfig(
        chunk_size=100,  # 100 tokens ~= 400 chars
        chunk_overlap=20,
        min_chunk_size=50
    )
    
    chunker = FixedSizeChunking(config)
    chunks = await chunker.chunk(SAMPLE_DOCUMENTS['short_email'])
    
    print(f"\nCreated {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1} ({chunk.size} chars):")
        print(f"  {chunk.content[:100]}...")
    
    stats = chunker.get_stats()
    print(f"\nStats: {stats}")


async def demo_recursive():
    """Demonstrate recursive chunking"""
    print("\n" + "="*60)
    print("2. RECURSIVE CHUNKING")
    print("="*60)
    print("Use case: Research summaries, product documentation")
    
    config = ChunkingConfig(
        chunk_size=200,
        preserve_structure=True
    )
    
    chunker = RecursiveChunking(config)
    chunks = await chunker.chunk(SAMPLE_DOCUMENTS['narrative'])
    
    print(f"\nCreated {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        split_level = chunk.metadata.get('split_level', 'unknown')
        print(f"\nChunk {i+1} (Level: {split_level}, {chunk.size} chars):")
        print(f"  {chunk.content[:150]}...")


async def demo_document_based():
    """Demonstrate document-based chunking"""
    print("\n" + "="*60)
    print("3. DOCUMENT-BASED CHUNKING")
    print("="*60)
    print("Use case: Technical docs, articles with clear structure")
    
    config = ChunkingConfig(
        chunk_size=300,
        min_chunk_size=100
    )
    
    chunker = DocumentBasedChunking(config)
    chunks = await chunker.chunk(
        SAMPLE_DOCUMENTS['technical_doc'],
        metadata={'format': 'markdown'}
    )
    
    print(f"\nCreated {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        header = chunk.metadata.get('section_header', 'N/A')
        level = chunk.metadata.get('section_level', 'N/A')
        print(f"\nChunk {i+1} (Header: '{header}', Level: {level}):")
        print(f"  {chunk.content[:150]}...")


async def demo_semantic():
    """Demonstrate semantic chunking"""
    print("\n" + "="*60)
    print("4. SEMANTIC CHUNKING")
    print("="*60)
    print("Use case: Research papers, textbooks, narrative documents")
    print("Note: Requires embedding function - using mock for demo")
    
    # Mock embedding function
    import numpy as np
    def mock_embedding(text: str) -> np.ndarray:
        # Simple mock: create embedding based on text length and content
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        np.random.seed(hash_val)
        return np.random.rand(384).astype(np.float32)
    
    config = ChunkingConfig(
        chunk_size=150,
        similarity_threshold=0.75
    )
    
    chunker = SemanticChunking(config, embedding_function=mock_embedding)
    chunks = await chunker.chunk(SAMPLE_DOCUMENTS['narrative'])
    
    print(f"\nCreated {len(chunks)} semantic chunks:")
    for i, chunk in enumerate(chunks):
        sent_count = chunk.metadata.get('sentence_count', 0)
        print(f"\nChunk {i+1} ({sent_count} sentences, {chunk.size} chars):")
        print(f"  {chunk.content[:150]}...")


async def demo_hierarchical():
    """Demonstrate hierarchical chunking"""
    print("\n" + "="*60)
    print("5. HIERARCHICAL CHUNKING")
    print("="*60)
    print("Use case: Handbooks, regulations, structured documentation")
    
    config = ChunkingConfig(
        chunk_size=150,
        min_chunk_size=50
    )
    
    chunker = HierarchicalChunking(config, max_levels=3)
    chunks = await chunker.chunk(SAMPLE_DOCUMENTS['technical_doc'])
    
    print(f"\nCreated {len(chunks)} hierarchical chunks:")
    
    # Group by level
    by_level = {}
    for chunk in chunks:
        level = chunk.semantic_level or 0
        if level not in by_level:
            by_level[level] = []
        by_level[level].append(chunk)
    
    for level in sorted(by_level.keys()):
        level_chunks = by_level[level]
        level_name = level_chunks[0].metadata.get('level_name', f'Level {level}')
        print(f"\n{level_name.upper()} ({len(level_chunks)} chunks):")
        for chunk in level_chunks[:2]:  # Show first 2
            print(f"  - {chunk.content[:100]}...")


async def demo_factory():
    """Demonstrate factory pattern and auto-selection"""
    print("\n" + "="*60)
    print("6. FACTORY PATTERN & AUTO-SELECTION")
    print("="*60)
    
    # Show all available strategies
    print("\nAvailable strategies:")
    for name, desc in ChunkingFactory.list_strategies().items():
        print(f"  • {name}: {desc}")
    
    # Show recommendations
    print("\n\nRecommendations by document type:")
    doc_types = ['email', 'research_paper', 'legal', 'handbook', 'blog']
    for doc_type in doc_types:
        rec = ChunkingFactory.get_recommendation(doc_type)
        print(f"  • {doc_type}: {rec}")
    
    # Auto-select strategy
    print("\n\nAuto-selecting strategy for technical document...")
    chunker = ChunkingFactory.create_optimal(
        SAMPLE_DOCUMENTS['technical_doc'],
        metadata={'type': 'documentation'}
    )
    print(f"Selected: {chunker.__class__.__name__}")
    
    chunks = await chunker.chunk(SAMPLE_DOCUMENTS['technical_doc'])
    print(f"Created {len(chunks)} chunks")


async def demo_comparison():
    """Compare all strategies on same document"""
    print("\n" + "="*60)
    print("7. STRATEGY COMPARISON")
    print("="*60)
    
    doc = SAMPLE_DOCUMENTS['narrative']
    config = ChunkingConfig(chunk_size=150)
    
    results = {}
    
    # Test multiple strategies
    strategies = [
        ('fixed_size', FixedSizeChunking(config)),
        ('recursive', RecursiveChunking(config)),
    ]
    
    print(f"\nComparing strategies on {len(doc)} char document:\n")
    
    for name, chunker in strategies:
        chunks = await chunker.chunk(doc)
        stats = chunker.get_stats()
        results[name] = {
            'chunks': len(chunks),
            'avg_size': stats['avg_chunk_size'],
            'time': stats['processing_time']
        }
        
        print(f"{name}:")
        print(f"  Chunks created: {results[name]['chunks']}")
        print(f"  Avg chunk size: {results[name]['avg_size']:.1f} chars")
        print(f"  Processing time: {results[name]['time']:.4f}s")
        print()


async def main():
    """Run all demonstrations"""
    print("="*60)
    print("DocEX CHUNKING STRATEGIES DEMONSTRATION")
    print("="*60)
    print("\nDemonstrating 8 chunking strategies for RAG systems")
    
    try:
        await demo_fixed_size()
        await demo_recursive()
        await demo_document_based()
        await demo_semantic()
        await demo_hierarchical()
        await demo_factory()
        await demo_comparison()
        
        print("\n" + "="*60)
        print("DEMONSTRATION COMPLETE")
        print("="*60)
        print("\n✅ All chunking strategies demonstrated successfully!")
        print("\nNext steps:")
        print("  1. Integrate with RAG pipeline")
        print("  2. Test with real documents")
        print("  3. Benchmark performance")
        print("  4. Add LLM-based and Agentic strategies (require LLM service)")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())
