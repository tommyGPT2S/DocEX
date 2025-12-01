"""
Compliance Trail Processor

Step 8 of the chargeback workflow: Generate compliance documentation
and ensure all audit trail information is complete.
"""

import logging
from typing import Dict, Any, Optional

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document

logger = logging.getLogger(__name__)


class ComplianceTrailProcessor(BaseProcessor):
    """
    Processor that generates compliance documentation and ensures
    complete audit trail for SOX compliance and audits.
    """
    
    def __init__(self, config: Dict[str, Any], db=None):
        """
        Initialize Compliance Trail Processor
        
        Args:
            config: Configuration dictionary with:
                - generate_compliance_doc: Generate compliance document (default: True)
                - compliance_template: Template for compliance documentation
                - include_screenshots: Include validation screenshots (default: False)
        """
        super().__init__(config, db=db)
        self.generate_compliance_doc = config.get('generate_compliance_doc', True)
        self.compliance_template = config.get('compliance_template')
        self.include_screenshots = config.get('include_screenshots', False)
    
    def can_process(self, document: Document) -> bool:
        """
        Check if this processor can handle the document
        
        Args:
            document: Document to check
            
        Returns:
            True if document has resolution status
        """
        try:
            from docex.services.metadata_service import MetadataService
            metadata_service = MetadataService(self.db)
            metadata = metadata_service.get_metadata(document.id)
        except Exception:
            metadata = {}
        
        # Check if chargeback has been resolved
        has_resolution = (
            metadata.get('chargeback_resolution_status') is not None or
            metadata.get('chargeback_resolved') is not None
        )
        
        return has_resolution
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Generate compliance trail
        
        Args:
            document: Chargeback document to process
            
        Returns:
            ProcessingResult with compliance trail information
        """
        try:
            # Record operation start
            self._record_operation(
                document,
                status='in_progress',
                input_metadata={
                    'document_id': document.id,
                    'processor': 'ComplianceTrailProcessor'
                }
            )
            
            # Get document metadata
            from docex.services.metadata_service import MetadataService
            metadata_service = MetadataService(self.db)
            metadata = metadata_service.get_metadata(document.id)
            
            # Generate compliance trail
            compliance_result = self._generate_compliance_trail(document, metadata)
            
            # Store compliance trail
            compliance_metadata = {
                'compliance_trail_generated': compliance_result['generated'],
                'compliance_trail_status': compliance_result['status'],
                'compliance_trail_generated_at': compliance_result['generated_at'],
                'compliance_trail_document_id': compliance_result.get('compliance_doc_id'),
                'compliance_trail_summary': compliance_result.get('summary'),
                'audit_trail_complete': compliance_result['audit_complete']
            }
            
            # Record success
            self._record_operation(
                document,
                status='success',
                output_metadata=compliance_metadata
            )
            
            return ProcessingResult(
                success=True,
                metadata=compliance_metadata,
                content=f"Compliance trail generated: {compliance_result['status']}"
            )
            
        except Exception as e:
            logger.error(f"Error generating compliance trail for document {document.id}: {str(e)}", exc_info=True)
            
            # Record failure
            self._record_operation(
                document,
                status='failed',
                error=str(e)
            )
            
            return ProcessingResult(
                success=False,
                error=f"Error generating compliance trail: {str(e)}"
            )
    
    def _generate_compliance_trail(self, document: Document, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate compliance trail documentation
        
        Args:
            document: Document being processed
            metadata: All document metadata
            
        Returns:
            Compliance trail result dictionary
        """
        from datetime import datetime
        
        # Collect all validation steps for audit trail
        validation_steps = [
            {
                'step': 'Extract Identifiers',
                'status': 'COMPLETED' if metadata.get('customer_name') else 'PENDING',
                'timestamp': metadata.get('extraction_timestamp')
            },
            {
                'step': 'Duplicate Check',
                'status': 'COMPLETED' if metadata.get('is_duplicate') is not None else 'PENDING',
                'result': 'DUPLICATE' if metadata.get('is_duplicate') else 'NEW',
                'timestamp': metadata.get('duplicate_confidence')
            },
            {
                'step': 'Contract Eligibility',
                'status': 'COMPLETED' if metadata.get('contract_eligibility_status') else 'PENDING',
                'result': metadata.get('contract_eligibility_status'),
                'timestamp': metadata.get('contract_eligibility_checked_at')
            },
            {
                'step': 'GPO Roster Validation',
                'status': 'COMPLETED' if metadata.get('gpo_roster_validation_status') else 'PENDING',
                'result': metadata.get('gpo_roster_validation_status'),
                'timestamp': metadata.get('gpo_roster_checked_at')
            },
            {
                'step': 'Federal DB Validation',
                'status': 'COMPLETED' if metadata.get('federal_db_validation_status') else 'PENDING',
                'result': metadata.get('federal_db_validation_status'),
                'timestamp': metadata.get('federal_db_checked_at')
            },
            {
                'step': 'SAP Customer Creation',
                'status': 'COMPLETED' if metadata.get('sap_customer_status') else 'PENDING',
                'result': metadata.get('sap_customer_status'),
                'timestamp': metadata.get('sap_customer_checked_at')
            },
            {
                'step': 'Chargeback Resolution',
                'status': 'COMPLETED' if metadata.get('chargeback_resolution_status') else 'PENDING',
                'result': metadata.get('chargeback_resolution_status'),
                'timestamp': metadata.get('chargeback_resolved_at')
            }
        ]
        
        # Check if all steps are completed
        all_completed = all(step['status'] == 'COMPLETED' for step in validation_steps)
        
        # Generate compliance summary
        summary = {
            'document_id': document.id,
            'workflow_completed': all_completed,
            'validation_steps': validation_steps,
            'final_status': metadata.get('chargeback_resolution_status'),
            'sap_customer_id': metadata.get('sap_customer_id'),
            'total_validations': len(validation_steps),
            'completed_validations': sum(1 for s in validation_steps if s['status'] == 'COMPLETED')
        }
        
        return {
            'generated': True,
            'status': 'COMPLETE' if all_completed else 'INCOMPLETE',
            'generated_at': datetime.now().isoformat(),
            'summary': summary,
            'audit_complete': all_completed,
            'compliance_doc_id': f"compliance_{document.id}" if self.generate_compliance_doc else None
        }


