"""LLM fallback tier, tested with fake llm_fn callables (no network, no keys)."""

import json

import pytest

from docex.extraction.config import ExtractionConfig
from docex.extraction.llm import build_prompt, extract_missing

SPECS = ExtractionConfig.from_dict({
    'total': {'type': 'money', 'labels': ['Total Due', 'Amount Due']},
    'vendor': {'type': 'text', 'labels': ['Remit To']},
}).fields

TEXT = "Acme Property Management LLC\nTot: $12,500.00\nThank you for your business"


def fake_llm(response):
    """Build a fake llm_fn returning a canned response, recording the prompt it got."""
    calls = []

    def llm_fn(prompt):
        calls.append(prompt)
        return response

    llm_fn.calls = calls
    return llm_fn


def test_accepts_value_with_verified_label():
    # The model matched the abbreviation "Tot" -- present in the text, so trusted.
    llm = fake_llm(json.dumps({'fields': {'total': {'value': '$12,500.00', 'label': 'Tot'}}}))
    results = extract_missing(llm, TEXT, [SPECS[0]])
    assert results['total'].value == '12500.00'
    assert results['total'].source == 'llm'
    assert results['total'].label == 'Tot'


def test_rejects_value_whose_label_is_not_in_document():
    llm = fake_llm(json.dumps({'fields': {'total': {'value': '999.99', 'label': 'Grand Total'}}}))
    assert extract_missing(llm, TEXT, [SPECS[0]]) == {}


def test_rejects_value_failing_type_validation():
    llm = fake_llm(json.dumps({'fields': {'total': {'value': 'twelve thousand', 'label': 'Tot'}}}))
    assert extract_missing(llm, TEXT, [SPECS[0]]) == {}


def test_null_and_garbage_responses_yield_nothing():
    assert extract_missing(fake_llm(json.dumps({'fields': {'total': None}})), TEXT, [SPECS[0]]) == {}
    assert extract_missing(fake_llm('not json at all'), TEXT, [SPECS[0]]) == {}


def test_no_call_made_when_nothing_is_missing():
    llm = fake_llm('{}')
    assert extract_missing(llm, TEXT, []) == {}
    assert llm.calls == []


def test_prompt_contains_only_requested_fields_with_labels_and_types():
    prompt = build_prompt(TEXT, [SPECS[0]])
    assert 'total' in prompt and 'money' in prompt
    assert 'Total Due' in prompt and 'Amount Due' in prompt
    assert 'vendor' not in prompt
    assert 'abbreviation' in prompt  # synonym/abbreviation/acronym instruction present
    assert TEXT in prompt


def test_non_string_response_raises():
    with pytest.raises(ValueError):
        extract_missing(lambda prompt: 12345, TEXT, [SPECS[0]])
