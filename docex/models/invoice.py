"""
Invoice Data Models with Pydantic Validation

Provides strict schema validation and normalization for invoice extraction.
Designed for processing invoices at scale with confidence scoring and exception routing.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import re

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class InvoiceStatus(str, Enum):
    """Invoice processing status"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    VALIDATED = "VALIDATED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ERROR = "ERROR"


class Currency(str, Enum):
    """Supported currencies"""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CAD = "CAD"
    AUD = "AUD"
    JPY = "JPY"
    CHF = "CHF"
    CNY = "CNY"
    INR = "INR"
    MXN = "MXN"
    BRL = "BRL"
    OTHER = "OTHER"


class ValidationError(BaseModel):
    """Represents a validation error"""
    field: str
    message: str
    severity: str = "error"  # error, warning, info
    code: Optional[str] = None


class LineItem(BaseModel):
    """Invoice line item with validation"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    description: str = Field(..., min_length=1, max_length=500)
    quantity: Decimal = Field(..., ge=0)
    unit_price: Decimal = Field(..., ge=0)
    total: Decimal = Field(..., ge=0)
    
    # Optional fields
    sku: Optional[str] = Field(None, max_length=100)
    unit_of_measure: Optional[str] = Field(None, max_length=50)
    tax_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    tax_amount: Optional[Decimal] = Field(None, ge=0)
    discount: Optional[Decimal] = Field(None, ge=0)
    
    @field_validator('quantity', 'unit_price', 'total', 'tax_rate', 'tax_amount', 'discount', mode='before')
    @classmethod
    def parse_decimal(cls, v: Any) -> Optional[Decimal]:
        """Parse decimal values from various formats"""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return v
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        if isinstance(v, str):
            # Remove currency symbols, commas, spaces
            cleaned = re.sub(r'[^\d.\-]', '', v.strip())
            if cleaned:
                try:
                    return Decimal(cleaned)
                except InvalidOperation:
                    return Decimal('0')
            return Decimal('0')
        return Decimal('0')
    
    @model_validator(mode='after')
    def validate_line_total(self) -> 'LineItem':
        """Validate that total equals quantity * unit_price (within tolerance)"""
        expected = self.quantity * self.unit_price
        if self.discount:
            expected -= self.discount
        if self.tax_amount:
            expected += self.tax_amount
        
        tolerance = Decimal('0.01')
        if abs(self.total - expected) > tolerance:
            # Auto-correct if within reasonable range (5%)
            if abs(self.total - expected) / max(expected, Decimal('1')) < Decimal('0.05'):
                self.total = expected
        
        return self


class Address(BaseModel):
    """Normalized address"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    line1: Optional[str] = Field(None, max_length=255)
    line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    
    @field_validator('postal_code', mode='before')
    @classmethod
    def normalize_postal_code(cls, v: Optional[str]) -> Optional[str]:
        """Normalize postal code format"""
        if not v:
            return None
        # Remove extra spaces, keep alphanumeric and dashes
        return re.sub(r'[^A-Za-z0-9\-\s]', '', v.strip()).upper()
    
    @field_validator('country', mode='before')
    @classmethod
    def normalize_country(cls, v: Optional[str]) -> Optional[str]:
        """Normalize country names"""
        if not v:
            return None
        
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
        
        upper = v.strip().upper()
        return country_map.get(upper, v.strip().title())


