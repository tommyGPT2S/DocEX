"""
Data models for the PDF intake.

These models carry an invoice from raw extraction through reconciliation. They
deliberately separate *what* was extracted from *how confident* the intake is
and *which tier* produced it, so the pipeline can escalate only the fields that
need it and the caller can see exactly how much each result cost.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from docex.intake.charges import ChargeType


class ExtractionTier(str, Enum):
    """The extraction strategy that produced a value, cheapest to most costly."""

    NONE = "none"
    HEURISTIC = "heuristic"
    LLM = "llm"


class ExtractedField(BaseModel):
    """A single extracted value with its provenance.

    ``value`` is already normalized to its target type (``Decimal`` for money,
    ``date`` for dates, ``str`` otherwise), so downstream layers never re-parse.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    value: Optional[Any]
    confidence: float = Field(ge=0.0, le=1.0)
    tier: ExtractionTier
    raw_text: Optional[str] = None
    label: Optional[str] = None  # the label phrase on the page that identified this value


class LineItem(BaseModel):
    """One charge line on a CRE invoice."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    description: Optional[str] = None
    charge_type: ChargeType = ChargeType.OTHER
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    amount: Optional[Decimal] = None
    confidence: float = 1.0


class ExtractedInvoice(BaseModel):
    """The result of extracting one invoice, with per-field provenance.

    Scalar fields live in ``fields`` keyed by canonical name (see
    :data:`docex.intake.fields.FIELDS`); charge detail lives in ``line_items``.
    """

    fields: Dict[str, ExtractedField] = Field(default_factory=dict)
    line_items: List[LineItem] = Field(default_factory=list)

    def value(self, name: str) -> Optional[Any]:
        """Return the normalized value for a field, or ``None`` if unextracted."""
        field = self.fields.get(name)
        return field.value if field else None

    def confidence(self, name: str) -> float:
        """Return the extraction confidence for a field (0.0 if unextracted)."""
        field = self.fields.get(name)
        return field.confidence if field else 0.0

    def tier(self, name: str) -> ExtractionTier:
        """Return the tier that produced a field (NONE if unextracted)."""
        field = self.fields.get(name)
        return field.tier if field else ExtractionTier.NONE

    def has(self, name: str) -> bool:
        """Whether a field was extracted with a non-null value."""
        field = self.fields.get(name)
        return field is not None and field.value is not None

    def put(self, field: ExtractedField) -> None:
        """Insert or replace a field by name."""
        self.fields[field.name] = field

    def tiers_used(self) -> set[ExtractionTier]:
        """Set of tiers that contributed at least one field."""
        return {field.tier for field in self.fields.values() if field.tier != ExtractionTier.NONE}


class MatchStatus(str, Enum):
    """Outcome of comparing one extracted field against ground truth."""

    MATCH = "match"
    MISMATCH = "mismatch"
    MISSING = "missing"  # ground truth had a value, extraction did not


class FieldComparison(BaseModel):
    """The reconciliation verdict for a single field."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    field: str
    expected: Optional[Any]
    actual: Optional[Any]
    status: MatchStatus
    confidence: float = 0.0
    tier: ExtractionTier = ExtractionTier.NONE
    note: Optional[str] = None


class LineItemComparison(BaseModel):
    """The reconciliation verdict for one charge type across the invoice."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    charge_type: ChargeType
    expected: Optional[Decimal]
    actual: Optional[Decimal]
    status: MatchStatus
    note: Optional[str] = None


class ReconciliationStatus(str, Enum):
    """Overall verdict for an invoice against its ground-truth record."""

    MATCHED = "matched"  # every compared field agrees
    DISCREPANCY = "discrepancy"  # at least one field disagrees
    INCOMPLETE = "incomplete"  # fields missing but nothing disagrees
    UNRESOLVED = "unresolved"  # no ground-truth record could be matched


class ReconciliationResult(BaseModel):
    """The full comparison of an extracted invoice against ground truth."""

    status: ReconciliationStatus
    ground_truth_id: Optional[str] = None
    field_comparisons: List[FieldComparison] = Field(default_factory=list)
    line_item_comparisons: List[LineItemComparison] = Field(default_factory=list)
    tiers_used: List[ExtractionTier] = Field(default_factory=list)

    def by_status(self, status: MatchStatus) -> List[FieldComparison]:
        """All field comparisons with the given status."""
        return [c for c in self.field_comparisons if c.status == status]

    @property
    def mismatches(self) -> List[FieldComparison]:
        """Field comparisons where extracted and expected values disagree."""
        return self.by_status(MatchStatus.MISMATCH)

    @property
    def missing(self) -> List[FieldComparison]:
        """Field comparisons where extraction failed to find an expected value."""
        return self.by_status(MatchStatus.MISSING)

    @property
    def is_clean(self) -> bool:
        """True when the invoice fully reconciles with no discrepancies."""
        return self.status == ReconciliationStatus.MATCHED
