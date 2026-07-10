"""
Invoice Normalizer

Normalizes extracted invoice data to a consistent format.
Handles:
- Date format standardization
- Currency normalization
- Decimal precision
- Address parsing
- Tax calculations
- Vendor/customer deduplication keys
"""

import logging
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document
from docex.models.invoice import (
    InvoiceData,
    LineItem,
    Party,
    Address,
    Currency,
    ValidationError
)

logger = logging.getLogger(__name__)


class InvoiceNormalizer(BaseProcessor):
    """
    Normalizes raw extracted invoice data to a consistent format.
    
    Features:
    - Date format standardization (ISO 8601)
    - Currency detection and normalization
    - Decimal precision (2 decimal places for amounts)
    - Address parsing and standardization
    - Tax recalculation if missing
    - Vendor/customer normalized keys for deduplication
    """
    
    def __init__(self, config: Dict[str, Any] = None, db=None):
        super().__init__(config or {}, db)
        
        # Configuration
        self.decimal_places = config.get('decimal_places', 2) if config else 2
        self.default_currency = Currency(config.get('default_currency', 'USD')) if config else Currency.USD
        self.auto_calculate_tax = config.get('auto_calculate_tax', True) if config else True
        self.tax_rate = Decimal(str(config.get('default_tax_rate', '0.0'))) if config else Decimal('0.0')
    
    def can_process(self, document: Document) -> bool:
        """Can process documents with raw invoice extraction data"""
        metadata = document.get_metadata_dict() if hasattr(document, 'get_metadata_dict') else {}
        return metadata.get('doc_type') == 'invoice' or metadata.get('has_raw_invoice', False)
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Normalize raw invoice data from document.
        
        Args:
            document: Document with raw extracted invoice data
            
        Returns:
            ProcessingResult with normalized invoice data
        """
        try:
            # Get raw extraction data
            raw_data = self._get_raw_data(document)
            
            if not raw_data:
                return ProcessingResult(
                    success=False,
                    error="No raw invoice data found in document"
                )
            
            # Normalize the data
            normalized = self._normalize_invoice_data(raw_data)
            
            # Track normalization changes
            changes = self._track_changes(raw_data, normalized)
            
            return ProcessingResult(
                success=True,
                content=normalized,
                metadata={
                    'normalization_applied': True,
                    'changes_made': len(changes),
                    'change_details': changes
                }
            )
            
        except Exception as e:
            logger.exception(f"Invoice normalization failed: {e}")
            return ProcessingResult(
                success=False,
                error=str(e)
            )
    
    def _get_raw_data(self, document: Document) -> Optional[Dict[str, Any]]:
        """Extract raw invoice data from document"""
        if hasattr(document, 'content') and document.content:
            if isinstance(document.content, dict):
                return document.content
        
        metadata = document.get_metadata_dict() if hasattr(document, 'get_metadata_dict') else {}
        if 'raw_invoice' in metadata:
            return metadata['raw_invoice']
        if 'extracted_data' in metadata:
            return metadata['extracted_data']
        
        return None
    
    def _normalize_invoice_data(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Apply all normalizations to raw data"""
        normalized = dict(raw)
        
        # Normalize dates
        for date_field in ['invoice_date', 'due_date']:
            if date_field in normalized:
                normalized[date_field] = self._normalize_date(normalized[date_field])
        
        # Normalize currency
        if 'currency' in normalized:
            normalized['currency'] = self._normalize_currency(normalized.get('currency'))
        else:
            normalized['currency'] = self.default_currency.value
        
        # Normalize amounts
        for amount_field in ['total_amount', 'subtotal', 'tax_amount', 'discount_amount', 'shipping_amount']:
            if amount_field in normalized and normalized[amount_field] is not None:
                normalized[amount_field] = self._normalize_amount(normalized[amount_field])
        
        # Normalize line items
        if 'line_items' in normalized and normalized['line_items']:
            normalized['line_items'] = [
                self._normalize_line_item(item) 
                for item in normalized['line_items']
            ]
        
        # Calculate missing subtotal from line items
        if 'line_items' in normalized and normalized['line_items']:
            if not normalized.get('subtotal'):
                normalized['subtotal'] = sum(
                    Decimal(str(item.get('total', 0))) 
                    for item in normalized['line_items']
                )
                normalized['subtotal'] = self._normalize_amount(normalized['subtotal'])
        
        # Auto-calculate tax if missing and enabled
        if self.auto_calculate_tax and self.tax_rate > 0:
            if not normalized.get('tax_amount') and normalized.get('subtotal'):
                subtotal = Decimal(str(normalized['subtotal']))
                normalized['tax_amount'] = self._normalize_amount(subtotal * self.tax_rate)
        
        # Calculate total if missing
        if not normalized.get('total_amount'):
            normalized['total_amount'] = self._calculate_total(normalized)
        
        # Normalize supplier/customer
        if 'supplier' in normalized:
            normalized['supplier'] = self._normalize_party(normalized['supplier'])
        if 'customer' in normalized:
            normalized['customer'] = self._normalize_party(normalized['customer'])
        
        # Normalize string fields
        for field in ['invoice_number', 'purchase_order_number', 'payment_terms']:
            if field in normalized and normalized[field]:
                normalized[field] = str(normalized[field]).strip()
        
        # Ensure confidence score
        if 'confidence_score' not in normalized:
            normalized['confidence_score'] = 0.5  # Default confidence
        
        return normalized
    
    def _normalize_date(self, value: Any) -> Optional[str]:
        """Normalize date to ISO format (YYYY-MM-DD)"""
        if value is None:
            return None
        
        if isinstance(value, date):
            return value.isoformat()
        
        if isinstance(value, datetime):
            return value.date().isoformat()
        
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            
            # Try common date formats
            formats = [
                '%Y-%m-%d',      # ISO format
                '%m/%d/%Y',      # US format
                '%d/%m/%Y',      # EU format
                '%m-%d-%Y',
                '%d-%m-%Y',
                '%Y/%m/%d',
                '%B %d, %Y',     # January 15, 2024
                '%b %d, %Y',     # Jan 15, 2024
                '%d %B %Y',      # 15 January 2024
                '%d %b %Y',      # 15 Jan 2024
                '%m/%d/%y',      # MM/DD/YY
                '%d/%m/%y',      # DD/MM/YY
            ]
            
            for fmt in formats:
                try:
                    parsed = datetime.strptime(value, fmt).date()
                    return parsed.isoformat()
                except ValueError:
                    continue
            
            # Return original if unparseable
            return value
        
        return None
    
    def _normalize_currency(self, value: Any) -> str:
        """Normalize currency code"""
        if value is None:
            return self.default_currency.value
        
        if isinstance(value, Currency):
            return value.value
        
        if isinstance(value, str):
            value = value.strip().upper()
            
            # Symbol mapping
            symbol_map = {
                '$': 'USD',
                '€': 'EUR',
                '£': 'GBP',
                '¥': 'JPY',
                'C$': 'CAD',
                'A$': 'AUD',
                '₹': 'INR',
            }
            value = symbol_map.get(value, value)
            
            try:
                return Currency(value).value
            except ValueError:
                return Currency.OTHER.value
        
        return self.default_currency.value
    
    def _normalize_amount(self, value: Any) -> float:
        """Normalize monetary amount to float with fixed precision"""
        if value is None:
            return 0.0
        
        try:
            if isinstance(value, Decimal):
                decimal_val = value
            elif isinstance(value, (int, float)):
                decimal_val = Decimal(str(value))
            elif isinstance(value, str):
                # Remove currency symbols, commas, spaces
                cleaned = re.sub(r'[^\d.\-]', '', value.strip())
                if cleaned:
                    decimal_val = Decimal(cleaned)
                else:
                    return 0.0
            else:
                return 0.0
            
            # Round to specified decimal places
            quantize_str = '0.' + '0' * self.decimal_places
            rounded = decimal_val.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)
            return float(rounded)
            
        except (InvalidOperation, ValueError):
            return 0.0
    
    def _normalize_line_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a line item"""
        normalized = dict(item)
        
        # Normalize amounts
        for field in ['quantity', 'unit_price', 'total', 'tax_rate', 'tax_amount', 'discount']:
            if field in normalized and normalized[field] is not None:
                normalized[field] = self._normalize_amount(normalized[field])
        
        # Clean description
        if 'description' in normalized and normalized['description']:
            normalized['description'] = str(normalized['description']).strip()
        
        # Recalculate total if quantity and unit_price present
        if normalized.get('quantity') and normalized.get('unit_price'):
            expected = normalized['quantity'] * normalized['unit_price']
            if normalized.get('discount'):
                expected -= normalized['discount']
            if normalized.get('tax_amount'):
                expected += normalized['tax_amount']
            
            # Update total if significantly different or missing
            if not normalized.get('total') or abs(normalized['total'] - expected) > 0.01:
                normalized['total'] = self._normalize_amount(expected)
        
        return normalized
    
    def _normalize_party(self, party: Any) -> Dict[str, Any]:
        """Normalize party (supplier/customer) data"""
        if party is None:
            return None
        
        if isinstance(party, str):
            return {'name': party.strip()}
        
        if not isinstance(party, dict):
            return None
        
        normalized = {}
        
        # Name
        if party.get('name'):
            normalized['name'] = str(party['name']).strip()
        
        # ID fields
        for field in ['id', 'tax_id']:
            if party.get(field):
                # Remove non-alphanumeric for tax_id
                val = str(party[field]).strip()
                if field == 'tax_id':
                    val = re.sub(r'[^A-Za-z0-9]', '', val).upper()
                normalized[field] = val
        
        # Email (lowercase)
        if party.get('email'):
            normalized['email'] = str(party['email']).strip().lower()
        
        # Phone
        if party.get('phone'):
            normalized['phone'] = str(party['phone']).strip()
        
        # Address
        if party.get('address'):
            normalized['address'] = self._normalize_address(party['address'])
        
        # Generate normalized key for deduplication
        normalized['normalized_key'] = self._generate_party_key(normalized)
        
        return normalized
    
    def _normalize_address(self, address: Any) -> Dict[str, Any]:
        """Normalize address data"""
        if address is None:
            return None
        
        if isinstance(address, str):
            return {'line1': address.strip()}
        
        if not isinstance(address, dict):
            return None
        
        normalized = {}
        
        for field in ['line1', 'line2', 'city', 'state', 'postal_code', 'country']:
            if address.get(field):
                val = str(address[field]).strip()
                
                if field == 'postal_code':
                    # Clean postal code
                    val = re.sub(r'[^A-Za-z0-9\-\s]', '', val).upper()
                elif field == 'country':
                    # Normalize country
                    val = self._normalize_country(val)
                elif field == 'state':
                    val = val.upper() if len(val) <= 2 else val.title()
                
                normalized[field] = val
        
        return normalized
    
    def _normalize_country(self, country: str) -> str:
        """Normalize country name"""
        country_map = {
            'US': 'United States',
            'USA': 'United States',
            'U.S.A.': 'United States',
            'U.S.': 'United States',
            'UNITED STATES OF AMERICA': 'United States',
            'UK': 'United Kingdom',
            'GB': 'United Kingdom',
            'GREAT BRITAIN': 'United Kingdom',
            'CA': 'Canada',
            'CAN': 'Canada',
        }
        
        upper = country.strip().upper()
        return country_map.get(upper, country.strip().title())
    
    def _generate_party_key(self, party: Dict[str, Any]) -> str:
        """Generate normalized key for entity matching/deduplication"""
        parts = []
        
        if party.get('tax_id'):
            parts.append(f"tax:{party['tax_id']}")
        
        if party.get('email'):
            parts.append(f"email:{party['email']}")
        
        if party.get('name'):
            # Normalize name for matching
            normalized_name = re.sub(r'[^a-z0-9]', '', party['name'].lower())
            parts.append(f"name:{normalized_name}")
        
        return "|".join(sorted(parts)) if parts else None
    
    def _calculate_total(self, data: Dict[str, Any]) -> float:
        """Calculate invoice total from components"""
        total = Decimal('0')
        
        if data.get('subtotal'):
            total = Decimal(str(data['subtotal']))
        elif data.get('line_items'):
            total = sum(
                Decimal(str(item.get('total', 0))) 
                for item in data['line_items']
            )
        
        if data.get('tax_amount'):
            total += Decimal(str(data['tax_amount']))
        
        if data.get('shipping_amount'):
            total += Decimal(str(data['shipping_amount']))
        
        if data.get('discount_amount'):
            total -= Decimal(str(data['discount_amount']))
        
        return self._normalize_amount(total)
    
    def _track_changes(self, original: Dict[str, Any], normalized: Dict[str, Any]) -> List[str]:
        """Track what changed during normalization"""
        changes = []
        
        # Compare top-level fields
        for key in set(list(original.keys()) + list(normalized.keys())):
            orig_val = original.get(key)
            norm_val = normalized.get(key)
            
            if orig_val != norm_val:
                if key == 'line_items':
                    changes.append(f"Normalized {len(normalized.get('line_items', []))} line items")
                elif key in ['supplier', 'customer']:
                    if normalized.get(key, {}).get('normalized_key'):
                        changes.append(f"Generated {key} dedup key")
                elif orig_val is None and norm_val is not None:
                    changes.append(f"Calculated {key}: {norm_val}")
                elif orig_val != norm_val:
                    changes.append(f"Normalized {key}: {orig_val} -> {norm_val}")
        
        return changes


def normalize_invoice_dict(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Standalone function to normalize invoice dictionary.
    
    Args:
        data: Raw invoice data dictionary
        config: Optional normalization configuration
        
    Returns:
        Normalized invoice dictionary
    """
    normalizer = InvoiceNormalizer(config=config)
    return normalizer._normalize_invoice_data(data)

