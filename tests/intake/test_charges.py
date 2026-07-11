"""The charge taxonomy must classify CRE line items, most-specific first."""

import pytest

from docex.intake.charges import ChargeType, classify_charge


@pytest.mark.parametrize(
    "description, expected",
    [
        ("Base Rent", ChargeType.BASE_RENT),
        ("Minimum Monthly Rent", ChargeType.BASE_RENT),
        ("Common Area Maintenance", ChargeType.CAM),
        ("CAM Charge", ChargeType.CAM),
        ("Real Estate Tax Recovery", ChargeType.REAL_ESTATE_TAX),
        ("Property Tax", ChargeType.REAL_ESTATE_TAX),
        ("Insurance Recovery", ChargeType.INSURANCE),
        ("Parking - 10 stalls", ChargeType.PARKING),
        ("Property Management Fee", ChargeType.MANAGEMENT_FEE),
        ("Late Charge", ChargeType.LATE_FEE),
        ("Percentage Rent", ChargeType.PERCENTAGE_RENT),
        ("After-Hours HVAC", ChargeType.HVAC),
        ("Holiday Decorations", ChargeType.OTHER),
    ],
)
def test_classify_charge(description, expected):
    assert classify_charge(description) == expected


def test_cam_reconciliation_beats_plain_cam():
    # "CAM reconciliation" must not fall through to the broader CAM bucket.
    assert classify_charge("Annual CAM Reconciliation") == ChargeType.CAM_RECONCILIATION


def test_blank_description_is_other():
    assert classify_charge("") == ChargeType.OTHER
