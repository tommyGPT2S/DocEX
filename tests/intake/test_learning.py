"""The self-improving label loop: confirmed phrasings teach the heuristic."""

from decimal import Decimal

from docex.intake.extractors.base import ExtractionContext
from docex.intake.extractors.heuristic import HeuristicExtractor
from docex.intake.fields import FIELDS
from docex.intake.ground_truth import GroundTruthInvoice
from docex.intake.learning import (
    InMemoryLearningStore,
    JsonFileLearningStore,
    record_confirmed_labels,
)
from docex.intake.models import (
    ExtractedField,
    ExtractedInvoice,
    ExtractionTier,
)
from docex.intake.reconcile import Reconciler


def test_records_normalised_counts():
    store = InMemoryLearningStore()
    store.record("total", "Amount Due")
    store.record("total", "amount due")  # same phrasing, different case
    assert store.label_counts("total") == {"amount due": 2}


def test_learned_labels_exclude_registry_phrasings():
    store = InMemoryLearningStore()
    store.record("total", "total amount due")  # already a registry label
    store.record("total", "net payable this cycle")  # genuinely new
    learned = store.learned_labels("total")
    assert "net payable this cycle" in learned
    assert "total amount due" not in learned


def test_only_matched_fields_are_recorded():
    store = InMemoryLearningStore()
    extracted = ExtractedInvoice()
    extracted.put(ExtractedField(name="total", value=Decimal("100"), confidence=0.95, tier=ExtractionTier.LLM, label="Net Payable This Cycle"))
    extracted.put(ExtractedField(name="tax", value=Decimal("9"), confidence=0.95, tier=ExtractionTier.LLM, label="Levy"))

    gt = GroundTruthInvoice(invoice_number="INV-1", total=Decimal("100"), tax=Decimal("0"))
    result = Reconciler().reconcile(extracted, gt)
    record_confirmed_labels(store, extracted, result)

    # total matched -> learned; tax mismatched -> not learned.
    assert store.learned_labels("total") == ("net payable this cycle",)
    assert store.learned_labels("tax") == ()


def test_heuristic_uses_a_learned_label(run):
    store = InMemoryLearningStore()
    store.record("total", "net payable this cycle")
    extractor = HeuristicExtractor(store)

    text = "Invoice Number: INV-1\nNet Payable This Cycle: $4,200.00"
    result = run(extractor.extract(ExtractionContext(raw_text=text, target_fields=())))
    assert result.fields["total"].value == Decimal("4200.00")


def test_json_file_store_persists(tmp_path):
    path = tmp_path / "learned.json"
    JsonFileLearningStore(path).record("total", "net payable this cycle")

    reloaded = JsonFileLearningStore(path)
    assert reloaded.label_counts("total") == {"net payable this cycle": 1}


def test_registry_unchanged_by_learning():
    # Learning must not mutate the static registry it reads from.
    before = FIELDS["total"].labels
    store = InMemoryLearningStore()
    store.record("total", "brand new phrase")
    assert FIELDS["total"].labels == before
