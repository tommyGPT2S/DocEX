"""Tier 1 extraction across the layouts and traps real invoices contain."""

from decimal import Decimal

from docex.intake.charges import ChargeType
from docex.intake.extractors.base import ExtractionContext
from docex.intake.extractors.heuristic import HeuristicExtractor


def extract(text: str, run):
    return run(HeuristicExtractor().extract(ExtractionContext(raw_text=text, target_fields=())))


def test_reads_labelled_colon_values(run):
    text = "Invoice Number: INV-7\nTotal Amount Due: $1,500.00\nSuite: 400"
    result = extract(text, run)
    assert result.fields["invoice_number"].value == "INV-7"
    assert result.fields["total"].value == Decimal("1500.00")
    assert result.fields["suite_number"].value == "400"


def test_reads_value_on_following_line(run):
    text = "Invoice Number\nINV-42\nAmount Due\n$2,000.00"
    result = extract(text, run)
    assert result.fields["invoice_number"].value == "INV-42"
    assert result.fields["total"].value == Decimal("2000.00")


def test_scalar_tax_ignores_real_estate_tax_charge_line(run):
    text = (
        "Invoice Number: INV-1\n"
        "Real Estate Tax Recovery            $1,250.00\n"
        "Tax                                 $0.00\n"
        "Total Amount Due                    $5,000.00\n"
    )
    result = extract(text, run)
    assert result.fields["tax"].value == Decimal("0.00")  # not the 1,250 charge line


def test_labelled_metric_lines_are_not_phantom_charges(run):
    text = (
        "Invoice Number: INV-1\n"
        "Rentable Square Feet: 12,500\n"
        "Pro Rata Share: 8.25%\n"
        "Base Rent                           $10,000.00\n"
        "Total Amount Due                    $10,000.00\n"
    )
    result = extract(text, run)
    assert result.fields["rentable_square_feet"].value == Decimal("12500")
    assert result.fields["pro_rata_share"].value == Decimal("8.25")
    charge_types = {item.charge_type for item in result.line_items}
    assert charge_types == {ChargeType.BASE_RENT}  # no OTHER phantoms from the metric rows


def test_specific_label_beats_generic_one(run):
    # "Tax ID" must not be read as the "tax" amount.
    text = "Invoice Number: INV-1\nTax ID: 99-1234567\nTax: $50.00\nTotal Amount Due: $100.00"
    result = extract(text, run)
    assert result.fields["landlord_tax_id"].value == "99-1234567"
    assert result.fields["tax"].value == Decimal("50.00")


def test_currency_inferred_from_symbol_when_unlabelled(run):
    text = "Invoice Number: INV-1\nTotal Amount Due: $1,000.00"
    result = extract(text, run)
    assert result.fields["currency"].value == "USD"


def test_unknown_charge_line_kept_as_other(run):
    text = (
        "Invoice Number: INV-1\n"
        "Holiday Decoration Fee              $500.00\n"
        "Total Amount Due                    $500.00\n"
    )
    result = extract(text, run)
    other = [item for item in result.line_items if item.charge_type == ChargeType.OTHER]
    assert len(other) == 1
    assert other[0].amount == Decimal("500.00")


def test_extracted_fields_carry_label_for_learning(run):
    text = "Invoice Number: INV-1\nTotal Amount Due: $1,000.00"
    result = extract(text, run)
    assert result.fields["total"].label == "total amount due"
