"""
Fixed-Size Chunking Strategy

Splits text strictly by token or character count.
- O(1) boundary selection
- No parsing or linguistic analysis
- Deterministic and extremely fast

Best for: Speed-critical tasks, short emails, FAQs, internal notes
"""

import time
from typing import List, Dict, Any, Optional
from .base import ChunkingStrategy, Chunk, ChunkingConfig


class FixedSizeChunking(ChunkingStrategy):
    """
    Fixed-size chunking with configurable overlap
    
    Technical Properties:
    - O(n) complexity where n is document length
    - No semantic awareness
    - Configurable overlap for context preservation
    - Supports both character and token-based chunking
    """
    
    def __init__(self, config: Optional[ChunkingConfig] = None, use_tokens: bool = False):
        """
        Initialize fixed-size chunking
        
        Args:
            config: Chunking configuration
            use_tokens: If True, count tokens; otherwise count characters
        """
        super().__init__(config)
        self.use_tokens = use_tokens
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """
        Split text into fixed-size chunks
        
        Args:
            text: Input text
            metadata: Optional metadata
            
        Returns:
            List of fixed-size chunks
        """
        start_time = time.time()
        chunks = []
        
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        
        # Calculate unit size
        if self.use_tokens:
            # Rough token count (4 chars ≈ 1 token)
            char_per_unit = 4
        else:
            char_per_unit = 1
        
        chunk_chars = chunk_size * char_per_unit
        overlap_chars = overlap * char_per_unit
        
        # Split into chunks
        start_idx = 0
        chunk_id = 0
        
        while start_idx < len(text):
            # Calculate end index
            end_idx = min(start_idx + chunk_chars, len(text))
            
            # Extract chunk content
            chunk_content = text[start_idx:end_idx].strip()
            
            # Only create chunk if it meets minimum size
            if len(chunk_content) >= self.config.min_chunk_size:
                chunk = Chunk(
                    id=f"fixed_{chunk_id:04d}",
                    content=chunk_content,
                    start_idx=start_idx,
                    end_idx=end_idx,
                    metadata={'chunk_number': chunk_id}
                )
                
                self._add_metadata(chunk, metadata)
                chunks.append(chunk)
                chunk_id += 1
            
            # Move to next chunk with overlap
            start_idx = end_idx - overlap_chars
            
            # Prevent infinite loop
            if start_idx >= len(text) or (end_idx == len(text)):
                break
        
        processing_time = time.time() - start_time
        self._update_stats(chunks, processing_time)
        
        return chunks
    
    def chunk_by_token_count(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """
        Synchronous version for token-based chunking
        Useful for simple use cases
        """
        import asyncio
        return asyncio.run(self.chunk(text, metadata))
