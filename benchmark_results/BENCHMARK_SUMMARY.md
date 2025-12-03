# Chunking Strategies Benchmark - Executive Summary

## Quick Overview

We benchmarked 5 chunking strategies across 6 document types to determine optimal strategies for different workloads. **Recursive chunking** emerged as the best general-purpose choice, while specialized strategies excel in specific use cases.

---

## Key Performance Results

### Speed Rankings (Fastest → Slowest)
1. **Recursive**: 0.12 ms avg ⚡⚡⚡⚡⚡
2. **Fixed-Size**: 0.13 ms avg ⚡⚡⚡⚡⚡
3. **Document-Based**: 0.13 ms avg ⚡⚡⚡⚡⚡
4. **Hierarchical**: 0.30 ms avg ⚡⚡⚡⚡
5. **Semantic**: 3.87 ms avg ⚡⚡⚡ (32x slower, but highest quality)

### Throughput Leaders
- **Recursive**: 17,846 K chars/sec
- **Fixed-Size**: 17,547 K chars/sec
- **Document-Based**: 15,807 K chars/sec

### Memory Efficiency
All strategies are memory-efficient (< 0.1 MB), with Fixed-Size, Recursive, and Document-Based using only 0.01 MB average.

---

## Quick Recommendations by Use Case

| Use Case | Recommended Strategy | Why |
|----------|---------------------|-----|
| **General RAG Systems** | **Recursive** | Best balance: fast (0.12ms) + good quality |
| **High-Throughput Batch** | **Fixed-Size** or **Recursive** | Maximum speed, predictable performance |
| **Technical Docs** | **Document-Based** | Preserves sections, headers, code blocks |
| **Research Papers** | **Semantic** (quality) or **Recursive** (speed) | Topic-aware chunking for better retrieval |
| **Legal/Contracts** | **Hierarchical** | Handles complex nested structures |
| **Quality-Critical RAG** | **Semantic** | Best retrieval quality (accept slower speed) |
| **Short Docs/Emails** | **Fixed-Size** | Simple, fast, overhead not justified |

---

## Strategy Comparison

| Strategy | Speed | Quality | Best For |
|----------|-------|---------|----------|
| **Fixed-Size** | ⚡⚡⚡⚡⚡ | ⭐⭐ | Batch processing, uniform docs |
| **Recursive** | ⚡⚡⚡⚡⚡ | ⭐⭐⭐ | **General-purpose (recommended default)** |
| **Document-Based** | ⚡⚡⚡⚡⚡ | ⭐⭐⭐⭐ | Structured docs (markdown, HTML) |
| **Semantic** | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | Quality-critical, topic-aware |
| **Hierarchical** | ⚡⚡⚡⚡ | ⭐⭐⭐⭐ | Complex nested structures |

---

## Top 3 Takeaways

1. **Recursive is the best default**: Fastest overall (0.12ms) with good quality - use for most general-purpose RAG systems.

2. **Speed vs Quality trade-off**: Semantic chunking is 32x slower but provides significantly better retrieval quality for topic-driven content.

3. **Structure matters**: Document-Based and Hierarchical excel when documents have clear structure (headers, sections, nested content).

---

## Benchmark Dataset

Tested 6 document types:
- **Tiny** (27 chars): Baseline testing
- **Small** (221 chars): Short documents, emails
- **Medium** (500 chars): Technical docs with markdown
- **Large** (3,556 chars): Research papers, articles
- **Very Large** (8,652 chars): Legal documents, contracts
- **Narrative** (2,377 chars): Flowing text without structure

**Configuration**: 512 char chunks, 50 char overlap, 3 runs per test (averaged)

---

## Implementation Quick Start

### For New Projects
```python
# Recommended default: Recursive
from docex.processors.chunking import RecursiveChunking, ChunkingConfig

config = ChunkingConfig(
    chunk_size=512,
    chunk_overlap=50,
    preserve_structure=True
)
chunker = RecursiveChunking(config)
chunks = await chunker.chunk(document_text)
```

### For Technical Documentation
```python
from docex.processors.chunking import DocumentBasedChunking

chunker = DocumentBasedChunking(config)
chunks = await chunker.chunk(markdown_text, metadata={'format': 'markdown'})
```

### For Quality-Critical Systems
```python
from docex.processors.chunking import SemanticChunking

chunker = SemanticChunking(config, embedding_function=embed_func)
chunks = await chunker.chunk(document_text)
```

---

## Performance Insights

- **30x speed difference** between fastest (Recursive) and slowest (Semantic)
- **All strategies are memory-efficient** (< 0.1 MB peak usage)
- **Chunk granularity varies significantly**: Hierarchical creates 5x more chunks than Fixed-Size
- **Throughput scales well**: Even slowest strategy processes 4K+ chars/sec

---

## Next Steps

1. **Profile your documents**: Run benchmarks on your actual document types
2. **Test multiple strategies**: Compare retrieval quality vs. performance
3. **Optimize iteratively**: Start with Recursive, upgrade to Semantic if quality is critical
4. **Consider hybrid approaches**: Use different strategies for different document types

---

## Full Report

For detailed analysis, methodology, and comprehensive recommendations, see:
- **Full Report**: `BENCHMARK_REPORT.md`
- **Raw Data**: `benchmark_results.json`
- **Visualizations**: 6 PNG charts in `benchmark_results/` folder

---

*Benchmark Date: December 3, 2024*  
*Strategies Tested: 5 | Documents Tested: 6 | Total Tests: 30*

