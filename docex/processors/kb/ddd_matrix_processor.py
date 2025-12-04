"""
DDD Matrix Processor

Processor for ingesting DDD Matrix documents into the Knowledge Base.
Extracts class-of-trade (COT) determination rules.
"""

import logging
from typing import Dict, Any

from .rule_book_processor import RuleBookProcessor
from docex.document import Document

logger = logging.getLogger(__name__)


class DDDMatrixProcessor(RuleBookProcessor):
    """
    Processor for DDD Matrix documents
    
    Extracts:
    - COT codes and descriptions
    - Customer type mappings
    - COT determination rules
    - Federal data mappings
    """
    
    def __init__(self, config: Dict[str, Any], llm_processor=None):
        """Initialize DDD Matrix processor"""
        config['rule_book_type'] = 'ddd_matrix'
        super().__init__(config, llm_processor)
    
    def can_process(self, document: Document) -> bool:
        """Check if document is a DDD Matrix"""
        name_lower = document.name.lower()
        return 'ddd matrix' in name_lower or 'class of trade' in name_lower
    
    async def _extract_structured_data(self, text_content: str) -> Dict[str, Any]:
        """
        Extract DDD Matrix structured data
        
        Expected structure:
        {
            "cot_rules": [
                {
                    "cot_code": str,
                    "cot_description": str,
                    "customer_types": [str],
                    "federal_mappings": Dict[str, str],
                    "conditions": [str]
                }
            ],
            "customer_type_mappings": Dict[str, str]
        }
        """
        result = await super()._extract_structured_data(text_content)
        if result:
            return result
        
        # Fallback: basic parsing if LLM extraction fails
        return {
            'cot_rules': [],
            'customer_type_mappings': {},
            'extraction_method': 'fallback'
        }

