"""
Field extraction strategies, ordered cheapest-first by the cascade.

There are deliberately only two tiers: a free, deterministic heuristic and a
paid LLM fallback. We considered an intermediate embedding-similarity tier and
chose not to build it - see :mod:`docex.intake.extractors.cascade` for the
rationale (the learning loop already makes it redundant and it carries a
false-positive risk the cascade cannot cheaply audit).
"""

from docex.intake.extractors.base import ExtractionContext, FieldExtractor
from docex.intake.extractors.cascade import CascadingExtractor
from docex.intake.extractors.heuristic import HeuristicExtractor
from docex.intake.extractors.llm import LLMExtractor

__all__ = [
    "ExtractionContext",
    "FieldExtractor",
    "HeuristicExtractor",
    "LLMExtractor",
    "CascadingExtractor",
]
