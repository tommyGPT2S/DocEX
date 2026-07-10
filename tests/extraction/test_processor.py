"""End-to-end: add a document, run the processor, verify the stored metadata."""

import json

from docex.extraction.config import ExtractionConfig
from docex.extraction.processor import FieldExtractionProcessor

FIELDS = {
    'invoice_number': {'type': 'text', 'labels': ['Invoice No.']},
    'invoice_date': {'type': 'date', 'labels': ['Invoice Date']},
    'total': {'type': 'money', 'labels': ['Total Due', 'Amount Due']},
    'vendor': {'type': 'text', 'labels': ['Remit To']},
}

CLEAN_INVOICE = """ACME PROPERTY MANAGEMENT LLC
Invoice No.: 2024-0042
Invoice Date: 07/03/2025
Remit To: Acme Property Management LLC
Total Due: $12,500.00
"""

# 'Tot' is not a configured label; only the LLM fallback can resolve the total.
ABBREVIATED_INVOICE = """ACME PROPERTY MANAGEMENT LLC
Invoice No.: 2024-0043
Invoice Date: 07/04/2025
Remit To: Acme Property Management LLC
Tot: $9,100.00
"""


def add_document(basket, tmp_path, name, content):
    file_path = tmp_path / name
    file_path.write_text(content)
    return basket.add(str(file_path))


def make_processor(**kwargs):
    return FieldExtractionProcessor(
        extraction_config=ExtractionConfig.from_dict(FIELDS), **kwargs
    )


def test_rules_only_document_fully_extracted(basket, tmp_path):
    doc = add_document(basket, tmp_path, 'clean_invoice.txt', CLEAN_INVOICE)
    result = make_processor().process(doc)

    assert result.success
    metadata = doc.get_metadata()
    assert metadata['invoice_number'] == '2024-0042'
    assert metadata['invoice_date'] == '2025-07-03'
    assert metadata['total'] == '12500.00'
    assert metadata['vendor'] == 'Acme Property Management LLC'
    assert metadata['total_source'] == 'regex'
    assert metadata['total_source_label'] == 'Total Due'
    assert metadata['needs_review'] == 'false'


def test_llm_fallback_used_only_for_missing_fields(basket, tmp_path):
    doc = add_document(basket, tmp_path, 'abbreviated_invoice.txt', ABBREVIATED_INVOICE)

    requested = []

    def fake_llm(prompt):
        requested.append(prompt)
        return json.dumps({'fields': {'total': {'value': '$9,100.00', 'label': 'Tot'}}})

    result = make_processor(llm_fn=fake_llm).process(doc)

    assert result.success
    metadata = doc.get_metadata()
    assert metadata['total'] == '9100.00'
    assert metadata['total_source'] == 'llm'
    assert metadata['total_source_label'] == 'Tot'
    assert metadata['needs_review'] == 'false'
    # Exactly one LLM call, asking only for the field the rules missed.
    assert len(requested) == 1
    assert 'total' in requested[0]
    assert 'invoice_number' not in requested[0]


def test_missing_field_flags_document_for_review(basket, tmp_path):
    doc = add_document(basket, tmp_path, 'incomplete_invoice.txt', ABBREVIATED_INVOICE)
    # No LLM provided: the abbreviated total cannot be resolved by rules.
    result = make_processor().process(doc)

    assert result.success
    metadata = doc.get_metadata()
    assert 'total' not in metadata
    assert metadata['needs_review'] == 'true'


def test_flagged_documents_findable_by_metadata_search(basket, tmp_path):
    matches = basket.find_documents_by_metadata({'needs_review': 'true'})
    assert any(m.name == 'incomplete_invoice.txt' for m in matches)
