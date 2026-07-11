"""
Synthetic commercial-real-estate invoice generator for the intake tests.

The generator produces a matched pair: a :class:`GroundTruthInvoice` (our
recorded actuals) and the text of a vendor invoice that should reconcile to it.
Both are driven by a seeded ``random.Random`` so every test is reproducible, and
the renderer deliberately varies label phrasing, date format, and column layout
so the heuristic extractor is exercised against the messiness real invoices
carry - without ever needing a real PDF.

Helpers are also provided for the specific edge cases the test suite asserts on
(overcharges, missing fields, novel labels, European amount formatting).
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Tuple

from docex.intake.charges import ChargeType
from docex.intake.ground_truth import GroundTruthInvoice
from docex.intake.models import LineItem

_TENANTS = ["Acme Retail LLC", "Borealis Trading Co", "Cedar & Vine Hospitality", "Delphi Analytics Inc"]
_LANDLORDS = ["Harbor Point Holdings", "Summit Property Group", "Northgate Realty Trust"]
_PROPERTIES = ["Harbor Point Tower", "Summit Plaza", "Northgate Commons", "Riverside Exchange"]
_MANAGERS = ["Meridian Property Management", "BlueStone Asset Services"]

# Phrasings the registry already knows, used to vary clean invoices.
_INVOICE_NO_LABELS = ["Invoice Number", "Invoice No", "Statement Number"]
_TOTAL_LABELS = ["Total Amount Due", "Amount Due", "Balance Due", "Total Due"]
_TENANT_LABELS = ["Bill To", "Tenant", "Billed To"]
_DATE_STYLES = ["iso", "us_slash", "spelled"]


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _format_money(value: Decimal) -> str:
    return f"${value:,.2f}"


def _format_date(value: date, style: str) -> str:
    if style == "iso":
        return value.isoformat()
    if style == "us_slash":
        return value.strftime("%m/%d/%Y")
    return value.strftime("%B %d, %Y")


def random_ground_truth(rng: random.Random) -> GroundTruthInvoice:
    """Build a self-consistent CRE ground-truth invoice for one lease period."""
    year = rng.choice([2023, 2024, 2025])
    invoice_date = date(year, rng.randint(1, 12), 1)
    due_date = invoice_date + timedelta(days=rng.choice([15, 30]))

    rentable_sf = Decimal(rng.choice([5000, 8200, 12500, 18750, 24000]))
    annual_base_psf = Decimal(rng.choice([24, 26, 30, 38, 42]))
    base_rent = _money(rentable_sf * annual_base_psf / 12)
    cam = _money(rentable_sf * Decimal(rng.choice([3, 4, 5])) / 12)
    real_estate_tax = _money(rentable_sf * Decimal(rng.choice([1, 2])) / 12)

    line_items = [
        LineItem(description="Base Rent", charge_type=ChargeType.BASE_RENT, amount=base_rent),
        LineItem(description="Common Area Maintenance", charge_type=ChargeType.CAM, amount=cam),
        LineItem(description="Real Estate Tax Recovery", charge_type=ChargeType.REAL_ESTATE_TAX, amount=real_estate_tax),
    ]
    if rng.random() < 0.5:
        insurance = _money(rentable_sf * Decimal("0.5") / 12)
        line_items.append(LineItem(description="Insurance Recovery", charge_type=ChargeType.INSURANCE, amount=insurance))

    subtotal = _money(sum((item.amount for item in line_items), Decimal("0")))
    building_sf = rentable_sf * Decimal(rng.choice([8, 10, 12]))
    pro_rata = _money(rentable_sf / building_sf * 100)

    return GroundTruthInvoice(
        invoice_number=f"INV-{year}-{rng.randint(1000, 9999)}",
        po_number=f"PO-{rng.randint(100000, 999999)}",
        landlord_name=rng.choice(_LANDLORDS),
        property_manager=rng.choice(_MANAGERS),
        tenant_name=rng.choice(_TENANTS),
        tenant_account=f"TEN-{rng.randint(1000, 9999)}",
        property_name=rng.choice(_PROPERTIES),
        suite_number=str(rng.choice([100, 250, 400, 1200, 2150])),
        lease_number=f"LS-{rng.randint(1000, 9999)}",
        rentable_square_feet=rentable_sf,
        pro_rata_share=pro_rata,
        invoice_date=invoice_date,
        due_date=due_date,
        currency="USD",
        subtotal=subtotal,
        tax=Decimal("0.00"),
        total=subtotal,
        line_items=line_items,
    )


def render_invoice(gt: GroundTruthInvoice, rng: random.Random) -> str:
    """Render a clean invoice that should reconcile exactly to ``gt``.

    Label phrasing, date format, and spacing are randomized so repeated calls
    exercise different layouts the heuristic must cope with.
    """
    date_style = rng.choice(_DATE_STYLES)
    gap = " " * rng.choice([2, 4, 8])

    def row(label: str, value: str) -> str:
        return f"{label}:{gap}{value}"

    lines = [
        gt.property_name.upper(),
        "Monthly Rent Statement",
        "",
        row(rng.choice(_INVOICE_NO_LABELS), gt.invoice_number),
        row("Purchase Order", gt.po_number),
        row("Landlord", gt.landlord_name),
        row("Property Manager", gt.property_manager),
        row("Property", gt.property_name),
        row("Invoice Date", _format_date(gt.invoice_date, date_style)),
        row("Due Date", _format_date(gt.due_date, date_style)),
        row(rng.choice(_TENANT_LABELS), gt.tenant_name),
        row("Tenant ID", gt.tenant_account),
        row("Suite", gt.suite_number),
        row("Lease Number", gt.lease_number),
        row("Rentable Square Feet", f"{gt.rentable_square_feet:,.0f}"),
        row("Pro Rata Share", f"{gt.pro_rata_share}%"),
        "",
    ]
    for item in gt.line_items:
        lines.append(f"{item.description}{gap}{_format_money(item.amount)}")
    lines.extend(
        [
            "",
            f"Subtotal{gap}{_format_money(gt.subtotal)}",
            f"Tax{gap}{_format_money(gt.tax)}",
            f"{rng.choice(_TOTAL_LABELS)}{gap}{_format_money(gt.total)}",
        ]
    )
    return "\n".join(lines)


def matched_pair(seed: int) -> Tuple[GroundTruthInvoice, str]:
    """A ground-truth record and a clean invoice that reconciles to it."""
    rng = random.Random(seed)
    gt = random_ground_truth(rng)
    return gt, render_invoice(gt, rng)


def overcharged_invoice(seed: int, charge_type: ChargeType, delta: Decimal) -> Tuple[GroundTruthInvoice, str]:
    """A pair where the rendered invoice overstates one charge by ``delta``.

    The ground truth is returned unchanged; the invoice text inflates the named
    charge (and its totals) so reconciliation must report a discrepancy.
    """
    rng = random.Random(seed)
    gt = random_ground_truth(rng)
    inflated = [
        LineItem(
            description=item.description,
            charge_type=item.charge_type,
            amount=(item.amount + delta) if item.charge_type == charge_type else item.amount,
        )
        for item in gt.line_items
    ]
    inflated_total = _money(sum((item.amount for item in inflated), Decimal("0")))
    invoice = GroundTruthInvoice(
        **{**gt.model_dump(), "line_items": [item.model_dump() for item in inflated], "subtotal": inflated_total, "total": inflated_total}
    )
    return gt, render_invoice(invoice, rng)


def lines_to_pdf_bytes(text: str) -> bytes:
    """Render invoice text into a minimal one-page PDF using reportlab.

    Raises ``ImportError`` if reportlab is not installed; callers skip the test.
    """
    import io

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    text_object = pdf.beginText(50, 740)
    text_object.setFont("Courier", 9)
    for line in text.split("\n"):
        text_object.textLine(line)
    pdf.drawText(text_object)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
