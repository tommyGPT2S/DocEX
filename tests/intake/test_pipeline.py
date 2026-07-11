"""End-to-end pipeline behaviour, the contract the whole package exists for."""

import json
from decimal import Decimal

from docex.intake.charges import ChargeType
from docex.intake.ground_truth import GroundTruthInvoice, InMemoryGroundTruthStore
from docex.intake.learning import InMemoryLearningStore
from docex.intake.models import ExtractionTier, MatchStatus, ReconciliationStatus
from docex.intake.pipeline import InvoiceIntakePipeline
from tests.intake.synthetic import matched_pair, overcharged_invoice


def _store(*records) -> InMemoryGroundTruthStore:
    store = InMemoryGroundTruthStore()
    for record in records:
        store.add(record)
    return store


def test_clean_invoice_matches_with_zero_llm_calls(run):
    gt, text = matched_pair(seed=1)
    store = _store(gt)

    def explode(prompt):
        raise AssertionError("a clean invoice must not reach the LLM")

    outcome = run(InvoiceIntakePipeline(llm_fn=explode).process_text(text, store))
    assert outcome.status == ReconciliationStatus.MATCHED
    assert outcome.reconciliation.tiers_used == [ExtractionTier.HEURISTIC]


def test_overcharge_is_reported_as_discrepancy(run):
    gt, text = overcharged_invoice(seed=2, charge_type=ChargeType.CAM, delta=Decimal("250.00"))
    outcome = run(InvoiceIntakePipeline().process_text(text, _store(gt)))

    assert outcome.status == ReconciliationStatus.DISCREPANCY
    assert "total" in {c.field for c in outcome.reconciliation.mismatches}
    cam = next(c for c in outcome.reconciliation.line_item_comparisons if c.charge_type == ChargeType.CAM)
    assert cam.status == MatchStatus.MISMATCH


def test_unmatched_invoice_is_unresolved(run):
    store = _store(GroundTruthInvoice(invoice_number="INV-KNOWN", total=Decimal("100.00")))
    outcome = run(InvoiceIntakePipeline().process_text("Invoice Number: INV-UNKNOWN\nTotal Amount Due: $100.00", store))
    assert outcome.status == ReconciliationStatus.UNRESOLVED
    assert outcome.ground_truth is None


def test_llm_escalation_repairs_a_missing_field(run):
    # Ground truth expects a tenant name the invoice never labels, so the
    # heuristic leaves it missing and the pipeline escalates just that field.
    gt = GroundTruthInvoice(invoice_number="INV-1", total=Decimal("100.00"), tenant_name="Acme Retail LLC")
    text = "Invoice Number: INV-1\nTotal Amount Due: $100.00\nAcme Retail LLC"  # name present, unlabelled

    def llm_fn(prompt):
        return json.dumps({"fields": {"tenant_name": {"value": "Acme Retail LLC", "label": "Customer"}}})

    outcome = run(InvoiceIntakePipeline(llm_fn=llm_fn).process_text(text, _store(gt)))
    assert outcome.status == ReconciliationStatus.MATCHED
    assert outcome.extracted.tier("tenant_name") == ExtractionTier.LLM


def test_learning_loop_eliminates_the_second_llm_call(run):
    gt = GroundTruthInvoice(invoice_number="INV-1", total=Decimal("100.00"))
    store = _store(gt)
    text = "Invoice Number: INV-1\nNet Payable This Cycle: $100.00"  # novel total label

    calls = []

    def llm_fn(prompt):
        calls.append(prompt)
        return json.dumps({"fields": {"total": {"value": "$100.00", "label": "Net Payable This Cycle"}}})

    pipeline = InvoiceIntakePipeline(llm_fn=llm_fn, learning_store=InMemoryLearningStore())

    first = run(pipeline.process_text(text, store))
    assert first.status == ReconciliationStatus.MATCHED
    assert len(calls) == 1  # LLM needed to read the novel label

    second = run(pipeline.process_text(text, store))
    assert second.status == ReconciliationStatus.MATCHED
    assert len(calls) == 1  # heuristic learned the label; no new call
    assert second.reconciliation.tiers_used == [ExtractionTier.HEURISTIC]


def test_heuristic_only_pipeline_runs_without_an_llm(run):
    gt, text = matched_pair(seed=3)
    outcome = run(InvoiceIntakePipeline().process_text(text, _store(gt)))
    assert outcome.status == ReconciliationStatus.MATCHED
