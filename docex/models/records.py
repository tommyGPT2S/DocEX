"""
Typed record models for lightweight DocEX reads.

These models provide stable, typed alternatives to the raw dictionaries
previously returned by metadata-first APIs such as
``DocEX.list_baskets_with_metadata`` and ``Document.get_details``.

Consumers that only need metadata should use these records rather than
constructing full ``DocBasket`` or ``Document`` objects, which initialise
storage, path helpers, and service layers that are unnecessary for
read-only inspection.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class BasketRecord(BaseModel):
    """Lightweight read-only record for a document basket.

    Returned by :meth:`DocEX.list_baskets_with_metadata`.
    Fields map 1-to-1 with the columns available in that method.

    All fields are ``Optional`` with ``None`` defaults because
    ``list_baskets_with_metadata`` accepts an arbitrary ``columns`` subset;
    any column not requested will not be present in the constructor call.

    Attributes:
        id: Basket primary key (``bas_<uuid>`` format).
        name: Human-readable basket name.
        description: Optional free-text description of the basket.
        status: Lifecycle status, e.g. ``'active'``.
        created_at: UTC timestamp when the basket was created.
        updated_at: UTC timestamp of the last basket update.
        document_count: Number of documents in the basket. Only populated
            when ``'document_count'`` is included in the ``columns``
            argument; ``None`` otherwise.
    """

    model_config = ConfigDict(frozen=True)

    id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    document_count: Optional[int] = None


class DocumentRecord(BaseModel):
    """Lightweight read-only record for a document.

    Returned by :meth:`Document.get_details` and document list/search
    methods. Fields map 1-to-1 with the keys in the existing
    ``get_details()`` dict.

    Attributes:
        id: Document primary key (``doc_<uuid>`` format).
        name: File name of the document.
        path: Storage path relative to the basket's storage root.
        content_type: MIME type of the document. ``None`` when the type
            could not be determined.
        document_type: Category of the document, e.g. ``'file'``.
        size: Size of the document in bytes. ``None`` when not yet
            computed.
        checksum: SHA-256 hex digest of the document content.
        status: Lifecycle status, e.g. ``'active'``.
        created_at: UTC timestamp when the document was ingested.
        updated_at: UTC timestamp of the last document update.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    path: str
    content_type: Optional[str] = None
    document_type: str
    size: Optional[int] = None
    checksum: str
    status: str
    created_at: datetime
    updated_at: datetime
