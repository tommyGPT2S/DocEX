"""Real PDF round-trip through pdfminer.

The bulk of the suite works on text so it stays fast and dependency-free. This
module proves the one boundary the text tests cannot: that a genuine PDF, parsed
by pdfminer, still flows through the pipeline. It is skipped when either
optional dependency (reportlab to write, pdfminer to read) is absent.
"""

import pytest

from docex.intake.ground_truth import InMemoryGroundTruthStore
from docex.intake.models import ReconciliationStatus
from docex.intake.pdf import HAS_PDFMINER
from docex.intake.pipeline import InvoiceIntakePipeline
from tests.intake.synthetic import lines_to_pdf_bytes, matched_pair

reportlab = pytest.importorskip("reportlab", reason="reportlab not installed; skipping real-PDF test")
pytestmark = pytest.mark.skipif(not HAS_PDFMINER, reason="pdfminer.six not installed; skipping real-PDF test")


def test_pdf_is_extracted_and_reconciled(run):
    gt, text = matched_pair(seed=7)
    pdf_bytes = lines_to_pdf_bytes(text)

    store = InMemoryGroundTruthStore()
    store.add(gt)

    outcome = run(InvoiceIntakePipeline().process_pdf(pdf_bytes, store))
    assert outcome.ground_truth is not None
    assert outcome.status in (ReconciliationStatus.MATCHED, ReconciliationStatus.INCOMPLETE)
    assert outcome.extracted.value("invoice_number") == gt.invoice_number
