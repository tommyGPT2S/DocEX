"""
Chunking Factory

Factory for creating and managing different chunking strategies.
"""

from typing import Dict, Any, Optional, Type
from .base import ChunkingStrategy, ChunkingConfig
from .fixed_size import FixedSizeChunking
from .recursive import RecursiveChunking
from .document_based import DocumentBasedChunking
from .semantic import SemanticChunking
from .llm_based import LLMBasedChunking
from .agentic import AgenticChunking
from .late import LateChunking
from .hierarchical import HierarchicalChunking


class ChunkingFactory:
    """
    Factory for creating chunking strategies
    
    Provides a centralized way to instantiate and configure
    different chunking strategies based on use case.
    """
    
    # Map strategy names to classes
    STRATEGIES: Dict[str, Type[ChunkingStrategy]] = {
        'fixed': FixedSizeChunking,
        'fixed_size': FixedSizeChunking,
        'recursive': RecursiveChunking,
        'document': DocumentBasedChunking,
        'document_based': DocumentBasedChunking,
        'semantic': SemanticChunking,
        'llm': LLMBasedChunking,
        'llm_based': LLMBasedChunking,
        'agentic': AgenticChunking,
        'late': LateChunking,
        'late_chunking': LateChunking,
        'hierarchical': HierarchicalChunking,
    }
    
    # Recommended strategies for different document types
    RECOMMENDATIONS = {
        'email': 'fixed_size',
        'faq': 'fixed_size',
        'note': 'fixed_size',
        'documentation': 'document_based',
        'manual': 'hierarchical',
        'handbook': 'hierarchical',
        'article': 'document_based',
        'blog': 'semantic',
        'research_paper': 'semantic',
        'textbook': 'semantic',
        'whitepaper': 'semantic',
        'legal': 'llm_based',
        'contract': 'llm_based',
        'medical': 'llm_based',
        'regulation': 'agentic',
        'compliance': 'agentic',
        'policy': 'agentic',
        'case_study': 'late_chunking',
        'analysis': 'late_chunking',
        'report': 'hierarchical',
    }
    
    @classmethod
    def create(
        cls,
        strategy: str,
        config: Optional[ChunkingConfig] = None,
        **kwargs
    ) -> ChunkingStrategy:
        """
        Create a chunking strategy
        
        Args:
            strategy: Strategy name (e.g., 'fixed', 'semantic', 'hierarchical')
            config: Optional chunking configuration
            **kwargs: Additional strategy-specific arguments
            
        Returns:
            Instantiated chunking strategy
            
        Raises:
            ValueError: If strategy name is unknown
        """
        strategy_lower = strategy.lower()
        
        if strategy_lower not in cls.STRATEGIES:
            available = ', '.join(cls.STRATEGIES.keys())
            raise ValueError(
                f"Unknown chunking strategy: '{strategy}'. "
                f"Available strategies: {available}"
            )
        
        strategy_class = cls.STRATEGIES[strategy_lower]
        
        # Create instance with appropriate arguments
        if config is None:
            config = ChunkingConfig()
        
        return strategy_class(config=config, **kwargs)
    
    @classmethod
    def create_for_document_type(
        cls,
        document_type: str,
        config: Optional[ChunkingConfig] = None,
        **kwargs
    ) -> ChunkingStrategy:
        """
        Create recommended strategy for a document type
        
        Args:
            document_type: Type of document (e.g., 'email', 'research_paper')
            config: Optional chunking configuration
            **kwargs: Additional strategy-specific arguments
            
        Returns:
            Instantiated chunking strategy
        """
        doc_type_lower = document_type.lower()
        
        # Get recommended strategy
        strategy = cls.RECOMMENDATIONS.get(doc_type_lower, 'recursive')
        
        return cls.create(strategy, config, **kwargs)
    
    @classmethod
    def get_recommendation(cls, document_type: str) -> str:
        """
        Get recommended strategy name for a document type
        
        Args:
            document_type: Type of document
            
        Returns:
            Recommended strategy name
        """
        return cls.RECOMMENDATIONS.get(document_type.lower(), 'recursive')
    
    @classmethod
    def list_strategies(cls) -> Dict[str, str]:
        """
        List all available strategies with descriptions
        
        Returns:
            Dict mapping strategy names to descriptions
        """
        return {
            'fixed_size': 'Fast, deterministic token/character-based splitting',
            'recursive': 'Hierarchical splitting with structure preservation',
            'document_based': 'Split at document boundaries (headers, sections)',
            'semantic': 'Topic-aware splitting using embeddings',
            'llm_based': 'Context-aware splitting using language models',
            'agentic': 'Autonomous AI-driven chunking decisions',
            'late_chunking': 'Whole-document embedding with derived chunks',
            'hierarchical': 'Multi-level document structure preservation',
        }
    
    @classmethod
    def create_optimal(
        cls,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        config: Optional[ChunkingConfig] = None,
        **kwargs
    ) -> ChunkingStrategy:
        """
        Automatically select optimal strategy based on text characteristics
        
        Args:
            text: Input text to analyze
            metadata: Optional metadata about the document
            config: Optional chunking configuration
            **kwargs: Additional strategy-specific arguments
            
        Returns:
            Optimal chunking strategy for the text
        """
        # Analyze text characteristics
        text_length = len(text)
        has_headers = any(marker in text for marker in ['#', '<h1', '<h2', 'Chapter'])
        has_structure = '\n\n' in text
        is_short = text_length < 1000
        
        # Check metadata for hints
        doc_type = None
        if metadata:
            doc_type = metadata.get('type') or metadata.get('document_type')
        
        # Use metadata hint if available
        if doc_type:
            strategy = cls.get_recommendation(doc_type)
        # Short documents: use fixed
        elif is_short:
            strategy = 'fixed_size'
        # Has clear structure: use document-based
        elif has_headers:
            strategy = 'document_based'
        # Has some structure: use recursive
        elif has_structure:
            strategy = 'recursive'
        # Default: recursive
        else:
            strategy = 'recursive'
        
        return cls.create(strategy, config, **kwargs)


# Convenience function
def chunk_text(
    text: str,
    strategy: str = 'auto',
    config: Optional[ChunkingConfig] = None,
    metadata: Optional[Dict[str, Any]] = None,
    **kwargs
):
    """
    Convenience function to chunk text
    
    Args:
        text: Text to chunk
        strategy: Chunking strategy ('auto' for automatic selection)
        config: Optional configuration
        metadata: Optional metadata
        **kwargs: Additional arguments
        
    Returns:
        List of chunks
    """
    import asyncio
    
    if strategy == 'auto':
        chunker = ChunkingFactory.create_optimal(text, metadata, config, **kwargs)
    else:
        chunker = ChunkingFactory.create(strategy, config, **kwargs)
    
    return asyncio.run(chunker.chunk(text, metadata))
