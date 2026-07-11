"""Property-style coverage: many randomized invoices, one invariant each.

These run the heuristic-only pipeline over dozens of seeded invoices with
varied layouts, labels, and values. A clean invoice must always reconcile; an
overcharged one must always be caught. If a layout the generator can produce
ever breaks the heuristic, one of these fails with the seed that did it.
"""

from decimal import Decimal

import pytest

from docex.intake.charges import ChargeType
from docex.intake.ground_truth import InMemoryGroundTruthStore
from docex.intake.models import ReconciliationStatus
from docex.intake.pipeline import InvoiceIntakePipeline
from tests.intake.synthetic import matched_pair, overcharged_invoice


@pytest.mark.parametrize("seed", range(40))
def test_clean_invoices_always_reconcile(run, seed):
    gt, text = matched_pair(seed)
    store = InMemoryGroundTruthStore()
    store.add(gt)
    outcome = run(InvoiceIntakePipeline().process_text(text, store))
    assert outcome.status == ReconciliationStatus.MATCHED, f"seed {seed} failed: {outcome.reconciliation.mismatches or outcome.reconciliation.missing}"


@pytest.mark.parametrize("seed", range(20))
def test_overcharged_invoices_are_always_caught(run, seed):
    charge = [ChargeType.CAM, ChargeType.BASE_RENT, ChargeType.REAL_ESTATE_TAX][seed % 3]
    gt, text = overcharged_invoice(seed, charge_type=charge, delta=Decimal("175.00"))
    store = InMemoryGroundTruthStore()
    store.add(gt)
    outcome = run(InvoiceIntakePipeline().process_text(text, store))
    assert outcome.status == ReconciliationStatus.DISCREPANCY, f"seed {seed} not caught"
