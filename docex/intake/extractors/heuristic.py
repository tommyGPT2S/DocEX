"""
Tier 1: heuristic extraction.

Free, fast, and deterministic. It scans for a field's label aliases and reads
the value that sits beside (or just below) the label, then parses each charge
line into a typed :class:`LineItem`. It resolves the great majority of fields on
well-formed invoices; whatever it leaves unresolved or low-confidence is what
the cascade escalates.

Two assumptions keep it honest, both documented in the package README:

* Labels are read longest-first and each matched label span is claimed, so
  ``tax id`` wins over ``tax`` and ``invoice date`` over ``date``.
* A charge amount is money-formatted (currency symbol, decimals, or thousands
  grouping). Bare integers such as ``Suite 400`` are never mistaken for charges.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from docex.intake.charges import ChargeType, classify_charge
from docex.intake.extractors.base import (
    ExtractionContext,
    ExtractionResult,
    FieldExtractor,
    find_typed_value,
    make_field,
)
from docex.intake.fields import FIELDS, FieldType
from docex.intake.learning import LearningStore
from docex.intake.models import ExtractedField, ExtractionTier, LineItem
from docex.intake.normalize import detect_currency, parse_amount

_SAME_LINE_CONFIDENCE = 0.9
_NEXT_LINE_CONFIDENCE = 0.7
_STRING_PENALTY = 0.05
_CURRENCY_FALLBACK_CONFIDENCE = 0.6
_NEXT_LINE_LOOKAHEAD = 2

_LABEL_SEPARATORS = " \t:#.-–"
_COLUMN_GAP = re.compile(r"\s{2,}")
_MONEY_LIKE = re.compile(
    r"[$€£]\s?\d[\d,]*(?:\.\d+)?"  # currency-symbol amounts
    r"|\d{1,3}(?:,\d{3})+(?:\.\d+)?"  # comma-grouped thousands
    r"|\d+\.\d{2}"  # plain decimal money
)
_QUANTITY_RATE = re.compile(r"(\d[\d,.]*)\s*(?:sf\s*)?(?:@|x)\s*[$€£]?\s*(\d[\d,.]*)", re.IGNORECASE)

_SUMMARY_KEYWORDS = (
    "subtotal", "total", "amount due", "balance", "payment", "prior balance",
    "grand total", "amount payable", "current charges", "tax", "vat", "gst",
    "currency", "invoice", "date", "page", "remit", "account",
)


class HeuristicExtractor(FieldExtractor):
    """Label-proximity field extraction plus charge line parsing.

    When given a :class:`~docex.intake.learning.LearningStore`, it also scans the
    labels learned from past ground-truth-confirmed invoices, so phrasings the
    LLM once discovered are now resolved here for free.
    """

    tier = ExtractionTier.HEURISTIC

    def __init__(self, learning_store: Optional[LearningStore] = None) -> None:
        self._learning_store = learning_store

    async def extract(self, context: ExtractionContext) -> ExtractionResult:
        claimed: Dict[int, List[Tuple[int, int]]] = {}
        result = ExtractionResult()

        # Claim recognised charge lines before scanning scalar fields, so a
        # field like ``tax`` reads the "Tax" summary row, not a "Real Estate
        # Tax Recovery" charge line that merely contains the word.
        charges = self._charge_lines(context.lines)
        known_charges = [(index, item) for index, item in charges if item.charge_type != ChargeType.OTHER]
        for index, _ in known_charges:
            claimed[index] = [(0, len(context.lines[index]))]

        for name in self._fields_by_label_specificity(context.target_fields):
            extracted = self._extract_field(name, context, claimed)
            if extracted:
                result.fields[name] = extracted

        if self._currency_wanted(context, result):
            currency = self._infer_currency(context.raw_text)
            if currency:
                result.fields["currency"] = currency

        if context.want_line_items:
            result.line_items = self._assemble_line_items(charges, known_charges, claimed)

        return result

    @staticmethod
    def _currency_wanted(context: ExtractionContext, result: ExtractionResult) -> bool:
        targets_currency = not context.target_fields or "currency" in context.target_fields
        return targets_currency and "currency" not in result.fields

    def _fields_by_label_specificity(self, target_fields: Tuple[str, ...]) -> List[str]:
        """Order fields so those with longer, more specific labels resolve first."""
        names = list(target_fields) or list(FIELDS)
        return sorted(names, key=lambda name: -max(len(label) for label in FIELDS[name].labels))

    def _extract_field(
        self,
        name: str,
        context: ExtractionContext,
        claimed: Dict[int, List[Tuple[int, int]]],
    ) -> Optional[ExtractedField]:
        spec = FIELDS[name]
        for label in self._labels_for(name):
            for line_index, line in enumerate(context.lines):
                span = self._match_label(line, label, claimed.get(line_index, []))
                if span is None:
                    continue
                field = self._read_value(name, spec.type, context, line_index, span, label)
                if field:
                    # Claim the whole line, not just the label span, so a generic
                    # label (e.g. "property") cannot later match a word embedded
                    # in this line's value ("Meridian Property Management").
                    claimed.setdefault(line_index, []).append((0, len(line)))
                    return field
        return None

    def _labels_for(self, name: str) -> List[str]:
        """Registry labels plus any learned for this field, longest-first."""
        labels = set(FIELDS[name].labels)
        if self._learning_store:
            labels.update(self._learning_store.learned_labels(name))
        return sorted(labels, key=len, reverse=True)

    def _match_label(self, line: str, label: str, claimed: List[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
        """Match ``label`` only when it leads the line, outside claimed spans.

        Invoice labels head a "label: value" row; requiring the label at the
        start of the (already whitespace-normalised) line stops a generic label
        like "property" from matching a word embedded in another field's value
        ("Summit Property Group").
        """
        lowered = line.lower()
        if not lowered.startswith(label):
            return None
        end = len(label)
        if self._ends_on_boundary(lowered, end) and not self._overlaps(0, end, claimed):
            return 0, end
        return None

    @staticmethod
    def _ends_on_boundary(text: str, end: int) -> bool:
        return end >= len(text) or not text[end].isalnum()

    @staticmethod
    def _overlaps(start: int, end: int, claimed: List[Tuple[int, int]]) -> bool:
        return any(start < c_end and c_start < end for c_start, c_end in claimed)

    def _read_value(
        self,
        name: str,
        field_type: FieldType,
        context: ExtractionContext,
        line_index: int,
        span: Tuple[int, int],
        label: str,
    ) -> Optional[ExtractedField]:
        tail = context.lines[line_index][span[1]:].lstrip(_LABEL_SEPARATORS)
        if field_type == FieldType.STRING:
            tail = _COLUMN_GAP.split(tail, maxsplit=1)[0]

        value, raw = find_typed_value(field_type, tail)
        if value is not None:
            confidence = _SAME_LINE_CONFIDENCE - (_STRING_PENALTY if field_type == FieldType.STRING else 0.0)
            return make_field(name, value, self.tier, confidence, raw, label)

        return self._read_following_lines(name, field_type, context, line_index, label)

    def _read_following_lines(
        self,
        name: str,
        field_type: FieldType,
        context: ExtractionContext,
        line_index: int,
        label: str,
    ) -> Optional[ExtractedField]:
        for offset in range(1, _NEXT_LINE_LOOKAHEAD + 1):
            next_index = line_index + offset
            if next_index >= len(context.lines):
                break
            candidate = context.lines[next_index]
            if field_type == FieldType.STRING:
                candidate = _COLUMN_GAP.split(candidate, maxsplit=1)[0]
            value, raw = find_typed_value(field_type, candidate)
            if value is not None:
                return make_field(name, value, self.tier, _NEXT_LINE_CONFIDENCE, raw, label)
        return None

    def _infer_currency(self, raw_text: str) -> Optional[ExtractedField]:
        currency = detect_currency(raw_text)
        if not currency:
            return None
        return make_field("currency", currency, self.tier, _CURRENCY_FALLBACK_CONFIDENCE, None)

    def _charge_lines(self, lines: List[str]) -> List[Tuple[int, LineItem]]:
        """Every line that parses as a charge, paired with its line index."""
        charges = []
        for index, line in enumerate(lines):
            item = self._parse_charge_line(line)
            if item:
                charges.append((index, item))
        return charges

    @staticmethod
    def _assemble_line_items(
        charges: List[Tuple[int, LineItem]],
        known_charges: List[Tuple[int, LineItem]],
        claimed: Dict[int, List[Tuple[int, int]]],
    ) -> List[LineItem]:
        """Recognised charges, plus unknown charges from lines no field claimed.

        A line a scalar field consumed (a labelled "Pro Rata Share" or
        "Rentable Square Feet" row) is excluded here so it is never also
        reported as a phantom charge.
        """
        items = [item for _, item in known_charges]
        items.extend(
            item
            for index, item in charges
            if item.charge_type == ChargeType.OTHER and index not in claimed
        )
        return items

    def _parse_charge_line(self, line: str) -> Optional[LineItem]:
        money_matches = list(_MONEY_LIKE.finditer(line))
        if not money_matches:
            return None

        amount_match = money_matches[-1]
        description = line[: amount_match.start()].strip(" \t:-")
        if not description:
            return None

        charge_type = classify_charge(description)
        if charge_type.value == "other" and self._is_summary_line(description):
            return None

        quantity, unit_price = self._parse_quantity_rate(description)
        return LineItem(
            description=description,
            charge_type=charge_type,
            quantity=quantity,
            unit_price=unit_price,
            amount=parse_amount(amount_match.group(0)),
            confidence=0.8,
        )

    @staticmethod
    def _is_summary_line(description: str) -> bool:
        lowered = description.lower()
        return any(keyword in lowered for keyword in _SUMMARY_KEYWORDS)

    @staticmethod
    def _parse_quantity_rate(description: str):
        match = _QUANTITY_RATE.search(description)
        if not match:
            return None, None
        return parse_amount(match.group(1)), parse_amount(match.group(2))
