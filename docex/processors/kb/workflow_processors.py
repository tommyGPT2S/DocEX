"""
Workflow Integration Processors

Processors that integrate KB service into the chargeback workflow:
- ContractEligibilityProcessor (Step 3)
- COTDeterminationProcessor (Step 6)
"""

import logging
from typing import Dict, Any, Optional

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document
from docex.services.knowledge_base_service import KnowledgeBaseService

logger = logging.getLogger(__name__)


class ContractEligibilityProcessor(BaseProcessor):
    """
    Contract Eligibility Processor (Step 3)
    
    Validates customer contract eligibility using KB service.
    Queries GPO Roster and Eligibility Guide.
    """
    
    def __init__(self, config: Dict[str, Any], kb_service: KnowledgeBaseService):
        """
        Initialize contract eligibility processor
        
        Args:
            config: Processor configuration
            kb_service: Knowledge Base Service instance
        """
        super().__init__(config)
        self.kb_service = kb_service
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Process chargeback document for contract eligibility validation
        
        Args:
            document: Chargeback document (EDI or similar)
            
        Returns:
            ProcessingResult with eligibility validation
        """
        try:
            logger.info(f"Processing contract eligibility for document: {document.name}")
            
            # Extract customer and contract information from document
            # In real implementation, this would parse EDI or extract from document metadata
            customer_info = self._extract_customer_info(document)
            
            if not customer_info.get('customer_name'):
                return ProcessingResult(
                    success=False,
                    error="Could not extract customer name from document"
                )
            
            # Query KB service for eligibility validation
            eligibility_result = await self.kb_service.validate_contract_eligibility(
                customer_name=customer_info.get('customer_name'),
                contract_id=customer_info.get('contract_id'),
                product_code=customer_info.get('product_code')
            )
            
            # Determine if eligible (99.9% should be eligible, 0.1% rejected)
            is_eligible = eligibility_result.get('eligible', False)
            confidence = eligibility_result.get('confidence_score', 0.0)
            
            # Route to exception queue if not eligible (0.1% case)
            if not is_eligible and confidence < 0.5:
                logger.warning(f"Customer {customer_info.get('customer_name')} not eligible - routing to exception queue")
            
            # Build metadata
            metadata = {
                'step': 3,
                'step_name': 'contract_eligibility_validation',
                'customer_name': customer_info.get('customer_name'),
                'contract_id': customer_info.get('contract_id'),
                'product_code': customer_info.get('product_code'),
                'eligible': is_eligible,
                'eligibility_reason': eligibility_result.get('reason'),
                'confidence_score': confidence,
                'kb_sources': eligibility_result.get('sources', []),
                'routed_to_exception': not is_eligible and confidence < 0.5
            }
            
            logger.info(f"Eligibility validation completed: eligible={is_eligible}, confidence={confidence:.2f}")
            
            return ProcessingResult(
                success=True,
                content=eligibility_result,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process contract eligibility: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                error=str(e)
            )
    
    def can_process(self, document: Document) -> bool:
        """Check if document can be processed for contract eligibility"""
        # Check document type or metadata
        doc_type = getattr(document, 'document_type', '')
        return doc_type in ['chargeback', 'edi', 'kickout'] or 'chargeback' in document.name.lower()
    
    def _extract_customer_info(self, document: Document) -> Dict[str, Any]:
        """
        Extract customer information from document
        
        In real implementation, this would parse EDI format or extract from metadata.
        For demo purposes, we'll try to extract from document metadata or name.
        
        Args:
            document: Document to extract from
            
        Returns:
            Dictionary with customer information
        """
        # Try to get from document metadata
        if hasattr(document, 'metadata') and document.metadata:
            return {
                'customer_name': document.metadata.get('customer_name'),
                'contract_id': document.metadata.get('contract_id'),
                'product_code': document.metadata.get('product_code')
            }
        
        # Fallback: try to extract from document name or content
        # This is a simplified version - real implementation would parse EDI
        return {
            'customer_name': None,
            'contract_id': None,
            'product_code': None
        }


class COTDeterminationProcessor(BaseProcessor):
    """
    Class-of-Trade (COT) Determination Processor (Step 6)
    
    Determines class-of-trade using DDD Matrix via KB service.
    Uses customer info and federal DB results.
    """
    
    def __init__(self, config: Dict[str, Any], kb_service: KnowledgeBaseService):
        """
        Initialize COT determination processor
        
        Args:
            config: Processor configuration
            kb_service: Knowledge Base Service instance
        """
        super().__init__(config)
        self.kb_service = kb_service
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Process document for COT determination
        
        Args:
            document: Document with customer info and federal DB results
            
        Returns:
            ProcessingResult with COT determination
        """
        try:
            logger.info(f"Processing COT determination for document: {document.name}")
            
            # Extract customer info and federal data from document
            customer_info = self._extract_customer_info(document)
            federal_data = self._extract_federal_data(document)
            
            if not customer_info.get('customer_name'):
                return ProcessingResult(
                    success=False,
                    error="Could not extract customer name from document"
                )
            
            # Query KB service for COT determination
            cot_result = await self.kb_service.get_class_of_trade(
                customer_name=customer_info.get('customer_name'),
                customer_type=customer_info.get('customer_type'),
                federal_data=federal_data
            )
            
            # Build metadata
            metadata = {
                'step': 6,
                'step_name': 'cot_determination',
                'customer_name': customer_info.get('customer_name'),
                'customer_type': customer_info.get('customer_type'),
                'cot_code': cot_result.get('cot_code'),
                'cot_description': cot_result.get('cot_description'),
                'cot_rules': cot_result.get('cot_rules', []),
                'confidence_score': cot_result.get('confidence_score', 0.0),
                'kb_sources': cot_result.get('sources', []),
                'federal_data_used': federal_data is not None
            }
            
            logger.info(f"COT determination completed: COT={cot_result.get('cot_code')}, confidence={cot_result.get('confidence_score', 0.0):.2f}")
            
            return ProcessingResult(
                success=True,
                content=cot_result,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process COT determination: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                error=str(e)
            )
    
    def can_process(self, document: Document) -> bool:
        """Check if document can be processed for COT determination"""
        # Check if document has federal data or is at step 6
        if hasattr(document, 'metadata') and document.metadata:
            step = document.metadata.get('step')
            return step == 6 or 'federal' in str(document.metadata).lower()
        return False
    
    def _extract_customer_info(self, document: Document) -> Dict[str, Any]:
        """Extract customer information from document"""
        if hasattr(document, 'metadata') and document.metadata:
            return {
                'customer_name': document.metadata.get('customer_name'),
                'customer_type': document.metadata.get('customer_type')
            }
        return {
            'customer_name': None,
            'customer_type': None
        }
    
    def _extract_federal_data(self, document: Document) -> Optional[Dict[str, Any]]:
        """Extract federal database lookup results from document"""
        if hasattr(document, 'metadata') and document.metadata:
            return document.metadata.get('federal_data')
        return None

