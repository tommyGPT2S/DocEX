"""
Shared extraction primitives.

Every extractor consumes an :class:`ExtractionContext` (the page text plus the
set of fields still worth attempting) and returns the fields it could resolve.
The cascade decides which extractor runs next based on what came back, so an
extractor only needs to answer "given this text, what can I find?".

The value matchers here turn a labelled span into a typed value. They live next
to the extractors rather than in :mod:`docex.intake.normalize` because they
encode *where on a line a value sits*, which is an extraction concern, not a
parsing one.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from docex.intake.fields import FieldType
from docex.intake.models import ExtractedField, ExtractionTier, LineItem
from docex.intake.normalize import normalize_text, parse_value

_MONEY_TOKEN = re.compile(r"\(?-?\s*[$€£]?\s*\d[\d,]*(?:\.\d+)?\s*\)?-?")
_DATE_TOKEN = re.compile(
    r"\d{1,4}[/\-.]\d{1,2}[/\-.]\d{1,4}"
    r"|[A-Za-z]{3,9}\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}"
    r"|\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}\.?,?\s+\d{4}"
)
_PERCENT_TOKEN = re.compile(r"\d[\d.,]*\s*%?")
_NUMBER_TOKEN = re.compile(r"\d[\d,]*(?:\.\d+)?")

_TYPE_TOKENS = {
    FieldType.AMOUNT: _MONEY_TOKEN,
    FieldType.DATE: _DATE_TOKEN,
    FieldType.PERCENT: _PERCENT_TOKEN,
    FieldType.NUMBER: _NUMBER_TOKEN,
}


@dataclass
class ExtractionContext:
    """Everything an extractor needs to do one pass over an invoice.

    Attributes:
        raw_text: The full page text from the PDF.
        target_fields: Canonical field names still worth attempting. The cascade
            narrows this to only the unresolved or disputed fields when it
            escalates, so costly tiers never re-extract what cheap tiers nailed.
        want_line_items: Whether to parse charge lines. Set only on the first,
            full pass; escalations target individual scalar fields.
    """

    raw_text: str
    target_fields: Tuple[str, ...]
    want_line_items: bool = True
    lines: List[str] = field(init=False)

    def __post_init__(self) -> None:
        self.lines = [normalize_text(line) for line in self.raw_text.splitlines() if line.strip()]


@dataclass
class ExtractionResult:
    """What one extractor produced: resolved fields and any parsed charges."""

    fields: Dict[str, ExtractedField] = field(default_factory=dict)
    line_items: List[LineItem] = field(default_factory=list)


class FieldExtractor(ABC):
    """One strategy for turning invoice text into typed fields."""

    tier: ExtractionTier

    @abstractmethod
    async def extract(self, context: ExtractionContext) -> ExtractionResult:
        """Return the fields and charges this strategy could resolve."""


def find_typed_value(field_type: FieldType, text: str) -> Tuple[Optional[object], Optional[str]]:
    """Find the first value of ``field_type`` in ``text``.

    Returns a ``(value, raw_span)`` pair, both ``None`` when nothing matched.
    For string fields the whole trimmed text is the value, since a label's tail
    is the value (a property name, a suite, a vendor).
    """
    if field_type in (FieldType.STRING, FieldType.CURRENCY):
        cleaned = normalize_text(text)
        if not cleaned:
            return None, None
        value = parse_value(field_type, cleaned)
        return (value, cleaned) if value else (None, None)

    token = _TYPE_TOKENS[field_type]
    for match in token.finditer(text):
        raw_span = match.group(0).strip()
        value = parse_value(field_type, raw_span)
        if value is not None:
            return value, raw_span
    return None, None


def make_field(
    name: str,
    value: object,
    tier: ExtractionTier,
    confidence: float,
    raw_text: Optional[str],
    label: Optional[str] = None,
) -> ExtractedField:
    """Construct an :class:`ExtractedField`, clamping confidence to ``[0, 1]``."""
    return ExtractedField(
        name=name,
        value=value,
        confidence=max(0.0, min(1.0, confidence)),
        tier=tier,
        raw_text=raw_text,
        label=label,
    )