class Party(BaseModel):
    """Invoice party (supplier or customer)"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: Optional[str] = Field(None, max_length=255)
    id: Optional[str] = Field(None, max_length=100)
    tax_id: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[Address] = None
    
    # For entity matching/deduplication
    normalized_key: Optional[str] = None
    
    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        """Normalize email to lowercase"""
        if not v:
            return None
        return v.strip().lower()
    
    @field_validator('tax_id', mode='before')
    @classmethod
    def normalize_tax_id(cls, v: Optional[str]) -> Optional[str]:
        """Normalize tax ID (remove non-alphanumeric)"""
        if not v:
            return None
        return re.sub(r'[^A-Za-z0-9]', '', v.strip()).upper()
    
    @model_validator(mode='after')
    def generate_normalized_key(self) -> 'Party':
        """Generate a normalized key for entity matching"""
        parts = []
        if self.tax_id:
            parts.append(f"tax:{self.tax_id}")
        if self.email:
            parts.append(f"email:{self.email}")
        if self.name:
            # Normalize name for matching
            normalized_name = re.sub(r'[^a-z0-9]', '', self.name.lower())
            parts.append(f"name:{normalized_name}")
        
        if parts:
            self.normalized_key = "|".join(sorted(parts))
        
        return self


class InvoiceData(BaseModel):
    """
    Complete invoice data model with strict validation.
    
    This is the target schema for invoice extraction. All invoices
    are normalized to this structure for downstream processing.
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Core identifiers
    invoice_number: str = Field(..., min_length=1, max_length=100)
    purchase_order_number: Optional[str] = Field(None, max_length=100)
    
    # Parties
    supplier: Optional[Party] = None
    customer: Optional[Party] = None
    
    # Legacy fields for backward compatibility
    supplier_id: Optional[str] = Field(None, max_length=100)
    customer_id: Optional[str] = Field(None, max_length=100)
    
    # Dates
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    payment_terms: Optional[str] = Field(None, max_length=100)
    
    # Amounts
    subtotal: Optional[Decimal] = Field(None, ge=0)
    tax_amount: Optional[Decimal] = Field(None, ge=0)
    discount_amount: Optional[Decimal] = Field(None, ge=0)
    shipping_amount: Optional[Decimal] = Field(None, ge=0)
    total_amount: Decimal = Field(..., ge=0)
    currency: Currency = Currency.USD
    
    # Line items
    line_items: List[LineItem] = Field(default_factory=list)
    
    # Extraction metadata
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    extraction_warnings: List[str] = Field(default_factory=list)
    
    @field_validator('invoice_date', 'due_date', mode='before')
    @classmethod
    def parse_date(cls, v: Any) -> Optional[date]:
        """Parse dates from various formats"""
        if v is None:
            return None
        if isinstance(v, date):
            return v
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, str):
            v = v.strip()
            if not v:
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
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(v, fmt).date()
                except ValueError:
                    continue
            
            return None
        return None
    
    @field_validator('total_amount', 'subtotal', 'tax_amount', 'discount_amount', 'shipping_amount', mode='before')
    @classmethod
    def parse_amount(cls, v: Any) -> Optional[Decimal]:
        """Parse monetary amounts from various formats"""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return v
        if isinstance(v, (int, float)):
            return Decimal(str(v)).quantize(Decimal('0.01'))
        if isinstance(v, str):
            # Remove currency symbols, commas, spaces
            cleaned = re.sub(r'[^\d.\-]', '', v.strip())
            if cleaned:
                try:
                    return Decimal(cleaned).quantize(Decimal('0.01'))
                except InvalidOperation:
                    return Decimal('0.00')
            return Decimal('0.00')
        return Decimal('0.00')
    
    @field_validator('currency', mode='before')
    @classmethod
    def parse_currency(cls, v: Any) -> Currency:
        """Parse currency from various formats"""
        if isinstance(v, Currency):
            return v
        if isinstance(v, str):
            v = v.strip().upper()
            # Handle common symbols
            symbol_map = {
                '$': 'USD',
                '€': 'EUR',
                '£': 'GBP',
                '¥': 'JPY',
            }
            v = symbol_map.get(v, v)
            
            try:
                return Currency(v)
            except ValueError:
                return Currency.OTHER
        return Currency.USD
    
    @model_validator(mode='after')
    def validate_invoice(self) -> 'InvoiceData':
        """Cross-field validation"""
        warnings = list(self.extraction_warnings)
        
        # Validate line items total matches invoice total
        if self.line_items:
            line_total = sum(item.total for item in self.line_items)
            expected = line_total
            if self.tax_amount:
                expected += self.tax_amount
            if self.shipping_amount:
                expected += self.shipping_amount
            if self.discount_amount:
                expected -= self.discount_amount
            
            tolerance = Decimal('0.02')
            if abs(self.total_amount - expected) > tolerance:
                warnings.append(
                    f"Line items total ({expected}) doesn't match invoice total ({self.total_amount})"
                )
        
        # Validate due date is after invoice date
        if self.invoice_date and self.due_date:
            if self.due_date < self.invoice_date:
                warnings.append(
                    f"Due date ({self.due_date}) is before invoice date ({self.invoice_date})"
                )
        
        # Check for missing critical fields
        if not self.supplier and not self.supplier_id:
            warnings.append("Missing supplier information")
        
        if not self.customer and not self.customer_id:
            warnings.append("Missing customer information")
        
        if not self.invoice_date:
            warnings.append("Missing invoice date")
        
        self.extraction_warnings = warnings
        return self
    
    def needs_review(self, confidence_threshold: float = 0.8) -> bool:
        """Check if invoice needs human review"""
        # Low confidence
        if self.confidence_score < confidence_threshold:
            return True
        
        # Has validation warnings
        if self.extraction_warnings:
            return True
        
        # Missing critical fields
        if not self.invoice_number:
            return True
        if self.total_amount == Decimal('0'):
            return True
        
        return False
    
    def get_validation_errors(self) -> List[ValidationError]:
        """Get list of validation errors"""
        errors = []
        
        for warning in self.extraction_warnings:
            errors.append(ValidationError(
                field="invoice",
                message=warning,
                severity="warning"
            ))
        
        if self.confidence_score < 0.5:
            errors.append(ValidationError(
                field="confidence_score",
                message=f"Very low confidence score: {self.confidence_score:.2f}",
                severity="error",
                code="LOW_CONFIDENCE"
            ))
        elif self.confidence_score < 0.8:
            errors.append(ValidationError(
                field="confidence_score",
                message=f"Low confidence score: {self.confidence_score:.2f}",
                severity="warning",
                code="MEDIUM_CONFIDENCE"
            ))
        
        return errors


