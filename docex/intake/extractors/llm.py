"""
Tier 2 (last resort): LLM extraction.

Invoked only on the fields the heuristic could not resolve or that reconciled
badly - never on a whole invoice that already parsed cleanly. The model is
caller-provided (``llm_fn``), exactly like the embedding function pattern
elsewhere in DocEX, so the core package takes no hard dependency on any provider
SDK. See ``examples/`` for a concrete Claude adapter.

The prompt asks the model to return, for each field, both the value and the
*label phrase as printed on the invoice*. That label feeds the learning loop:
once a novel phrasing is confirmed against ground truth, the free heuristic tier
learns it and this expensive tier is not needed for it again.
"""

from __future__ import annotations

import inspect
import json
import re
from typing import Awaitable, Callable, Dict, List, Optional, Tuple, Union

from docex.intake.charges import classify_charge
from docex.intake.extractors.base import (
    ExtractionContext,
    ExtractionResult,
    FieldExtractor,
    make_field,
)
from docex.intake.fields import FIELDS
from docex.intake.models import ExtractionTier, LineItem
from docex.intake.normalize import parse_amount, parse_value

LLMFn = Callable[[str], Union[str, Awaitable[str]]]

_LLM_CONFIDENCE = 0.95
_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


class LLMExtractor(FieldExtractor):
    """Extracts fields by prompting a caller-provided language model."""

    tier = ExtractionTier.LLM

    def __init__(self, llm_fn: LLMFn) -> None:
        if not callable(llm_fn):
            raise ValueError("llm_fn is required and must be callable")
        self._llm_fn = llm_fn

    async def extract(self, context: ExtractionContext) -> ExtractionResult:
        targets = context.target_fields or tuple(FIELDS)
        prompt = self._build_prompt(context.raw_text, targets, context.want_line_items)
        response = await self._call(prompt)
        data = self._parse_response(response)
        if data is None:
            return ExtractionResult()

        result = ExtractionResult()
        for name, entry in self._extracted_fields(data, targets):
            result.fields[name] = entry
        if context.want_line_items:
            result.line_items = self._extracted_line_items(data)
        return result

    def _build_prompt(self, raw_text: str, targets: Tuple[str, ...], want_line_items: bool) -> str:
        field_lines = "\n".join(
            f"- {name} ({FIELDS[name].type.value}): the invoice's {name.replace('_', ' ')}"
            for name in targets
        )
        line_item_clause = (
            '\n  "line_items": [{"description": "...", "amount": "..."}],' if want_line_items else ""
        )
        return (
            "You extract fields from a commercial real estate invoice.\n"
            "Return ONLY minified JSON, no prose, in this exact shape:\n"
            "{\n"
            '  "fields": {"<field_name>": {"value": "...", "label": "<the label text as printed>"}},'
            f"{line_item_clause}\n"
            "}\n"
            "Use null for any field you cannot find. The 'label' is the heading or caption that "
            "sits next to the value on the page; it is how we learn new invoice formats.\n\n"
            f"Fields to extract:\n{field_lines}\n\n"
            f"Invoice text:\n{raw_text}"
        )

    async def _call(self, prompt: str) -> str:
        response = self._llm_fn(prompt)
        if inspect.isawaitable(response):
            response = await response
        if not isinstance(response, str):
            raise ValueError("llm_fn must return a JSON string (or an awaitable that resolves to one)")
        return response

    def _parse_response(self, response: str) -> Optional[Dict]:
        match = _JSON_BLOCK.search(response)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    def _extracted_fields(self, data: Dict, targets: Tuple[str, ...]):
        fields = data.get("fields", {})
        if not isinstance(fields, dict):
            return
        for name in targets:
            entry = fields.get(name)
            value = self._normalize_entry(name, entry)
            if value is not None:
                label = entry.get("label") if isinstance(entry, dict) else None
                yield name, make_field(name, value, self.tier, _LLM_CONFIDENCE, _raw(entry), label)

    def _normalize_entry(self, name: str, entry) -> Optional[object]:
        raw = entry.get("value") if isinstance(entry, dict) else entry
        if raw is None or raw == "":
            return None
        return parse_value(FIELDS[name].type, str(raw))

    def _extracted_line_items(self, data: Dict) -> List[LineItem]:
        raw_items = data.get("line_items", [])
        if not isinstance(raw_items, list):
            return []
        items = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            description = (raw.get("description") or "").strip()
            amount = parse_amount(str(raw.get("amount", "")))
            if not description and amount is None:
                continue
            items.append(
                LineItem(
                    description=description or None,
                    charge_type=classify_charge(description),
                    amount=amount,
                    confidence=_LLM_CONFIDENCE,
                )
            )
        return items


def _raw(entry) -> Optional[str]:
    if isinstance(entry, dict):
        value = entry.get("value")
        return str(value) if value is not None else None
    return str(entry) if entry is not None else None
