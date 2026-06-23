"""Reconciliation: tolerances, statuses, and per-charge comparison."""

from datetime import date
from decimal import Decimal

from docex.intake.charges import ChargeType
from docex.intake.ground_truth import GroundTruthInvoice
from docex.intake.models import (
    ExtractedField,
    ExtractedInvoice,
    ExtractionTier,
    LineItem,
    MatchStatus,
    ReconciliationStatus,
)
from docex.intake.reconcile import Reconciler, TolerancePolicy


def _extracted(fields=None, line_items=None) -> ExtractedInvoice:
    invoice = ExtractedInvoice(line_items=line_items or [])
    # Ground truth always carries a currency (defaults to USD), so supply it
    # unless a test overrides it; otherwise every case reports currency missing.
    merged = {"currency": "USD", **(fields or {})}
    for name, value in merged.items():
        invoice.put(ExtractedField(name=name, value=value, confidence=0.9, tier=ExtractionTier.HEURISTIC))
    return invoice


def _ground_truth(**overrides) -> GroundTruthInvoice:
    base = dict(invoice_number="INV-1", total=Decimal("1000.00"))
    base.update(overrides)
    return GroundTruthInvoice(**base)


def test_exact_match_is_matched():
    gt = _ground_truth(total=Decimal("1000.00"))
    result = Reconciler().reconcile(_extracted({"invoice_number": "INV-1", "total": Decimal("1000.00")}), gt)
    assert result.status == ReconciliationStatus.MATCHED
    assert not result.mismatches


def test_amount_within_tolerance_matches():
    gt = _ground_truth(total=Decimal("1000.00"))
    extracted = _extracted({"invoice_number": "INV-1", "total": Decimal("1000.01")})
    assert Reconciler().reconcile(extracted, gt).status == ReconciliationStatus.MATCHED


def test_amount_beyond_tolerance_is_discrepancy():
    gt = _ground_truth(total=Decimal("1000.00"))
    extracted = _extracted({"invoice_number": "INV-1", "total": Decimal("1000.50")})
    result = Reconciler().reconcile(extracted, gt)
    assert result.status == ReconciliationStatus.DISCREPANCY
    assert [c.field for c in result.mismatches] == ["total"]


def test_missing_value_is_incomplete_not_discrepancy():
    gt = _ground_truth(total=Decimal("1000.00"), tenant_name="Acme")
    extracted = _extracted({"invoice_number": "INV-1", "total": Decimal("1000.00")})
    result = Reconciler().reconcile(extracted, gt)
    assert result.status == ReconciliationStatus.INCOMPLETE
    assert [c.field for c in result.missing] == ["tenant_name"]


def test_date_tolerance_is_configurable():
    gt = _ground_truth(due_date=date(2024, 1, 15))
    extracted = _extracted({"invoice_number": "INV-1", "total": Decimal("1000.00"), "due_date": date(2024, 1, 16)})

    strict = Reconciler().reconcile(extracted, gt)
    assert strict.status == ReconciliationStatus.DISCREPANCY

    lenient = Reconciler(TolerancePolicy(date_days=2)).reconcile(extracted, gt)
    assert lenient.status == ReconciliationStatus.MATCHED


def test_string_comparison_ignores_case_and_whitespace():
    gt = _ground_truth(tenant_name="Acme Retail LLC")
    extracted = _extracted({"invoice_number": "INV-1", "total": Decimal("1000.00"), "tenant_name": "acme   retail llc"})
    assert Reconciler().reconcile(extracted, gt).status == ReconciliationStatus.MATCHED


def test_only_fields_with_expectations_are_judged():
    gt = _ground_truth(total=Decimal("1000.00"))  # no suite expectation
    extracted = _extracted({"invoice_number": "INV-1", "total": Decimal("1000.00"), "suite_number": "400"})
    result = Reconciler().reconcile(extracted, gt)
    judged = {c.field for c in result.field_comparisons}
    assert "suite_number" not in judged


def test_line_items_reconcile_by_charge_type():
    gt = _ground_truth(
        line_items=[
            LineItem(charge_type=ChargeType.BASE_RENT, amount=Decimal("900")),
            LineItem(charge_type=ChargeType.CAM, amount=Decimal("100")),
        ]
    )
    extracted = _extracted(
        {"invoice_number": "INV-1", "total": Decimal("1000.00")},
        line_items=[
            LineItem(charge_type=ChargeType.BASE_RENT, amount=Decimal("900")),
            LineItem(charge_type=ChargeType.CAM, amount=Decimal("130")),  # overcharged
        ],
    )
    result = Reconciler().reconcile(extracted, gt)
    by_type = {c.charge_type: c.status for c in result.line_item_comparisons}
    assert by_type[ChargeType.BASE_RENT] == MatchStatus.MATCH
    assert by_type[ChargeType.CAM] == MatchStatus.MISMATCH
