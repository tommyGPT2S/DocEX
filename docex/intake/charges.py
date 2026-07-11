"""
Charge taxonomy for commercial-real-estate invoice line items.

CRE invoices break the amount due into recurring and pass-through charges:
base rent, CAM, real estate tax and insurance recoveries, utilities, parking,
management fees, and periodic reconciliations. Classifying each line item into
a canonical charge type lets the reconciler compare like-for-like against the
ground-truth lease schedule instead of relying on free-text descriptions.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Tuple


class ChargeType(str, Enum):
    """Canonical category for a CRE invoice line item."""

    BASE_RENT = "base_rent"
    ADDITIONAL_RENT = "additional_rent"
    PERCENTAGE_RENT = "percentage_rent"
    CAM = "cam"
    OPERATING_EXPENSES = "operating_expenses"
    REAL_ESTATE_TAX = "real_estate_tax"
    INSURANCE = "insurance"
    UTILITIES = "utilities"
    HVAC = "hvac"
    PARKING = "parking"
    MANAGEMENT_FEE = "management_fee"
    JANITORIAL = "janitorial"
    SECURITY = "security"
    LATE_FEE = "late_fee"
    TENANT_IMPROVEMENT = "tenant_improvement"
    ESCALATION = "escalation"
    PREPAID_RENT = "prepaid_rent"
    SECURITY_DEPOSIT = "security_deposit"
    CAM_RECONCILIATION = "cam_reconciliation"
    OTHER = "other"


# Aliases are checked most-specific first so that, e.g., "CAM reconciliation"
# classifies as CAM_RECONCILIATION rather than CAM.
_LABELS: Tuple[Tuple[ChargeType, Tuple[str, ...]], ...] = (
    (ChargeType.CAM_RECONCILIATION, ("cam reconciliation", "cam true-up", "cam true up", "year-end adjustment", "expense reconciliation", "opex reconciliation")),
    (ChargeType.PERCENTAGE_RENT, ("percentage rent", "overage rent", "% rent")),
    (ChargeType.BASE_RENT, ("base rent", "minimum rent", "fixed rent", "base monthly rent", "minimum monthly rent")),
    (ChargeType.ADDITIONAL_RENT, ("additional rent", "supplemental rent")),
    (ChargeType.OPERATING_EXPENSES, ("operating expense", "operating cost", "opex", "common area expense")),
    (ChargeType.CAM, ("common area maintenance", "cam charge", "cam", "common area")),
    (ChargeType.REAL_ESTATE_TAX, ("real estate tax", "property tax", "real property tax", "re tax", "tax recovery")),
    (ChargeType.INSURANCE, ("insurance recovery", "property insurance", "liability insurance", "insurance")),
    (ChargeType.UTILITIES, ("electricity", "water", "sewer", "natural gas", "utility", "utilities")),
    (ChargeType.HVAC, ("hvac", "air conditioning", "after-hours hvac", "heating")),
    (ChargeType.PARKING, ("parking", "parking stall", "garage")),
    (ChargeType.MANAGEMENT_FEE, ("management fee", "property management fee", "administrative fee")),
    (ChargeType.JANITORIAL, ("janitorial", "cleaning", "day porter")),
    (ChargeType.SECURITY, ("security service", "security")),
    (ChargeType.LATE_FEE, ("late fee", "late charge", "penalty", "interest charge")),
    (ChargeType.TENANT_IMPROVEMENT, ("tenant improvement", "ti amortization", "build-out", "build out", "ti charge")),
    (ChargeType.ESCALATION, ("escalation", "annual increase", "cpi adjustment", "rent step")),
    (ChargeType.PREPAID_RENT, ("prepaid rent", "rent in advance")),
    (ChargeType.SECURITY_DEPOSIT, ("security deposit", "deposit")),
)


_LABEL_INDEX: Dict[str, ChargeType] = {
    alias: charge_type for charge_type, aliases in _LABELS for alias in aliases
}


def classify_charge(description: str) -> ChargeType:
    """Map a free-text line-item description to a canonical charge type.

    Args:
        description: The raw description text from the invoice line.

    Returns:
        The best-matching :class:`ChargeType`, or ``ChargeType.OTHER`` when no
        alias is recognised.
    """
    if not description:
        return ChargeType.OTHER

    text = description.strip().lower()
    for charge_type, aliases in _LABELS:
        if any(alias in text for alias in aliases):
            return charge_type
    return ChargeType.OTHER
