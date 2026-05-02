"""
Text Chunking Strategies for DocEX RAG System

This module implements deterministic chunking strategies optimized for
document storage and vector indexing.

Strategies:
- Fixed-Size: Fast, deterministic token/character-based splitting
- Recursive: Hierarchical splitting with structure preservation
- Document-Based: Split at document boundaries (headers, sections)
- Hierarchical: Multi-level document structure preservation
"""

from .base import ChunkingStrategy, Chunk, ChunkingConfig
from .fixed_size import FixedSizeChunking
from .recursive import RecursiveChunking
from .document_based import DocumentBasedChunking
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
    'HierarchicalChunking',
    
    # Factory
    'ChunkingFactory',
]

__version__ = '1.0.0'
