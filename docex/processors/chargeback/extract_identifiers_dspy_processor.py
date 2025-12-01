"""
DSPy-based Extract Identifiers Processor

Step 1 of the chargeback workflow using DSPy for structured extraction.
DSPy enables automatic prompt optimization and better extraction quality.

Reference: https://dspy.ai/
"""

import logging
from typing import Dict, Any, Optional

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document
from docex.processors.llm.dspy_adapter import DSPyAdapter, DSPySignatureBuilder

logger = logging.getLogger(__name__)


class ExtractIdentifiersDSPyProcessor(BaseProcessor):
    """
    DSPy-powered processor for extracting customer identifiers and contract information
    from chargeback documents.
    
    Benefits of DSPy:
    - Declarative signatures instead of prompt strings
    - Automatic prompt optimization
    - Better structured extraction
    - Easy to iterate and improve
    
    Example:
        ```python
        processor = ExtractIdentifiersDSPyProcessor({
            'model': 'openai/gpt-4o-mini',
            'use_chain_of_thought': True,
            'optimizer': {
                'type': 'BootstrapFewShot',
                'metric': lambda example, prediction, trace=None: 
                    example.customer_name == prediction.customer_name
            }
        })
        ```
    """
    
    # Chargeback extraction fields
    CHARGEBACK_FIELDS = [
        'customer_name',
        'address',
        'city',
        'state',
        'zip_code',
        'hin',
        'dea',
        'contract_number',
        'contract_type',
        'ndc',
        'quantity',
        'invoice_date',
        'chargeback_amount',
        'invoice_number',
        'class_of_trade',
        'confidence_score'
    ]
    
    def __init__(self, config: Dict[str, Any], db=None):
        """
        Initialize DSPy Extract Identifiers Processor
        
        Args:
            config: Configuration dictionary with:
                - model: Model identifier (default: 'openai/gpt-4o-mini')
                - api_key: Optional API key
                - use_chain_of_thought: Use ChainOfThought (default: True)
                - optimizer: Optional optimizer config
                - training_data: Optional training examples
                - signature: Optional custom signature (auto-generated if not provided)
            db: Optional tenant-aware database instance
        """
        super().__init__(config, db=db)
        
        # Get model configuration
        model = config.get('model', 'openai/gpt-4o-mini')
        api_key = config.get('api_key')
        
        # Build signature if not provided
        signature = config.get('signature')
        if not signature:
            signature = DSPySignatureBuilder.from_field_list(
                self.CHARGEBACK_FIELDS,
                input_name='chargeback_document_text'
            )
        
        # Create DSPy adapter config
        dspy_config = {
            'signature': signature,
            'model': model,
            'api_key': api_key,
            'use_chain_of_thought': config.get('use_chain_of_thought', True),
            'optimizer': config.get('optimizer'),
            'training_data': config.get('training_data', [])
        }
        
        # Initialize DSPy adapter
        self.dspy_adapter = DSPyAdapter(dspy_config, db=db)
    
    def can_process(self, document: Document) -> bool:
        """Check if this processor can handle the document"""
        # Use DSPy adapter's can_process
        return self.dspy_adapter.can_process(document)
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Extract identifiers from chargeback document using DSPy
        
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
                    'processor': 'ExtractIdentifiersDSPyProcessor'
                }
            )
            
            # Use DSPy adapter to extract structured data
            result = await self.dspy_adapter.process(document)
            
            if not result.success:
                # Record failure
                self._record_operation(
                    document,
                    status='failed',
                    error=result.error
                )
                return ProcessingResult(
                    success=False,
                    error=f"DSPy extraction failed: {result.error}"
                )
            
            # Extract key identifiers from DSPy result
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
                'extraction_timestamp': result.timestamp.isoformat() if hasattr(result, 'timestamp') else None,
                'reasoning': extracted_metadata.get('reasoning')  # From ChainOfThought
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
                    'has_contract': identifiers.get('contract_number') is not None,
                    'used_dspy': True
                }
            )
            
            return ProcessingResult(
                success=True,
                metadata=identifiers,
                content="Identifiers extracted successfully using DSPy"
            )
            
        except Exception as e:
            logger.error(f"Error extracting identifiers with DSPy from document {document.id}: {str(e)}", exc_info=True)
            
            # Record failure
            self._record_operation(
                document,
                status='failed',
                error=str(e)
            )
            
            return ProcessingResult(
                success=False,
                error=f"Error extracting identifiers with DSPy: {str(e)}"
            )

