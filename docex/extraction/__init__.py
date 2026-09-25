"""
Configurable field extraction for DocEX documents.

Fields are declared as label phrases plus a type (money, date, text) -- see
:mod:`docex.extraction.config`. A rules tier finds and validates values for
free; an optional caller-provided LLM handles only the fields the rules miss.
Results are stored as document metadata with full traceability of how each
value was found.
"""

from docex.extraction.config import ExtractionConfig, FieldSpec
from docex.extraction.engine import (
    CONFLICT,
    FOUND,
    NOT_FOUND,
    FieldResult,
    RulesEngine,
)
from docex.extraction.llm import LLMFn, build_prompt, extract_missing
from docex.extraction.processor import FieldExtractionProcessor

__all__ = [
    'ExtractionConfig',
    'FieldSpec',
    'FieldResult',
    'RulesEngine',
    'FieldExtractionProcessor',
    'LLMFn',
    'build_prompt',
    'extract_missing',
    'FOUND',
    'NOT_FOUND',
    'CONFLICT',
]
