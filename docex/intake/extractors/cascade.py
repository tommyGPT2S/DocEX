"""
The extraction cascade: cheap first, expensive only when needed.

Order of operations:

1. **Heuristic pass** over the whole invoice - free and deterministic.
2. **LLM pass**, but only for *gaps* - required fields the heuristic could not
   read at all. Without those (an invoice number, a total) we cannot even match
   a ground-truth record, so they are worth one call up front.
3. Later, the pipeline calls :meth:`repair` to re-extract *specific* fields the
   reconciler flagged as wrong - again, the LLM touches only those fields.

A clean invoice costs zero LLM calls. A messy one costs one call for the gaps
plus, at most, one repair call for disputed fields.

Why there is no embedding-similarity tier between the two
--------------------------------------------------------
An embedding tier would exist to map a never-before-seen label phrasing to a
canonical field without paying for an LLM. We deliberately left it out:

* The learning loop already removes that cost. The first time a novel phrasing
  appears, the LLM resolves it and - once confirmed against ground truth - the
  heuristic learns it permanently (:mod:`docex.intake.learning`). Every later
  occurrence is then free at Tier 1. The embedding tier would only save the
  *single* LLM call on the *first* sighting.
* That saving comes with a real downside: an embedding match is a similarity
  score, not an auditable label-and-value on the page. It can confidently bind
  the wrong line to a field, and a wrong value that happens to match ground
  truth would be learned as a true alias, poisoning the heuristic.
* It also adds a hard dependency on a caller-supplied embedding model whose
  quality we cannot guarantee.

A minor, one-time cost saving is not worth a false-positive risk to a learning
loop we already built. If the heuristic cannot read a field, we go straight to
the authoritative tier.
"""

from __future__ import annotations

from typing import Optional, Tuple

from docex.intake.extractors.base import (
    ExtractionContext,
    ExtractionResult,
    FieldExtractor,
)
from docex.intake.fields import required_fields


class CascadingExtractor:
    """Runs the heuristic first and the LLM only for what it leaves behind."""

    def __init__(self, heuristic: FieldExtractor, llm: Optional[FieldExtractor] = None) -> None:
        """
        Args:
            heuristic: The Tier 1 extractor (always present).
            llm: The Tier 2 extractor, or ``None`` to run heuristic-only (for
                offline or cost-capped deployments).
        """
        self._heuristic = heuristic
        self._llm = llm

    async def extract(self, raw_text: str) -> ExtractionResult:
        """Full heuristic pass, escalating only missing required fields."""
        result = await self._heuristic.extract(
            ExtractionContext(raw_text=raw_text, target_fields=(), want_line_items=True)
        )

        gaps = self._required_gaps(result)
        if gaps and self._llm is not None:
            llm_result = await self._llm.extract(
                ExtractionContext(
                    raw_text=raw_text,
                    target_fields=gaps,
                    want_line_items=not result.line_items,
                )
            )
            result = self._merge(result, llm_result)
        return result

    async def repair(self, raw_text: str, fields: Tuple[str, ...], base: ExtractionResult) -> ExtractionResult:
        """Re-extract specific disputed fields with the LLM and merge them in.

        Returns ``base`` unchanged when there is no LLM or nothing to repair, so
        the pipeline can call this unconditionally.
        """
        if not fields or self._llm is None:
            return base
        llm_result = await self._llm.extract(
            ExtractionContext(raw_text=raw_text, target_fields=fields, want_line_items=False)
        )
        return self._merge(base, llm_result)

    @staticmethod
    def _required_gaps(result: ExtractionResult) -> Tuple[str, ...]:
        return tuple(name for name in required_fields() if name not in result.fields)

    @staticmethod
    def _merge(base: ExtractionResult, addition: ExtractionResult) -> ExtractionResult:
        """Overlay ``addition`` onto ``base``; the newer tier wins per field."""
        merged_fields = dict(base.fields)
        merged_fields.update(addition.fields)
        line_items = base.line_items or addition.line_items
        return ExtractionResult(fields=merged_fields, line_items=line_items)
