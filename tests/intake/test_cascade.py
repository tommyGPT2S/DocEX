"""The cascade: heuristic first, LLM only for gaps, repair on demand."""

import json
from decimal import Decimal

from docex.intake.extractors.cascade import CascadingExtractor
from docex.intake.extractors.heuristic import HeuristicExtractor
from docex.intake.extractors.llm import LLMExtractor
from docex.intake.models import ExtractionTier


def _llm(payload):
    return LLMExtractor(lambda prompt: json.dumps(payload))


def test_heuristic_only_leaves_required_gaps(run):
    cascade = CascadingExtractor(HeuristicExtractor())  # no LLM
    result = run(cascade.extract("Invoice Number: INV-1\nMystery line with no total"))
    assert "total" not in result.fields


def test_llm_fills_a_required_gap(run):
    cascade = CascadingExtractor(
        HeuristicExtractor(),
        _llm({"fields": {"total": {"value": "$500.00", "label": "Net Payable"}}}),
    )
    # "Net Payable" is not a label the heuristic knows, so total is a gap.
    result = run(cascade.extract("Invoice Number: INV-1\nNet Payable: $500.00"))
    assert result.fields["total"].value == Decimal("500.00")
    assert result.fields["total"].tier == ExtractionTier.LLM
    assert result.fields["invoice_number"].tier == ExtractionTier.HEURISTIC


def test_no_llm_call_when_required_fields_present(run):
    def explode(prompt):
        raise AssertionError("LLM must not be called when the heuristic resolved all required fields")

    cascade = CascadingExtractor(HeuristicExtractor(), LLMExtractor(explode))
    result = run(cascade.extract("Invoice Number: INV-1\nTotal Amount Due: $500.00"))
    assert result.fields["total"].tier == ExtractionTier.HEURISTIC


def test_repair_overrides_disputed_field(run):
    cascade = CascadingExtractor(
        HeuristicExtractor(),
        _llm({"fields": {"total": {"value": "$999.00", "label": "Total"}}}),
    )
    base = run(cascade.extract("Invoice Number: INV-1\nTotal Amount Due: $100.00"))
    assert base.fields["total"].value == Decimal("100.00")

    repaired = run(cascade.repair("...", ("total",), base))
    assert repaired.fields["total"].value == Decimal("999.00")
    assert repaired.fields["total"].tier == ExtractionTier.LLM


def test_repair_is_noop_without_llm(run):
    cascade = CascadingExtractor(HeuristicExtractor())
    base = run(cascade.extract("Invoice Number: INV-1\nTotal Amount Due: $100.00"))
    assert run(cascade.repair("...", ("total",), base)) is base
