"""
Base Rule Book Processor

Base processor for ingesting rule books into the Knowledge Base.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.processors.llm import BaseLLMProcessor
from docex.document import Document

logger = logging.getLogger(__name__)


class RuleBookProcessor(BaseProcessor):
    """
    Base processor for rule book ingestion
    
    Handles:
    - Document text extraction
    - LLM-based structured data extraction
    - Metadata enrichment
    - Rule book type detection
    """
    
    def __init__(self, config: Dict[str, Any], llm_processor: Optional[BaseLLMProcessor] = None):
        """
        Initialize rule book processor
        
        Args:
            config: Processor configuration
            llm_processor: Optional LLM processor for extraction
        """
        super().__init__(config)
        self.llm_processor = llm_processor
        self.rule_book_type = config.get('rule_book_type', 'unknown')
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Process rule book document
        
        Args:
            document: Rule book document to process
            
        Returns:
            ProcessingResult with extracted data
        """
        try:
            logger.info(f"Processing rule book: {document.name}")
            
            # Extract text content
            text_content = self.get_document_content(document, mode='text')
            if not text_content:
                return ProcessingResult(
                    success=False,
                    error="Could not extract text content from document"
                )
            
            # Detect rule book type if not specified
            if self.rule_book_type == 'unknown':
                self.rule_book_type = self._detect_rule_book_type(document, text_content)
            
            # Extract structured data using LLM if available
            extracted_data = None
            if self.llm_processor:
                extracted_data = await self._extract_structured_data(text_content)
            
            # Build metadata
            metadata = {
                'rule_book_type': self.rule_book_type,
                'processed_at': datetime.now().isoformat(),
                'document_name': document.name,
                'extracted_data': extracted_data
            }
            
            logger.info(f"Successfully processed rule book: {self.rule_book_type}")
            
            return ProcessingResult(
                success=True,
                content=text_content,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process rule book: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                error=str(e)
            )
    
    def can_process(self, document: Document) -> bool:
        """Check if document can be processed as a rule book"""
        # Check by file name patterns
        name_lower = document.name.lower()
        
        rule_book_patterns = [
            'gpo roster',
            'ddd matrix',
            'eligibility guide',
            'iccr eligibility',
            'contract eligibility'
        ]
        
        return any(pattern in name_lower for pattern in rule_book_patterns)
    
    def _detect_rule_book_type(self, document: Document, text_content: str) -> str:
        """
        Detect rule book type from document name and content
        
        Args:
            document: Document to analyze
            text_content: Document text content
            
        Returns:
            Detected rule book type
        """
        name_lower = document.name.lower()
        content_lower = text_content[:1000].lower()  # Check first 1000 chars
        
        # Check for GPO Roster
        if 'gpo roster' in name_lower or 'gpo' in name_lower and 'roster' in name_lower:
            return 'gpo_roster'
        
        # Check for DDD Matrix
        if 'ddd matrix' in name_lower or 'class of trade' in content_lower:
            return 'ddd_matrix'
        
        # Check for Eligibility Guide
        if 'eligibility guide' in name_lower or 'iccr eligibility' in name_lower:
            return 'eligibility_guide'
        
        # Default
        return 'unknown'
    
    async def _extract_structured_data(self, text_content: str) -> Optional[Dict[str, Any]]:
        """
        Extract structured data from rule book text using LLM
        
        Args:
            text_content: Document text content
            
        Returns:
            Extracted structured data or None
        """
        if not self.llm_processor:
            return None
        
        try:
            # Get extraction prompt based on rule book type
            prompt_name = f"{self.rule_book_type}_extraction"
            
            # Use LLM to extract structured data
            if hasattr(self.llm_processor, 'llm_service'):
                result = await self.llm_processor.llm_service.extract_structured_data(
                    text=text_content[:5000],  # Limit text length
                    system_prompt=self.llm_processor.get_system_prompt(prompt_name),
                    user_prompt=self.llm_processor.get_user_prompt(prompt_name, content=text_content[:5000])
                )
                return result.get('extracted_data')
            else:
                logger.warning("LLM processor doesn't support structured extraction")
                return None
                
        except Exception as e:
            logger.warning(f"Failed to extract structured data: {e}")
            return None

