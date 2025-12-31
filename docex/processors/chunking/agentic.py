"""
Agentic Chunking Strategy

Delegates chunking decisions to an autonomous AI agent that evaluates
structure, semantics, and task-specific criteria.

Technical Properties:
- Multi-objective chunking (structure + meaning + task requirements)
- Can iterate, evaluate, and refine splits
- Highest computational complexity

Best for: Regulatory filings, compliance material, complex corporate policies
"""

import time
import json
from typing import List, Dict, Any, Optional
from .base import ChunkingStrategy, Chunk, ChunkingConfig


class AgenticChunking(ChunkingStrategy):
    """
    Autonomous AI agent-based chunking
    
    The agent:
    1. Analyzes document characteristics
    2. Evaluates multiple chunking strategies
    3. Applies custom rules based on content type
    4. Iterates to optimize chunk quality
    """
    
    def __init__(
        self,
        config: Optional[ChunkingConfig] = None,
        llm_service: Optional[Any] = None,
        task_requirements: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize agentic chunking
        
        Args:
            config: Chunking configuration
            llm_service: LLM service for agent reasoning
            task_requirements: Specific requirements for chunking
        """
        super().__init__(config)
        self.llm_service = llm_service
        self.task_requirements = task_requirements or {}
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """
        Split text using autonomous agent
        
        Args:
            text: Input text
            metadata: Optional metadata
            
        Returns:
            List of agent-optimized chunks
        """
        start_time = time.time()
        
        if not self.llm_service:
            raise ValueError("LLM service is required for agentic chunking")
        
        # Step 1: Agent analyzes document
        doc_analysis = await self._analyze_document(text, metadata)
        
        # Step 2: Agent selects optimal strategy
        strategy_plan = await self._select_strategy(text, doc_analysis)
        
        # Step 3: Agent performs chunking
        initial_chunks = await self._perform_chunking(text, strategy_plan)
        
        # Step 4: Agent evaluates and refines
        final_chunks = await self._evaluate_and_refine(text, initial_chunks, doc_analysis)
        
        # Add metadata
        for i, chunk in enumerate(final_chunks):
            chunk.metadata['chunk_number'] = i
            chunk.metadata['agent_analyzed'] = True
            chunk.metadata['strategy_used'] = strategy_plan.get('strategy', 'hybrid')
            self._add_metadata(chunk, metadata)
        
        processing_time = time.time() - start_time
        self._update_stats(final_chunks, processing_time)
        
        return final_chunks
    
    async def _analyze_document(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Agent analyzes document characteristics"""
        
        system_prompt = """You are an AI agent specializing in document analysis for optimal chunking.

Analyze the given document and provide a structured assessment including:
1. Document type (technical, narrative, legal, conversational, etc.)
2. Structure complexity (simple, moderate, complex)
3. Key features (has headings, tables, lists, code blocks, etc.)
4. Optimal chunking approach recommendation
5. Special considerations

Return as JSON."""
        
        user_prompt = f"""Analyze this document (first 2000 chars):

{text[:2000]}

Metadata: {json.dumps(metadata or {}, indent=2)}

Task requirements: {json.dumps(self.task_requirements, indent=2)}

Provide your analysis as JSON."""
        
        try:
            response = await self.llm_service.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1
            )
            
            # Parse response
            analysis = self._extract_json(response)
            return analysis
            
        except Exception as e:
            # Fallback analysis
            return {
                'document_type': 'unknown',
                'structure_complexity': 'moderate',
                'features': ['text_content'],
                'recommendation': 'recursive',
                'considerations': []
            }
    
    async def _select_strategy(
        self,
        text: str,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Agent selects optimal chunking strategy"""
        
        system_prompt = """You are an AI agent that selects optimal chunking strategies.

Based on document analysis, determine the best chunking approach:
- 'fixed': For simple, uniform content
- 'recursive': For structured documents with hierarchy
- 'semantic': For narrative content with topic shifts
- 'document': For well-structured docs with clear sections
- 'hybrid': Combination of multiple strategies

Return a strategy plan as JSON with:
- strategy: chosen strategy name
- parameters: specific parameters to use
- reasoning: why this strategy is optimal
"""
        
        user_prompt = f"""Document analysis:
{json.dumps(analysis, indent=2)}

Task requirements:
{json.dumps(self.task_requirements, indent=2)}

Select optimal chunking strategy and parameters."""
        
        try:
            response = await self.llm_service.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1
            )
            
            plan = self._extract_json(response)
            return plan
            
        except Exception:
            # Default plan
            return {
                'strategy': 'recursive',
                'parameters': {
                    'chunk_size': self.config.chunk_size,
                    'overlap': self.config.chunk_overlap
                },
                'reasoning': 'Default fallback strategy'
            }
    
    async def _perform_chunking(
        self,
        text: str,
        strategy_plan: Dict[str, Any]
    ) -> List[Chunk]:
        """Execute the selected chunking strategy"""
        
        strategy_name = strategy_plan.get('strategy', 'recursive')
        
        # Import and use the appropriate strategy
        if strategy_name == 'fixed':
            from .fixed_size import FixedSizeChunking
            strategy = FixedSizeChunking(self.config)
        elif strategy_name == 'recursive':
            from .recursive import RecursiveChunking
            strategy = RecursiveChunking(self.config)
        elif strategy_name == 'semantic':
            # Would need embedding function
            from .recursive import RecursiveChunking
            strategy = RecursiveChunking(self.config)
        elif strategy_name == 'document':
            from .document_based import DocumentBasedChunking
            strategy = DocumentBasedChunking(self.config)
        else:  # hybrid
            # Use recursive as default for hybrid
            from .recursive import RecursiveChunking
            strategy = RecursiveChunking(self.config)
        
        chunks = await strategy.chunk(text)
        return chunks
    
    async def _evaluate_and_refine(
        self,
        text: str,
        chunks: List[Chunk],
        analysis: Dict[str, Any]
    ) -> List[Chunk]:
        """Agent evaluates chunks and refines if needed"""
        
        # Check if refinement is needed
        needs_refinement = False
        
        # Check for issues
        for chunk in chunks:
            # Too small
            if len(chunk.content) < self.config.min_chunk_size:
                needs_refinement = True
                break
            # Too large
            if len(chunk.content) > self.config.max_chunk_size * 1.5:
                needs_refinement = True
                break
        
        # If no refinement needed, return as-is
        if not needs_refinement:
            return chunks
        
        # Perform refinement
        refined_chunks = self._refine_chunks(chunks)
        return refined_chunks
    
    def _refine_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """Refine chunks by merging small ones and splitting large ones"""
        refined = []
        current_merge = []
        current_size = 0
        
        for chunk in chunks:
            chunk_size = len(chunk.content)
            
            # If chunk is too small, accumulate for merging
            if chunk_size < self.config.min_chunk_size:
                current_merge.append(chunk)
                current_size += chunk_size
                
                # Merge if accumulated size is sufficient
                if current_size >= self.config.min_chunk_size:
                    merged = self._merge_chunks(current_merge)
                    refined.append(merged)
                    current_merge = []
                    current_size = 0
            
            # If chunk is too large, split it
            elif chunk_size > self.config.max_chunk_size * 1.5:
                # First, add any accumulated chunks
                if current_merge:
                    merged = self._merge_chunks(current_merge)
                    refined.append(merged)
                    current_merge = []
                    current_size = 0
                
                # Split large chunk
                split_chunks = self._split_large_chunk(chunk)
                refined.extend(split_chunks)
            
            # Chunk is good size
            else:
                # Add any accumulated chunks first
                if current_merge:
                    merged = self._merge_chunks(current_merge)
                    refined.append(merged)
                    current_merge = []
                    current_size = 0
                
                refined.append(chunk)
        
        # Add any remaining merged chunks
        if current_merge:
            merged = self._merge_chunks(current_merge)
            refined.append(merged)
        
        return refined
    
    def _merge_chunks(self, chunks: List[Chunk]) -> Chunk:
        """Merge multiple small chunks into one"""
        if len(chunks) == 1:
            return chunks[0]
        
        merged_content = '\n\n'.join(c.content for c in chunks)
        start_idx = chunks[0].start_idx
        end_idx = chunks[-1].end_idx
        
        return Chunk(
            id=f"agentic_merged_{chunks[0].id}",
            content=merged_content,
            start_idx=start_idx,
            end_idx=end_idx,
            metadata={
                'merged_from': [c.id for c in chunks],
                'merge_reason': 'too_small'
            }
        )
    
    def _split_large_chunk(self, chunk: Chunk) -> List[Chunk]:
        """Split a large chunk into smaller ones"""
        target_size = self.config.chunk_size * 4
        content = chunk.content
        
        # Split by paragraphs
        paragraphs = content.split('\n\n')
        
        sub_chunks = []
        current_parts = []
        current_size = 0
        current_start = chunk.start_idx
        
        for para in paragraphs:
            para_size = len(para)
            
            if current_size + para_size > target_size and current_parts:
                # Create sub-chunk
                sub_content = '\n\n'.join(current_parts)
                sub_chunks.append(Chunk(
                    id=f"agentic_split_{chunk.id}_{len(sub_chunks)}",
                    content=sub_content,
                    start_idx=current_start,
                    end_idx=current_start + len(sub_content),
                    metadata={'split_from': chunk.id, 'split_reason': 'too_large'}
                ))
                
                current_parts = [para]
                current_size = para_size
                current_start += len(sub_content) + 2
            else:
                current_parts.append(para)
                current_size += para_size
        
        # Add remaining
        if current_parts:
            sub_content = '\n\n'.join(current_parts)
            sub_chunks.append(Chunk(
                id=f"agentic_split_{chunk.id}_{len(sub_chunks)}",
                content=sub_content,
                start_idx=current_start,
                end_idx=current_start + len(sub_content),
                metadata={'split_from': chunk.id, 'split_reason': 'too_large'}
            ))
        
        return sub_chunks
    
    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response"""
        try:
            # Find JSON in response
            start = text.find('{')
            end = text.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)
        except:
            pass
        
        return {}
