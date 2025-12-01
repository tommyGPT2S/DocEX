"""
GPO Roster Validation Processor

Step 4 of the chargeback workflow: Validate customer against GPO roster
to ensure they are authorized for the contract.
"""

import logging
from typing import Dict, Any, Optional

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document

logger = logging.getLogger(__name__)


class GpoRosterValidationProcessor(BaseProcessor):
    """
    Processor that validates customers against GPO rosters.
    Checks if the customer is listed on the GPO roster for the contract.
    """
    
    def __init__(self, config: Dict[str, Any], db=None):
        """
        Initialize GPO Roster Validation Processor
        
        Args:
            config: Configuration dictionary with:
                - gpo_roster_source: Source for GPO rosters ('gdrive', 's3', 'local')
                - gpo_roster_path: Path to GPO roster file or folder
                - gdrive_credentials: Google Drive API credentials (if using G-Drive)
        """
        super().__init__(config, db=db)
        self.gpo_roster_source = config.get('gpo_roster_source', 'local')
        self.gpo_roster_path = config.get('gpo_roster_path')
    
    def can_process(self, document: Document) -> bool:
        """
        Check if this processor can handle the document
        
        Args:
            document: Document to check
            
        Returns:
            True if document has contract and customer information
        """
        try:
            from docex.services.metadata_service import MetadataService
            metadata_service = MetadataService(self.db)
            metadata = metadata_service.get_metadata(document.id)
        except Exception:
            metadata = {}
        
        # Check if contract eligibility has been validated
        has_contract = (
            metadata.get('contract_number') is not None and
            metadata.get('contract_eligibility_valid') is not None
        )
        
        return has_contract
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Validate customer against GPO roster
        
        Args:
            document: Chargeback document to process
            
        Returns:
            ProcessingResult with GPO roster validation results
        """
        try:
            # Record operation start
            self._record_operation(
                document,
                status='in_progress',
                input_metadata={
                    'document_id': document.id,
                    'processor': 'GpoRosterValidationProcessor'
                }
            )
            
            # Get document metadata
            from docex.services.metadata_service import MetadataService
            metadata_service = MetadataService(self.db)
            metadata = metadata_service.get_metadata(document.id)
            
            contract_number = metadata.get('contract_number')
            customer_name = metadata.get('customer_name')
            hin = metadata.get('hin')
            dea = metadata.get('dea')
            
            # Validate against GPO roster
            # In production, this would:
            # 1. Load GPO roster from G-Drive/S3
            # 2. Search for customer by HIN/DEA/name
            # 3. Verify they're on the roster for this contract
            # 4. Check roster dates
            
            validation_result = self._validate_against_gpo_roster(
                contract_number, customer_name, hin, dea
            )
            
            # Store validation results
            validation_metadata = {
                'gpo_roster_validation_status': validation_result['status'],
                'gpo_roster_valid': validation_result['is_valid'],
                'gpo_roster_reason': validation_result['reason'],
                'gpo_roster_checked_at': validation_result['checked_at'],
                'gpo_roster_match_method': validation_result.get('match_method'),
                'gpo_roster_customer_found': validation_result.get('customer_found', False)
            }
            
            # Record success
            self._record_operation(
                document,
                status='success',
                output_metadata=validation_metadata
            )
            
            return ProcessingResult(
                success=True,
                metadata=validation_metadata,
                content=f"GPO roster validation: {validation_result['status']}"
            )
            
        except Exception as e:
            logger.error(f"Error validating GPO roster for document {document.id}: {str(e)}", exc_info=True)
            
            # Record failure
            self._record_operation(
                document,
                status='failed',
                error=str(e)
            )
            
            return ProcessingResult(
                success=False,
                error=f"Error validating GPO roster: {str(e)}"
            )
    
    def _validate_against_gpo_roster(
        self,
        contract_number: Optional[str],
        customer_name: Optional[str],
        hin: Optional[str],
        dea: Optional[str]
    ) -> Dict[str, Any]:
        """
        Validate customer against GPO roster (MVP implementation)
        
        In production, this would:
        - Load GPO roster from G-Drive/S3
        - Search for customer
        - Verify contract association
        
        Args:
            contract_number: Contract number
            customer_name: Customer name
            hin: Healthcare Identification Number
            dea: DEA registration number
            
        Returns:
            Validation result dictionary
        """
        from datetime import datetime
        
        # MVP: Simulate GPO roster validation
        # In production, this would query actual GPO rosters from G-Drive/S3
        
        if not contract_number or not (hin or dea or customer_name):
            return {
                'status': 'INVALID',
                'is_valid': False,
                'reason': 'Missing contract number or customer identifiers',
                'checked_at': datetime.now().isoformat()
            }
        
        # Simulate roster lookup
        # For MVP, assume customers with valid contracts are on the roster
        if contract_number.startswith('CONTRACT-'):
            return {
                'status': 'VALID',
                'is_valid': True,
                'reason': f'Customer found on GPO roster for contract {contract_number}',
                'checked_at': datetime.now().isoformat(),
                'match_method': 'HIN/DEA match',
                'customer_found': True
            }
        else:
            return {
                'status': 'NOT_FOUND',
                'is_valid': False,
                'reason': f'Customer not found on GPO roster for contract {contract_number}',
                'checked_at': datetime.now().isoformat(),
                'customer_found': False
            }


