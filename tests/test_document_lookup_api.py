from __future__ import annotations

from types import SimpleNamespace

from docex.docCore import DocEX
from docex.docbasket.document_manager import DocBasketDocumentManager


class _SessionContext:
    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):
        return False


def test_docex_get_document_uses_document_id_without_basket() -> None:
    docex = object.__new__(DocEX)

    document = SimpleNamespace(
        id="doc_123",
        model=SimpleNamespace(basket_id="bas_123"),
    )
    basket = SimpleNamespace(
        id="bas_123",
        get_document=lambda document_id: document if document_id == "doc_123" else None,
    )

    class Session:
        def get(self, model_cls, document_id):
            assert document_id == "doc_123"
            return SimpleNamespace(id=document_id, basket_id="bas_123")

    docex.db = SimpleNamespace(session=lambda: _SessionContext(Session()))
    docex.get_basket = lambda basket_id=None, basket_name=None: basket if basket_id == "bas_123" else None

    resolved = docex.get_document("doc_123")

    assert resolved is document


def test_docex_get_document_rejects_cross_basket_match() -> None:
    docex = object.__new__(DocEX)

    wrong_document = SimpleNamespace(
        id="doc_123",
        model=SimpleNamespace(basket_id="bas_other"),
    )
    basket = SimpleNamespace(
        id="bas_123",
        get_document=lambda document_id: wrong_document,
    )

    docex.get_basket = lambda basket_id=None, basket_name=None: basket if basket_id == "bas_123" else None

    resolved = docex.get_document("doc_123", basket_id="bas_123")

    assert resolved is None


def test_docbasket_document_manager_get_document_filters_by_basket(monkeypatch) -> None:
    captured = {}
    fake_document_model = SimpleNamespace(id="doc_123", basket_id="bas_123")

    def fake_select(model_cls):
        captured["model_cls"] = model_cls

        class _Query:
            def where(self, condition):
                captured["condition"] = condition
                return self

        return _Query()

    def fake_and_(*conditions):
        captured["conditions"] = conditions
        return ("and", conditions)

    monkeypatch.setattr("docex.docbasket.document_manager.select", fake_select)
    monkeypatch.setattr("docex.docbasket.document_manager.and_", fake_and_)

    class Session:
        def execute(self, query):
            captured["query"] = query

            class _Result:
                def scalar_one_or_none(self):
                    return fake_document_model

            return _Result()

    basket = SimpleNamespace(
        id="bas_123",
        db=SimpleNamespace(session=lambda: _SessionContext(Session())),
    )
    manager = DocBasketDocumentManager(basket)
    manager._document_instance = lambda document: ("wrapped", document.id, document.basket_id)

    resolved = manager.get_document("doc_123")

    assert resolved == ("wrapped", "doc_123", "bas_123")
    assert len(captured["conditions"]) == 2
