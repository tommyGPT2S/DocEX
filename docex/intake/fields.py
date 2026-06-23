"""
Canonical commercial-real-estate (CRE) invoice field registry.

This is the single source of truth for the scalar header fields the intake
knows how to extract and reconcile. Every layer (heuristic extractor, embedding
extractor, LLM prompt, reconciler) reads from this registry, so adding a field
is a one-line change here rather than an edit in five places.

The model is CRE-first: alongside generic invoice identity and totals it covers
the lease, property, billing-period, and pro-rata concepts that appear on rent
statements and operating-expense bills. Per-charge detail (base rent, CAM, real
estate tax pass-throughs, and so on) lives in line items, classified by the
charge taxonomy in :mod:`docex.intake.charges`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple


class FieldType(str, Enum):
    """How a field's value is parsed and compared."""

    STRING = "string"
    AMOUNT = "amount"
    DATE = "date"
    CURRENCY = "currency"
    PERCENT = "percent"
    NUMBER = "number"


@dataclass(frozen=True)
class FieldSpec:
    """Describes one canonical invoice field.

    Attributes:
        name: Canonical machine name (also the key used everywhere).
        type: How the value is normalized and compared.
        labels: Human label aliases that may precede the value on a page.
            Used by the heuristic extractor for label-proximity matching and
            by the embedding extractor as the prototype text for a field.
        required: Whether the field is expected on every invoice. Required
            fields that cannot be extracted drive escalation up the cascade.
    """

    name: str
    type: FieldType
    labels: Tuple[str, ...]
    required: bool = False


_SPECS: Tuple[FieldSpec, ...] = (
    # --- Invoice identity ------------------------------------------------
    FieldSpec(
        name="invoice_number",
        type=FieldType.STRING,
        labels=("invoice number", "invoice no", "invoice #", "invoice id", "statement number", "bill number"),
        required=True,
    ),
    FieldSpec(
        name="po_number",
        type=FieldType.STRING,
        labels=("purchase order", "po number", "po no", "po #", "p.o.", "order number"),
    ),
    # --- Parties ---------------------------------------------------------
    FieldSpec(
        name="landlord_name",
        type=FieldType.STRING,
        labels=("landlord", "lessor", "owner", "billed by", "remit to", "from"),
    ),
    FieldSpec(
        name="landlord_tax_id",
        type=FieldType.STRING,
        labels=("tax id", "ein", "vat number", "abn", "gst number"),
    ),
    FieldSpec(
        name="property_manager",
        type=FieldType.STRING,
        labels=("property manager", "managing agent", "management company", "managed by"),
    ),
    FieldSpec(
        name="tenant_name",
        type=FieldType.STRING,
        labels=("tenant", "lessee", "bill to", "billed to", "occupant"),
    ),
    FieldSpec(
        name="tenant_account",
        type=FieldType.STRING,
        labels=("tenant id", "account number", "account no", "tenant code", "customer number"),
    ),
    # --- Property and lease ---------------------------------------------
    FieldSpec(
        name="property_name",
        type=FieldType.STRING,
        labels=("property", "building", "property name", "building name", "premises", "project"),
    ),
    FieldSpec(
        name="property_address",
        type=FieldType.STRING,
        labels=("property address", "premises address", "building address", "site address"),
    ),
    FieldSpec(
        name="suite_number",
        type=FieldType.STRING,
        labels=("suite", "unit", "suite number", "unit number", "space", "floor"),
    ),
    FieldSpec(
        name="lease_number",
        type=FieldType.STRING,
        labels=("lease number", "lease id", "lease no", "lease reference", "lease #"),
    ),
    # --- Measures --------------------------------------------------------
    FieldSpec(
        name="rentable_square_feet",
        type=FieldType.NUMBER,
        labels=("rentable square feet", "rentable sf", "rsf", "rentable area", "leased area", "square feet", "sq ft"),
    ),
    FieldSpec(
        name="pro_rata_share",
        type=FieldType.PERCENT,
        labels=("pro rata share", "pro-rata share", "proportionate share", "tenant share", "percentage share"),
    ),
    # --- Billing period --------------------------------------------------
    FieldSpec(
        name="invoice_date",
        type=FieldType.DATE,
        labels=("invoice date", "statement date", "date of issue", "billing date", "date"),
    ),
    FieldSpec(
        name="due_date",
        type=FieldType.DATE,
        labels=("due date", "payment due", "pay by", "due"),
    ),
    FieldSpec(
        name="billing_period_start",
        type=FieldType.DATE,
        labels=("billing period from", "period start", "service period from", "from", "period beginning"),
    ),
    FieldSpec(
        name="billing_period_end",
        type=FieldType.DATE,
        labels=("billing period to", "period end", "service period to", "to", "period ending"),
    ),
    # --- Money -----------------------------------------------------------
    FieldSpec(
        name="currency",
        type=FieldType.CURRENCY,
        labels=("currency", "ccy"),
    ),
    FieldSpec(
        name="prior_balance",
        type=FieldType.AMOUNT,
        labels=("prior balance", "previous balance", "balance forward", "beginning balance"),
    ),
    FieldSpec(
        name="payments_received",
        type=FieldType.AMOUNT,
        labels=("payments received", "less payments", "payments applied", "amount paid"),
    ),
    FieldSpec(
        name="current_charges",
        type=FieldType.AMOUNT,
        labels=("current charges", "current period charges", "charges this period", "new charges"),
    ),
    FieldSpec(
        name="subtotal",
        type=FieldType.AMOUNT,
        labels=("subtotal", "sub total", "net amount", "net total", "amount before tax"),
    ),
    FieldSpec(
        name="tax",
        type=FieldType.AMOUNT,
        labels=("tax", "vat", "gst", "sales tax", "tax amount"),
    ),
    FieldSpec(
        name="total",
        type=FieldType.AMOUNT,
        labels=("total amount due", "total due", "amount due", "balance due", "grand total", "total", "amount payable"),
        required=True,
    ),
)


FIELDS: Dict[str, FieldSpec] = {spec.name: spec for spec in _SPECS}


def required_fields() -> Tuple[str, ...]:
    """Names of fields expected on every invoice."""
    return tuple(name for name, spec in FIELDS.items() if spec.required)
