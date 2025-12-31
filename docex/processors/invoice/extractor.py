"""
Invoice Extractor

Extracts structured invoice data from document text using LLM.
Handles OCR detection and multi-stage extraction for complex invoices.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document
from docex.models.invoice import (
    InvoiceData,
    InvoiceExtractionResult,
    InvoiceStatus,
    InvoiceProcessingConfig
)

logger = logging.getLogger(__name__)


class InvoiceExtractor(BaseProcessor):
    """
    Extracts structured invoice data from document text using LLM.
    
    Features:
    - Uses configurable LLM adapter for extraction
    - Loads prompt from docex/prompts/invoice_extraction.yaml
    - Two-stage extraction for line items (heuristic + LLM refinement)
    - OCR text quality detection
    - Confidence scoring
    """
    
    def __init__(self, config: Dict[str, Any] = None, db=None):
        super().__init__(config or {}, db)
        
        # Get LLM adapter from config
        self.llm_adapter = config.get('llm_adapter') if config else None
        
        # Processing config
        self.processing_config = InvoiceProcessingConfig(
            **(config.get('processing_config', {}) if config else {})
        )
        
        # Prompt template (will be loaded)
        self._prompt_template = None
        self._system_prompt = None
    
    def can_process(self, document: Document) -> bool:
        """Can process documents with text content"""
        # Check if document has text content
        if hasattr(document, 'raw_content') and document.raw_content:
            return True
        
        # Check metadata
        metadata = document.get_metadata_dict() if hasattr(document, 'get_metadata_dict') else {}
        return metadata.get('doc_type') == 'invoice' or metadata.get('has_text', False)
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Extract invoice data from document.
        
        Args:
            document: Document with text content
            
        Returns:
            ProcessingResult with InvoiceExtractionResult
        """
        start_time = time.time()
        
        try:
            # Get text content
            text = self._get_text_content(document)
            
            if not text:
                return ProcessingResult(
                    success=False,
                    error="No text content found in document"
                )
            
            # Check text quality (OCR detection)
            text_quality = self._assess_text_quality(text)
            
            # Load prompt template
            self._load_prompt_template()
            
            # Extract using LLM
            extraction_result = await self._extract_with_llm(text, document.id)
            
            # Calculate extraction time
            extraction_time_ms = int((time.time() - start_time) * 1000)
            extraction_result['extraction_time_ms'] = extraction_time_ms
            
            # Add text quality info
            extraction_result['text_quality'] = text_quality
            
            return ProcessingResult(
                success=extraction_result.get('success', False),
                content=extraction_result,
                metadata={
                    'extraction_method': 'llm',
                    'llm_model': self._get_model_name(),
                    'extraction_time_ms': extraction_time_ms,
                    'text_quality': text_quality.get('quality_score', 0),
                    'confidence_score': extraction_result.get('raw_json', {}).get('confidence_score', 0)
                }
            )
            
        except Exception as e:
            logger.exception(f"Invoice extraction failed: {e}")
            return ProcessingResult(
                success=False,
                error=str(e)
            )
    
    def _get_text_content(self, document: Document) -> Optional[str]:
        """Get text content from document"""
        # Try raw_content first
        if hasattr(document, 'raw_content') and document.raw_content:
            return document.raw_content
        
        # Try get_content method
        if hasattr(document, 'get_content'):
            try:
                return document.get_content(mode='text')
            except Exception:
                pass
        
        # Try content dict
        if hasattr(document, 'content') and document.content:
            if isinstance(document.content, dict):
                return document.content.get('text', document.content.get('raw_text', ''))
            if isinstance(document.content, str):
                return document.content
        
        return None
    
    def _assess_text_quality(self, text: str) -> Dict[str, Any]:
        """
        Assess text quality to detect OCR issues.
        
        Returns quality metrics that can indicate if OCR is needed or
        if existing OCR quality is poor.
        """
        if not text:
            return {'quality_score': 0, 'issues': ['empty_text']}
        
        issues = []
        
        # Check for common OCR artifacts
        # High ratio of special characters
        special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
        special_ratio = special_chars / len(text) if text else 0
        
        if special_ratio > 0.3:
            issues.append('high_special_char_ratio')
        
        # Check for repeated garbage characters
        if '□' in text or '�' in text or '\x00' in text:
            issues.append('ocr_artifacts')
        
        # Check word density (words per character)
        words = text.split()
        word_density = len(words) / len(text) if text else 0
        
        if word_density < 0.05:  # Very low word density
            issues.append('low_word_density')
        
        # Check for numeric content (invoices should have numbers)
        numbers = sum(1 for c in text if c.isdigit())
        number_ratio = numbers / len(text) if text else 0
        
        if number_ratio < 0.01:
            issues.append('low_numeric_content')
        
        # Calculate quality score
        quality_score = 1.0
        quality_score -= special_ratio * 0.5
        quality_score -= 0.2 * len(issues)
        quality_score = max(0.0, min(1.0, quality_score))
        
        return {
            'quality_score': round(quality_score, 2),
            'word_count': len(words),
            'char_count': len(text),
            'special_char_ratio': round(special_ratio, 3),
            'number_ratio': round(number_ratio, 3),
            'issues': issues,
            'needs_ocr': 'ocr_artifacts' in issues or quality_score < 0.3
        }
    
    def _load_prompt_template(self) -> None:
        """Load prompt template from yaml file"""
        if self._prompt_template is not None:
            return
        
        try:
            import yaml
            from pathlib import Path
            
            # Find prompt file
            prompt_path = Path(__file__).parent.parent.parent / 'prompts' / 'invoice_extraction.yaml'
            
            if prompt_path.exists():
                with open(prompt_path, 'r') as f:
                    prompt_config = yaml.safe_load(f)
                
                self._system_prompt = prompt_config.get('system_prompt', '')
                self._prompt_template = prompt_config.get('user_prompt_template', '')
            else:
                # Fallback default prompt
                self._system_prompt = self._get_default_system_prompt()
                self._prompt_template = "Please extract the invoice data from this text:\n\n{{ content }}"
                
        except Exception as e:
            logger.warning(f"Could not load prompt template: {e}, using default")
            self._system_prompt = self._get_default_system_prompt()
            self._prompt_template = "Please extract the invoice data from this text:\n\n{{ content }}"
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for invoice extraction"""
        return """You are an expert invoice data extraction system. Extract the following information from invoice text:

