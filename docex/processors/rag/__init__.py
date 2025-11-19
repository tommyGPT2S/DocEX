"""
RAG (Retrieval-Augmented Generation) Module for DocEX

This module provides advanced RAG capabilities with:
- Basic RAG service using existing semantic search
- Enhanced RAG with FAISS and Pinecone integration
- Vector database adapters
- Hybrid search capabilities
"""

from .rag_service import RAGService, RAGResult, AdvancedRAGService
from .vector_databases import (
    BaseVectorDatabase,
    FAISSVectorDatabase, 
    PineconeVectorDatabase,
    VectorDocument,
    VectorSearchResult,
    VectorDatabaseFactory
)
from .enhanced_rag_service import EnhancedRAGService, EnhancedRAGConfig

__all__ = [
    # Core RAG services
    'RAGService',
    'RAGResult', 
    'AdvancedRAGService',
    
    # Enhanced RAG with vector databases
    'EnhancedRAGService',
    'EnhancedRAGConfig',
    
    # Vector database components
    'BaseVectorDatabase',
    'FAISSVectorDatabase',
    'PineconeVectorDatabase', 
    'VectorDocument',
    'VectorSearchResult',
    'VectorDatabaseFactory'
]

# Version info
__version__ = '1.0.0'