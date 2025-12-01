"""
Extract Identifiers Processor

Step 1 of the chargeback workflow: Extract customer identifiers and contract information
from chargeback documents using LLM extraction.
"""

import logging
from typing import Dict, Any, Optional

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document

logger = logging.getLogger(__name__)


class ExtractIdentifiersProcessor(BaseProcessor):
    """
    Processor that extracts customer identifiers and contract information
    from chargeback documents using LLM extraction.
    
    Supports multiple LLM providers:
    - OpenAI (OpenAIAdapter)
    - Local/Ollama (LocalLLMAdapter)
    - Claude (ClaudeAdapter)
    """
    
    def __init__(self, config: Dict[str, Any], db=None):
        """
        Initialize Extract Identifiers Processor
        
        Args:
            config: Configuration dictionary with:
                - llm_provider: 'openai', 'local', 'ollama', or 'claude' (default: 'openai')
                - llm_config: Configuration for LLM adapter
                - prompt_name: Name of prompt template (default: 'chargeback_modeln')
        """
        super().__init__(config, db=db)
        
        # Get LLM provider (default: openai)
        llm_provider = config.get('llm_provider', 'openai').lower()
        llm_config = config.get('llm_config', {})
        llm_config.setdefault('prompt_name', 'chargeback_modeln')
        
        # Initialize appropriate LLM adapter
        if llm_provider in ['local', 'ollama']:
            from docex.processors.llm.local_llm_adapter import LocalLLMAdapter
            self.llm_adapter = LocalLLMAdapter(llm_config, db=db)
        elif llm_provider == 'claude':
            from docex.processors.llm.claude_adapter import ClaudeAdapter
            self.llm_adapter = ClaudeAdapter(llm_config, db=db)
        else:  # default to OpenAI
            from docex.processors.llm.openai_adapter import OpenAIAdapter
            self.llm_adapter = OpenAIAdapter(llm_config, db=db)
    
    def can_process(self, document: Document) -> bool:
        """
        Check if this processor can handle the document
        
        Args:
            document: Document to check
            
        Returns:
            True if document is a chargeback document
        """
        # Check document type or metadata
        doc_type = document.document_type or ''
        
        # Safely get metadata
        try:
            metadata = document.get_metadata_dict()
        except (AttributeError, TypeError):
            # Fallback: try to get metadata directly
            try:
                from docex.services.metadata_service import MetadataService
                metadata_service = MetadataService(self.db)
                metadata = metadata_service.get_metadata(document.id)
            except Exception:
                metadata = {}
        
        # Check if it's a chargeback document
        is_chargeback = (
            'chargeback' in doc_type.lower() or
            'chargeback' in str(metadata.get('document_type', '')).lower() or
            metadata.get('source') == 'model_n'
        )
        
        return is_chargeback
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Extract identifiers from chargeback document
        
        Args:
            document: Chargeback document to process
            
        Returns:
            ProcessingResult with extracted identifiers in metadata
        """
        try:
            # Record operation start
            self._record_operation(
                document,
                status='in_progress',
                input_metadata={
                    'document_id': document.id,
                    'document_type': document.document_type,
                    'processor': 'ExtractIdentifiersProcessor'
                }
            )
            
            # Use LLM adapter to extract structured data
            result = await self.llm_adapter.process(document)
            
            if not result.success:
                # Record failure
                self._record_operation(
                    document,
                    status='failed',
                    error=result.error
                )
                return ProcessingResult(
                    success=False,
                    error=f"LLM extraction failed: {result.error}"
                )
            
            # Extract key identifiers from LLM result
            extracted_metadata = result.metadata or {}
            
            # Store extracted identifiers with standardized keys
            identifiers = {
                'customer_name': extracted_metadata.get('customer_name'),
                'address': extracted_metadata.get('address'),
                'city': extracted_metadata.get('city'),
                'state': extracted_metadata.get('state'),
                'zip_code': extracted_metadata.get('zip_code'),
                'hin': extracted_metadata.get('hin'),
                'dea': extracted_metadata.get('dea'),
                'contract_number': extracted_metadata.get('contract_number'),
                'contract_type': extracted_metadata.get('contract_type'),
                'ndc': extracted_metadata.get('ndc'),
                'quantity': extracted_metadata.get('quantity'),
                'invoice_date': extracted_metadata.get('invoice_date'),
                'chargeback_amount': extracted_metadata.get('chargeback_amount'),
                'invoice_number': extracted_metadata.get('invoice_number'),
                'class_of_trade': extracted_metadata.get('class_of_trade'),
                'extraction_confidence': extracted_metadata.get('confidence_score'),
                'extraction_timestamp': result.timestamp.isoformat() if hasattr(result, 'timestamp') else None
            }
            
            # Record success
            self._record_operation(
                document,
                status='success',
                output_metadata={
                    'identifiers_extracted': True,
                    'extracted_fields': list(identifiers.keys()),
                    'has_hin': identifiers.get('hin') is not None,
                    'has_dea': identifiers.get('dea') is not None,
                    'has_contract': identifiers.get('contract_number') is not None
                }
            )
            
            return ProcessingResult(
                success=True,
                metadata=identifiers,
                content="Identifiers extracted successfully"
            )
            
        except Exception as e:
            logger.error(f"Error extracting identifiers from document {document.id}: {str(e)}", exc_info=True)
            
            # Record failure
            self._record_operation(
                document,
                status='failed',
                error=str(e)
            )
            
            return ProcessingResult(
                success=False,
                error=f"Error extracting identifiers: {str(e)}"
            )

