"""Rules engine: label matching, type validation, normalization, conflicts."""

from docex.extraction.config import ExtractionConfig
from docex.extraction.engine import CONFLICT, FOUND, NOT_FOUND, RulesEngine


def make_engine(fields):
    return RulesEngine(ExtractionConfig.from_dict(fields))


def test_value_on_same_line():
    engine = make_engine({'total': {'type': 'money', 'labels': ['Total Due']}})
    results = engine.extract("Invoice\nTotal Due: $12,500.00\nThank you")
    assert results['total'].status == FOUND
    assert results['total'].value == '12500.00'
    assert results['total'].label == 'Total Due'
    assert results['total'].source == 'regex'


def test_value_on_next_line():
    engine = make_engine({'total': {'type': 'money', 'labels': ['Amount Due']}})
    results = engine.extract("Amount Due\n$3,200.50")
    assert results['total'].status == FOUND
    assert results['total'].value == '3200.50'


def test_conflicting_values_flagged_not_guessed():
    engine = make_engine({'total': {'type': 'money', 'labels': ['Total Due', 'Balance Due']}})
    results = engine.extract("Total Due: $100.00\nBalance Due: $200.00")
    assert results['total'].status == CONFLICT
    assert results['total'].value is None


def test_same_value_under_two_labels_is_not_a_conflict():
    engine = make_engine({'total': {'type': 'money', 'labels': ['Total Due', 'Balance Due']}})
    results = engine.extract("Total Due: $100.00\nBalance Due: $100.00")
    assert results['total'].status == FOUND
    assert results['total'].value == '100.00'


def test_garbled_money_rejected():
    # Scanner artifact: letter O instead of zeros. Must not be stored as a number.
    engine = make_engine({'total': {'type': 'money', 'labels': ['Total Due']}})
    results = engine.extract("Total Due: $12,5OO")
    assert results['total'].status == NOT_FOUND


def test_date_normalized_to_iso():
    engine = make_engine({'invoice_date': {'type': 'date', 'labels': ['Invoice Date']}})
    results = engine.extract("Invoice Date: 07/03/2025")
    assert results['invoice_date'].value == '2025-07-03'


def test_impossible_date_rejected():
    engine = make_engine({'invoice_date': {'type': 'date', 'labels': ['Invoice Date']}})
    results = engine.extract("Invoice Date: 13/45/2025")
    assert results['invoice_date'].status == NOT_FOUND


def test_label_requires_word_boundary():
    # "Subtotal" must not match the label "Total".
    engine = make_engine({'total': {'type': 'money', 'labels': ['Total']}})
    results = engine.extract("Subtotal: $99.00\nTotal: $150.00")
    assert results['total'].status == FOUND
    assert results['total'].value == '150.00'


def test_longer_label_wins_on_same_span():
    # "Due Date" (due_date) must suppress "Date" (invoice_date) on its line.
    engine = make_engine({
        'invoice_date': {'type': 'date', 'labels': ['Date']},
        'due_date': {'type': 'date', 'labels': ['Due Date']},
    })
    results = engine.extract("Due Date: 08/01/2025\nDate: 07/03/2025")
    assert results['due_date'].value == '2025-08-01'
    assert results['invoice_date'].status == FOUND
    assert results['invoice_date'].value == '2025-07-03'


def test_text_field_extracted_and_missing_field_reported():
    engine = make_engine({
        'vendor': {'type': 'text', 'labels': ['Remit To']},
        'cam': {'type': 'money', 'labels': ['CAM']},
    })
    results = engine.extract("Remit To: Acme Property Management LLC")
    assert results['vendor'].status == FOUND
    assert results['vendor'].value == 'Acme Property Management LLC'
    assert results['cam'].status == NOT_FOUND
