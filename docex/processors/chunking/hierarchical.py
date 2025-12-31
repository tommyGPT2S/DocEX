"""
Hierarchical Chunking Strategy

Builds a multi-level hierarchy: document → sections → paragraphs → sentences.
Chunking occurs at each layer.

Technical Properties:
- Preserves full document outline
- Enables multi-resolution retrieval (section-level vs sentence-level)
- Useful for structured documents with predictable layout

Best for: Employee handbooks, regulations, software documentation
"""

import time
from typing import List, Dict, Any, Optional, Tuple
from .base import ChunkingStrategy, Chunk, ChunkingConfig


class HierarchicalChunking(ChunkingStrategy):
    """
    Multi-level hierarchical chunking
    
    Creates a tree structure:
    - Level 0: Full document
    - Level 1: Major sections
    - Level 2: Subsections
    - Level 3: Paragraphs
    - Level 4: Sentences
    
    Each chunk knows its parent and children, enabling:
    - Drill-down from section to details
    - Roll-up from sentence to context
    - Multi-granularity search
    """
    
    def __init__(self, config: Optional[ChunkingConfig] = None, max_levels: int = 4):
        """
        Initialize hierarchical chunking
        
        Args:
            config: Chunking configuration
            max_levels: Maximum hierarchy depth (default: 4)
        """
        super().__init__(config)
        self.max_levels = max_levels
        self.hierarchy_tree = {}  # Maps chunk IDs to their hierarchy info
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """
        Split text into hierarchical chunks
        
        Args:
            text: Input text
            metadata: Optional metadata
            
        Returns:
            List of all chunks at all levels (flattened)
        """
        start_time = time.time()
        
        # Build hierarchy
        root_chunk = self._create_root_chunk(text)
        all_chunks = [root_chunk]
        
        # Level 1: Major sections (by double newline or size)
        level1_chunks = self._split_into_sections(root_chunk)
        all_chunks.extend(level1_chunks)
        
        # Level 2: Subsections (paragraphs)
        level2_chunks = []
        for section_chunk in level1_chunks:
            subsections = self._split_into_subsections(section_chunk)
            level2_chunks.extend(subsections)
        all_chunks.extend(level2_chunks)
        
        # Level 3: Sentences (optional, only if configured)
        if self.max_levels >= 4:
            level3_chunks = []
            for subsection_chunk in level2_chunks:
                sentences = self._split_into_sentences(subsection_chunk)
                level3_chunks.extend(sentences)
            all_chunks.extend(level3_chunks)
        
        # Add metadata to all chunks
        for i, chunk in enumerate(all_chunks):
            chunk.metadata['hierarchy_position'] = i
            chunk.metadata['total_hierarchy_size'] = len(all_chunks)
            self._add_metadata(chunk, metadata)
        
        processing_time = time.time() - start_time
        self._update_stats(all_chunks, processing_time)
        
        return all_chunks
    
    def _create_root_chunk(self, text: str) -> Chunk:
        """Create root chunk (entire document)"""
        chunk = Chunk(
            id="hier_root_0000",
            content=text,
            start_idx=0,
            end_idx=len(text),
            semantic_level=0,
            metadata={
                'level_name': 'document',
                'hierarchy_role': 'root'
            }
        )
        return chunk
    
    def _split_into_sections(self, parent_chunk: Chunk) -> List[Chunk]:
        """Split into major sections (Level 1)"""
        text = parent_chunk.content
        sections = []
        
        # Try to split by large gaps (double newlines)
        parts = text.split('\n\n\n')  # Triple newline indicates major section
        
        if len(parts) <= 1:
            # Fallback: split by double newline
            parts = text.split('\n\n')
        
        # Combine small parts and split large parts
        processed_parts = self._balance_sections(parts, target_size=self.config.chunk_size * 4)
        
        start_idx = parent_chunk.start_idx
        for i, part in enumerate(processed_parts):
            if len(part.strip()) < self.config.min_chunk_size:
                continue
            
            chunk = Chunk(
                id=f"hier_sec_{i:04d}",
                content=part.strip(),
                start_idx=start_idx,
                end_idx=start_idx + len(part),
                parent_id=parent_chunk.id,
                semantic_level=1,
                metadata={
                    'level_name': 'section',
                    'section_number': i + 1
                }
            )
            
            # Update parent's children
            parent_chunk.children_ids.append(chunk.id)
            
            sections.append(chunk)
            start_idx += len(part)
        
        return sections
    
    def _split_into_subsections(self, parent_chunk: Chunk) -> List[Chunk]:
        """Split section into subsections/paragraphs (Level 2)"""
        text = parent_chunk.content
        subsections = []
        
        # Split by paragraphs
        paragraphs = self._split_by_paragraphs(text)
        
        start_idx = parent_chunk.start_idx
        section_num = parent_chunk.metadata.get('section_number', 0)
        
        for i, para in enumerate(paragraphs):
            if len(para.strip()) < self.config.min_chunk_size:
                continue
            
            chunk = Chunk(
                id=f"hier_sub_{section_num}_{i:04d}",
                content=para.strip(),
                start_idx=start_idx,
                end_idx=start_idx + len(para),
                parent_id=parent_chunk.id,
                semantic_level=2,
                metadata={
                    'level_name': 'subsection',
                    'subsection_number': i + 1,
                    'parent_section': section_num
                }
            )
            
            # Update parent's children
            parent_chunk.children_ids.append(chunk.id)
            
            subsections.append(chunk)
            start_idx += len(para) + 2  # +2 for \n\n
        
        return subsections
    
    def _split_into_sentences(self, parent_chunk: Chunk) -> List[Chunk]:
        """Split subsection into sentences (Level 3)"""
        text = parent_chunk.content
        sentences_list = []
        
        # Split by sentences
        sentences = self._split_by_sentences(text)
        
        start_idx = parent_chunk.start_idx
        subsection_num = parent_chunk.metadata.get('subsection_number', 0)
        section_num = parent_chunk.metadata.get('parent_section', 0)
        
        for i, sent in enumerate(sentences):
            sent = sent.strip()
            if len(sent) < 20:  # Skip very short sentences
                continue
            
            chunk = Chunk(
                id=f"hier_sent_{section_num}_{subsection_num}_{i:04d}",
                content=sent,
                start_idx=start_idx,
                end_idx=start_idx + len(sent),
                parent_id=parent_chunk.id,
                semantic_level=3,
                metadata={
                    'level_name': 'sentence',
                    'sentence_number': i + 1,
                    'parent_subsection': subsection_num,
                    'parent_section': section_num
                }
            )
            
            # Update parent's children
            parent_chunk.children_ids.append(chunk.id)
            
            sentences_list.append(chunk)
            
            # Approximate position advancement
            start_idx += len(sent) + 2
        
        return sentences_list
    
    def _balance_sections(
        self,
        parts: List[str],
        target_size: int
    ) -> List[str]:
        """Balance section sizes by merging small and splitting large"""
        balanced = []
        current = ""
        
        for part in parts:
            part_size = len(part)
            
            # If part is too large, split it
            if part_size > target_size * 2:
                # First, add accumulated content
                if current:
                    balanced.append(current)
                    current = ""
                
                # Split large part
                sub_parts = self._split_large_part(part, target_size)
                balanced.extend(sub_parts)
            
            # If adding this part keeps us under target, accumulate
            elif len(current) + part_size < target_size:
                current += "\n\n" + part if current else part
            
            # Adding this part exceeds target
            else:
                if current:
                    balanced.append(current)
                current = part
        
        # Add remaining
        if current:
            balanced.append(current)
        
        return balanced
    
    def _split_large_part(self, text: str, target_size: int) -> List[str]:
        """Split a large part into smaller chunks"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + target_size
            
            # Try to find a good break point (paragraph or sentence)
            if end < len(text):
                # Look for paragraph break
                para_break = text.rfind('\n\n', start, end)
                if para_break > start:
                    end = para_break
                else:
                    # Look for sentence break
                    sent_break = max(
                        text.rfind('. ', start, end),
                        text.rfind('! ', start, end),
                        text.rfind('? ', start, end)
                    )
                    if sent_break > start:
                        end = sent_break + 2
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end
        
        return chunks
    
    def get_chunk_hierarchy(self, chunk_id: str, all_chunks: List[Chunk]) -> Dict[str, Any]:
        """
        Get full hierarchy info for a chunk
        
        Returns dict with:
        - parents: List of parent chunks
        - siblings: Chunks at same level
        - children: Direct children
        """
        # Create lookup dict
        chunk_dict = {c.id: c for c in all_chunks}
        
        if chunk_id not in chunk_dict:
            return {}
        
        chunk = chunk_dict[chunk_id]
        
        # Get parents
        parents = []
        current = chunk
        while current.parent_id and current.parent_id in chunk_dict:
            parent = chunk_dict[current.parent_id]
            parents.insert(0, parent)
            current = parent
        
        # Get children
        children = [chunk_dict[cid] for cid in chunk.children_ids if cid in chunk_dict]
        
        # Get siblings (other children of same parent)
        siblings = []
        if chunk.parent_id and chunk.parent_id in chunk_dict:
            parent = chunk_dict[chunk.parent_id]
            siblings = [
                chunk_dict[cid]
                for cid in parent.children_ids
                if cid in chunk_dict and cid != chunk_id
            ]
        
        return {
            'chunk': chunk,
            'level': chunk.semantic_level,
            'parents': parents,
            'siblings': siblings,
            'children': children,
            'hierarchy_path': [p.metadata.get('level_name', 'unknown') for p in parents]
        }
