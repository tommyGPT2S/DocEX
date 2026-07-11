"""The in-memory store and the matcher that finds the right record."""

from decimal import Decimal

from docex.intake.ground_truth import GroundTruthInvoice, InMemoryGroundTruthStore
from docex.intake.models import ExtractedField, ExtractedInvoice, ExtractionTier
from docex.intake.reconcile import GroundTruthMatcher


def _record(**overrides) -> GroundTruthInvoice:
    base = dict(invoice_number="INV-1", po_number="PO-9", total=Decimal("100.00"))
    base.update(overrides)
    return GroundTruthInvoice(**base)


def _extracted(**values) -> ExtractedInvoice:
    invoice = ExtractedInvoice()
    for name, value in values.items():
        invoice.put(ExtractedField(name=name, value=value, confidence=0.9, tier=ExtractionTier.HEURISTIC))
    return invoice


def test_add_assigns_id_and_indexes_by_invoice_and_po():
    store = InMemoryGroundTruthStore()
    stored = store.add(_record())
    assert stored.id is not None
    assert store.get_by_invoice_number("INV-1") is stored
    assert store.get_by_po_number("PO-9") is stored


def test_matcher_prefers_invoice_number():
    store = InMemoryGroundTruthStore()
    store.add(_record(invoice_number="INV-1", po_number="PO-9"))
    other = store.add(_record(invoice_number="INV-2", po_number="PO-OTHER"))

    match = GroundTruthMatcher(store).find(_extracted(invoice_number="INV-2", po_number="PO-9"))
    assert match.id == other.id  # invoice number wins over the conflicting PO


def test_matcher_falls_back_to_po_number():
    store = InMemoryGroundTruthStore()
    stored = store.add(_record(invoice_number="INV-1", po_number="PO-9"))

    match = GroundTruthMatcher(store).find(_extracted(po_number="PO-9"))
    assert match.id == stored.id


def test_matcher_returns_none_when_nothing_identifies_the_record():
    store = InMemoryGroundTruthStore()
    store.add(_record())
    assert GroundTruthMatcher(store).find(_extracted()) is None


def test_charge_total_sums_by_type():
    from docex.intake.charges import ChargeType
    from docex.intake.models import LineItem

    record = _record(
        line_items=[
            LineItem(charge_type=ChargeType.CAM, amount=Decimal("100")),
            LineItem(charge_type=ChargeType.CAM, amount=Decimal("50")),
            LineItem(charge_type=ChargeType.BASE_RENT, amount=Decimal("900")),
        ]
    )
    assert record.charge_total(ChargeType.CAM) == Decimal("150")
    assert record.charge_total(ChargeType.PARKING) is None
