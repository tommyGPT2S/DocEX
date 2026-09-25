"""
Fallback tier: LLM extraction for fields the rules missed.

The caller supplies a plain callable (``llm_fn``) that maps a prompt string to
a response string, following the same bring-your-own-provider pattern DocEX
uses for embedding functions. The package contains no provider SDK and makes
no network calls of its own.

The prompt is built from the same :class:`ExtractionConfig` the rules tier
uses: only configured fields are requested, the configured label phrases are
given as hints, and the model is told to also consider synonyms,
abbreviations, and acronyms of those phrases. For traceability the model must
return, per field, the exact label text as printed in the document; a value
whose claimed label does not actually appear in the text is rejected, and
every accepted value passes the same type validation as the rules tier.
"""

import json
import re
from typing import Callable, Dict, List

from docex.extraction.engine import FOUND, SOURCE_LLM, FieldResult, normalize_value
from docex.extraction.config import FieldSpec

LLMFn = Callable[[str], str]

_JSON_BLOCK = re.compile(r'\{.*\}', re.DOTALL)


def build_prompt(text: str, specs: List[FieldSpec]) -> str:
    """Build the extraction prompt for the fields the rules tier could not find."""
    field_lines = '\n'.join(
        f"- {spec.name} (type: {spec.type}), usually labelled: {', '.join(spec.labels)}"
        for spec in specs
    )
    return (
        "Extract the following fields from the document text below.\n"
        "The fields may appear under different wording than the labels listed, "
        "including synonyms, abbreviations, or acronyms (for example 'Tot' or "
        "'Amt Due' for a total). Search for those variations too.\n\n"
        "Return ONLY minified JSON, no prose, in exactly this shape:\n"
        '{"fields": {"<field_name>": {"value": "<value>", "label": "<label text exactly as printed>"}}}\n'
        "Use null for any field you cannot find. The label must be copied "
        "character-for-character from the document text.\n\n"
        f"Fields to extract:\n{field_lines}\n\n"
        f"Document text:\n{text}"
    )


def extract_missing(llm_fn: LLMFn, text: str, specs: List[FieldSpec]) -> Dict[str, FieldResult]:
    """Ask the LLM for the given fields. Returns results only for verified finds.

    A field is accepted only if the model returned both a value and a label,
    the label actually occurs in the document text, and the value passes the
    field's type validation. Everything else stays missing.
    """
    if not specs:
        return {}

    response = llm_fn(build_prompt(text, specs))
    if not isinstance(response, str):
        raise ValueError("llm_fn must return a string response")

    match = _JSON_BLOCK.search(response)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}

    fields = data.get('fields')
    if not isinstance(fields, dict):
        return {}

    lowered_text = text.lower()
    results: Dict[str, FieldResult] = {}
    for spec in specs:
        entry = fields.get(spec.name)
        if not isinstance(entry, dict):
            continue
        value, label = entry.get('value'), entry.get('label')
        if value in (None, '') or not isinstance(label, str) or not label.strip():
            continue
        if label.strip().lower() not in lowered_text:
            # The model claimed a label that is not in the document; do not trust the value.
            continue
        normalized = normalize_value(spec.type, str(value))
        if normalized is None:
            continue
        results[spec.name] = FieldResult(spec.name, FOUND, normalized, label.strip(), SOURCE_LLM)
    return results
