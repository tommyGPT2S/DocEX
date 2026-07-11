"""Fuzzy ground-truth retrieval by embedding similarity.

A deterministic bag-of-words embedding stands in for a real model so these tests
run everywhere: each token hashes to a fixed dimension and increments it, so
text overlap drives cosine similarity exactly as a sentence embedding would,
without any provider.
"""

import hashlib
from decimal import Decimal

from docex.intake.charges import ChargeType
from docex.intake.embedding_match import EmbeddingGroundTruthMatcher
from docex.intake.ground_truth import GroundTruthInvoice, InMemoryGroundTruthStore
from docex.intake.models import (
    ExtractedField,
    ExtractedInvoice,
    ExtractionTier,
    LineItem,
    ReconciliationStatus,
)
from docex.intake.pipeline import InvoiceIntakePipeline

_DIMS = 128


def bag_of_words(text: str) -> list:
    """A stable token-frequency embedding (deterministic across runs)."""
    vector = [0.0] * _DIMS
    for token in text.lower().split():
        index = int(hashlib.md5(token.encode()).hexdigest(), 16) % _DIMS
        vector[index] += 1.0
    return vector


def _lease(invoice_number, tenant, property_name, total, charge) -> GroundTruthInvoice:
    return GroundTruthInvoice(
        invoice_number=invoice_number,
        tenant_name=tenant,
        property_name=property_name,
        total=Decimal(total),
        line_items=[LineItem(description=charge, charge_type=ChargeType.BASE_RENT, amount=Decimal(total))],
    )


def _three_lease_store():
    store = InMemoryGroundTruthStore()
    a = store.add(_lease("INV-A", "Acme Retail", "Harbor Point Tower", "1000", "Base Rent"))
    b = store.add(_lease("INV-B", "Borealis Trading", "Summit Plaza", "2000", "Base Rent"))
    c = store.add(_lease("INV-C", "Cedar Vine", "Northgate Commons", "3000", "Base Rent"))
    return store, a, b, c


def _extracted(**values) -> ExtractedInvoice:
    invoice = ExtractedInvoice()
    line_items = values.pop("line_items", [])
    for name, value in values.items():
        invoice.put(ExtractedField(name=name, value=value, confidence=0.9, tier=ExtractionTier.HEURISTIC))
    invoice.line_items = line_items
    return invoice


def test_candidates_rank_the_right_lease_first(run):
    store, _a, b, _c = _three_lease_store()
    # Wrong invoice number, but tenant/property/total point unmistakably at B.
    extracted = _extracted(
        invoice_number="INV-TYPO",
        tenant_name="Borealis Trading",
        property_name="Summit Plaza",
        total=Decimal("2000"),
        line_items=[LineItem(description="Base Rent", charge_type=ChargeType.BASE_RENT, amount=Decimal("2000"))],
    )
    ranked = run(EmbeddingGroundTruthMatcher(bag_of_words).candidates(extracted, store, top_k=3))
    assert ranked[0].record.id == b.id
    assert ranked[0].score >= ranked[1].score >= ranked[2].score


def test_find_returns_best_above_threshold(run):
    store, _a, b, _c = _three_lease_store()
    extracted = _extracted(
        tenant_name="Borealis Trading",
        property_name="Summit Plaza",
        total=Decimal("2000"),
    )
    match = run(EmbeddingGroundTruthMatcher(bag_of_words, threshold=0.5).find(extracted, store))
    assert match is not None and match.record.id == b.id


def test_find_returns_none_below_threshold(run):
    store, _a, b, _c = _three_lease_store()
    extracted = _extracted(tenant_name="Borealis Trading", property_name="Summit Plaza", total=Decimal("2000"))
    assert run(EmbeddingGroundTruthMatcher(bag_of_words, threshold=0.999).find(extracted, store)) is None


def test_empty_invoice_has_no_candidates(run):
    store, *_ = _three_lease_store()
    assert run(EmbeddingGroundTruthMatcher(bag_of_words).candidates(ExtractedInvoice(), store)) == []


def test_record_embeddings_are_cached(run):
    store, *_ = _three_lease_store()
    calls = []

    def counting_embedding(text):
        calls.append(text)
        return bag_of_words(text)

    matcher = EmbeddingGroundTruthMatcher(counting_embedding, threshold=0.0)
    extracted = _extracted(tenant_name="Borealis Trading", total=Decimal("2000"))
    run(matcher.find(extracted, store))
    after_first = len(calls)
    run(matcher.find(extracted, store))
    # Second run re-embeds only the query, not the three cached records.
    assert len(calls) == after_first + 1


def test_pipeline_falls_back_to_embedding_when_identifier_is_wrong(run):
    store, _a, b, _c = _three_lease_store()
    # Invoice text whose number is a typo absent from the store, so identifier
    # matching fails; tenant/property/total still identify lease B.
    text = (
        "Invoice Number: INV-TYPO-999\n"
        "Bill To: Borealis Trading\n"
        "Property: Summit Plaza\n"
        "Base Rent                         $2,000.00\n"
        "Total Amount Due                  $2,000.00\n"
    )

    without_embeddings = run(InvoiceIntakePipeline().process_text(text, store))
    assert without_embeddings.status == ReconciliationStatus.UNRESOLVED

    with_embeddings = run(InvoiceIntakePipeline(embedding_fn=bag_of_words, match_threshold=0.4).process_text(text, store))
    assert with_embeddings.ground_truth is not None
    assert with_embeddings.ground_truth.id == b.id
    # The right lease was found; the typo'd invoice number is now a flagged discrepancy.
    assert with_embeddings.status == ReconciliationStatus.DISCREPANCY
    assert "invoice_number" in {c.field for c in with_embeddings.reconciliation.mismatches}
