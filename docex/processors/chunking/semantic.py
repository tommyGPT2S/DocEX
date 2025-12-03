"""
Semantic Chunking Strategy

Identifies chunk boundaries based on semantic coherence—topic shifts,
conceptual boundaries, key idea transitions.

Technical Properties:
- Requires embedding-based similarity analysis
- Detects semantic drifts (cosine distance thresholding)
- O(n) embedding operations

Best for: Textbooks, scientific papers, whitepapers, narrative documents
"""

import time
import numpy as np
from typing import List, Dict, Any, Optional
from .base import ChunkingStrategy, Chunk, ChunkingConfig


class SemanticChunking(ChunkingStrategy):
    """
    Semantic-aware chunking using embeddings
    
    Algorithm:
    1. Split text into sentences
    2. Generate embeddings for each sentence
    3. Calculate similarity between consecutive sentences
    4. Create chunk boundaries where similarity drops below threshold
    """
    
    def __init__(
        self,
        config: Optional[ChunkingConfig] = None,
        embedding_function: Optional[callable] = None
    ):
        """
        Initialize semantic chunking
        
        Args:
            config: Chunking configuration
            embedding_function: Function to generate embeddings
                               Should accept text and return numpy array
        """
        super().__init__(config)
        self.embedding_function = embedding_function
        self._embedding_cache = {}
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """
        Split text based on semantic boundaries
        
        Args:
            text: Input text
            metadata: Optional metadata
            
        Returns:
            List of semantically coherent chunks
        """
        start_time = time.time()
        
        if not self.embedding_function:
            raise ValueError("Embedding function is required for semantic chunking")
        
        # Split into sentences
        sentences = self._split_by_sentences(text)
        
        if len(sentences) <= 1:
            # Single sentence, return as-is
            return [Chunk(
                id="semantic_0000",
                content=text,
                start_idx=0,
                end_idx=len(text),
                metadata={'chunk_number': 0}
            )]
        
        # Generate embeddings for each sentence
        embeddings = await self._get_embeddings(sentences)
        
        # Calculate similarity scores between consecutive sentences
        similarities = self._calculate_similarities(embeddings)
        
        # Find chunk boundaries based on similarity drops
        boundaries = self._find_boundaries(similarities)
        
        # Create chunks from boundaries
        chunks = self._create_chunks_from_boundaries(text, sentences, boundaries)
        
        # Add metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata['chunk_number'] = i
            self._add_metadata(chunk, metadata)
        
        processing_time = time.time() - start_time
        self._update_stats(chunks, processing_time)
        
        return chunks
    
    async def _get_embeddings(self, sentences: List[str]) -> List[np.ndarray]:
        """Generate embeddings for sentences"""
        embeddings = []
        
        # Process in batches for efficiency
        batch_size = self.config.embedding_batch_size
        
        for i in range(0, len(sentences), batch_size):
            batch = sentences[i:i + batch_size]
            
            # Check cache first
            batch_embeddings = []
            for sent in batch:
                if self.config.enable_caching and sent in self._embedding_cache:
                    batch_embeddings.append(self._embedding_cache[sent])
                else:
                    # Generate embedding
                    embedding = await self._generate_embedding(sent)
                    batch_embeddings.append(embedding)
                    
                    # Cache it
                    if self.config.enable_caching:
                        self._embedding_cache[sent] = embedding
            
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    async def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single text"""
        # Call the embedding function
        result = self.embedding_function(text)
        
        # Handle both sync and async functions
        if hasattr(result, '__await__'):
            result = await result
        
        # Convert to numpy array if needed
        if not isinstance(result, np.ndarray):
            result = np.array(result)
        
        return result
    
    def _calculate_similarities(self, embeddings: List[np.ndarray]) -> List[float]:
        """Calculate cosine similarity between consecutive embeddings"""
        similarities = []
        
        for i in range(len(embeddings) - 1):
            sim = self._cosine_similarity(embeddings[i], embeddings[i + 1])
            similarities.append(sim)
        
        return similarities
    
    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def _find_boundaries(self, similarities: List[float]) -> List[int]:
        """
        Find chunk boundaries where similarity drops
        
        Uses adaptive thresholding based on statistical properties
        """
        if not similarities:
            return []
        
        boundaries = [0]  # Always start at 0
        
        # Calculate threshold
        mean_sim = np.mean(similarities)
        std_sim = np.std(similarities)
        threshold = max(
            self.config.similarity_threshold,
            mean_sim - std_sim  # One standard deviation below mean
        )
        
        # Find significant drops in similarity
        for i, sim in enumerate(similarities):
            if sim < threshold:
                # This is a semantic boundary
                boundaries.append(i + 1)
        
        return boundaries
    
    def _create_chunks_from_boundaries(
        self,
        original_text: str,
        sentences: List[str],
        boundaries: List[int]
    ) -> List[Chunk]:
        """Create chunks from identified boundaries"""
        chunks = []
        
        for i in range(len(boundaries)):
            # Determine sentence range for this chunk
            start_sent_idx = boundaries[i]
            end_sent_idx = boundaries[i + 1] if i + 1 < len(boundaries) else len(sentences)
            
            # Get sentences for this chunk
            chunk_sentences = sentences[start_sent_idx:end_sent_idx]
            
            # Combine sentences
            chunk_content = ' '.join(chunk_sentences)
            
            # Find position in original text (approximate)
            start_idx = original_text.find(chunk_sentences[0])
            end_idx = start_idx + len(chunk_content)
            
            # Ensure chunk meets size requirements
            if len(chunk_content) >= self.config.min_chunk_size:
                # Check if chunk is too large
                if len(chunk_content) > self.config.max_chunk_size:
                    # Split large chunk further
                    sub_chunks = self._split_large_chunk(
                        chunk_content,
                        start_idx,
                        chunk_sentences
                    )
                    chunks.extend(sub_chunks)
                else:
                    chunk = Chunk(
                        id=f"semantic_{i:04d}",
                        content=chunk_content,
                        start_idx=max(0, start_idx),
                        end_idx=min(len(original_text), end_idx),
                        metadata={
                            'sentence_count': len(chunk_sentences),
                            'boundary_type': 'semantic'
                        }
                    )
                    chunks.append(chunk)
        
        return chunks
    
    def _split_large_chunk(
        self,
        content: str,
        start_idx: int,
        sentences: List[str]
    ) -> List[Chunk]:
        """Split a chunk that's too large"""
        chunks = []
        target_size = self.config.chunk_size * 4  # Convert to chars
        
        current_sentences = []
        current_size = 0
        chunk_start = start_idx
        
        for sent in sentences:
            sent_size = len(sent)
            
            if current_size + sent_size > target_size and current_sentences:
                # Create chunk from accumulated sentences
                chunk_content = ' '.join(current_sentences)
                chunks.append(Chunk(
                    id=f"semantic_sub_{len(chunks)}",
                    content=chunk_content,
                    start_idx=chunk_start,
                    end_idx=chunk_start + len(chunk_content),
                    metadata={
                        'sentence_count': len(current_sentences),
                        'boundary_type': 'semantic_size_split'
                    }
                ))
                
                # Reset for next chunk
                current_sentences = [sent]
                current_size = sent_size
                chunk_start += len(chunk_content) + 1
            else:
                current_sentences.append(sent)
                current_size += sent_size
        
        # Add remaining sentences
        if current_sentences:
            chunk_content = ' '.join(current_sentences)
            chunks.append(Chunk(
                id=f"semantic_sub_{len(chunks)}",
                content=chunk_content,
                start_idx=chunk_start,
                end_idx=chunk_start + len(chunk_content),
                metadata={
                    'sentence_count': len(current_sentences),
                    'boundary_type': 'semantic_size_split'
                }
            ))
        
        return chunks
    
    def clear_cache(self):
        """Clear embedding cache"""
        self._embedding_cache.clear()
