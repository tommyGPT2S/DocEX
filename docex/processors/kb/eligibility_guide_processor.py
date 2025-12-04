"""
Eligibility Guide Processor

Processor for ingesting ICCR Eligibility Guide documents into the Knowledge Base.
Extracts eligibility verification rules and procedures.
"""

import logging
from typing import Dict, Any

from .rule_book_processor import RuleBookProcessor
from docex.document import Document

logger = logging.getLogger(__name__)


class EligibilityGuideProcessor(RuleBookProcessor):
    """
    Processor for Eligibility Guide documents
    
    Extracts:
    - Eligibility criteria
    - Verification procedures
    - Contract requirements
    - Exception handling rules
    """
    
    def __init__(self, config: Dict[str, Any], llm_processor=None):
        """Initialize Eligibility Guide processor"""
        config['rule_book_type'] = 'eligibility_guide'
        super().__init__(config, llm_processor)
    
    def can_process(self, document: Document) -> bool:
        """Check if document is an Eligibility Guide"""
        name_lower = document.name.lower()
        return 'eligibility guide' in name_lower or 'iccr eligibility' in name_lower
    
    async def _extract_structured_data(self, text_content: str) -> Dict[str, Any]:
        """
        Extract Eligibility Guide structured data
        
        Expected structure:
        {
            "eligibility_criteria": [
                {
                    "criterion": str,
                    "description": str,
                    "required": bool,
                    "verification_method": str
                }
            ],
            "verification_procedures": [str],
            "exception_rules": [str]
        }
        """
        result = await super()._extract_structured_data(text_content)
        if result:
            return result
        
        # Fallback: basic parsing if LLM extraction fails
        return {
            'eligibility_criteria': [],
            'verification_procedures': [],
            'exception_rules': [],
            'extraction_method': 'fallback'
        }

