"""
DocEX Processors Module

Contains various document processors including:
- Base processing framework
- LLM adapters (OpenAI, Claude, Local LLM)
- Vector processing (semantic search, vector indexing)
- RAG (Retrieval-Augmented Generation) services
- Specialized processors (CSV, PDF, etc.)
"""

from . import base
from . import factory
from . import llm
from . import vector

# Import RAG module if available
try:
    from . import rag
    __all__ = ['base', 'factory', 'llm', 'vector', 'rag']
except ImportError:
    __all__ = ['base', 'factory', 'llm', 'vector']
