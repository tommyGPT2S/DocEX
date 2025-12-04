"""
Recursive Chunking Strategy

Repeatedly divides text into smaller segments until each meets target size,
preserving internal structure when possible.

Technical Properties:
- Recursive splitting at paragraph → sentence → clause levels
- Maintains partial hierarchy
- Balances structure retention with size constraints

Best for: Research summaries, product documentation
"""

import time
from typing import List, Dict, Any, Optional
from .base import ChunkingStrategy, Chunk, ChunkingConfig


class RecursiveChunking(ChunkingStrategy):
    """
    Recursive text splitting with structure preservation
    
    Split hierarchy:
    1. Try splitting at paragraph boundaries (\n\n)
    2. If still too large, split at sentence boundaries
    3. If still too large, split at clause boundaries (commas, semicolons)
    4. If still too large, fall back to character splitting
    """
    
    def __init__(self, config: Optional[ChunkingConfig] = None):
        """Initialize recursive chunking"""
        super().__init__(config)
        
        # Define split levels in order of preference
        self.split_levels = [
            ('\n\n', 'paragraph'),  # Paragraphs
            ('\n', 'line'),  # Lines
            ('. ', 'sentence'),  # Sentences
            (', ', 'clause'),  # Clauses
            (' ', 'word'),  # Words
        ]
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """
        Recursively split text into chunks
        
        Args:
            text: Input text
            metadata: Optional metadata
            
        Returns:
            List of recursively split chunks
        """
        start_time = time.time()
        
        # Perform recursive splitting
        chunks = self._recursive_split(text, start_idx=0, depth=0)
        
        # Add metadata to all chunks
        for i, chunk in enumerate(chunks):
            chunk.metadata['chunk_number'] = i
            self._add_metadata(chunk, metadata)
        
        processing_time = time.time() - start_time
        self._update_stats(chunks, processing_time)
        
        return chunks
    
    def _recursive_split(
        self,
        text: str,
        start_idx: int,
        depth: int,
        level_idx: int = 0
    ) -> List[Chunk]:
        """
        Recursively split text
        
        Args:
            text: Text to split
            start_idx: Starting index in original document
            depth: Current recursion depth
            level_idx: Current split level index
            
        Returns:
            List of chunks
        """
        # Base case: text is small enough
        if len(text) <= self.config.chunk_size * 4:  # Convert to chars
            if len(text) >= self.config.min_chunk_size:
                return [Chunk(
                    id=f"recursive_{start_idx}_{depth}",
                    content=text.strip(),
                    start_idx=start_idx,
                    end_idx=start_idx + len(text),
                    metadata={'depth': depth, 'split_level': 'final'}
                )]
            return []
        
        # Try to split at current level
        if level_idx < len(self.split_levels):
            separator, level_name = self.split_levels[level_idx]
            
            if separator in text:
                segments = self._split_by_separator(text, separator, keep_separator=True)
                
                # Combine small segments
                combined_segments = self._combine_small_segments(
                    segments,
                    min_size=self.config.min_chunk_size
                )
                
                # Check if we successfully reduced size
                if len(combined_segments) > 1:
                    chunks = []
                    current_idx = start_idx
                    
                    for segment in combined_segments:
                        # Recursively process each segment
                        segment_chunks = self._recursive_split(
                            segment,
                            start_idx=current_idx,
                            depth=depth + 1,
                            level_idx=level_idx + 1
                        )
                        
                        # Update split level metadata
                        for chunk in segment_chunks:
                            if 'split_level' not in chunk.metadata:
                                chunk.metadata['split_level'] = level_name
                        
                        chunks.extend(segment_chunks)
                        current_idx += len(segment)
                    
                    return chunks
        
        # Fallback: try next split level
        if level_idx + 1 < len(self.split_levels):
            return self._recursive_split(text, start_idx, depth, level_idx + 1)
        
        # Final fallback: character-based splitting
        return self._character_split(text, start_idx, depth)
    
    def _combine_small_segments(self, segments: List[str], min_size: int) -> List[str]:
        """Combine segments that are too small"""
        if not segments:
            return []
        
        combined = []
        current = segments[0]
        
        for segment in segments[1:]:
            if len(current) < min_size:
                current += segment
            else:
                combined.append(current)
                current = segment
        
        # Add the last segment
        if current:
            combined.append(current)
        
        return combined
    
    def _character_split(self, text: str, start_idx: int, depth: int) -> List[Chunk]:
        """Fallback character-based splitting"""
        chunks = []
        chunk_size = self.config.chunk_size * 4  # Convert to chars
        overlap = self.config.chunk_overlap * 4
        
        current_idx = start_idx
        local_idx = 0
        
        while local_idx < len(text):
            end_local = min(local_idx + chunk_size, len(text))
            chunk_content = text[local_idx:end_local].strip()
            
            if len(chunk_content) >= self.config.min_chunk_size:
                chunks.append(Chunk(
                    id=f"recursive_{current_idx}_{depth}_char",
                    content=chunk_content,
                    start_idx=current_idx + local_idx,
                    end_idx=current_idx + end_local,
                    metadata={'depth': depth, 'split_level': 'character'}
                ))
            
            local_idx = end_local - overlap
            if local_idx >= len(text):
                break
        
        return chunks
