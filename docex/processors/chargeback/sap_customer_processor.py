"""
SAP Customer Check or Create Processor

Step 6 of the chargeback workflow: Check if customer exists in SAP,
or create new customer record if needed.
"""

import logging
from typing import Dict, Any, Optional

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document

logger = logging.getLogger(__name__)


class SapCustomerCheckOrCreateProcessor(BaseProcessor):
    """
    Processor that checks for existing SAP customer or creates a new one.
    Integrates with SAP 4 HANA Customer Master.
    """
    
    def __init__(self, config: Dict[str, Any], db=None):
        """
        Initialize SAP Customer Processor
        
        Args:
            config: Configuration dictionary with:
                - sap_api_url: SAP 4 HANA API endpoint
                - sap_client_id: SAP client ID
                - sap_username: SAP username
                - sap_password: SAP password (or use token)
                - create_if_not_exists: Create customer if not found (default: True)
        """
        super().__init__(config, db=db)
        self.sap_api_url = config.get('sap_api_url')
        self.sap_client_id = config.get('sap_client_id')
        self.sap_username = config.get('sap_username')
        self.sap_password = config.get('sap_password')
        self.create_if_not_exists = config.get('create_if_not_exists', True)
    
    def can_process(self, document: Document) -> bool:
        """
        Check if this processor can handle the document
        
        Args:
            document: Document to check
            
        Returns:
            True if document has passed federal DB validation
        """
        try:
            from docex.services.metadata_service import MetadataService
            metadata_service = MetadataService(self.db)
            metadata = metadata_service.get_metadata(document.id)
        except Exception:
            metadata = {}
        
        # Check if federal DB validation has passed
        has_federal_validation = (
            metadata.get('federal_db_validation_status') == 'VALID' or
            metadata.get('federal_db_valid') is True
        )
        
        return has_federal_validation
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Check or create SAP customer
        
        Args:
            document: Chargeback document to process
            
        Returns:
            ProcessingResult with SAP customer information
        """
        try:
            # Record operation start
            self._record_operation(
                document,
                status='in_progress',
                input_metadata={
                    'document_id': document.id,
                    'processor': 'SapCustomerCheckOrCreateProcessor'
                }
            )
            
            # Get document metadata
            from docex.services.metadata_service import MetadataService
            metadata_service = MetadataService(self.db)
            metadata = metadata_service.get_metadata(document.id)
            
            customer_name = metadata.get('customer_name')
            hin = metadata.get('hin')
            dea = metadata.get('dea')
            address = metadata.get('address')
            city = metadata.get('city')
            state = metadata.get('state')
            zip_code = metadata.get('zip_code')
            class_of_trade = metadata.get('class_of_trade')
            
            # Check if customer exists in SAP
            sap_result = await self._check_or_create_sap_customer(
                customer_name, hin, dea, address, city, state, zip_code, class_of_trade
            )
            
            # Store SAP customer information
            sap_metadata = {
                'sap_customer_status': sap_result['status'],
                'sap_customer_id': sap_result.get('sap_customer_id'),
                'sap_customer_created': sap_result.get('created', False),
                'sap_customer_exists': sap_result.get('exists', False),
                'sap_customer_checked_at': sap_result['checked_at'],
                'sap_customer_number': sap_result.get('customer_number'),
                'sap_customer_name': sap_result.get('sap_customer_name')
            }
            
            # Record success
            self._record_operation(
                document,
                status='success',
                output_metadata=sap_metadata
            )
            
            return ProcessingResult(
                success=True,
                metadata=sap_metadata,
                content=f"SAP customer {sap_result['status']}: {sap_result.get('sap_customer_id', 'N/A')}"
            )
            
        except Exception as e:
            logger.error(f"Error checking/creating SAP customer for document {document.id}: {str(e)}", exc_info=True)
            
            # Record failure
            self._record_operation(
                document,
                status='failed',
                error=str(e)
            )
            
            return ProcessingResult(
                success=False,
                error=f"Error checking/creating SAP customer: {str(e)}"
            )
    
    async def _check_or_create_sap_customer(
        self,
        customer_name: Optional[str],
        hin: Optional[str],
        dea: Optional[str],
        address: Optional[str],
        city: Optional[str],
        state: Optional[str],
        zip_code: Optional[str],
        class_of_trade: Optional[str]
    ) -> Dict[str, Any]:
        """
        Check if customer exists in SAP or create new one
        
        In production, this would:
        - Query SAP 4 HANA Customer Master
        - Search by HIN, DEA, or name
        - Create customer if not found (if create_if_not_exists=True)
        - Return SAP customer number
        
        Args:
            customer_name: Customer name
            hin: Healthcare Identification Number
            dea: DEA registration number
            address: Street address
            city: City
            state: State
            zip_code: ZIP code
            class_of_trade: Class of trade
            
        Returns:
            SAP customer result dictionary
        """
        from datetime import datetime
        
        # MVP: Simulate SAP customer check/create
        # In production, would call SAP API: self.sap_api_url
        
        if not customer_name and not hin and not dea:
            return {
                'status': 'ERROR',
                'reason': 'Missing customer identifiers',
                'checked_at': datetime.now().isoformat()
            }
        
        # Simulate SAP API call
        # In production: async with httpx.AsyncClient() as client:
        #     # Authenticate
        #     auth_response = await client.post(f"{self.sap_api_url}/auth", ...)
        #     # Search customer
        #     search_response = await client.get(f"{self.sap_api_url}/customers", 
        #         params={"hin": hin, "dea": dea}, headers={"Authorization": f"Bearer {token}"})
        
        # MVP: Check if we have an existing entity (from entity matching)
        # If entity exists, assume SAP customer exists
        # If new entity, create SAP customer
        
        # Generate SAP customer ID (in production, this comes from SAP)
        sap_customer_id = f"SAP-{hin or dea or customer_name[:10].upper().replace(' ', '')}"
        
        # MVP: Assume customer exists if we have HIN/DEA
        # In production, would query SAP to verify
        customer_exists = bool(hin or dea)
        
        if customer_exists:
            return {
                'status': 'EXISTS',
                'exists': True,
                'created': False,
                'sap_customer_id': sap_customer_id,
                'customer_number': sap_customer_id,
                'sap_customer_name': customer_name,
                'checked_at': datetime.now().isoformat()
            }
        elif self.create_if_not_exists:
            # Create new SAP customer
            # In production, would POST to SAP API
            return {
                'status': 'CREATED',
                'exists': False,
                'created': True,
                'sap_customer_id': sap_customer_id,
                'customer_number': sap_customer_id,
                'sap_customer_name': customer_name,
                'checked_at': datetime.now().isoformat()
            }
        else:
            return {
                'status': 'NOT_FOUND',
                'exists': False,
                'created': False,
                'reason': 'Customer not found and create_if_not_exists is False',
                'checked_at': datetime.now().isoformat()
            }


