"""
Ground-truth invoices: our recorded actuals and where they live.

A ground-truth record is what the lease *should* bill, against which an
incoming vendor PDF is reconciled. The schema mirrors the canonical field
registry one-to-one so the reconciler can read an expected value by name with
``record.get("base_rent_field")`` and never special-case anything.

Two stores ship here:

* :class:`InMemoryGroundTruthStore` - a dict-backed store for tests and small
  in-process use.
* :class:`DocEXGroundTruthStore` - persists each record as a JSON document in a
  DocEX basket, mirroring the lookup keys into document metadata so retrieval is
  an indexed metadata query rather than a scan.
"""

from __future__ import annotations

import json
import tempfile
from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from docex.intake.charges import ChargeType
from docex.intake.models import LineItem


class GroundTruthInvoice(BaseModel):
    """The expected (actual) invoice for a lease and billing period.

    Attribute names match the canonical field registry so the reconciler can
    look up an expected value by field name via :meth:`get`.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: Optional[str] = None

    # Identity
    invoice_number: str
    po_number: Optional[str] = None

    # Parties
    landlord_name: Optional[str] = None
    landlord_tax_id: Optional[str] = None
    property_manager: Optional[str] = None
    tenant_name: Optional[str] = None
    tenant_account: Optional[str] = None

    # Property and lease
    property_name: Optional[str] = None
    property_address: Optional[str] = None
    suite_number: Optional[str] = None
    lease_number: Optional[str] = None

    # Measures
    rentable_square_feet: Optional[Decimal] = None
    pro_rata_share: Optional[Decimal] = None

    # Billing period
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    billing_period_start: Optional[date] = None
    billing_period_end: Optional[date] = None

    # Money
    currency: str = "USD"
    prior_balance: Optional[Decimal] = None
    payments_received: Optional[Decimal] = None
    current_charges: Optional[Decimal] = None
    subtotal: Optional[Decimal] = None
    tax: Optional[Decimal] = None
    total: Decimal

    line_items: List[LineItem] = Field(default_factory=list)

    def get(self, field_name: str) -> Optional[Any]:
        """Return the expected value for a canonical field, or ``None``."""
        return getattr(self, field_name, None)

    def charge_total(self, charge_type: ChargeType) -> Optional[Decimal]:
        """Sum the line-item amounts for one charge type, or ``None`` if absent."""
        amounts = [item.amount for item in self.line_items if item.charge_type == charge_type and item.amount is not None]
        return sum(amounts, Decimal("0")) if amounts else None

    def lookup_keys(self) -> Dict[str, Optional[str]]:
        """The metadata keys a store mirrors for fast retrieval."""
        return {
            "invoice_number": self.invoice_number,
            "po_number": self.po_number,
            "lease_number": self.lease_number,
            "tenant_account": self.tenant_account,
        }


class GroundTruthStore(ABC):
    """Retrieval interface over recorded ground-truth invoices."""

    @abstractmethod
    def add(self, record: GroundTruthInvoice) -> GroundTruthInvoice:
        """Persist a record and return it (with ``id`` populated)."""

    @abstractmethod
    def get_by_invoice_number(self, invoice_number: str) -> Optional[GroundTruthInvoice]:
        """Return the record with this invoice number, if any."""

    @abstractmethod
    def get_by_po_number(self, po_number: str) -> Optional[GroundTruthInvoice]:
        """Return the record with this PO number, if any."""

    @abstractmethod
    def all(self) -> List[GroundTruthInvoice]:
        """Return every stored record."""


class InMemoryGroundTruthStore(GroundTruthStore):
    """A dict-backed store, indexed by invoice and PO number."""

    def __init__(self) -> None:
        self._by_invoice: Dict[str, GroundTruthInvoice] = {}
        self._by_po: Dict[str, GroundTruthInvoice] = {}

    def add(self, record: GroundTruthInvoice) -> GroundTruthInvoice:
        if record.id is None:
            record = record.model_copy(update={"id": f"gt_{len(self._by_invoice) + 1:06d}"})
        self._by_invoice[record.invoice_number] = record
        if record.po_number:
            self._by_po[record.po_number] = record
        return record

    def get_by_invoice_number(self, invoice_number: str) -> Optional[GroundTruthInvoice]:
        return self._by_invoice.get(invoice_number)

    def get_by_po_number(self, po_number: str) -> Optional[GroundTruthInvoice]:
        return self._by_po.get(po_number)

    def all(self) -> List[GroundTruthInvoice]:
        return list(self._by_invoice.values())


class DocEXGroundTruthStore(GroundTruthStore):
    """Persists ground-truth invoices as JSON documents in a DocEX basket.

    Each record becomes one JSON document; its lookup keys are mirrored into
    document metadata so retrieval is an indexed metadata query. The full record
    is reconstructed from the document's JSON content on read.
    """

    _METADATA_MARKER = "ground_truth_invoice"

    def __init__(self, basket: Any) -> None:
        """
        Args:
            basket: A DocEX ``DocBasket`` dedicated to ground-truth records.
        """
        self._basket = basket

    def add(self, record: GroundTruthInvoice) -> GroundTruthInvoice:
        payload = record.model_dump(mode="json")
        metadata = {key: value for key, value in record.lookup_keys().items() if value is not None}
        metadata["record_type"] = self._METADATA_MARKER

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=f"_{record.invoice_number}.json", delete=False
        ) as handle:
            json.dump(payload, handle)
            temp_path = handle.name
        try:
            document = self._basket.add(temp_path, document_type="ground_truth", metadata=metadata)
        finally:
            Path(temp_path).unlink(missing_ok=True)

        return record.model_copy(update={"id": document.id})

    def get_by_invoice_number(self, invoice_number: str) -> Optional[GroundTruthInvoice]:
        return self._first_match({"invoice_number": invoice_number})

    def get_by_po_number(self, po_number: str) -> Optional[GroundTruthInvoice]:
        return self._first_match({"po_number": po_number})

    def all(self) -> List[GroundTruthInvoice]:
        documents = self._basket.find_documents_by_metadata({"record_type": self._METADATA_MARKER})
        return [self._load(document) for document in documents]

    def _first_match(self, metadata: Dict[str, str]) -> Optional[GroundTruthInvoice]:
        documents = self._basket.find_documents_by_metadata(metadata, limit=1)
        return self._load(documents[0]) if documents else None

    def _load(self, document: Any) -> GroundTruthInvoice:
        payload = document.get_content(mode="json")
        record = GroundTruthInvoice.model_validate(payload)
        return record.model_copy(update={"id": document.id})
