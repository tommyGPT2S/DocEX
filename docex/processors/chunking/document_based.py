"""
Document-Based Chunking Strategy

Splits only at clearly defined document boundaries such as heading tags,
Markdown headers, or section dividers.

Technical Properties:
- Requires structural metadata or heading detection
- Suitable for semi-structured inputs
- Produces fewer, larger, more coherent chunks

Best for: Multi-section documents, customer support tickets, news articles
"""

import time
import re
from typing import List, Dict, Any, Optional, Tuple
from .base import ChunkingStrategy, Chunk, ChunkingConfig


class DocumentBasedChunking(ChunkingStrategy):
    """
    Structure-aware chunking based on document boundaries
    
    Supports:
    - Markdown headers (#, ##, ###)
    - HTML heading tags (h1, h2, h3, etc.)
    - Custom section markers
    - Table of contents structure
    """
    
    def __init__(self, config: Optional[ChunkingConfig] = None):
        """Initialize document-based chunking"""
        super().__init__(config)
        
        # Compile regex patterns for different formats
        self.markdown_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        self.html_heading_pattern = re.compile(
            r'<(h[1-6])(?:\s+[^>]*)?>(.+?)</\1>',
            re.IGNORECASE | re.DOTALL
        )
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """
        Split text at document boundaries
        
        Args:
            text: Input text
            metadata: Optional metadata (can include 'format': 'markdown'|'html'|'plain')
            
        Returns:
            List of document-based chunks
        """
        start_time = time.time()
        
        # Detect document format
        doc_format = metadata.get('format', 'auto') if metadata else 'auto'
        
        if doc_format == 'auto':
            doc_format = self._detect_format(text)
        
        # Split based on format
        if doc_format == 'markdown':
            chunks = self._split_markdown(text)
        elif doc_format == 'html':
            chunks = self._split_html(text)
        else:
            chunks = self._split_plain(text)
        
        # Add metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata['chunk_number'] = i
            chunk.metadata['document_format'] = doc_format
            self._add_metadata(chunk, metadata)
        
        processing_time = time.time() - start_time
        self._update_stats(chunks, processing_time)
        
        return chunks
    
    def _detect_format(self, text: str) -> str:
        """Auto-detect document format"""
        # Check for HTML tags
        if re.search(r'<h[1-6]', text, re.IGNORECASE):
            return 'html'
        
        # Check for Markdown headers
        if re.search(r'^#{1,6}\s+', text, re.MULTILINE):
            return 'markdown'
        
        return 'plain'
    
    def _split_markdown(self, text: str) -> List[Chunk]:
        """Split Markdown document by headers"""
        chunks = []
        sections = []
        
        # Find all headers
        matches = list(self.markdown_pattern.finditer(text))
        
        if not matches:
            # No headers found, treat as single chunk
            return self._split_plain(text)
        
        # Extract sections
        for i, match in enumerate(matches):
            start_idx = match.start()
            header_level = len(match.group(1))  # Number of # symbols
            header_text = match.group(2)
            
            # Determine section end
            if i + 1 < len(matches):
                end_idx = matches[i + 1].start()
            else:
                end_idx = len(text)
            
            content = text[start_idx:end_idx].strip()
            
            # Only create chunk if it meets minimum size
            if len(content) >= self.config.min_chunk_size:
                sections.append((start_idx, end_idx, header_level, header_text, content))
        
        # Create chunks from sections
        for i, (start_idx, end_idx, level, header, content) in enumerate(sections):
            chunk = Chunk(
                id=f"doc_md_{i:04d}",
                content=content,
                start_idx=start_idx,
                end_idx=end_idx,
                metadata={
                    'section_level': level,
                    'section_header': header,
                    'section_type': 'markdown_header'
                }
            )
            
            # If section is too large, split it further
            if len(content) > self.config.max_chunk_size:
                chunk = self._split_large_section(chunk, sections[i])
                chunks.extend(chunk if isinstance(chunk, list) else [chunk])
            else:
                chunks.append(chunk)
        
        return chunks
    
    def _split_html(self, text: str) -> List[Chunk]:
        """Split HTML document by heading tags"""
        chunks = []
        
        # Find all heading tags
        matches = list(self.html_heading_pattern.finditer(text))
        
        if not matches:
            # No headings found
            return self._split_plain(text)
        
        # Extract sections
        for i, match in enumerate(matches):
            start_idx = match.start()
            tag = match.group(1).lower()
            header_level = int(tag[1])  # Extract number from h1, h2, etc.
            header_text = match.group(2)
            
            # Determine section end
            if i + 1 < len(matches):
                end_idx = matches[i + 1].start()
            else:
                end_idx = len(text)
            
            content = text[start_idx:end_idx].strip()
            
            # Only create chunk if it meets minimum size
            if len(content) >= self.config.min_chunk_size:
                chunk = Chunk(
                    id=f"doc_html_{i:04d}",
                    content=content,
                    start_idx=start_idx,
                    end_idx=end_idx,
                    metadata={
                        'section_level': header_level,
                        'section_header': header_text,
                        'section_type': 'html_heading'
                    }
                )
                
                # Split large sections
                if len(content) > self.config.max_chunk_size:
                    sub_chunks = self._split_large_section_plain(content, start_idx)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(chunk)
        
        return chunks
    
    def _split_plain(self, text: str) -> List[Chunk]:
        """Split plain text by paragraph boundaries"""
        chunks = []
        paragraphs = self._split_by_paragraphs(text)
        
        current_chunk_parts = []
        current_size = 0
        start_idx = 0
        current_start = 0
        chunk_id = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            # If adding this paragraph exceeds max size, create chunk
            if current_size + para_size > self.config.chunk_size * 4:
                if current_chunk_parts:
                    content = '\n\n'.join(current_chunk_parts)
                    chunks.append(Chunk(
                        id=f"doc_plain_{chunk_id:04d}",
                        content=content,
                        start_idx=current_start,
                        end_idx=current_start + len(content),
                        metadata={'section_type': 'paragraph_group'}
                    ))
                    chunk_id += 1
                
                # Start new chunk
                current_chunk_parts = [para]
                current_size = para_size
                current_start = start_idx
            else:
                current_chunk_parts.append(para)
                current_size += para_size
            
            start_idx += para_size + 2  # +2 for \n\n
        
        # Add remaining content
        if current_chunk_parts:
            content = '\n\n'.join(current_chunk_parts)
            chunks.append(Chunk(
                id=f"doc_plain_{chunk_id:04d}",
                content=content,
                start_idx=current_start,
                end_idx=current_start + len(content),
                metadata={'section_type': 'paragraph_group'}
            ))
        
        return chunks
    
    def _split_large_section(self, chunk: Chunk, section_info: Tuple) -> List[Chunk]:
        """Split a large section into smaller chunks"""
        # Simple paragraph-based splitting for large sections
        return self._split_large_section_plain(chunk.content, chunk.start_idx)
    
    def _split_large_section_plain(self, text: str, start_offset: int) -> List[Chunk]:
        """Split large section by paragraphs"""
        chunks = []
        paragraphs = self._split_by_paragraphs(text)
        
        current_content = []
        current_size = 0
        current_start = start_offset
        
        for para in paragraphs:
            para_size = len(para)
            
            if current_size + para_size > self.config.chunk_size * 4:
                if current_content:
                    content = '\n\n'.join(current_content)
                    chunks.append(Chunk(
                        id=f"doc_subsection_{len(chunks)}",
                        content=content,
                        start_idx=current_start,
                        end_idx=current_start + len(content),
                        metadata={'section_type': 'subsection'}
                    ))
                
                current_content = [para]
                current_size = para_size
                current_start += len('\n\n'.join(current_content))
            else:
                current_content.append(para)
                current_size += para_size
        
        # Add remaining
        if current_content:
            content = '\n\n'.join(current_content)
            chunks.append(Chunk(
                id=f"doc_subsection_{len(chunks)}",
                content=content,
                start_idx=current_start,
                end_idx=current_start + len(content),
                metadata={'section_type': 'subsection'}
            ))
        
        return chunks
