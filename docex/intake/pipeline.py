"""
The intake pipeline: PDF in, reconciliation out.

This ties the pieces together in the cost-minimal order the whole design is
built around:

1. Extract cheaply (heuristic), escalating only missing required fields.
2. Match the invoice to a ground-truth record by stable identifier.
3. Reconcile against that record.
4. *Only if* the reconciliation shows disputes, ask the LLM to re-extract just
   those fields, then reconcile once more. This is the "final check if
   everything else shows an issue" step - a clean invoice never reaches it.
5. Record the labels of confirmed fields so the heuristic keeps improving.

The LLM is optional. With no ``llm_fn`` the pipeline runs fully offline and
simply reports the fields the heuristic could not resolve.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Union

from docex.intake.embedding_match import EmbeddingFn, EmbeddingGroundTruthMatcher
from docex.intake.extractors.cascade import CascadingExtractor
from docex.intake.extractors.heuristic import HeuristicExtractor
from docex.intake.extractors.llm import LLMExtractor, LLMFn
from docex.intake.ground_truth import GroundTruthInvoice, GroundTruthStore
from docex.intake.learning import LearningStore, record_confirmed_labels
from docex.intake.models import (
    ExtractedInvoice,
    MatchStatus,
    ReconciliationResult,
    ReconciliationStatus,
)
from docex.intake.pdf import extract_text_from_pdf
from docex.intake.reconcile import GroundTruthMatcher, Reconciler, TolerancePolicy

GroundTruth = Union[GroundTruthInvoice, GroundTruthStore]


@dataclass
class IntakeOutcome:
    """The result of running one invoice through the pipeline."""

    extracted: ExtractedInvoice
    reconciliation: ReconciliationResult
    ground_truth: Optional[GroundTruthInvoice]

    @property
    def status(self) -> ReconciliationStatus:
        return self.reconciliation.status

    @property
    def is_clean(self) -> bool:
        return self.reconciliation.is_clean


class InvoiceIntakePipeline:
    """Extracts, matches, reconciles, and (only as needed) escalates to an LLM."""

    def __init__(
        self,
        llm_fn: Optional[LLMFn] = None,
        learning_store: Optional[LearningStore] = None,
        tolerance: Optional[TolerancePolicy] = None,
        embedding_fn: Optional[EmbeddingFn] = None,
        match_threshold: float = 0.8,
    ) -> None:
        """
        Args:
            llm_fn: Optional caller-provided language model (see
                :class:`~docex.intake.extractors.llm.LLMExtractor`). Omit to run
                heuristic-only.
            learning_store: Optional store that records confirmed label phrasings
                so the heuristic improves over time.
            tolerance: Optional reconciliation tolerances; sensible defaults
                otherwise (a cent on money, exact on dates).
            embedding_fn: Optional embedding function enabling fuzzy ground-truth
                retrieval. When set, an invoice that does not match any record by
                identifier falls back to the closest record by embedding
                similarity instead of being reported as unresolved.
            match_threshold: Minimum cosine similarity for the embedding fallback
                to accept a record.
        """
        llm = LLMExtractor(llm_fn) if llm_fn else None
        self._cascade = CascadingExtractor(HeuristicExtractor(learning_store), llm)
        self._reconciler = Reconciler(tolerance)
        self._learning_store = learning_store
        self._can_escalate = llm is not None
        self._embedding_matcher = (
            EmbeddingGroundTruthMatcher(embedding_fn, match_threshold) if embedding_fn else None
        )

    async def process_pdf(self, source, ground_truth: GroundTruth) -> IntakeOutcome:
        """Extract text from a PDF (path or bytes) and run the pipeline."""
        return await self.process_text(extract_text_from_pdf(source), ground_truth)

    async def process_text(self, raw_text: str, ground_truth: GroundTruth) -> IntakeOutcome:
        """Run the pipeline on already-extracted invoice text."""
        extraction = await self._cascade.extract(raw_text)
        extracted = ExtractedInvoice(fields=extraction.fields, line_items=extraction.line_items)

        record = await self._resolve_ground_truth(extracted, ground_truth)
        if record is None:
            return IntakeOutcome(extracted, _unresolved(), None)

        result = self._reconciler.reconcile(extracted, record)
        if self._should_escalate(result):
            extraction = await self._cascade.repair(raw_text, self._disputed_fields(result), extraction)
            extracted = ExtractedInvoice(fields=extraction.fields, line_items=extraction.line_items)
            result = self._reconciler.reconcile(extracted, record)

        if self._learning_store is not None:
            record_confirmed_labels(self._learning_store, extracted, result)

        return IntakeOutcome(extracted, result, record)

    async def _resolve_ground_truth(self, extracted: ExtractedInvoice, ground_truth: GroundTruth) -> Optional[GroundTruthInvoice]:
        if isinstance(ground_truth, GroundTruthInvoice):
            return ground_truth

        exact = GroundTruthMatcher(ground_truth).find(extracted)
        if exact is not None or self._embedding_matcher is None:
            return exact

        # No identifier matched; fall back to the closest record by similarity.
        match = await self._embedding_matcher.find(extracted, ground_truth)
        return match.record if match else None

    def _should_escalate(self, result: ReconciliationResult) -> bool:
        return self._can_escalate and result.status != ReconciliationStatus.MATCHED

    @staticmethod
    def _disputed_fields(result: ReconciliationResult) -> Tuple[str, ...]:
        return tuple(
            comparison.field
            for comparison in result.field_comparisons
            if comparison.status in (MatchStatus.MISMATCH, MatchStatus.MISSING)
        )


def _unresolved() -> ReconciliationResult:
    return ReconciliationResult(status=ReconciliationStatus.UNRESOLVED)