class InvoiceExtractionResult(BaseModel):
    """Result of invoice extraction operation"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Document reference
    document_id: str
    operation_id: Optional[str] = None
    
    # Extraction result
    success: bool
    invoice: Optional[InvoiceData] = None
    
    # Status and routing
    status: InvoiceStatus = InvoiceStatus.PENDING
    needs_review: bool = False
    review_reasons: List[str] = Field(default_factory=list)
    
    # Validation
    validation_errors: List[ValidationError] = Field(default_factory=list)
    
    # Raw data for debugging
    raw_text: Optional[str] = None
    raw_json: Optional[Dict[str, Any]] = None
    
    # Error information
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    # Timing
    extraction_time_ms: Optional[int] = None
    
    def set_needs_review(self, reasons: List[str]) -> None:
        """Mark for human review"""
        self.needs_review = True
        self.review_reasons = reasons
        self.status = InvoiceStatus.NEEDS_REVIEW


class InvoiceProcessingConfig(BaseModel):
    """Configuration for invoice processing"""
    
    # Confidence thresholds
    confidence_threshold: float = Field(0.8, ge=0.0, le=1.0)
    auto_approve_threshold: float = Field(0.95, ge=0.0, le=1.0)
    
    # Required fields for auto-approval
    required_fields: List[str] = Field(default_factory=lambda: [
        'invoice_number', 'total_amount', 'invoice_date'
    ])
    
    # Processing options
    enable_ocr: bool = True
    enable_line_item_extraction: bool = True
    enable_vendor_normalization: bool = True
    
    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: int = 5
    
    # LLM settings
    llm_model: Optional[str] = None
    llm_temperature: float = 0.0
    max_tokens: int = 4000

