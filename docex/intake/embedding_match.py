"""
Find the ground-truth record an invoice most likely belongs to, by embedding
similarity.

:class:`~docex.intake.reconcile.GroundTruthMatcher` matches on a stable
identifier (invoice number, then PO). That is the right default - exact and
auditable - but it cannot help when the incoming invoice has no clean identifier
to match on: a typo in the invoice number, a vendor using their own numbering,
or a field the extractor simply could not read.

This matcher fills that gap. It embeds a short fingerprint of each ground-truth
record (tenant, property, suite, lease, totals, charge descriptions) and the
same fingerprint of the extracted invoice, and ranks records by cosine
similarity. It is a *retrieval* aid, not a verdict: the pipeline still reconciles
against whatever record this returns, so a wrong guess shows up as a discrepancy
rather than being silently trusted - which is exactly why embeddings are safe
here and were left out of field extraction.

The embedding function is caller-provided (sync or async), the same one you
would use for DocEX vector indexing. Record embeddings are cached by record id,
so the cost is one embedding per record per process, not per invoice.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, List, Optional, Union

from docex.intake.ground_truth import GroundTruthInvoice, GroundTruthStore
from docex.intake.models import ExtractedInvoice

EmbeddingFn = Callable[[str], Union[List[float], Awaitable[List[float]]]]

_FINGERPRINT_FIELDS = (
    "invoice_number",
    "po_number",
    "landlord_name",
    "tenant_name",
    "tenant_account",
    "property_name",
    "property_address",
    "suite_number",
    "lease_number",
    "total",
)
_DEFAULT_THRESHOLD = 0.8


@dataclass
class GroundTruthMatch:
    """A candidate ground-truth record and its similarity to the invoice."""

    record: GroundTruthInvoice
    score: float


def ground_truth_fingerprint(record: GroundTruthInvoice) -> str:
    """The text an embedding model sees for a ground-truth record."""
    parts = [str(record.get(name)) for name in _FINGERPRINT_FIELDS if record.get(name) is not None]
    parts.extend(item.description for item in record.line_items if item.description)
    return " ".join(parts)


def extracted_fingerprint(extracted: ExtractedInvoice) -> str:
    """The matching fingerprint for an extracted invoice."""
    parts = [str(extracted.value(name)) for name in _FINGERPRINT_FIELDS if extracted.value(name) is not None]
    parts.extend(item.description for item in extracted.line_items if item.description)
    return " ".join(parts)


class EmbeddingGroundTruthMatcher:
    """Ranks ground-truth records by embedding similarity to an invoice."""

    def __init__(self, embedding_fn: EmbeddingFn, threshold: float = _DEFAULT_THRESHOLD) -> None:
        """
        Args:
            embedding_fn: Sync or async callable mapping text to an embedding.
            threshold: Minimum cosine similarity for :meth:`find` to accept a
                match. :meth:`candidates` ignores it and returns a ranked list.
        """
        if not callable(embedding_fn):
            raise ValueError("embedding_fn is required and must be callable")
        self._embedding_fn = embedding_fn
        self._threshold = threshold
        self._cache: Dict[str, List[float]] = {}

    async def find(self, extracted: ExtractedInvoice, store: GroundTruthStore) -> Optional[GroundTruthMatch]:
        """Return the single best match above the threshold, or ``None``."""
        ranked = await self.candidates(extracted, store, top_k=1)
        best = ranked[0] if ranked else None
        return best if best and best.score >= self._threshold else None

    async def candidates(
        self,
        extracted: ExtractedInvoice,
        store: GroundTruthStore,
        top_k: int = 5,
    ) -> List[GroundTruthMatch]:
        """Return up to ``top_k`` records ranked by similarity, best first."""
        fingerprint = extracted_fingerprint(extracted)
        if not fingerprint:
            return []

        query = await self._embed(fingerprint)
        scored = [
            GroundTruthMatch(record=record, score=_cosine(query, await self._record_vector(record)))
            for record in store.all()
        ]
        scored.sort(key=lambda match: match.score, reverse=True)
        return scored[:top_k]

    async def _record_vector(self, record: GroundTruthInvoice) -> List[float]:
        if record.id is not None and record.id in self._cache:
            return self._cache[record.id]
        vector = await self._embed(ground_truth_fingerprint(record))
        if record.id is not None:
            self._cache[record.id] = vector
        return vector

    async def _embed(self, text: str) -> List[float]:
        embedding = self._embedding_fn(text)
        if inspect.isawaitable(embedding):
            embedding = await embedding
        if not isinstance(embedding, list) or not embedding:
            raise ValueError("embedding_fn must return a non-empty list of floats")
        return [float(value) for value in embedding]


def _cosine(left: List[float], right: List[float]) -> float:
    """Cosine similarity of two equal-length vectors, 0.0 when either is zero."""
    dot = sum(a * b for a, b in zip(left, right))
    norm_left = sum(a * a for a in left) ** 0.5
    norm_right = sum(b * b for b in right) ** 0.5
    return dot / (norm_left * norm_right) if norm_left and norm_right else 0.0
