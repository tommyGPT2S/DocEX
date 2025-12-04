"""
Text Chunking Strategies for DocEX RAG System

This module implements multiple chunking strategies optimized for different
document types and RAG use cases. Based on industry best practices for
semantic search and vector database operations.

Strategies:
- Fixed-Size: Fast, deterministic token/character-based splitting
- Recursive: Hierarchical splitting with structure preservation
- Document-Based: Split at document boundaries (headers, sections)
- Semantic: Topic-aware splitting using embeddings
- LLM-Based: Context-aware splitting using language models
- Agentic: Autonomous AI-driven chunking decisions
- Late: Whole-document embedding with derived chunk embeddings
- Hierarchical: Multi-level document structure preservation
"""

from .base import ChunkingStrategy, Chunk, ChunkingConfig
from .fixed_size import FixedSizeChunking
from .recursive import RecursiveChunking
from .document_based import DocumentBasedChunking
from .semantic import SemanticChunking
from .llm_based import LLMBasedChunking
from .agentic import AgenticChunking
from .late import LateChunking
from .hierarchical import HierarchicalChunking
from .factory import ChunkingFactory

__all__ = [
    # Base classes
    'ChunkingStrategy',
    'Chunk',
    'ChunkingConfig',
    
    # Chunking strategies
    'FixedSizeChunking',
    'RecursiveChunking',
    'DocumentBasedChunking',
    'SemanticChunking',
    'LLMBasedChunking',
    'AgenticChunking',
    'LateChunking',
    'HierarchicalChunking',
    
    # Factory
    'ChunkingFactory',
]

__version__ = '1.0.0'
