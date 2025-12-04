"""
LLM-Based Chunking Strategy

Uses a language model to determine chunk boundaries contextually,
analyzing meaning, intent, and discourse structure.

Technical Properties:
- Dynamic boundary selection
- High semantic fidelity
- High computational complexity due to model inference

Best for: Legal briefs, medical records, long reports
"""

import time
import json
from typing import List, Dict, Any, Optional
from .base import ChunkingStrategy, Chunk, ChunkingConfig


class LLMBasedChunking(ChunkingStrategy):
    """
    LLM-powered chunking with contextual understanding
    
    Uses an LLM to:
    1. Analyze document structure and content
    2. Identify natural semantic boundaries
    3. Determine optimal chunk sizes based on content
    """
    
    def __init__(
        self,
        config: Optional[ChunkingConfig] = None,
        llm_service: Optional[Any] = None
    ):
        """
        Initialize LLM-based chunking
        
        Args:
            config: Chunking configuration
            llm_service: LLM service with generate_completion method
        """
        super().__init__(config)
        self.llm_service = llm_service
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """
        Split text using LLM analysis
        
        Args:
            text: Input text
            metadata: Optional metadata
            
        Returns:
            List of contextually appropriate chunks
        """
        start_time = time.time()
        
        if not self.llm_service:
            raise ValueError("LLM service is required for LLM-based chunking")
        
        # For very short text, return as single chunk
        if len(text) < self.config.min_chunk_size * 2:
            return [Chunk(
                id="llm_0000",
                content=text,
                start_idx=0,
                end_idx=len(text),
                metadata={'chunk_number': 0, 'llm_analyzed': False}
            )]
        
        # Analyze text with LLM to identify chunk boundaries
        boundaries = await self._identify_boundaries_with_llm(text)
        
        # Create chunks from boundaries
        chunks = self._create_chunks_from_boundaries(text, boundaries)
        
        # Add metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata['chunk_number'] = i
            chunk.metadata['llm_analyzed'] = True
            self._add_metadata(chunk, metadata)
        
        processing_time = time.time() - start_time
        self._update_stats(chunks, processing_time)
        
        return chunks
    
    async def _identify_boundaries_with_llm(self, text: str) -> List[Dict[str, Any]]:
        """Use LLM to identify optimal chunk boundaries"""
        
        # Create prompt for LLM
        system_prompt = """You are an expert at analyzing document structure and identifying natural semantic boundaries for text chunking.

Your task is to analyze the given text and identify optimal locations to split it into chunks. Each chunk should:
- Be semantically coherent (single topic or concept)
- Be between 300-1500 characters
- End at natural boundaries (paragraph breaks, topic shifts, etc.)

Return your analysis as a JSON array of boundary objects, where each object has:
- "position": approximate character position (integer)
- "reason": brief explanation for the boundary
- "topic": the topic/theme of the section before this boundary

Example format:
[
  {"position": 500, "reason": "Topic shift from introduction to methods", "topic": "Introduction"},
  {"position": 1200, "reason": "End of methods section", "topic": "Methods"}
]
"""
        
        user_prompt = f"""Analyze this text and identify optimal chunk boundaries:

TEXT:
{text[:4000]}  

Provide boundaries as a JSON array."""
        
        try:
            # Call LLM
            response = await self.llm_service.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=self.config.llm_temperature
            )
            
            # Parse response
            boundaries = self._parse_llm_response(response, text)
            
            return boundaries
            
        except Exception as e:
            # Fallback to simple splitting if LLM fails
            return self._fallback_boundaries(text)
    
    def _parse_llm_response(self, response: str, text: str) -> List[Dict[str, Any]]:
        """Parse LLM response to extract boundaries"""
        try:
            # Try to find JSON in response
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                boundaries = json.loads(json_str)
                
                # Validate and clean boundaries
                valid_boundaries = []
                for b in boundaries:
                    if isinstance(b, dict) and 'position' in b:
                        pos = b['position']
                        # Ensure position is within text bounds
                        if 0 < pos < len(text):
                            valid_boundaries.append(b)
                
                # Sort by position
                valid_boundaries.sort(key=lambda x: x['position'])
                
                return valid_boundaries
            
        except json.JSONDecodeError:
            pass
        
        # Fallback if parsing fails
        return self._fallback_boundaries(text)
    
    def _fallback_boundaries(self, text: str) -> List[Dict[str, Any]]:
        """Create fallback boundaries if LLM analysis fails"""
        boundaries = []
        target_size = self.config.chunk_size * 4
        
        # Split by paragraphs
        paragraphs = text.split('\n\n')
        current_pos = 0
        current_size = 0
        
        for para in paragraphs:
            para_len = len(para) + 2  # +2 for \n\n
            
            if current_size + para_len > target_size and current_size > 0:
                boundaries.append({
                    'position': current_pos,
                    'reason': 'Paragraph boundary (fallback)',
                    'topic': 'Auto-detected'
                })
                current_size = 0
            
            current_pos += para_len
            current_size += para_len
        
        return boundaries
    
    def _create_chunks_from_boundaries(
        self,
        text: str,
        boundaries: List[Dict[str, Any]]
    ) -> List[Chunk]:
        """Create chunks from identified boundaries"""
        chunks = []
        
        # Add start and end positions
        positions = [0] + [b['position'] for b in boundaries] + [len(text)]
        
        for i in range(len(positions) - 1):
            start_idx = positions[i]
            end_idx = positions[i + 1]
            
            chunk_content = text[start_idx:end_idx].strip()
            
            # Only create chunk if it meets minimum size
            if len(chunk_content) >= self.config.min_chunk_size:
                # Get boundary info if available
                boundary_info = {}
                if i < len(boundaries):
                    boundary_info = {
                        'boundary_reason': boundaries[i].get('reason', 'N/A'),
                        'topic': boundaries[i].get('topic', 'Unknown')
                    }
                
                chunk = Chunk(
                    id=f"llm_{i:04d}",
                    content=chunk_content,
                    start_idx=start_idx,
                    end_idx=end_idx,
                    metadata={
                        **boundary_info,
                        'chunking_method': 'llm_analysis'
                    }
                )
                
                chunks.append(chunk)
        
        return chunks
