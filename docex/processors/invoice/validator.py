"""
Invoice Validator

Validates extracted invoice data against schema and business rules.
Flags issues for human review rather than silently failing.
"""

import logging
from typing import Any, Dict, List, Optional
from decimal import Decimal

from pydantic import ValidationError as PydanticValidationError

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document
from docex.models.invoice import (
    InvoiceData,
    InvoiceExtractionResult,
    InvoiceStatus,
    ValidationError,
    LineItem
)

logger = logging.getLogger(__name__)


class InvoiceValidator(BaseProcessor):
    """
    Validates invoice data against schema and business rules.
    
    Features:
    - Strict JSON schema validation via Pydantic
    - Business rule validation (totals match, dates logical, etc.)
    - Configurable required fields
    - Detailed error reporting for human review
    """
    
    def __init__(self, config: Dict[str, Any] = None, db=None):
        super().__init__(config or {}, db)
        
        # Validation configuration
        self.required_fields = config.get('required_fields', [
            'invoice_number', 'total_amount'
        ])
        self.confidence_threshold = config.get('confidence_threshold', 0.8)
        self.strict_line_items = config.get('strict_line_items', True)
        self.tolerance_percentage = config.get('tolerance_percentage', 0.01)  # 1%
    
    def can_process(self, document: Document) -> bool:
        """Can process documents with extracted invoice data"""
        metadata = document.get_metadata_dict() if hasattr(document, 'get_metadata_dict') else {}
        return metadata.get('doc_type') == 'invoice' or metadata.get('has_invoice_data', False)
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Validate invoice data from document.
        
        Args:
            document: Document with extracted invoice data in content
            
        Returns:
            ProcessingResult with validated InvoiceExtractionResult
        """
        try:
            # Get raw extraction data
            raw_data = self._get_invoice_data(document)
            
            if not raw_data:
                return ProcessingResult(
                    success=False,
                    error="No invoice data found in document"
                )
            
            # Validate against schema
            validation_errors = []
            invoice = None
            
            try:
                invoice = InvoiceData(**raw_data)
            except PydanticValidationError as e:
                for error in e.errors():
                    validation_errors.append(ValidationError(
                        field='.'.join(str(loc) for loc in error['loc']),
                        message=error['msg'],
                        severity='error',
                        code=error['type']
                    ))
            
            # If schema validation passed, run business rules
            if invoice:
                business_errors = self._validate_business_rules(invoice)
                validation_errors.extend(business_errors)
            
            # Check required fields
            missing_fields = self._check_required_fields(raw_data)
            for field in missing_fields:
                validation_errors.append(ValidationError(
                    field=field,
                    message=f"Required field '{field}' is missing",
                    severity='error',
                    code='MISSING_REQUIRED_FIELD'
                ))
            
            # Determine status
            has_errors = any(e.severity == 'error' for e in validation_errors)
            has_warnings = any(e.severity == 'warning' for e in validation_errors)
            
            if has_errors:
                status = InvoiceStatus.NEEDS_REVIEW
            elif has_warnings:
                status = InvoiceStatus.VALIDATED
            else:
                status = InvoiceStatus.VALIDATED
            
            # Build result
            result = InvoiceExtractionResult(
                document_id=document.id,
                success=not has_errors,
                invoice=invoice,
                status=status,
                needs_review=has_errors or (invoice and invoice.needs_review(self.confidence_threshold)),
                review_reasons=self._get_review_reasons(validation_errors, invoice),
                validation_errors=validation_errors,
                raw_json=raw_data
            )
            
            return ProcessingResult(
                success=True,
                content=result.model_dump(),
                metadata={
                    'validation_status': status.value,
                    'error_count': len([e for e in validation_errors if e.severity == 'error']),
                    'warning_count': len([e for e in validation_errors if e.severity == 'warning']),
                    'needs_review': result.needs_review
                }
            )
            
        except Exception as e:
            logger.exception(f"Invoice validation failed: {e}")
            return ProcessingResult(
                success=False,
                error=str(e)
            )
    
    def _get_invoice_data(self, document: Document) -> Optional[Dict[str, Any]]:
        """Extract invoice data from document"""
        # Try document content first
        if hasattr(document, 'content') and document.content:
            if isinstance(document.content, dict):
                if 'invoice_data' in document.content:
                    return document.content['invoice_data']
                # Check if content itself is invoice data
                if 'invoice_number' in document.content:
                    return document.content
        
        # Try metadata
        metadata = document.get_metadata_dict() if hasattr(document, 'get_metadata_dict') else {}
        if 'extracted_invoice' in metadata:
            return metadata['extracted_invoice']
        
        return None
    
    def _validate_business_rules(self, invoice: InvoiceData) -> List[ValidationError]:
        """Validate business rules beyond schema"""
        errors = []
        
        # Rule 1: Line items total should match subtotal
        if invoice.line_items and invoice.subtotal:
            line_total = sum(item.total for item in invoice.line_items)
            tolerance = invoice.subtotal * Decimal(str(self.tolerance_percentage))
            
            if abs(line_total - invoice.subtotal) > tolerance:
                errors.append(ValidationError(
                    field='line_items',
                    message=f"Line items total ({line_total}) differs from subtotal ({invoice.subtotal})",
                    severity='warning',
                    code='LINE_ITEMS_MISMATCH'
                ))
        
        # Rule 2: Tax calculation sanity check
        if invoice.subtotal and invoice.tax_amount:
            tax_rate = invoice.tax_amount / invoice.subtotal
            if tax_rate > Decimal('0.30'):  # 30% tax rate seems high
                errors.append(ValidationError(
                    field='tax_amount',
                    message=f"Tax rate ({tax_rate:.1%}) seems unusually high",
                    severity='warning',
                    code='HIGH_TAX_RATE'
                ))
        
        # Rule 3: Total calculation
        if invoice.subtotal:
            expected_total = invoice.subtotal
            if invoice.tax_amount:
                expected_total += invoice.tax_amount
            if invoice.shipping_amount:
                expected_total += invoice.shipping_amount
            if invoice.discount_amount:
                expected_total -= invoice.discount_amount
            
            tolerance = invoice.total_amount * Decimal(str(self.tolerance_percentage))
            if abs(expected_total - invoice.total_amount) > tolerance:
                errors.append(ValidationError(
                    field='total_amount',
                    message=f"Calculated total ({expected_total}) differs from stated total ({invoice.total_amount})",
                    severity='warning',
                    code='TOTAL_MISMATCH'
                ))
        
        # Rule 4: Line item individual validation
        if self.strict_line_items:
            for i, item in enumerate(invoice.line_items):
                expected = item.quantity * item.unit_price
                tolerance = expected * Decimal(str(self.tolerance_percentage))
                
                if abs(item.total - expected) > tolerance:
                    errors.append(ValidationError(
                        field=f'line_items[{i}].total',
                        message=f"Line item total ({item.total}) differs from qty*price ({expected})",
                        severity='warning',
                        code='LINE_ITEM_TOTAL_MISMATCH'
                    ))
        
        # Rule 5: Invoice number format (should not be empty or just whitespace)
        if invoice.invoice_number and not invoice.invoice_number.strip():
            errors.append(ValidationError(
                field='invoice_number',
                message="Invoice number is empty or whitespace",
                severity='error',
                code='EMPTY_INVOICE_NUMBER'
            ))
        
        # Rule 6: Future invoice date check
        if invoice.invoice_date:
            from datetime import date
            if invoice.invoice_date > date.today():
                errors.append(ValidationError(
                    field='invoice_date',
                    message=f"Invoice date ({invoice.invoice_date}) is in the future",
                    severity='warning',
                    code='FUTURE_INVOICE_DATE'
                ))
        
        # Rule 7: Very old invoice check (more than 2 years)
        if invoice.invoice_date:
            from datetime import date, timedelta
            two_years_ago = date.today() - timedelta(days=730)
            if invoice.invoice_date < two_years_ago:
                errors.append(ValidationError(
                    field='invoice_date',
                    message=f"Invoice date ({invoice.invoice_date}) is more than 2 years old",
                    severity='warning',
                    code='OLD_INVOICE_DATE'
                ))
        
        return errors
    
    def _check_required_fields(self, data: Dict[str, Any]) -> List[str]:
        """Check for missing required fields"""
        missing = []
        for field in self.required_fields:
            value = data.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(field)
        return missing
    
    def _get_review_reasons(
        self,
        errors: List[ValidationError],
        invoice: Optional[InvoiceData]
    ) -> List[str]:
        """Generate human-readable review reasons"""
        reasons = []
        
        # From validation errors
        error_fields = set()
        for error in errors:
            if error.severity == 'error':
                error_fields.add(error.field)
        
        if error_fields:
            reasons.append(f"Validation errors in fields: {', '.join(error_fields)}")
        
        # From invoice confidence
        if invoice and invoice.confidence_score < self.confidence_threshold:
            reasons.append(f"Low extraction confidence: {invoice.confidence_score:.1%}")
        
        # From invoice warnings
        if invoice and invoice.extraction_warnings:
            reasons.extend(invoice.extraction_warnings)
        
        return reasons


def validate_invoice_json(data: Dict[str, Any]) -> tuple[Optional[InvoiceData], List[ValidationError]]:
    """
    Standalone function to validate invoice JSON data.
    
    Args:
        data: Raw invoice data dictionary
        
    Returns:
        Tuple of (InvoiceData or None, list of validation errors)
    """
    errors = []
    invoice = None
    
    try:
        invoice = InvoiceData(**data)
    except PydanticValidationError as e:
        for error in e.errors():
            errors.append(ValidationError(
                field='.'.join(str(loc) for loc in error['loc']),
                message=error['msg'],
                severity='error',
                code=error['type']
            ))
    
    return invoice, errors

