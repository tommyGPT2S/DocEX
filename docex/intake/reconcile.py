"""
Reconciliation: does the extracted invoice agree with our recorded actuals?

The reconciler compares an :class:`~docex.intake.models.ExtractedInvoice`
against a :class:`~docex.intake.ground_truth.GroundTruthInvoice` field by field,
applying type-aware tolerances (a cent of rounding on money, a day on dates),
and rolls per-charge line items up by category so a vendor's "CAM" line is
compared against the lease's expected CAM regardless of wording.

It only judges fields the ground truth actually specifies - a value we never
recorded an expectation for cannot be right or wrong, so it is not reported.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Optional

from docex.intake.charges import ChargeType
from docex.intake.fields import FIELDS, FieldType
from docex.intake.ground_truth import GroundTruthInvoice, GroundTruthStore
from docex.intake.models import (
    ExtractedInvoice,
    FieldComparison,
    LineItemComparison,
    MatchStatus,
    ReconciliationResult,
    ReconciliationStatus,
)
from docex.intake.normalize import normalize_for_compare


class TolerancePolicy:
    """How much disagreement still counts as a match, per value type."""

    def __init__(
        self,
        amount_abs: Decimal = Decimal("0.01"),
        amount_rel: float = 0.0,
        date_days: int = 0,
        percent_abs: Decimal = Decimal("0.01"),
    ) -> None:
        self.amount_abs = amount_abs
        self.amount_rel = amount_rel
        self.date_days = date_days
        self.percent_abs = percent_abs

    def amounts_match(self, expected: Decimal, actual: Decimal) -> bool:
        allowed = max(self.amount_abs, Decimal(str(self.amount_rel)) * abs(expected))
        return abs(expected - actual) <= allowed

    def percents_match(self, expected: Decimal, actual: Decimal) -> bool:
        return abs(expected - actual) <= self.percent_abs

    def dates_match(self, expected: date, actual: date) -> bool:
        return abs((expected - actual).days) <= self.date_days


class Reconciler:
    """Compares an extracted invoice against ground truth with tolerances."""

    def __init__(self, tolerance: Optional[TolerancePolicy] = None) -> None:
        self._tolerance = tolerance or TolerancePolicy()

    def reconcile(self, extracted: ExtractedInvoice, ground_truth: GroundTruthInvoice) -> ReconciliationResult:
        field_comparisons = [
            comparison
            for name in FIELDS
            if (comparison := self._compare_field(name, extracted, ground_truth)) is not None
        ]
        line_item_comparisons = self._compare_line_items(extracted, ground_truth)

        return ReconciliationResult(
            status=self._overall_status(field_comparisons),
            ground_truth_id=ground_truth.id,
            field_comparisons=field_comparisons,
            line_item_comparisons=line_item_comparisons,
            tiers_used=sorted(extracted.tiers_used(), key=lambda tier: tier.value),
        )

    def _compare_field(
        self,
        name: str,
        extracted: ExtractedInvoice,
        ground_truth: GroundTruthInvoice,
    ) -> Optional[FieldComparison]:
        expected = ground_truth.get(name)
        if expected is None:
            return None  # no recorded expectation -> nothing to judge

        actual = extracted.value(name)
        status = self._field_status(FIELDS[name].type, expected, actual)
        return FieldComparison(
            field=name,
            expected=expected,
            actual=actual,
            status=status,
            confidence=extracted.confidence(name),
            tier=extracted.tier(name),
        )

    def _field_status(self, field_type: FieldType, expected: object, actual: object) -> MatchStatus:
        if actual is None:
            return MatchStatus.MISSING
        return MatchStatus.MATCH if self._values_match(field_type, expected, actual) else MatchStatus.MISMATCH

    def _values_match(self, field_type: FieldType, expected: object, actual: object) -> bool:
        if field_type == FieldType.AMOUNT:
            return self._tolerance.amounts_match(expected, actual)
        if field_type == FieldType.NUMBER:
            return self._tolerance.amounts_match(expected, actual)
        if field_type == FieldType.PERCENT:
            return self._tolerance.percents_match(expected, actual)
        if field_type == FieldType.DATE:
            return self._tolerance.dates_match(expected, actual)
        return normalize_for_compare(str(expected)) == normalize_for_compare(str(actual))

    def _compare_line_items(
        self,
        extracted: ExtractedInvoice,
        ground_truth: GroundTruthInvoice,
    ) -> List[LineItemComparison]:
        charge_types = self._charge_types(extracted, ground_truth)
        comparisons = []
        for charge_type in charge_types:
            expected = ground_truth.charge_total(charge_type)
            actual = self._extracted_charge_total(extracted, charge_type)
            comparisons.append(
                LineItemComparison(
                    charge_type=charge_type,
                    expected=expected,
                    actual=actual,
                    status=self._charge_status(expected, actual),
                )
            )
        return comparisons

    def _charge_types(self, extracted: ExtractedInvoice, ground_truth: GroundTruthInvoice) -> List[ChargeType]:
        seen = {item.charge_type for item in ground_truth.line_items}
        seen.update(item.charge_type for item in extracted.line_items)
        return sorted(seen, key=lambda charge: charge.value)

    @staticmethod
    def _extracted_charge_total(extracted: ExtractedInvoice, charge_type: ChargeType) -> Optional[Decimal]:
        amounts = [
            item.amount
            for item in extracted.line_items
            if item.charge_type == charge_type and item.amount is not None
        ]
        return sum(amounts, Decimal("0")) if amounts else None

    def _charge_status(self, expected: Optional[Decimal], actual: Optional[Decimal]) -> MatchStatus:
        if expected is None or actual is None:
            return MatchStatus.MISSING
        return MatchStatus.MATCH if self._tolerance.amounts_match(expected, actual) else MatchStatus.MISMATCH

    @staticmethod
    def _overall_status(comparisons: List[FieldComparison]) -> ReconciliationStatus:
        statuses = {comparison.status for comparison in comparisons}
        if MatchStatus.MISMATCH in statuses:
            return ReconciliationStatus.DISCREPANCY
        if MatchStatus.MISSING in statuses:
            return ReconciliationStatus.INCOMPLETE
        return ReconciliationStatus.MATCHED


class GroundTruthMatcher:
    """Finds the ground-truth record an extracted invoice should match.

    Matching is by stable identifiers only - invoice number first, then PO
    number. We never guess a record from fuzzy totals: reconciling against the
    wrong lease is worse than reporting that no record was found.
    """

    def __init__(self, store: GroundTruthStore) -> None:
        self._store = store

    def find(self, extracted: ExtractedInvoice) -> Optional[GroundTruthInvoice]:
        invoice_number = extracted.value("invoice_number")
        if invoice_number:
            match = self._store.get_by_invoice_number(str(invoice_number))
            if match:
                return match

        po_number = extracted.value("po_number")
        if po_number:
            return self._store.get_by_po_number(str(po_number))
        return None
