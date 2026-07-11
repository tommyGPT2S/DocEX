"""
DocEX PDF Intake

Reads commercial-real-estate invoice PDFs of arbitrary layout, extracts their
fields using a cost-ordered cascade (a free heuristic first, an LLM only as a
last resort), and reconciles the extracted invoice against a stored
ground-truth record. Confirmed field labels feed a learning loop so the cheap
heuristic keeps improving and the LLM is needed less over time.

See ``README.md`` in this package for the full design, testing notes, and the
assumptions the intake makes about its inputs.

The DocEX ``BaseProcessor`` glue lives in :mod:`docex.intake.processor` and is
imported separately so that the core pipeline stays free of any database
dependency.
"""

from docex.intake.charges import ChargeType, classify_charge
from docex.intake.embedding_match import (
    EmbeddingGroundTruthMatcher,
    GroundTruthMatch,
    extracted_fingerprint,
    ground_truth_fingerprint,
)
from docex.intake.fields import FIELDS, FieldSpec, FieldType
from docex.intake.ground_truth import (
    DocEXGroundTruthStore,
    GroundTruthInvoice,
    GroundTruthStore,
    InMemoryGroundTruthStore,
)
from docex.intake.learning import (
    FieldObservation,
    InMemoryLearningStore,
    JsonFileLearningStore,
    LearningStore,
)
from docex.intake.models import (
    ExtractedField,
    ExtractedInvoice,
    ExtractionTier,
    FieldComparison,
    LineItem,
    LineItemComparison,
    MatchStatus,
    ReconciliationResult,
    ReconciliationStatus,
)
from docex.intake.pipeline import IntakeOutcome, InvoiceIntakePipeline
from docex.intake.reconcile import GroundTruthMatcher, Reconciler, TolerancePolicy

__all__ = [
    "FIELDS",
    "FieldSpec",
    "FieldType",
    "ChargeType",
    "classify_charge",
    "ExtractedField",
    "ExtractedInvoice",
    "ExtractionTier",
    "LineItem",
    "FieldComparison",
    "LineItemComparison",
    "MatchStatus",
    "ReconciliationResult",
    "ReconciliationStatus",
    "GroundTruthInvoice",
    "GroundTruthStore",
    "InMemoryGroundTruthStore",
    "DocEXGroundTruthStore",
    "LearningStore",
    "InMemoryLearningStore",
    "JsonFileLearningStore",
    "FieldObservation",
    "Reconciler",
    "TolerancePolicy",
    "GroundTruthMatcher",
    "EmbeddingGroundTruthMatcher",
    "GroundTruthMatch",
    "ground_truth_fingerprint",
    "extracted_fingerprint",
    "InvoiceIntakePipeline",
    "IntakeOutcome",
]
