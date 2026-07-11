"""Normalization is the foundation; these cases pin down the messy formats."""

from datetime import date
from decimal import Decimal

import pytest

from docex.intake.fields import FieldType
from docex.intake.normalize import (
    detect_currency,
    parse_amount,
    parse_date,
    parse_percent,
    parse_value,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("$1,234.56", Decimal("1234.56")),
        ("USD 1,234.56", Decimal("1234.56")),
        ("1234.56", Decimal("1234.56")),
        ("1,234", Decimal("1234")),
        ("$27,083.33", Decimal("27083.33")),
        ("(125.00)", Decimal("-125.00")),
        ("125.00-", Decimal("-125.00")),
        ("-125.00", Decimal("-125.00")),
        ("1.234,56", Decimal("1234.56")),  # European grouping
        ("€2.000,00", Decimal("2000.00")),
        ("0.00", Decimal("0.00")),
    ],
)
def test_parse_amount_handles_real_world_formats(raw, expected):
    assert parse_amount(raw) == expected


@pytest.mark.parametrize("raw", ["", "  ", "n/a", "—", None])
def test_parse_amount_returns_none_for_non_amounts(raw):
    assert parse_amount(raw) is None


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("2024-01-15", date(2024, 1, 15)),
        ("01/15/2024", date(2024, 1, 15)),
        ("1/5/2024", date(2024, 1, 5)),
        ("January 15, 2024", date(2024, 1, 15)),
        ("Jan 15 2024", date(2024, 1, 15)),
        ("15 January 2024", date(2024, 1, 15)),
        ("25/12/2024", date(2024, 12, 25)),  # day-first disambiguated by 25 > 12
        ("2024/03/09", date(2024, 3, 9)),
    ],
)
def test_parse_date_handles_common_formats(raw, expected):
    assert parse_date(raw) == expected


@pytest.mark.parametrize("raw", ["", "not a date", "13/13/2024"])
def test_parse_date_returns_none_when_unparseable(raw):
    assert parse_date(raw) is None


@pytest.mark.parametrize(
    "raw, expected",
    [("8.25%", Decimal("8.25")), ("12.5 percent", Decimal("12.5")), ("3", Decimal("3"))],
)
def test_parse_percent(raw, expected):
    assert parse_percent(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [("$1,000", "USD"), ("€500", "EUR"), ("£10", "GBP"), ("USD 5", "USD"), ("plain", None)],
)
def test_detect_currency(raw, expected):
    assert detect_currency(raw) == expected


def test_parse_value_dispatches_by_field_type():
    assert parse_value(FieldType.AMOUNT, "$1,000.00") == Decimal("1000.00")
    assert parse_value(FieldType.DATE, "2024-01-15") == date(2024, 1, 15)
    assert parse_value(FieldType.PERCENT, "8.25%") == Decimal("8.25")
    assert parse_value(FieldType.NUMBER, "12,500") == Decimal("12500")
    assert parse_value(FieldType.CURRENCY, "$100") == "USD"
    assert parse_value(FieldType.STRING, "  Acme   Corp ") == "Acme Corp"
