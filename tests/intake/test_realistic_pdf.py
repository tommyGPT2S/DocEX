"""The committed realistic-invoice PDFs: a positive and a negative case.

These read the same files a human can open in ``example_docs/cre_invoices/``.
They need only pdfminer (to read); the PDFs themselves are committed, so
reportlab is not required at test time. A live-LLM variant runs when
``ANTHROPIC_API_KEY`` is set.
"""

import os

import pytest

from docex.intake.charges import ChargeType
from docex.intake.ground_truth import InMemoryGroundTruthStore
from docex.intake.models import MatchStatus, ReconciliationStatus
from docex.intake.pdf import HAS_PDFMINER
from docex.intake.pipeline import InvoiceIntakePipeline
from tests.intake.realistic_invoice import (
    FIXTURE_PATH,
    OVERCHARGED_FIXTURE_PATH,
    SAMPLE_GROUND_TRUTH,
)

pytestmark = pytest.mark.skipif(not HAS_PDFMINER, reason="pdfminer.six not installed; skipping real-PDF tests")


def _store() -> InMemoryGroundTruthStore:
    store = InMemoryGroundTruthStore()
    store.add(SAMPLE_GROUND_TRUTH)
    return store


def test_positive_invoice_reconciles_clean(run):
    outcome = run(InvoiceIntakePipeline().process_pdf(FIXTURE_PATH.read_bytes(), _store()))
    assert outcome.status == ReconciliationStatus.MATCHED
    assert outcome.extracted.value("invoice_number") == "INV-2024-0042"


def test_negative_invoice_is_flagged_as_overcharge(run):
    outcome = run(InvoiceIntakePipeline().process_pdf(OVERCHARGED_FIXTURE_PATH.read_bytes(), _store()))

    assert outcome.status == ReconciliationStatus.DISCREPANCY
    assert "total" in {c.field for c in outcome.reconciliation.mismatches}
    cam = next(c for c in outcome.reconciliation.line_item_comparisons if c.charge_type == ChargeType.CAM)
    assert cam.status == MatchStatus.MISMATCH


@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set; skipping live LLM test")
def test_live_llm_on_realistic_pdf(run):
    """Drive the full pipeline with a real Claude model as the LLM tier."""
    anthropic = pytest.importorskip("anthropic")
    client = anthropic.Anthropic()

    def llm_fn(prompt: str) -> str:
        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in message.content if block.type == "text")

    positive = run(InvoiceIntakePipeline(llm_fn=llm_fn).process_pdf(FIXTURE_PATH.read_bytes(), _store()))
    assert positive.status == ReconciliationStatus.MATCHED

    negative = run(InvoiceIntakePipeline(llm_fn=llm_fn).process_pdf(OVERCHARGED_FIXTURE_PATH.read_bytes(), _store()))
    assert negative.status == ReconciliationStatus.DISCREPANCY
