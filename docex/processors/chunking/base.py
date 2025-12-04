"""
Base classes for chunking strategies
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib


@dataclass
class Chunk:
    """Represents a single chunk of text"""
    
    id: str  # Unique chunk identifier
    content: str  # The actual text content
    start_idx: int  # Starting index in original document
    end_idx: int  # Ending index in original document
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Optional fields
    parent_id: Optional[str] = None  # For hierarchical chunking
    children_ids: List[str] = field(default_factory=list)  # For hierarchical chunking
    embedding: Optional[List[float]] = None  # Cached embedding
    semantic_level: Optional[int] = None  # For hierarchical chunking (0=doc, 1=section, etc.)
    
    def __post_init__(self):
        """Generate ID if not provided"""
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate unique ID based on content and position"""
        hash_input = f"{self.content[:100]}{self.start_idx}{self.end_idx}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]
    
    @property
    def size(self) -> int:
        """Return chunk size in characters"""
        return len(self.content)
    
    @property
    def token_count(self) -> int:
        """Estimate token count (rough approximation: ~4 chars per token)"""
        return len(self.content) // 4
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'content': self.content,
            'start_idx': self.start_idx,
            'end_idx': self.end_idx,
            'metadata': self.metadata,
            'parent_id': self.parent_id,
            'children_ids': self.children_ids,
            'semantic_level': self.semantic_level,
            'size': self.size,
            'token_count': self.token_count,
        }


@dataclass
class ChunkingConfig:
    """Configuration for chunking strategies"""
    
    # Common parameters
    chunk_size: int = 512  # Target chunk size (tokens or characters)
    chunk_overlap: int = 50  # Overlap between chunks
    min_chunk_size: int = 100  # Minimum chunk size
    max_chunk_size: int = 2000  # Maximum chunk size
    
    # Strategy-specific parameters
    preserve_structure: bool = True  # Try to keep semantic structure
    split_on_sentences: bool = True  # Split at sentence boundaries when possible
    split_on_paragraphs: bool = True  # Split at paragraph boundaries when possible
    
    # Semantic chunking parameters
    similarity_threshold: float = 0.8  # For semantic boundary detection
    embedding_batch_size: int = 32  # Batch size for embedding generation
    
    # Document-based parameters
    header_tags: List[str] = field(default_factory=lambda: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    section_markers: List[str] = field(default_factory=lambda: ['#', '##', '###'])
    
    # LLM-based parameters
    llm_model: Optional[str] = None
    llm_temperature: float = 0.0
    
    # Performance parameters
    enable_caching: bool = True
    parallel_processing: bool = True
    
    # Metadata
    include_metadata: bool = True
    metadata_fields: List[str] = field(default_factory=list)


class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies"""
    
    def __init__(self, config: Optional[ChunkingConfig] = None):
        """
        Initialize chunking strategy
        
        Args:
            config: Chunking configuration
        """
        self.config = config or ChunkingConfig()
        self.stats = {
            'chunks_created': 0,
            'avg_chunk_size': 0,
            'documents_processed': 0,
            'processing_time': 0.0,
        }
    
    @abstractmethod
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """
        Split text into chunks
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata to attach to chunks
            
        Returns:
            List of Chunk objects
        """
        pass
    
    def _add_metadata(self, chunk: Chunk, base_metadata: Optional[Dict[str, Any]] = None):
        """Add metadata to chunk"""
        if not self.config.include_metadata:
            return
        
        if base_metadata:
            chunk.metadata.update(base_metadata)
        
        chunk.metadata.update({
            'strategy': self.__class__.__name__,
            'created_at': datetime.utcnow().isoformat(),
            'size': chunk.size,
            'token_count': chunk.token_count,
        })
    
    def _update_stats(self, chunks: List[Chunk], processing_time: float):
        """Update processing statistics"""
        self.stats['chunks_created'] += len(chunks)
        self.stats['documents_processed'] += 1
        self.stats['processing_time'] += processing_time
        
        if len(chunks) > 0:
            avg_size = sum(c.size for c in chunks) / len(chunks)
            total_docs = self.stats['documents_processed']
            current_avg = self.stats['avg_chunk_size']
            self.stats['avg_chunk_size'] = (current_avg * (total_docs - 1) + avg_size) / total_docs
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset processing statistics"""
        self.stats = {
            'chunks_created': 0,
            'avg_chunk_size': 0,
            'documents_processed': 0,
            'processing_time': 0.0,
        }
    
    @staticmethod
    def _split_by_separator(text: str, separator: str, keep_separator: bool = True) -> List[str]:
        """Split text by separator, optionally keeping the separator"""
        if separator not in text:
            return [text]
        
        parts = text.split(separator)
        if keep_separator:
            return [p + separator for p in parts[:-1]] + [parts[-1]]
        return parts
    
    @staticmethod
    def _split_by_sentences(text: str) -> List[str]:
        """Split text into sentences"""
        import re
        # Simple sentence splitting (can be improved with NLTK or spaCy)
        sentence_endings = r'[.!?]+[\s\n]+'
        sentences = re.split(sentence_endings, text)
        return [s.strip() for s in sentences if s.strip()]
    
    @staticmethod
    def _split_by_paragraphs(text: str) -> List[str]:
        """Split text into paragraphs"""
        paragraphs = text.split('\n\n')
        return [p.strip() for p in paragraphs if p.strip()]
