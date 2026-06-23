"""
A realistic commercial-real-estate invoice PDF fixture.

The bulk of the suite tests on text. This module builds a genuinely formatted
invoice - landlord letterhead, billing and property blocks, a ruled charges
table, and a totals section - so the intake is proven against a document that
looks like something a property manager would actually send, not a plain text
dump.

``SAMPLE_GROUND_TRUTH`` is the recorded actuals for this invoice. The committed
fixture ``fixtures/sample_cre_invoice.pdf`` is produced by
:func:`build_realistic_invoice_pdf` (run ``python -m tests.intake.realistic_invoice``
to regenerate it). The renderer lays each label/value on its own baseline and
right-aligns charge amounts so pdfminer recovers clean "label: value" and
"description ... amount" lines.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from docex.intake.charges import ChargeType
from docex.intake.ground_truth import GroundTruthInvoice
from docex.intake.models import LineItem

# The sample PDFs live under example_docs/ so a non-technical reader can open
# and view them directly; the tests read the same files.
_SAMPLE_DIR = Path(__file__).resolve().parents[2] / "example_docs" / "cre_invoices"
FIXTURE_PATH = _SAMPLE_DIR / "positive_invoice_matches_ground_truth.pdf"
OVERCHARGED_FIXTURE_PATH = _SAMPLE_DIR / "negative_invoice_overcharged_cam.pdf"
OVERCHARGE_DELTA = Decimal("750.00")  # CAM the negative fixture overstates by

SAMPLE_GROUND_TRUTH = GroundTruthInvoice(
    invoice_number="INV-2024-0042",
    po_number="PO-778812",
    landlord_name="Summit Property Group",
    property_manager="Meridian Property Management",
    tenant_name="Acme Retail LLC",
    tenant_account="TEN-4821",
    property_name="Harbor Point Tower",
    suite_number="1200",
    lease_number="LS-5567",
    rentable_square_feet=Decimal("12500"),
    pro_rata_share=Decimal("8.25"),
    invoice_date=None,  # printed on the invoice but not reconciled in the fixture test
    due_date=None,
    currency="USD",
    subtotal=Decimal("27083.33"),
    tax=Decimal("0.00"),
    total=Decimal("27083.33"),
    line_items=[
        LineItem(description="Base Rent", charge_type=ChargeType.BASE_RENT, amount=Decimal("20833.33")),
        LineItem(description="Common Area Maintenance", charge_type=ChargeType.CAM, amount=Decimal("5000.00")),
        LineItem(description="Real Estate Tax Recovery", charge_type=ChargeType.REAL_ESTATE_TAX, amount=Decimal("1250.00")),
    ],
)


_TABLE_WIDTH = 64  # characters across the monospaced body column


def _row(left_text: str, right_text: str = "") -> str:
    """One monospaced row, ``right_text`` flushed to the right margin."""
    if not right_text:
        return left_text
    pad = max(1, _TABLE_WIDTH - len(left_text) - len(right_text))
    return f"{left_text}{' ' * pad}{right_text}"


def build_realistic_invoice_pdf(gt: GroundTruthInvoice = SAMPLE_GROUND_TRUTH) -> bytes:
    """Render ``gt`` as a formatted one-page invoice PDF (requires reportlab).

    A styled Helvetica letterhead and "INVOICE" banner sit above a monospaced
    body. The body is drawn as one text object so each logical row (a labelled
    field, a charge line, a total) is a single line of text - the way many
    property-management systems emit invoices, and what lets pdfminer recover
    the rows intact instead of splitting columns.
    """
    import io

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    width, height = letter
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    left = 54
    right = width - 54

    # Styled letterhead and banner.
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(left, height - 60, gt.landlord_name)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(left, height - 74, "1 Harbor Plaza, 30th Floor, Boston, MA 02210")
    pdf.drawString(left, height - 86, f"Managed by {gt.property_manager}")
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawRightString(right, height - 64, "INVOICE")
    pdf.line(left, height - 96, right, height - 96)

    rule = "-" * _TABLE_WIDTH
    body = [
        _row("Invoice Number:", gt.invoice_number),
        _row("Purchase Order:", gt.po_number),
        _row("Invoice Date:", "January 01, 2024"),
        _row("Due Date:", "January 15, 2024"),
        "",
        _row("Bill To:", gt.tenant_name),
        _row("Tenant ID:", gt.tenant_account),
        _row("Property:", gt.property_name),
        _row("Suite:", gt.suite_number),
        _row("Lease Number:", gt.lease_number),
        _row("Rentable Square Feet:", f"{gt.rentable_square_feet:,.0f}"),
        _row("Pro Rata Share:", f"{gt.pro_rata_share}%"),
        "",
        _row("Description", "Amount"),
        rule,
    ]
    body.extend(_row(item.description, f"${item.amount:,.2f}") for item in gt.line_items)
    body.extend(
        [
            rule,
            _row("Subtotal", f"${gt.subtotal:,.2f}"),
            _row("Tax", f"${gt.tax:,.2f}"),
            _row("Total Amount Due", f"${gt.total:,.2f}"),
            "",
            _row("Remit To:", gt.landlord_name),
            "Please reference the invoice number on your payment.",
        ]
    )

    text_object = pdf.beginText(left, height - 130)
    text_object.setFont("Courier", 10)
    text_object.setLeading(15)
    for line in body:
        text_object.textLine(line)
    pdf.drawText(text_object)

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def as_billed_overcharge(gt: GroundTruthInvoice = SAMPLE_GROUND_TRUTH) -> GroundTruthInvoice:
    """The same invoice with CAM (and its totals) overstated by ``OVERCHARGE_DELTA``.

    Same invoice number, so it still matches the ground-truth record - but the
    printed charges no longer agree with it, which is exactly the
    vendor-overcharge case the intake must catch.
    """
    inflated_items = [
        item.model_copy(update={"amount": item.amount + OVERCHARGE_DELTA})
        if item.charge_type == ChargeType.CAM
        else item
        for item in gt.line_items
    ]
    inflated_total = sum((item.amount for item in inflated_items), Decimal("0"))
    return gt.model_copy(
        update={"line_items": inflated_items, "subtotal": inflated_total, "total": inflated_total}
    )


def build_overcharged_invoice_pdf() -> bytes:
    """Render the negative (overcharged) invoice as a realistic PDF."""
    return build_realistic_invoice_pdf(as_billed_overcharge())


def regenerate_fixtures() -> tuple[Path, Path]:
    """Write both committed PDF fixtures to disk and return their paths."""
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_bytes(build_realistic_invoice_pdf())
    OVERCHARGED_FIXTURE_PATH.write_bytes(build_overcharged_invoice_pdf())
    return FIXTURE_PATH, OVERCHARGED_FIXTURE_PATH


if __name__ == "__main__":
    for path in regenerate_fixtures():
        print(f"Wrote {path}")
