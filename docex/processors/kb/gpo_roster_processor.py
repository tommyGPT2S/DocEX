"""
GPO Roster Processor

Processor for ingesting GPO Roster documents into the Knowledge Base.
Extracts customer contract eligibility information.
"""

import logging
from typing import Dict, Any

from .rule_book_processor import RuleBookProcessor
from docex.document import Document

logger = logging.getLogger(__name__)


class GPORosterProcessor(RuleBookProcessor):
    """
    Processor for GPO Roster documents
    
    Extracts:
    - Customer names and IDs
    - Contract identifiers
    - GPO names
    - Eligibility dates
    - Contract terms
    """
    
    def __init__(self, config: Dict[str, Any], llm_processor=None):
        """Initialize GPO Roster processor"""
        config['rule_book_type'] = 'gpo_roster'
        super().__init__(config, llm_processor)
    
    def can_process(self, document: Document) -> bool:
        """Check if document is a GPO Roster"""
        name_lower = document.name.lower()
        return 'gpo roster' in name_lower or ('gpo' in name_lower and 'roster' in name_lower)
    
    async def _extract_structured_data(self, text_content: str) -> Dict[str, Any]:
        """
        Extract GPO Roster structured data
        
        Expected structure:
        {
            "customers": [
                {
                    "customer_name": str,
                    "customer_id": str,
                    "gpo_name": str,
                    "contract_id": str,
                    "eligible": bool,
                    "effective_date": str,
                    "expiration_date": str
                }
            ],
            "gpo_list": [str],
            "contracts": [str]
        }
        """
        result = await super()._extract_structured_data(text_content)
        if result:
            return result
        
        # Fallback: basic parsing if LLM extraction fails
        return {
            'customers': [],
            'gpo_list': [],
            'contracts': [],
            'extraction_method': 'fallback'
        }

