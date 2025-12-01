"""
Chargeback Resolution Processor

Step 7 of the chargeback workflow: Resolve the chargeback by updating
status and routing to appropriate destination.
"""

import logging
from typing import Dict, Any, Optional

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document

logger = logging.getLogger(__name__)


class ChargebackResolutionProcessor(BaseProcessor):
    """
    Processor that resolves chargebacks by updating status and routing.
    Final step before compliance trail.
    """
    
    def __init__(self, config: Dict[str, Any], db=None):
        """
        Initialize Chargeback Resolution Processor
        
        Args:
            config: Configuration dictionary with:
                - resolution_rules: Rules for chargeback resolution
                - auto_resolve: Automatically resolve if all validations pass (default: True)
                - resolution_status: Status to set ('resolved', 'pending_review', etc.)
        """
        super().__init__(config, db=db)
        self.resolution_rules = config.get('resolution_rules', {})
        self.auto_resolve = config.get('auto_resolve', True)
        self.resolution_status = config.get('resolution_status', 'resolved')
    
    def can_process(self, document: Document) -> bool:
        """
        Check if this processor can handle the document
        
        Args:
            document: Document to check
            
        Returns:
            True if document has SAP customer information
        """
        try:
            from docex.services.metadata_service import MetadataService
            metadata_service = MetadataService(self.db)
            metadata = metadata_service.get_metadata(document.id)
        except Exception:
            metadata = {}
        
        # Check if SAP customer has been created/verified
        has_sap_customer = (
            metadata.get('sap_customer_status') in ['EXISTS', 'CREATED'] or
            metadata.get('sap_customer_id') is not None
        )
        
        return has_sap_customer
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Resolve chargeback
        
        Args:
            document: Chargeback document to process
            
        Returns:
            ProcessingResult with resolution information
        """
        try:
            # Record operation start
            self._record_operation(
                document,
                status='in_progress',
                input_metadata={
                    'document_id': document.id,
                    'processor': 'ChargebackResolutionProcessor'
                }
            )
            
            # Get document metadata
            from docex.services.metadata_service import MetadataService
            metadata_service = MetadataService(self.db)
            metadata = metadata_service.get_metadata(document.id)
            
            # Determine resolution status based on validations
            resolution_result = self._determine_resolution(metadata)
            
            # Store resolution results
            resolution_metadata = {
                'chargeback_resolution_status': resolution_result['status'],
                'chargeback_resolved': resolution_result['resolved'],
                'chargeback_resolution_reason': resolution_result['reason'],
                'chargeback_resolved_at': resolution_result['resolved_at'],
                'chargeback_routing': resolution_result.get('routing'),
                'chargeback_next_action': resolution_result.get('next_action')
            }
            
            # Record success
            self._record_operation(
                document,
                status='success',
                output_metadata=resolution_metadata
            )
            
            return ProcessingResult(
                success=True,
                metadata=resolution_metadata,
                content=f"Chargeback resolution: {resolution_result['status']}"
            )
            
        except Exception as e:
            logger.error(f"Error resolving chargeback for document {document.id}: {str(e)}", exc_info=True)
            
            # Record failure
            self._record_operation(
                document,
                status='failed',
                error=str(e)
            )
            
            return ProcessingResult(
                success=False,
                error=f"Error resolving chargeback: {str(e)}"
            )
    
    def _determine_resolution(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine chargeback resolution based on validation results
        
        Args:
            metadata: Document metadata with all validation results
            
        Returns:
            Resolution result dictionary
        """
        from datetime import datetime
        
        # Check all validation steps
        validations = {
            'duplicate_check': metadata.get('is_duplicate') is False,
            'contract_eligibility': metadata.get('contract_eligibility_valid') is True,
            'gpo_roster': metadata.get('gpo_roster_valid') is True,
            'federal_db': metadata.get('federal_db_valid') is True,
            'sap_customer': metadata.get('sap_customer_status') in ['EXISTS', 'CREATED']
        }
        
        # Determine if all validations passed
        all_valid = all(validations.values())
        
        if all_valid and self.auto_resolve:
            return {
                'status': 'RESOLVED',
                'resolved': True,
                'reason': 'All validations passed, chargeback resolved',
                'resolved_at': datetime.now().isoformat(),
                'routing': 'processed_chargebacks',
                'next_action': 'Complete'
            }
        elif not all_valid:
            failed_validations = [k for k, v in validations.items() if not v]
            return {
                'status': 'PENDING_REVIEW',
                'resolved': False,
                'reason': f'Validations failed: {", ".join(failed_validations)}',
                'resolved_at': datetime.now().isoformat(),
                'routing': 'exception_queue',
                'next_action': 'Manual review required'
            }
        else:
            return {
                'status': 'PENDING',
                'resolved': False,
                'reason': 'Auto-resolve disabled, manual review required',
                'resolved_at': datetime.now().isoformat(),
                'routing': 'pending_review',
                'next_action': 'Manual review'
            }


