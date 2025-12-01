"""
Contract Eligibility Processor

Step 3 of the chargeback workflow: Validate contract eligibility
by checking contract number against GPO rosters and eligibility rules.
"""

import logging
from typing import Dict, Any, Optional

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document

logger = logging.getLogger(__name__)


class ContractEligibilityProcessor(BaseProcessor):
    """
    Processor that validates contract eligibility for chargebacks.
    Checks if the contract number is valid and the customer is eligible.
    """
    
    def __init__(self, config: Dict[str, Any], db=None):
        """
        Initialize Contract Eligibility Processor
        
        Args:
            config: Configuration dictionary with:
                - gpo_roster_source: Source for GPO rosters ('gdrive', 's3', 'local')
                - eligibility_rules_path: Path to eligibility rules file
                - contract_api_url: Optional API endpoint for contract validation
        """
        super().__init__(config, db=db)
        self.gpo_roster_source = config.get('gpo_roster_source', 'local')
        self.eligibility_rules_path = config.get('eligibility_rules_path')
        self.contract_api_url = config.get('contract_api_url')
    
    def can_process(self, document: Document) -> bool:
        """
        Check if this processor can handle the document
        
        Args:
            document: Document to check
            
        Returns:
            True if document has contract information
        """
        try:
            from docex.services.metadata_service import MetadataService
            metadata_service = MetadataService(self.db)
            metadata = metadata_service.get_metadata(document.id)
        except Exception:
            metadata = {}
        
        # Check if contract information is available
        has_contract = (
            metadata.get('contract_number') is not None or
            metadata.get('contract_type') is not None
        )
        
        return has_contract
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Validate contract eligibility
        
        Args:
            document: Chargeback document to process
            
        Returns:
            ProcessingResult with eligibility validation results
        """
        try:
            # Record operation start
            self._record_operation(
                document,
                status='in_progress',
                input_metadata={
                    'document_id': document.id,
                    'processor': 'ContractEligibilityProcessor'
                }
            )
            
            # Get extracted identifiers from document metadata
            from docex.services.metadata_service import MetadataService
            metadata_service = MetadataService(self.db)
            metadata = metadata_service.get_metadata(document.id)
            
            contract_number = metadata.get('contract_number')
            contract_type = metadata.get('contract_type')
            customer_name = metadata.get('customer_name')
            hin = metadata.get('hin')
            
            # Validate contract eligibility
            # In production, this would:
            # 1. Query GPO roster from G-Drive/S3
            # 2. Check if customer is on the roster
            # 3. Verify contract is active
            # 4. Check eligibility dates
            
            # For MVP: Simulate validation
            eligibility_result = self._validate_contract_eligibility(
                contract_number, contract_type, customer_name, hin
            )
            
            # Store eligibility results in metadata
            eligibility_metadata = {
                'contract_eligibility_status': eligibility_result['status'],
                'contract_eligibility_valid': eligibility_result['is_valid'],
                'contract_eligibility_reason': eligibility_result['reason'],
                'contract_eligibility_checked_at': eligibility_result['checked_at'],
                'contract_active': eligibility_result.get('contract_active', True),
                'eligibility_start_date': eligibility_result.get('eligibility_start_date'),
                'eligibility_end_date': eligibility_result.get('eligibility_end_date')
            }
            
            # Record success
            self._record_operation(
                document,
                status='success',
                output_metadata=eligibility_metadata
            )
            
            return ProcessingResult(
                success=True,
                metadata=eligibility_metadata,
                content=f"Contract eligibility validated: {eligibility_result['status']}"
            )
            
        except Exception as e:
            logger.error(f"Error validating contract eligibility for document {document.id}: {str(e)}", exc_info=True)
            
            # Record failure
            self._record_operation(
                document,
                status='failed',
                error=str(e)
            )
            
            return ProcessingResult(
                success=False,
                error=f"Error validating contract eligibility: {str(e)}"
            )
    
    def _validate_contract_eligibility(
        self,
        contract_number: Optional[str],
        contract_type: Optional[str],
        customer_name: Optional[str],
        hin: Optional[str]
    ) -> Dict[str, Any]:
        """
        Validate contract eligibility (MVP implementation)
        
        In production, this would:
        - Query GPO roster from G-Drive/S3
        - Check customer against roster
        - Verify contract dates
        - Check eligibility rules
        
        Args:
            contract_number: Contract number
            contract_type: Type of contract (GPO, Direct, etc.)
            customer_name: Customer name
            hin: Healthcare Identification Number
            
        Returns:
            Validation result dictionary
        """
        from datetime import datetime
        
        # MVP: Simple validation logic
        # In production, this would query actual GPO rosters
        
        if not contract_number:
            return {
                'status': 'INVALID',
                'is_valid': False,
                'reason': 'Contract number is missing',
                'checked_at': datetime.now().isoformat()
            }
        
        # Simulate contract validation
        # For MVP, assume contracts starting with "CONTRACT-" are valid
        if contract_number.startswith('CONTRACT-'):
            return {
                'status': 'ELIGIBLE',
                'is_valid': True,
                'reason': f'Contract {contract_number} is valid and customer is eligible',
                'checked_at': datetime.now().isoformat(),
                'contract_active': True,
                'eligibility_start_date': '2024-01-01',
                'eligibility_end_date': '2024-12-31'
            }
        else:
            return {
                'status': 'INVALID',
                'is_valid': False,
                'reason': f'Contract {contract_number} not found or invalid',
                'checked_at': datetime.now().isoformat()
            }


