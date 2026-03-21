"""
Unit tests for BasketRecord and DocumentRecord typed models.

All tests are fully isolated — no real database connections are made.
The session layer is mocked at the ``Database`` class level so that
``list_baskets_with_metadata`` can be exercised without any external
infrastructure.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from docex import DocEX, BasketRecord, DocumentRecord
from docex.document import Document


# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------

NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def reset_docex_singleton():
    """Ensure the DocEX singleton is cleared before and after every test."""
    DocEX._instance = None
    yield
    DocEX._instance = None


@pytest.fixture
def docex_with_mock_db():
    """Yield a (DocEX instance, mock_db) pair with no real DB calls.

    ``Database`` is patched at import time in ``docex.docCore`` so that
    ``DocEX.__init__`` stores a ``MagicMock`` as ``self.db``.
    """
    with (
        patch("docex.docCore.DocEX.is_initialized", return_value=True),
        patch("docex.docCore.DocEXConfig") as mock_config_cls,
        patch("docex.docCore.Database") as mock_db_cls,
    ):
        mock_config = MagicMock()
        mock_config.get.return_value = {}
        mock_config_cls.return_value = mock_config

        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db

        instance = DocEX()
        yield instance, mock_db


@pytest.fixture
def sample_document():
    """Return a ``Document`` instance constructed from known values."""
    return Document(
        id="doc_abc123",
        name="invoice.pdf",
        path="baskets/inv/invoice.pdf",
        content_type="application/pdf",
        document_type="file",
        size=4096,
        checksum="deadbeef" * 8,
        status="active",
        created_at=NOW,
        updated_at=NOW,
    )


# ---------------------------------------------------------------------------
# BasketRecord — instantiation and immutability
# ---------------------------------------------------------------------------


def test_basket_record_instantiation():
    """BasketRecord stores every field exactly as supplied."""
    record = BasketRecord(
        id="bas_001",
        name="invoices",
        description="Raw invoice drop zone",
        status="active",
        created_at=NOW,
        updated_at=NOW,
        document_count=7,
    )

    assert record.id == "bas_001"
    assert record.name == "invoices"
    assert record.description == "Raw invoice drop zone"
    assert record.status == "active"
    assert record.created_at == NOW
    assert record.updated_at == NOW
    assert record.document_count == 7


def test_basket_record_is_frozen():
    """Mutating any field on a BasketRecord must raise TypeError."""
    record = BasketRecord(id="bas_001", name="invoices")

    with pytest.raises((TypeError, ValidationError)):
        record.name = "something_else"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DocumentRecord — instantiation and immutability
# ---------------------------------------------------------------------------


def test_document_record_instantiation():
    """DocumentRecord stores every field exactly as supplied."""
    record = DocumentRecord(
        id="doc_abc123",
        name="invoice.pdf",
        path="baskets/inv/invoice.pdf",
        content_type="application/pdf",
        document_type="file",
        size=4096,
        checksum="deadbeef" * 8,
        status="active",
        created_at=NOW,
        updated_at=NOW,
    )

    assert record.id == "doc_abc123"
    assert record.name == "invoice.pdf"
    assert record.path == "baskets/inv/invoice.pdf"
    assert record.content_type == "application/pdf"
    assert record.document_type == "file"
    assert record.size == 4096
    assert record.checksum == "deadbeef" * 8
    assert record.status == "active"
    assert record.created_at == NOW
    assert record.updated_at == NOW


def test_document_record_is_frozen():
    """Mutating any field on a DocumentRecord must raise TypeError."""
    record = DocumentRecord(
        id="doc_abc123",
        name="invoice.pdf",
        path="baskets/inv/invoice.pdf",
        content_type="application/pdf",
        document_type="file",
        size=4096,
        checksum="deadbeef" * 8,
        status="active",
        created_at=NOW,
        updated_at=NOW,
    )

    with pytest.raises((TypeError, ValidationError)):
        record.name = "other.pdf"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Integration: list_baskets_with_metadata returns typed records
# ---------------------------------------------------------------------------


def test_list_baskets_with_metadata_returns_typed_records(docex_with_mock_db):
    """list_baskets_with_metadata must return BasketRecord instances."""
    instance, mock_db = docex_with_mock_db

    # Simulate a single DB row containing (id, name)
    fake_row = ("bas_test001", "test_basket")
    mock_session = MagicMock()
    mock_session.execute.return_value.all.return_value = [fake_row]
    mock_db.session.return_value.__enter__.return_value = mock_session
    mock_db.session.return_value.__exit__.return_value = False

    results = instance.list_baskets_with_metadata(columns=["id", "name"])

    assert len(results) == 1
    assert isinstance(results[0], BasketRecord)
    assert results[0].id == "bas_test001"
    assert results[0].name == "test_basket"


# ---------------------------------------------------------------------------
# Integration: Document.get_details returns a typed record
# ---------------------------------------------------------------------------


def test_get_details_returns_typed_record(sample_document):
    """Document.get_details must return a DocumentRecord with matching fields."""
    result = sample_document.get_details()

    assert isinstance(result, DocumentRecord)
    assert result.id == "doc_abc123"
    assert result.name == "invoice.pdf"
    assert result.path == "baskets/inv/invoice.pdf"
    assert result.content_type == "application/pdf"
    assert result.document_type == "file"
    assert result.size == 4096
    assert result.checksum == "deadbeef" * 8
    assert result.status == "active"
    assert result.created_at == NOW
    assert result.updated_at == NOW


# ---------------------------------------------------------------------------
# model_dump
# ---------------------------------------------------------------------------


def test_basket_record_model_dump():
    """BasketRecord.model_dump() returns a plain dict with all field keys."""
    record = BasketRecord(
        id="bas_001",
        name="invoices",
        description=None,
        status="active",
        created_at=NOW,
        updated_at=NOW,
        document_count=3,
    )

    dumped = record.model_dump()

    assert isinstance(dumped, dict)
    assert set(dumped.keys()) == {
        "id",
        "name",
        "description",
        "status",
        "created_at",
        "updated_at",
        "document_count",
    }
    assert dumped["id"] == "bas_001"
    assert dumped["document_count"] == 3
    assert dumped["description"] is None


def test_document_record_model_dump():
    """DocumentRecord.model_dump() returns a plain dict with all field keys."""
    record = DocumentRecord(
        id="doc_abc123",
        name="invoice.pdf",
        path="baskets/inv/invoice.pdf",
        content_type=None,
        document_type="file",
        size=None,
        checksum="deadbeef" * 8,
        status="active",
        created_at=NOW,
        updated_at=NOW,
    )

    dumped = record.model_dump()

    assert isinstance(dumped, dict)
    assert set(dumped.keys()) == {
        "id",
        "name",
        "path",
        "content_type",
        "document_type",
        "size",
        "checksum",
        "status",
        "created_at",
        "updated_at",
    }
    assert dumped["id"] == "doc_abc123"
    assert dumped["content_type"] is None
    assert dumped["size"] is None
