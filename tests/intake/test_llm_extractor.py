"""The LLM tier.

Two layers of coverage:

* Deterministic stub tests that run everywhere (CI included) and pin down the
  contract: JSON parsing, value normalization, label capture, line items.
* A live test against Claude, skipped unless ``ANTHROPIC_API_KEY`` is set, that
  proves the real model produces output the extractor can consume.
"""

import json
import os
from datetime import date
from decimal import Decimal

import pytest

from docex.intake.charges import ChargeType
from docex.intake.extractors.base import ExtractionContext
from docex.intake.extractors.llm import LLMExtractor
from docex.intake.models import ExtractionTier


def _stub(payload):
    def llm_fn(prompt):
        return json.dumps(payload)

    return llm_fn


def test_extracts_fields_with_value_and_label(run):
    payload = {
        "fields": {
            "total": {"value": "$4,200.00", "label": "Net Payable This Cycle"},
            "invoice_number": {"value": "INV-9", "label": "Invoice Number"},
        }
    }
    result = run(LLMExtractor(_stub(payload)).extract(ExtractionContext(raw_text="...", target_fields=("total", "invoice_number"))))

    assert result.fields["total"].value == Decimal("4200.00")
    assert result.fields["total"].label == "Net Payable This Cycle"
    assert result.fields["total"].tier == ExtractionTier.LLM
    assert result.fields["invoice_number"].value == "INV-9"


def test_normalizes_typed_values(run):
    payload = {"fields": {"invoice_date": {"value": "January 15, 2024", "label": "Date"}}}
    result = run(LLMExtractor(_stub(payload)).extract(ExtractionContext(raw_text="...", target_fields=("invoice_date",))))
    assert result.fields["invoice_date"].value == date(2024, 1, 15)


def test_parses_line_items(run):
    payload = {
        "fields": {},
        "line_items": [
            {"description": "Base Rent", "amount": "$10,000.00"},
            {"description": "CAM", "amount": "$1,200.00"},
        ],
    }
    result = run(LLMExtractor(_stub(payload)).extract(ExtractionContext(raw_text="...", target_fields=("total",), want_line_items=True)))
    assert {item.charge_type for item in result.line_items} == {ChargeType.BASE_RENT, ChargeType.CAM}


def test_tolerates_prose_around_json(run):
    def llm_fn(prompt):
        return 'Sure:\n{"fields": {"total": {"value": "100.00", "label": "Total"}}}\nHope that helps!'

    result = run(LLMExtractor(llm_fn).extract(ExtractionContext(raw_text="...", target_fields=("total",))))
    assert result.fields["total"].value == Decimal("100.00")


def test_returns_empty_on_unparseable_response(run):
    result = run(LLMExtractor(lambda prompt: "no json here").extract(ExtractionContext(raw_text="...", target_fields=("total",))))
    assert result.fields == {}


def test_supports_async_llm(run):
    async def llm_fn(prompt):
        return json.dumps({"fields": {"total": {"value": "50.00", "label": "Total"}}})

    result = run(LLMExtractor(llm_fn).extract(ExtractionContext(raw_text="...", target_fields=("total",))))
    assert result.fields["total"].value == Decimal("50.00")


def test_null_values_are_skipped(run):
    payload = {"fields": {"total": {"value": None, "label": "Total"}, "po_number": {"value": "PO-1", "label": "PO"}}}
    result = run(LLMExtractor(_stub(payload)).extract(ExtractionContext(raw_text="...", target_fields=("total", "po_number"))))
    assert "total" not in result.fields
    assert result.fields["po_number"].value == "PO-1"


_LIVE_INVOICE = """
HARBOR POINT TOWER - Monthly Rent Statement
Invoice Number: INV-2024-0042
Bill To: Acme Retail LLC
Suite: 1200
Base Rent                          $20,833.33
Common Area Maintenance            $5,000.00
Real Estate Tax Recovery           $1,250.00
Total Amount Due                   $27,083.33
"""


@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set; skipping live LLM test")
def test_live_claude_extraction(run):
    """End-to-end against a real Claude model (Haiku, to keep the call cheap)."""
    anthropic = pytest.importorskip("anthropic")
    client = anthropic.Anthropic()

    def llm_fn(prompt: str) -> str:
        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in message.content if block.type == "text")

    result = run(
        LLMExtractor(llm_fn).extract(
            ExtractionContext(raw_text=_LIVE_INVOICE, target_fields=("invoice_number", "total"), want_line_items=False)
        )
    )

    assert result.fields["invoice_number"].value == "INV-2024-0042"
    assert abs(result.fields["total"].value - Decimal("27083.33")) <= Decimal("0.01")
