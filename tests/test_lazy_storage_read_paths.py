"""Regression tests for lazy storage behavior on Postgres-backed read paths."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import text

from docex import DocEX
from docex.config.docex_config import DocEXConfig
from docex.db.connection import Database
from docex.db.models import Base
from docex.docbasket import DocBasket
from docex.services.storage_service import StorageService


def _load_env_settings() -> None:
    """Load the repo .env file once for test configuration."""
    load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)


def _database_config_from_env() -> dict:
    """Load DocEX database settings from the repo .env file."""
    _load_env_settings()
    db_type = os.environ.get("DOCEX_DB_TYPE", "postgresql")
    db_section = "postgres" if db_type in {"postgres", "postgresql"} else db_type
    return {
        "type": db_type,
        db_section: {
            "host": os.environ["DOCEX_DB_HOST"],
            "port": int(os.environ["DOCEX_DB_PORT"]),
            "database": os.environ["DOCEX_DB_NAME"],
            "user": os.environ["DOCEX_DB_USER"],
            "password": os.environ["DOCEX_DB_PASSWORD"],
            "schema": os.environ.get("DOCEX_DB_SCHEMA", "docex"),
        },
    }


@pytest.fixture(scope="module")
def docex_env(tmp_path_factory: pytest.TempPathFactory):
    """Set up a DocEX environment using the configured .env database."""
    root = tmp_path_factory.mktemp("docex_lazy_reads")
    storage_path = root / "storage"

    config = DocEXConfig()
    config.config["database"] = _database_config_from_env()
    config.config.setdefault("storage", {})
    config.config["storage"]["filesystem"] = {"path": str(storage_path)}
    config.config.setdefault("logging", {})
    config.config["logging"]["level"] = "DEBUG"

    DocEX._instance = None
    DocEX._config = config

    try:
        db = Database(config=config)
        with db.session() as session:
            session.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - environment-dependent skip
        pytest.skip(f"Configured Postgres is not reachable for DocEX tests: {exc}")

    Base.metadata.create_all(db.get_engine())
    docex = DocEX()

    yield {
        "root": root,
        "storage_path": storage_path,
        "docex": docex,
    }

    db.close()


@pytest.fixture
def populated_basket(docex_env):
    """Create a basket with a couple of real documents and metadata."""
    root: Path = docex_env["root"]
    docex: DocEX = docex_env["docex"]

    basket_name = f"lazy-storage-basket-{uuid.uuid4().hex[:8]}"
    basket = docex.create_basket(basket_name)
    source_dir = root / "input_docs"
    source_dir.mkdir(exist_ok=True)

    added_docs = []
    document_specs = [
        ("alpha.txt", "alpha document body", {"group": "alpha", "kind": "fact-sheet"}),
        ("beta.txt", "beta document body", {"group": "beta", "kind": "site-plan"}),
    ]

    for filename, content, metadata in document_specs:
        file_path = source_dir / filename
        file_path.write_text(content)
        added_docs.append(
            basket.add(str(file_path), metadata=metadata),
        )

    yield basket, added_docs

    basket.delete()


def test_list_basket_reads_do_not_initialize_storage(populated_basket, monkeypatch):
    """Basket listing should stay metadata-only and avoid storage setup."""
    basket, _ = populated_basket
    docex = DocEX()

    def fail_on_storage_init(self, storage_config):
        raise AssertionError("Storage should not initialize during basket reads")

    monkeypatch.setattr(StorageService, "__init__", fail_on_storage_init)

    baskets = docex.list_baskets()
    basket_rows = docex.list_baskets_with_metadata(columns=["id", "name"])

    matching_baskets = [listed for listed in baskets if listed.id == basket.id]
    matching_rows = [row for row in basket_rows if row.id == basket.id]

    assert len(matching_baskets) == 1
    assert matching_baskets[0]._storage_service is None
    assert len(matching_rows) == 1
    assert matching_rows[0].id == basket.id
    assert matching_rows[0].name == basket.name


def test_doccore_lightweight_basket_listing_skips_docbasket_instantiation(
    populated_basket,
    monkeypatch,
):
    """The lightweight docCore basket listing should avoid DocBasket construction."""
    basket, _ = populated_basket
    docex = DocEX()
    original_init = DocBasket.__init__
    constructed_baskets = []

    def tracked_init(self, *args, **kwargs):
        constructed_baskets.append(kwargs.get("id"))
        return original_init(self, *args, **kwargs)

    monkeypatch.setattr(DocBasket, "__init__", tracked_init)

    basket_rows = docex.list_baskets_with_metadata(columns=["id", "name"])
    assert any(row.id == basket.id for row in basket_rows)
    assert constructed_baskets == []

    baskets = docex.list_baskets()
    assert any(listed.id == basket.id for listed in baskets)
    assert basket.id in constructed_baskets


def test_document_list_and_search_reads_do_not_initialize_storage(
    populated_basket,
    monkeypatch,
):
    """List/search paths should not touch storage when only metadata is needed."""
    basket, docs = populated_basket

    def fail_on_storage_init(self, storage_config):
        raise AssertionError("Storage should not initialize during metadata reads")

    monkeypatch.setattr(StorageService, "__init__", fail_on_storage_init)

    listed_docs = basket.list_documents()
    listed_rows = basket.list_documents_with_metadata(columns=["id", "name"])
    matched_docs = basket.find_documents_by_metadata({"group": "alpha"})
    matched_rows = basket.find_documents_by_metadata_with_metadata(
        {"group": "alpha"},
        columns=["id", "name", "document_type"],
    )

    assert {doc.id for doc in listed_docs} == {doc.id for doc in docs}
    assert all(doc._storage_service is None for doc in listed_docs)
    assert matched_docs[0].id == docs[0].id
    assert matched_docs[0]._storage_service is None
    assert {row["id"] for row in listed_rows} == {doc.id for doc in docs}
    assert matched_rows == [
        {
            "id": docs[0].id,
            "name": matched_docs[0].name,
            "document_type": "file",
        }
    ]


def test_document_content_is_only_fetched_on_explicit_get_content(
    populated_basket,
    monkeypatch,
):
    """Getting a document record should not retrieve content until requested."""
    basket, docs = populated_basket
    target_doc = docs[0]
    retrieve_calls = []
    original_retrieve = StorageService.retrieve_document

    def tracked_retrieve(self, full_document_path):
        retrieve_calls.append(full_document_path)
        return original_retrieve(self, full_document_path)

    monkeypatch.setattr(StorageService, "retrieve_document", tracked_retrieve)

    fetched = basket.get_document(target_doc.id)
    searched = basket.find_documents_by_metadata({"group": "alpha"})[0]

    assert fetched is not None
    assert fetched._storage_service is None
    assert searched._storage_service is None
    assert retrieve_calls == []

    metadata = fetched.get_metadata()
    assert metadata["group"] == "alpha"
    assert retrieve_calls == []

    content = fetched.get_content(mode="text")
    assert content == "alpha document body"
    assert len(retrieve_calls) == 1