Return a JSON object with these exact fields:
{
    "invoice_number": "string",
    "customer_id": "string",
    "supplier_id": "string",
    "purchase_order_number": "string",
    "total_amount": number,
    "subtotal": number,
    "tax_amount": number,
    "currency": "string (USD, EUR, GBP, etc.)",
    "invoice_date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD",
    "supplier": {
        "name": "string",
        "id": "string",
        "tax_id": "string",
        "email": "string",
        "address": {
            "line1": "string",
            "city": "string",
            "state": "string",
            "postal_code": "string",
            "country": "string"
        }
    },
    "customer": {
        "name": "string",
        "id": "string",
        "tax_id": "string",
        "email": "string",
        "address": {
            "line1": "string",
            "city": "string",
            "state": "string",
            "postal_code": "string",
            "country": "string"
        }
    },
    "line_items": [
        {
            "description": "string",
            "quantity": number,
            "unit_price": number,
            "total": number,
            "sku": "string (if available)"
        }
    ],
    "payment_terms": "string",
    "confidence_score": number (0.0 to 1.0, your confidence in the extraction)
}

Be precise and extract only what you can clearly identify. Set confidence_score based on how clear and complete the extracted data is."""
    
    async def _extract_with_llm(self, text: str, document_id: str) -> Dict[str, Any]:
        """Extract invoice data using LLM"""
        if not self.llm_adapter:
            return {
                'success': False,
                'document_id': document_id,
                'error': 'No LLM adapter configured',
                'status': InvoiceStatus.ERROR.value
            }
        
        try:
            # Build prompt
            user_prompt = self._prompt_template.replace('{{ content }}', text[:10000])  # Limit text length
            
            # Call LLM
            messages = [
                {'role': 'system', 'content': self._system_prompt},
                {'role': 'user', 'content': user_prompt}
            ]
            
            response = await self.llm_adapter.generate(
                messages,
                temperature=self.processing_config.llm_temperature,
                max_tokens=self.processing_config.max_tokens
            )
            
            # Parse JSON response
            raw_json = self._parse_llm_response(response)
            
            if raw_json is None:
                return {
                    'success': False,
                    'document_id': document_id,
                    'error': 'Failed to parse LLM response as JSON',
                    'raw_text': text[:1000],
                    'llm_response': response[:1000] if response else None,
                    'status': InvoiceStatus.ERROR.value
                }
            
            # Determine if needs review
            confidence = raw_json.get('confidence_score', 0)
            needs_review = confidence < self.processing_config.confidence_threshold
            
            review_reasons = []
            if needs_review:
                review_reasons.append(f"Low confidence score: {confidence:.2f}")
            
            # Check for missing required fields
            for field in self.processing_config.required_fields:
                if not raw_json.get(field):
                    needs_review = True
                    review_reasons.append(f"Missing required field: {field}")
            
            return {
                'success': True,
                'document_id': document_id,
                'raw_json': raw_json,
                'raw_text': text[:1000],  # First 1000 chars for reference
                'needs_review': needs_review,
                'review_reasons': review_reasons,
                'status': InvoiceStatus.NEEDS_REVIEW.value if needs_review else InvoiceStatus.EXTRACTED.value
            }
            
        except Exception as e:
            logger.exception(f"LLM extraction failed: {e}")
            return {
                'success': False,
                'document_id': document_id,
                'error': str(e),
                'status': InvoiceStatus.ERROR.value
            }
    
    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response to extract JSON"""
        if not response:
            return None
        
        # Try direct JSON parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code block
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object in text
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _get_model_name(self) -> str:
        """Get name of the LLM model being used"""
        if self.llm_adapter:
            if hasattr(self.llm_adapter, 'model'):
                return self.llm_adapter.model
            if hasattr(self.llm_adapter, 'model_name'):
                return self.llm_adapter.model_name
        return 'unknown'


