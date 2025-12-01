"""
Duplicate Check Processor

Step 2 of the chargeback workflow: Check for duplicate chargebacks
using entity matching.
"""

import logging
from typing import Dict, Any

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document
from docex.processors.chargeback.entity_matching_processor import EntityMatchingProcessor

logger = logging.getLogger(__name__)


class DuplicateCheckProcessor(BaseProcessor):
    """
    Processor that checks for duplicate chargebacks using entity matching.
    This is a wrapper around EntityMatchingProcessor specifically for duplicate detection.
    """
    
    def __init__(self, config: Dict[str, Any], db=None):
        """
        Initialize Duplicate Check Processor
        
        Args:
            config: Configuration dictionary (passed to EntityMatchingProcessor)
        """
        super().__init__(config, db=db)
        self.entity_matcher = EntityMatchingProcessor(config, db=db)
    
    def can_process(self, document: Document) -> bool:
        """
        Check if this processor can handle the document
        
        Args:
            document: Document to check
            
        Returns:
            True if document has extracted identifiers
        """
        return self.entity_matcher.can_process(document)
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Check for duplicate chargeback
        
        Args:
            document: Chargeback document to check
            
        Returns:
            ProcessingResult with duplicate check results
        """
        try:
            # Record operation start
            self._record_operation(
                document,
                status='in_progress',
                input_metadata={
                    'document_id': document.id,
                    'processor': 'DuplicateCheckProcessor'
                }
            )
            
            # Use entity matcher to check for duplicates
            match_result = await self.entity_matcher.process(document)
            
            if not match_result.success:
                return ProcessingResult(
                    success=False,
                    error=f"Entity matching failed: {match_result.error}"
                )
            
            # Extract match information
            match_metadata = match_result.metadata or {}
            is_duplicate = match_metadata.get('entity_match_status') == 'MATCHED'
            existing_entity_id = match_metadata.get('existing_entity_id')
            confidence = match_metadata.get('match_confidence', 0.0)
            
            # Determine if this is a duplicate chargeback
            duplicate_metadata = {
                'is_duplicate': is_duplicate,
                'duplicate_entity_id': existing_entity_id if is_duplicate else None,
                'duplicate_confidence': confidence,
                'duplicate_reasoning': match_metadata.get('match_reasoning'),
                'requires_review': match_metadata.get('requires_review', False) or (is_duplicate and confidence < 0.95)
            }
            
            # Record success
            self._record_operation(
                document,
                status='success',
                output_metadata=duplicate_metadata
            )
            
            return ProcessingResult(
                success=True,
                metadata=duplicate_metadata,
                content=f"Duplicate check completed: {'DUPLICATE' if is_duplicate else 'NEW'}"
            )
            
        except Exception as e:
            logger.error(f"Error checking duplicate for document {document.id}: {str(e)}", exc_info=True)
            
            # Record failure
            self._record_operation(
                document,
                status='failed',
                error=str(e)
            )
            
            return ProcessingResult(
                success=False,
                error=f"Error checking duplicate: {str(e)}"
            )


