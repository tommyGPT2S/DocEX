"""
DocEX processor integration for invoice intake.

Wraps :class:`~docex.intake.pipeline.InvoiceIntakePipeline` as a DocEX
``BaseProcessor`` so an invoice already stored in a basket can be reconciled in
place, with the verdict written back to the document's metadata.

The pipeline dependencies (the ground-truth store, the optional LLM, the
learning store) are passed to the constructor rather than through the
JSON-serialisable processor config, mirroring how
:class:`~docex.processors.vector.VectorIndexingProcessor` takes its
``embedding_fn``. A tenant-aware ``db`` is optional: without it the processor
still returns the full reconciliation, it just does not persist metadata.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from docex.db.connection import Database
from docex.document import Document
from docex.intake.extractors.llm import LLMFn
from docex.intake.ground_truth import GroundTruthStore
from docex.intake.learning import LearningStore
from docex.intake.pipeline import IntakeOutcome, InvoiceIntakePipeline
from docex.intake.reconcile import TolerancePolicy
from docex.processors.base import BaseProcessor, ProcessingResult
from docex.services.metadata_service import MetadataService


class InvoiceIntakeProcessor(BaseProcessor):
    """Reconciles a stored invoice PDF against ground truth, recording the verdict."""

    def __init__(
        self,
        ground_truth_store: GroundTruthStore,
        llm_fn: Optional[LLMFn] = None,
        learning_store: Optional[LearningStore] = None,
        tolerance: Optional[TolerancePolicy] = None,
        db: Optional[Database] = None,
        store_in_metadata: bool = True,
    ) -> None:
        self.config = {"store_in_metadata": store_in_metadata}
        self.db = db
        self._store = ground_truth_store
        self._pipeline = InvoiceIntakePipeline(llm_fn, learning_store, tolerance)
        self._store_in_metadata = store_in_metadata

    def can_process(self, document: Document) -> bool:
        return document.name.lower().endswith(".pdf")

    async def process(self, document: Document) -> ProcessingResult:
        try:
            pdf_bytes = self.get_document_bytes(document)
            outcome = await self._pipeline.process_pdf(pdf_bytes, self._store)
            metadata = self._build_metadata(outcome)

            if self._store_in_metadata and self.db is not None and outcome.ground_truth is not None:
                MetadataService(self.db).update_metadata(document.id, metadata)

            return ProcessingResult(success=True, content=outcome.status.value, metadata=metadata)
        except Exception as exc:  # noqa: BLE001 - surfaced as a processing failure
            return ProcessingResult(success=False, error=str(exc))

    def _build_metadata(self, outcome: IntakeOutcome) -> Dict[str, Any]:
        reconciliation = outcome.reconciliation
        return {
            "intake_status": reconciliation.status.value,
            "intake_ground_truth_id": reconciliation.ground_truth_id,
            "intake_invoice_number": outcome.extracted.value("invoice_number"),
            "intake_total": _as_text(outcome.extracted.value("total")),
            "intake_mismatched_fields": [comparison.field for comparison in reconciliation.mismatches],
            "intake_missing_fields": [comparison.field for comparison in reconciliation.missing],
            "intake_tiers_used": [tier.value for tier in reconciliation.tiers_used],
        }


def _as_text(value: Any) -> Optional[str]:
    return str(value) if value is not None else None