class LineItemExtractor:
    """
    Specialized extractor for invoice line items.
    
    Uses a two-stage approach:
    1. Heuristic/regex parsing to identify candidate line rows
    2. LLM refinement for complex cases
    """
    
    def __init__(self, llm_adapter=None):
        self.llm_adapter = llm_adapter
    
    def extract_line_items(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract line items from invoice text.
        
        Args:
            text: Invoice text content
            
        Returns:
            List of line item dictionaries
        """
        # Stage 1: Heuristic extraction
        candidates = self._extract_candidates_heuristic(text)
        
        if not candidates:
            return []
        
        return candidates
    
    def _extract_candidates_heuristic(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract line item candidates using heuristics.
        
        Looks for patterns like:
        - Description followed by quantity, price, total
        - Table-like structures with columns
        """
        import re
        
        items = []
        
        # Pattern: Description, Quantity, Unit Price, Total
        # e.g., "Widget A     10    $5.00    $50.00"
        line_pattern = re.compile(
            r'^(.+?)\s+'                          # Description
            r'(\d+(?:\.\d+)?)\s+'                 # Quantity
            r'\$?([\d,]+(?:\.\d{2})?)\s+'         # Unit price
            r'\$?([\d,]+(?:\.\d{2})?)$',          # Total
            re.MULTILINE
        )
        
        for match in line_pattern.finditer(text):
            description, qty, unit_price, total = match.groups()
            
            # Clean values
            qty = float(qty)
            unit_price = float(unit_price.replace(',', ''))
            total = float(total.replace(',', ''))
            
            # Only add if total roughly equals qty * unit_price
            expected = qty * unit_price
            if abs(total - expected) < total * 0.1:  # 10% tolerance
                items.append({
                    'description': description.strip(),
                    'quantity': qty,
                    'unit_price': unit_price,
                    'total': total
                })
        
        # Alternative pattern: SKU, Description, Qty, Price, Total
        sku_pattern = re.compile(
            r'^([A-Z0-9\-]+)\s+'                   # SKU
            r'(.+?)\s+'                            # Description
            r'(\d+(?:\.\d+)?)\s+'                  # Quantity
            r'\$?([\d,]+(?:\.\d{2})?)\s+'          # Unit price
            r'\$?([\d,]+(?:\.\d{2})?)$',           # Total
            re.MULTILINE
        )
        
        for match in sku_pattern.finditer(text):
            sku, description, qty, unit_price, total = match.groups()
            
            qty = float(qty)
            unit_price = float(unit_price.replace(',', ''))
            total = float(total.replace(',', ''))
            
            expected = qty * unit_price
            if abs(total - expected) < total * 0.1:
                items.append({
                    'sku': sku.strip(),
                    'description': description.strip(),
                    'quantity': qty,
                    'unit_price': unit_price,
                    'total': total
                })
        
        return items
    
    async def refine_with_llm(self, text: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Refine line item extraction using LLM.
        
        Args:
            text: Original text
            candidates: Heuristically extracted candidates
            
        Returns:
            Refined list of line items
        """
        if not self.llm_adapter:
            return candidates
        
        # Only use LLM if heuristics found few items or text seems complex
        if len(candidates) > 3:
            return candidates
        
        try:
            prompt = f"""Given this invoice text, extract all line items as a JSON array.
Each item should have: description, quantity, unit_price, total, and optionally sku.

Text:
{text[:5000]}

Return only a JSON array of line items, nothing else."""
            
            response = await self.llm_adapter.generate([
                {'role': 'user', 'content': prompt}
            ])
            
            # Parse response
            import json
            items = json.loads(response)
            if isinstance(items, list):
                return items
                
        except Exception as e:
            logger.warning(f"LLM line item refinement failed: {e}")
        
        return candidates

