"""
Late Chunking Strategy

Embeds the entire document first (single global embedding), then derives
individual chunk embeddings from the document-level context.

Technical Properties:
- Full-context embedding informs local chunk splits
- Useful for models that struggle with long-range dependencies
- More expensive as it requires whole-document embedding

Best for: Case studies, long-form analyses, comprehensive manuals
"""

import time
import numpy as np
from typing import List, Dict, Any, Optional
from .base import ChunkingStrategy, Chunk, ChunkingConfig


class LateChunking(ChunkingStrategy):
    """
    Late chunking with document-level context embedding
    
    Algorithm:
    1. Generate embedding for entire document
    2. Split document into preliminary chunks
    3. For each chunk, derive embedding that incorporates document context
    4. Store both local and global context embeddings
    """
    
    def __init__(
        self,
        config: Optional[ChunkingConfig] = None,
        embedding_function: Optional[callable] = None
    ):
        """
        Initialize late chunking
        
        Args:
            config: Chunking configuration
            embedding_function: Function to generate embeddings
        """
        super().__init__(config)
        self.embedding_function = embedding_function
        self.document_embedding = None
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """
        Split text with late chunking approach
        
        Args:
            text: Input text
            metadata: Optional metadata
            
        Returns:
            List of chunks with document-context-aware embeddings
        """
        start_time = time.time()
        
        if not self.embedding_function:
            raise ValueError("Embedding function is required for late chunking")
        
        # Step 1: Generate document-level embedding
        self.document_embedding = await self._get_document_embedding(text)
        
        # Step 2: Create preliminary chunks using recursive splitting
        preliminary_chunks = self._create_preliminary_chunks(text)
        
        # Step 3: Generate context-aware embeddings for each chunk
        final_chunks = await self._generate_chunk_embeddings(
            preliminary_chunks,
            text,
            self.document_embedding
        )
        
        # Add metadata
        for i, chunk in enumerate(final_chunks):
            chunk.metadata['chunk_number'] = i
            chunk.metadata['has_document_context'] = True
            self._add_metadata(chunk, metadata)
        
        processing_time = time.time() - start_time
        self._update_stats(final_chunks, processing_time)
        
        return final_chunks
    
    async def _get_document_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for entire document"""
        # Truncate if too long (most embedding models have limits)
        max_chars = 8000  # Adjust based on model
        truncated_text = text[:max_chars] if len(text) > max_chars else text
        
        # Generate embedding
        result = self.embedding_function(truncated_text)
        
        # Handle async
        if hasattr(result, '__await__'):
            result = await result
        
        # Convert to numpy
        if not isinstance(result, np.ndarray):
            result = np.array(result)
        
        return result
    
    def _create_preliminary_chunks(self, text: str) -> List[Chunk]:
        """Create initial chunks using simple strategy"""
        chunks = []
        
        # Use paragraph-based splitting
        paragraphs = self._split_by_paragraphs(text)
        
        current_parts = []
        current_size = 0
        start_idx = 0
        chunk_id = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            # Check if adding this paragraph exceeds target size
            if current_size + para_size > self.config.chunk_size * 4 and current_parts:
                # Create chunk
                chunk_content = '\n\n'.join(current_parts)
                chunks.append(Chunk(
                    id=f"late_{chunk_id:04d}",
                    content=chunk_content,
                    start_idx=start_idx,
                    end_idx=start_idx + len(chunk_content),
                    metadata={'chunk_type': 'preliminary'}
                ))
                
                # Reset
                current_parts = [para]
                current_size = para_size
                start_idx += len(chunk_content) + 2
                chunk_id += 1
            else:
                current_parts.append(para)
                current_size += para_size
        
        # Add remaining
        if current_parts:
            chunk_content = '\n\n'.join(current_parts)
            chunks.append(Chunk(
                id=f"late_{chunk_id:04d}",
                content=chunk_content,
                start_idx=start_idx,
                end_idx=start_idx + len(chunk_content),
                metadata={'chunk_type': 'preliminary'}
            ))
        
        return chunks
    
    async def _generate_chunk_embeddings(
        self,
        chunks: List[Chunk],
        full_text: str,
        doc_embedding: np.ndarray
    ) -> List[Chunk]:
        """Generate context-aware embeddings for each chunk"""
        
        for chunk in chunks:
            # Generate local chunk embedding
            local_embedding = await self._get_chunk_embedding(chunk.content)
            
            # Combine with document embedding
            # Use weighted average: 70% local, 30% document context
            context_embedding = self._combine_embeddings(
                local_embedding,
                doc_embedding,
                local_weight=0.7,
                global_weight=0.3
            )
            
            # Store both embeddings
            chunk.embedding = context_embedding.tolist()
            chunk.metadata['local_embedding_dim'] = len(local_embedding)
            chunk.metadata['has_global_context'] = True
            chunk.metadata['embedding_method'] = 'late_chunking'
        
        return chunks
    
    async def _get_chunk_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single chunk"""
        result = self.embedding_function(text)
        
        if hasattr(result, '__await__'):
            result = await result
        
        if not isinstance(result, np.ndarray):
            result = np.array(result)
        
        return result
    
    @staticmethod
    def _combine_embeddings(
        local_emb: np.ndarray,
        global_emb: np.ndarray,
        local_weight: float = 0.7,
        global_weight: float = 0.3
    ) -> np.ndarray:
        """
        Combine local and global embeddings
        
        Args:
            local_emb: Chunk-specific embedding
            global_emb: Document-level embedding
            local_weight: Weight for local embedding
            global_weight: Weight for global embedding
            
        Returns:
            Combined embedding
        """
        # Ensure embeddings are same dimension
        if local_emb.shape != global_emb.shape:
            raise ValueError(
                f"Embedding dimensions must match: {local_emb.shape} != {global_emb.shape}"
            )
        
        # Weighted combination
        combined = (local_weight * local_emb) + (global_weight * global_emb)
        
        # Normalize
        norm = np.linalg.norm(combined)
        if norm > 0:
            combined = combined / norm
        
        return combined
    
    def get_document_embedding(self) -> Optional[np.ndarray]:
        """Get the document-level embedding"""
        return self.document_embedding
