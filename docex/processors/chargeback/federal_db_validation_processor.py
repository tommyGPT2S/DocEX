"""
Federal DB Validation Processor

Step 5 of the chargeback workflow: Validate customer against federal databases
(DEA, HIBCC, HRSA) to verify class-of-trade and eligibility.
"""

import logging
from typing import Dict, Any, Optional
import httpx

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document

logger = logging.getLogger(__name__)


class FederalDbValidationProcessor(BaseProcessor):
    """
    Processor that validates customers against federal databases.
    Checks DEA registration, HIBCC HIN validation, and HRSA program eligibility.
    """
    
    def __init__(self, config: Dict[str, Any], db=None):
        """
        Initialize Federal DB Validation Processor
        
        Args:
            config: Configuration dictionary with:
                - dea_api_url: DEA API endpoint (optional)
                - hibcc_api_url: HIBCC API endpoint (optional)
                - hrsa_api_url: HRSA API endpoint (optional)
                - api_timeout: Request timeout in seconds (default: 30)
                - retry_attempts: Number of retry attempts (default: 3)
        """
        super().__init__(config, db=db)
        self.dea_api_url = config.get('dea_api_url')
        self.hibcc_api_url = config.get('hibcc_api_url')
        self.hrsa_api_url = config.get('hrsa_api_url')
        self.api_timeout = config.get('api_timeout', 30)
        self.retry_attempts = config.get('retry_attempts', 3)
    
    def can_process(self, document: Document) -> bool:
        """
        Check if this processor can handle the document
        
        Args:
            document: Document to check
            
        Returns:
            True if document has passed GPO roster validation
        """
        try:
            from docex.services.metadata_service import MetadataService
            metadata_service = MetadataService(self.db)
            metadata = metadata_service.get_metadata(document.id)
        except Exception:
            metadata = {}
        
        # Check if GPO roster validation has passed
        has_gpo_validation = (
            metadata.get('gpo_roster_validation_status') == 'VALID' or
            metadata.get('gpo_roster_valid') is True
        )
        
        return has_gpo_validation
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Validate customer against federal databases
        
        Args:
            document: Chargeback document to process
            
        Returns:
            ProcessingResult with federal DB validation results
        """
        try:
            # Record operation start
            self._record_operation(
                document,
                status='in_progress',
                input_metadata={
                    'document_id': document.id,
                    'processor': 'FederalDbValidationProcessor'
                }
            )
            
            # Get document metadata
            from docex.services.metadata_service import MetadataService
            metadata_service = MetadataService(self.db)
            metadata = metadata_service.get_metadata(document.id)
            
            dea = metadata.get('dea')
            hin = metadata.get('hin')
            customer_name = metadata.get('customer_name')
            class_of_trade = metadata.get('class_of_trade')
            
            # Validate against federal databases
            validation_results = await self._validate_federal_databases(
                dea, hin, customer_name, class_of_trade
            )
            
            # Store validation results
            validation_metadata = {
                'federal_db_validation_status': validation_results['overall_status'],
                'federal_db_valid': validation_results['is_valid'],
                'federal_db_checked_at': validation_results['checked_at'],
                'dea_validation': validation_results.get('dea_validation', {}),
                'hibcc_validation': validation_results.get('hibcc_validation', {}),
                'hrsa_validation': validation_results.get('hrsa_validation', {}),
                'federal_db_validation_errors': validation_results.get('errors', [])
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
                content=f"Federal DB validation: {validation_results['overall_status']}"
            )
            
        except Exception as e:
            logger.error(f"Error validating federal databases for document {document.id}: {str(e)}", exc_info=True)
            
            # Record failure
            self._record_operation(
                document,
                status='failed',
                error=str(e)
            )
            
            return ProcessingResult(
                success=False,
                error=f"Error validating federal databases: {str(e)}"
            )
    
    async def _validate_federal_databases(
        self,
        dea: Optional[str],
        hin: Optional[str],
        customer_name: Optional[str],
        class_of_trade: Optional[str]
    ) -> Dict[str, Any]:
        """
        Validate customer against federal databases (MVP implementation)
        
        In production, this would:
        - Query DEA registrant database
        - Query HIBCC HIN portal
        - Query HRSA program portal
        
        Args:
            dea: DEA registration number
            hin: Healthcare Identification Number
            customer_name: Customer name
            class_of_trade: Class of trade
            
        Returns:
            Validation result dictionary
        """
        from datetime import datetime
        
        results = {
            'checked_at': datetime.now().isoformat(),
            'dea_validation': {},
            'hibcc_validation': {},
            'hrsa_validation': {},
            'errors': []
        }
        
        # Validate DEA (if provided)
        if dea:
            dea_result = await self._validate_dea(dea)
            results['dea_validation'] = dea_result
            if not dea_result.get('valid', False):
                results['errors'].append(f"DEA validation failed: {dea_result.get('reason', 'Unknown')}")
        
        # Validate HIN (if provided)
        if hin:
            hibcc_result = await self._validate_hibcc(hin)
            results['hibcc_validation'] = hibcc_result
            if not hibcc_result.get('valid', False):
                results['errors'].append(f"HIBCC validation failed: {hibcc_result.get('reason', 'Unknown')}")
        
        # Validate HRSA (if class of trade suggests HRSA eligibility)
        if class_of_trade and '340B' in class_of_trade.upper():
            hrsa_result = await self._validate_hrsa(hin, customer_name)
            results['hrsa_validation'] = hrsa_result
            if not hrsa_result.get('valid', False):
                results['errors'].append(f"HRSA validation failed: {hrsa_result.get('reason', 'Unknown')}")
        
        # Determine overall status
        all_valid = (
            (not dea or results['dea_validation'].get('valid', False)) and
            (not hin or results['hibcc_validation'].get('valid', False)) and
            (not (class_of_trade and '340B' in class_of_trade.upper()) or 
             results['hrsa_validation'].get('valid', False))
        )
        
        results['overall_status'] = 'VALID' if all_valid else 'INVALID'
        results['is_valid'] = all_valid
        
        return results
    
    async def _validate_dea(self, dea: str) -> Dict[str, Any]:
        """Validate DEA registration number"""
        # MVP: Simulate DEA validation
        # In production, would call DEA API: self.dea_api_url
        
        if not dea or len(dea) < 7:
            return {
                'valid': False,
                'reason': 'Invalid DEA format',
                'checked_at': None
            }
        
        # Simulate API call
        # In production: async with httpx.AsyncClient() as client:
        #     response = await client.get(f"{self.dea_api_url}/validate", params={"dea": dea})
        
        # MVP: Assume valid if starts with "DEA"
        if dea.startswith('DEA'):
            return {
                'valid': True,
                'reason': 'DEA registration verified',
                'registration_active': True,
                'checked_at': None
            }
        else:
            return {
                'valid': False,
                'reason': 'DEA registration not found',
                'checked_at': None
            }
    
    async def _validate_hibcc(self, hin: str) -> Dict[str, Any]:
        """Validate HIBCC HIN"""
        # MVP: Simulate HIBCC validation
        # In production, would call HIBCC API: self.hibcc_api_url
        
        if not hin or len(hin) < 6:
            return {
                'valid': False,
                'reason': 'Invalid HIN format',
                'checked_at': None
            }
        
        # Simulate API call
        # In production: async with httpx.AsyncClient() as client:
        #     response = await client.get(f"{self.hibcc_api_url}/validate", params={"hin": hin})
        
        # MVP: Assume valid if starts with "HIN"
        if hin.startswith('HIN'):
            return {
                'valid': True,
                'reason': 'HIN verified in HIBCC database',
                'hin_active': True,
                'checked_at': None
            }
        else:
            return {
                'valid': False,
                'reason': 'HIN not found in HIBCC database',
                'checked_at': None
            }
    
    async def _validate_hrsa(self, hin: Optional[str], customer_name: Optional[str]) -> Dict[str, Any]:
        """Validate HRSA 340B program eligibility"""
        # MVP: Simulate HRSA validation
        # In production, would call HRSA API: self.hrsa_api_url
        
        if not hin:
            return {
                'valid': False,
                'reason': 'HIN required for HRSA validation',
                'checked_at': None
            }
        
        # Simulate API call
        # In production: async with httpx.AsyncClient() as client:
        #     response = await client.get(f"{self.hrsa_api_url}/validate", params={"hin": hin})
        
        # MVP: Assume eligible if HIN is valid
        return {
            'valid': True,
            'reason': 'Customer eligible for 340B program',
            'program_active': True,
            'checked_at': None
        }


