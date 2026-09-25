"""
Rules tier: label-based field extraction with type validation.

For each configured field the engine scans the document text for any of the
field's label phrases and takes the nearest value of the declared type --
first on the same line after the label, then on the next non-empty line
(invoices often print the label above the value).

Values must parse cleanly for their type (real number, real calendar date) or
the candidate is rejected, so a scanner artifact like "$12,5OO" is never
stored as a total. If different labels produce different valid values for the
same field, the field is marked conflicting instead of silently picking one.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple

from docex.extraction.config import ExtractionConfig, FieldSpec

# Field result statuses
FOUND = 'found'
NOT_FOUND = 'not_found'
CONFLICT = 'conflict'

# Extraction sources
SOURCE_RULES = 'regex'
SOURCE_LLM = 'llm'

_MONEY_RE = re.compile(r'\(?\$?\s?-?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?\)?')

_DATE_RES = (
    re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'),
    re.compile(r'\b\d{4}-\d{1,2}-\d{1,2}\b'),
    re.compile(r'\b[A-Za-z]{3,9}\.? \d{1,2},? \d{4}\b'),
)

_DATE_FORMATS = (
    '%m/%d/%Y', '%m/%d/%y', '%m-%d-%Y', '%m-%d-%y', '%Y-%m-%d',
    '%B %d, %Y', '%B %d %Y', '%b %d, %Y', '%b %d %Y',
)

_MAX_TEXT_LENGTH = 120


@dataclass
class FieldResult:
    """Outcome of extracting one field."""

    name: str
    status: str
    value: Optional[str] = None
    label: Optional[str] = None
    source: Optional[str] = None


def parse_money(raw: str) -> Optional[str]:
    """Normalize a money string to a plain decimal, or None if it is not a valid amount."""
    cleaned = raw.strip().replace('$', '').replace(',', '').replace(' ', '')
    negative = cleaned.startswith('(') and cleaned.endswith(')')
    if negative:
        cleaned = cleaned[1:-1]
    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        return None
    return str(-amount if negative else amount)


def parse_date(raw: str) -> Optional[str]:
    """Normalize a date string to YYYY-MM-DD, or None if it is not a real date."""
    cleaned = raw.strip().replace('.', '')
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_text(raw: str) -> Optional[str]:
    """Clean a free-text value; reject empty or implausibly long grabs."""
    cleaned = raw.strip(' \t:#-\u2013\u2014.').strip()
    if not cleaned or len(cleaned) > _MAX_TEXT_LENGTH:
        return None
    return cleaned


def normalize_value(field_type: str, raw: str) -> Optional[str]:
    """Validate and normalize a raw value for the given field type."""
    if field_type == 'money':
        return _first_valid(_money_candidates(raw), parse_money)
    if field_type == 'date':
        candidates = [m.group(0) for rx in _DATE_RES for m in rx.finditer(raw)]
        return _first_valid(candidates, parse_date)
    return parse_text(raw)


def _money_candidates(segment: str):
    """Money-looking matches with clean boundaries.

    A match glued to letters or to malformed digit groups (e.g. the "$12"
    inside a scanner-garbled "$12,5OO") is rejected rather than returning a
    wrong amount.
    """
    for m in _MONEY_RE.finditer(segment):
        start, end = m.span()
        if start > 0 and segment[start - 1].isalnum():
            continue
        if end < len(segment):
            following = segment[end]
            if following.isalnum():
                continue
            if following in ',.' and end + 1 < len(segment) and not segment[end + 1].isspace():
                continue
        yield m.group(0)


def _first_valid(candidates, parser) -> Optional[str]:
    for candidate in candidates:
        value = parser(candidate)
        if value is not None:
            return value
    return None


class RulesEngine:
    """Extracts configured fields from text using label phrases and type validation."""

    def __init__(self, config: ExtractionConfig):
        self.config = config

    def extract(self, text: str) -> Dict[str, FieldResult]:
        """Extract every configured field. Returns a result per field, found or not."""
        lines = text.splitlines()
        candidates: Dict[str, List[Tuple[str, str]]] = {spec.name: [] for spec in self.config.fields}

        for index, line in enumerate(lines):
            for start, end, spec, label in self._label_matches(line):
                value = self._value_near(spec.type, line[end:], self._next_nonempty(lines, index))
                if value is not None:
                    candidates[spec.name].append((value, label))

        results = {}
        for spec in self.config.fields:
            found = candidates[spec.name]
            distinct = {value for value, _ in found}
            if not found:
                results[spec.name] = FieldResult(spec.name, NOT_FOUND)
            elif len(distinct) == 1:
                value, label = found[0]
                results[spec.name] = FieldResult(spec.name, FOUND, value, label, SOURCE_RULES)
            else:
                results[spec.name] = FieldResult(spec.name, CONFLICT)
        return results

    def _label_matches(self, line: str) -> List[Tuple[int, int, FieldSpec, str]]:
        """All label occurrences in a line, at word boundaries.

        A shorter label contained inside a longer one is suppressed, so a
        configured "Due Date" wins over a configured "Date" on the same span.
        """
        matches = []
        for spec in self.config.fields:
            for label in spec.labels:
                for m in re.finditer(re.escape(label), line, re.IGNORECASE):
                    start, end = m.span()
                    if start > 0 and line[start - 1].isalnum():
                        continue
                    if end < len(line) and line[end].isalnum():
                        continue
                    matches.append((start, end, spec, label))

        return [
            m for m in matches
            if not any(
                o is not m and o[0] <= m[0] and m[1] <= o[1] and (o[1] - o[0]) > (m[1] - m[0])
                for o in matches
            )
        ]

    @staticmethod
    def _value_near(field_type: str, same_line: str, next_line: Optional[str]) -> Optional[str]:
        value = normalize_value(field_type, same_line)
        if value is None and next_line is not None:
            value = normalize_value(field_type, next_line)
        return value

    @staticmethod
    def _next_nonempty(lines: List[str], index: int) -> Optional[str]:
        for line in lines[index + 1:]:
            if line.strip():
                return line
        return None
