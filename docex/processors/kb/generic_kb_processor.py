"""
Generic Knowledge Base Document Processor

A domain-agnostic processor for ingesting documents into the knowledge base.
Can be configured for any document type and extraction schema.
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.processors.llm import BaseLLMProcessor
from docex.document import Document

logger = logging.getLogger(__name__)


class GenericKBProcessor(BaseProcessor):
    """
    Generic processor for knowledge base document ingestion
    
    Handles:
    - Document text extraction
    - LLM-based structured data extraction (configurable)
    - Metadata enrichment
    - Document type detection (optional)
    
    Usage:
        processor = GenericKBProcessor(
            config={
                'doc_type': 'policy',  # or None for auto-detection
                'extract_structured': True,
                'extraction_schema': {
                    'description': 'Extract policy information',
                    'fields': ['title', 'summary', 'key_points', 'effective_date']
                }
            },
            llm_processor=llm_adapter
        )
        
        result = await processor.process(document)
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        llm_processor: Optional[BaseLLMProcessor] = None
    ):
        """
        Initialize generic KB processor
        
        Args:
            config: Processor configuration:
                - doc_type: Optional document type (if None, will attempt auto-detection)
                - extract_structured: Whether to extract structured data (default: True)
                - extraction_schema: Optional extraction schema dict
                - auto_detect_type: Whether to auto-detect document type (default: True)
            llm_processor: Optional LLM processor for extraction
        """
        super().__init__(config)
        self.llm_processor = llm_processor
        self.doc_type = config.get('doc_type')
        self.extract_structured = config.get('extract_structured', True)
        self.extraction_schema = config.get('extraction_schema')
        self.auto_detect_type = config.get('auto_detect_type', True)
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Process knowledge base document
        
        Args:
            document: Document to process
            
        Returns:
            ProcessingResult with extracted data
        """
        try:
            logger.info(f"Processing KB document: {document.name}")
            
            # Extract text content
            text_content = self.get_document_content(document, mode='text')
            if not text_content:
                return ProcessingResult(
                    success=False,
                    error="Could not extract text content from document"
                )
            
            # Detect document type if not specified
            if not self.doc_type and self.auto_detect_type:
                self.doc_type = self._detect_document_type(document, text_content)
            
            # Extract structured data using LLM if available and requested
            extracted_data = None
            if self.extract_structured and self.llm_processor:
                extracted_data = await self._extract_structured_data(
                    text_content,
                    self.doc_type or 'unknown'
                )
            
            # Build metadata
            metadata = {
                'kb_doc_type': self.doc_type or 'unknown',
                'processed_at': datetime.now().isoformat(),
                'document_name': document.name,
                'extracted_data': extracted_data
            }
            
            # Set document metadata
            document.set_metadata('kb_doc_type', self.doc_type or 'unknown')
            if extracted_data:
                import json
                document.set_metadata('kb_extracted_data', json.dumps(extracted_data))
            
            logger.info(f"Successfully processed KB document: {self.doc_type or 'unknown'}")
            
            return ProcessingResult(
                success=True,
                content=text_content,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process KB document: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                error=str(e)
            )
    
    def can_process(self, document: Document) -> bool:
        """
        Check if document can be processed
        
        By default, processes all documents. Override in subclasses
        for type-specific filtering.
        """
        return True
    
    def _detect_document_type(
        self,
        document: Document,
        text_content: str
    ) -> str:
        """
        Detect document type from document name and content
        
        Args:
            document: Document to analyze
            text_content: Document text content
            
        Returns:
            Detected document type or 'unknown'
        """
        name_lower = document.name.lower()
        content_lower = text_content[:1000].lower()  # Check first 1000 chars
        
        # Common document type patterns (can be extended)
        type_patterns = {
            'policy': ['policy', 'policies', 'guideline'],
            'contract': ['contract', 'agreement', 'terms'],
            'guide': ['guide', 'manual', 'handbook', 'instructions'],
            'specification': ['spec', 'specification', 'requirements'],
            'report': ['report', 'analysis', 'summary'],
            'procedure': ['procedure', 'process', 'workflow'],
            'reference': ['reference', 'roster', 'matrix', 'directory']
        }
        
        # Check name first
        for doc_type, patterns in type_patterns.items():
            if any(pattern in name_lower for pattern in patterns):
                return doc_type
        
        # Check content if name didn't match
        for doc_type, patterns in type_patterns.items():
            if any(pattern in content_lower for pattern in patterns):
                return doc_type
        
        # Default
        return 'unknown'
    
    async def _extract_structured_data(
        self,
        text_content: str,
        doc_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract structured data from document text using LLM
        
        Args:
            text_content: Document text content
            doc_type: Document type
            
        Returns:
            Extracted structured data or None
        """
        if not self.llm_processor:
            return None
        
        try:
            # Build extraction prompt
            if self.extraction_schema:
                schema = self.extraction_schema
            else:
                # Default schema
                schema = {
                    'description': f'Extract key information from {doc_type} document',
                    'fields': ['summary', 'key_points', 'metadata']
                }
            
            extraction_prompt = self._build_extraction_prompt(text_content, schema, doc_type)
            
            # Use LLM to extract structured data
            if hasattr(self.llm_processor, 'llm_service'):
                result = await self.llm_processor.llm_service.generate_completion(
                    prompt=extraction_prompt,
                    max_tokens=1000,
                    temperature=0.1
                )
                
                # Try to parse as JSON
                import json
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse JSON from LLM response")
                        return None
                else:
                    logger.warning("No JSON found in LLM response")
                    return None
            else:
                logger.warning("LLM processor doesn't support structured extraction")
                return None
                
        except Exception as e:
            logger.warning(f"Failed to extract structured data: {e}")
            return None
    
    def _build_extraction_prompt(
        self,
        text_content: str,
        schema: Dict[str, Any],
        doc_type: str
    ) -> str:
        """
        Build extraction prompt from schema
        
        Args:
            text_content: Document text content
            schema: Extraction schema
            doc_type: Document type
            
        Returns:
            Extraction prompt string
        """
        schema_description = schema.get('description', 'Extract key information')
        fields = schema.get('fields', [])
        
        prompt = f"""Extract structured data from the following {doc_type} document.

{schema_description}

Extract the following fields: {', '.join(fields)}

Return the extracted data as JSON with the following structure:
{json.dumps({field: 'value' for field in fields}, indent=2)}

Document content:
{text_content[:5000]}  # Limit to first 5000 chars

Return only valid JSON, no additional text."""
        
        return prompt

