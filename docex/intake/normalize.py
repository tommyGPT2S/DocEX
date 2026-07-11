"""
Value normalization for messy invoice text.

Vendors format the same number a dozen ways: ``$1,234.56``, ``1.234,56``,
``(125.00)`` for a credit, ``USD 1,234``. Dates are worse. These helpers turn
raw spans into normalized Python types (``Decimal``, ``date``, ISO currency
codes) so every layer above compares apples to apples.

Assumption: amounts and dates default to US conventions (``,`` groups
thousands, ``.`` is the decimal point, dates are month-first) unless the text
itself disambiguates (for example a component greater than 12 in a date, or a
value that has both separators). The reconciler never re-parses; it trusts the
normalized value carried on each field.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

from docex.intake.fields import FieldType

_CURRENCY_SYMBOLS = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "A$": "AUD",
    "C$": "CAD",
}

_CURRENCY_CODES = {"USD", "EUR", "GBP", "JPY", "AUD", "CAD", "NZD", "CHF"}

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}


def normalize_text(value: str) -> str:
    """Collapse runs of whitespace and trim. ``None``-safe via empty string."""
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_for_compare(value: str) -> str:
    """Casefold and collapse whitespace for tolerant string comparison."""
    return normalize_text(value).casefold()


def parse_amount(raw: str) -> Optional[Decimal]:
    """Parse a monetary string into a signed ``Decimal``.

    Handles currency symbols and codes, thousands grouping, both US and
    European decimal separators, and parenthesised or trailing-minus negatives.
    Returns ``None`` when no numeric value is present.
    """
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]
    if text.endswith("-"):
        negative = True
        text = text[:-1]
    if text.startswith("-"):
        negative = True
        text = text[1:]

    digits = re.sub(r"[^0-9.,]", "", text)
    if not re.search(r"\d", digits):
        return None

    digits = _unify_decimal_separator(digits)
    try:
        amount = Decimal(digits)
    except InvalidOperation:
        return None
    return -amount if negative else amount


def _unify_decimal_separator(digits: str) -> str:
    """Reduce a grouped numeric string to a bare ``Decimal``-parseable string."""
    has_dot = "." in digits
    has_comma = "," in digits

    if has_dot and has_comma:
        # The rightmost separator is the decimal point; the other groups thousands.
        decimal_sep = "." if digits.rfind(".") > digits.rfind(",") else ","
        thousands_sep = "," if decimal_sep == "." else "."
        digits = digits.replace(thousands_sep, "").replace(decimal_sep, ".")
    elif has_comma:
        digits = _resolve_single_separator(digits, ",")
    elif has_dot:
        digits = _resolve_single_separator(digits, ".")
    return digits


def _resolve_single_separator(digits: str, sep: str) -> str:
    """Decide whether a lone separator groups thousands or marks the decimal."""
    if digits.count(sep) > 1:
        return digits.replace(sep, "")  # only thousands grouping repeats
    fractional_digits = len(digits.split(sep)[1])
    if fractional_digits == 3 and sep == ",":
        return digits.replace(sep, "")  # "1,234" is one thousand two hundred
    return digits.replace(sep, ".")


def detect_currency(raw: str) -> Optional[str]:
    """Return the ISO currency code implied by a string, if any."""
    if not raw:
        return None
    text = raw.upper()
    for code in _CURRENCY_CODES:
        if code in text:
            return code
    for symbol, code in _CURRENCY_SYMBOLS.items():
        if symbol in raw:
            return code
    return None


def parse_percent(raw: str) -> Optional[Decimal]:
    """Parse a percentage into its numeric value (``"12.5%"`` -> ``Decimal('12.5')``)."""
    if not raw:
        return None
    return parse_amount(raw.replace("%", " ").replace("percent", " "))


def parse_number(raw: str) -> Optional[Decimal]:
    """Parse a plain (possibly grouped) number such as a square-foot figure."""
    return parse_amount(raw)


def parse_date(raw: str) -> Optional[date]:
    """Parse a date in any of the common invoice formats.

    Supports ISO (``2024-01-15``), slash/dot/dash numeric dates with US
    month-first defaulting, and spelled-out months (``Jan 15, 2024`` or
    ``15 January 2024``). Returns ``None`` if no date can be read.
    """
    if not raw:
        return None
    text = normalize_text(raw)

    spelled = _parse_spelled_date(text)
    if spelled:
        return spelled
    return _parse_numeric_date(text)


def _parse_spelled_date(text: str) -> Optional[date]:
    """Parse dates that name the month, e.g. ``January 15, 2024``."""
    match = re.search(r"([A-Za-z]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})", text)
    if match:
        month = _MONTHS.get(match.group(1).lower())
        if month:
            return _safe_date(int(match.group(3)), month, int(match.group(2)))

    match = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\.?\s+([A-Za-z]+)\.?,?\s+(\d{4})", text)
    if match:
        month = _MONTHS.get(match.group(2).lower())
        if month:
            return _safe_date(int(match.group(3)), month, int(match.group(1)))
    return None


def _parse_numeric_date(text: str) -> Optional[date]:
    """Parse all-numeric dates, defaulting to month-first when ambiguous."""
    match = re.search(r"(\d{1,4})[/\-.](\d{1,2})[/\-.](\d{1,4})", text)
    if not match:
        return None
    first, second, third = (int(g) for g in match.groups())

    if first > 31:  # leading four-digit year: YYYY-MM-DD
        return _safe_date(first, second, third)

    year = third if third > 99 else 2000 + third
    month, day = first, second
    if first > 12 >= second:  # first component cannot be a month
        month, day = second, first
    return _safe_date(year, month, day)


def _safe_date(year: int, month: int, day: int) -> Optional[date]:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_value(field_type: FieldType, raw: str) -> Optional[object]:
    """Normalize a raw span according to its canonical field type."""
    if field_type == FieldType.AMOUNT:
        return parse_amount(raw)
    if field_type == FieldType.DATE:
        return parse_date(raw)
    if field_type == FieldType.CURRENCY:
        return detect_currency(raw)
    if field_type == FieldType.PERCENT:
        return parse_percent(raw)
    if field_type == FieldType.NUMBER:
        return parse_number(raw)
    return normalize_text(raw)
