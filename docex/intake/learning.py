"""
The self-improving label loop.

Every time an extracted field is confirmed against ground truth, the label
phrase that identified it is recorded with a running count. That yields two
things:

* A *trend*: how customers actually phrase each field (``total`` arrives as
  "Amount Due" far more often than "Balance Payable"), useful for analytics.
* A *learned alias*: a phrasing the static registry did not know about - often
  surfaced by the LLM on a messy invoice - is promoted into the heuristic's
  alias set, so the next invoice that uses it is solved for free by Tier 1.

Only ground-truth-validated labels are recorded, so the loop cannot teach the
heuristic a wrong mapping. Over time the cheap tier absorbs the long tail of
vendor phrasings and the LLM is needed less and less.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Tuple

from pydantic import BaseModel

from docex.intake.fields import FIELDS
from docex.intake.models import ExtractedInvoice, MatchStatus, ReconciliationResult
from docex.intake.normalize import normalize_for_compare


class FieldObservation(BaseModel):
    """How often one label phrasing has been confirmed for a canonical field."""

    field_name: str
    label: str
    count: int


class LearningStore(ABC):
    """Persists confirmed (field, label) observations and their counts."""

    @abstractmethod
    def record(self, field_name: str, label: str) -> None:
        """Increment the confirmed-count for a (field, label) pairing."""

    @abstractmethod
    def label_counts(self, field_name: str) -> Dict[str, int]:
        """Confirmed label phrasings for a field, mapped to their counts."""

    @abstractmethod
    def observations(self) -> List[FieldObservation]:
        """Every observation, descending by count - the formatting trend report."""

    def learned_labels(self, field_name: str, min_count: int = 1) -> Tuple[str, ...]:
        """Labels confirmed at least ``min_count`` times that the registry lacks.

        Registry labels are excluded because the heuristic already scans those;
        this returns only the *new* phrasings worth teaching it.
        """
        known = {normalize_for_compare(label) for label in FIELDS[field_name].labels} if field_name in FIELDS else set()
        learned = [
            label
            for label, count in self.label_counts(field_name).items()
            if count >= min_count and label not in known
        ]
        return tuple(learned)


class InMemoryLearningStore(LearningStore):
    """A counter-backed store for tests and single-process use."""

    def __init__(self) -> None:
        self._counts: Dict[Tuple[str, str], int] = {}

    def record(self, field_name: str, label: str) -> None:
        key = (field_name, normalize_for_compare(label))
        if not key[1]:
            return
        self._counts[key] = self._counts.get(key, 0) + 1

    def label_counts(self, field_name: str) -> Dict[str, int]:
        return {label: count for (name, label), count in self._counts.items() if name == field_name}

    def observations(self) -> List[FieldObservation]:
        rows = [
            FieldObservation(field_name=name, label=label, count=count)
            for (name, label), count in self._counts.items()
        ]
        return sorted(rows, key=lambda row: row.count, reverse=True)


class JsonFileLearningStore(InMemoryLearningStore):
    """An :class:`InMemoryLearningStore` that persists to a JSON file.

    Counts survive across runs so the heuristic keeps everything it has learned.
    The file is small (one entry per confirmed phrasing) and written on each
    record; for high write volumes swap in a database-backed store.
    """

    def __init__(self, path: str | Path) -> None:
        super().__init__()
        self._path = Path(path)
        self._load()

    def record(self, field_name: str, label: str) -> None:
        super().record(field_name, label)
        self._save()

    def _load(self) -> None:
        if not self._path.exists():
            return
        payload = json.loads(self._path.read_text())
        for row in payload:
            self._counts[(row["field_name"], row["label"])] = row["count"]

    def _save(self) -> None:
        payload = [obs.model_dump() for obs in self.observations()]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, indent=2))


def record_confirmed_labels(
    store: LearningStore,
    extracted: ExtractedInvoice,
    result: ReconciliationResult,
) -> None:
    """Record the label of every field that reconciled cleanly against ground truth.

    This is the write side of the learning loop: it is called by the pipeline
    after reconciliation so that only confirmed mappings are ever learned.
    """
    matched = {comparison.field for comparison in result.field_comparisons if comparison.status == MatchStatus.MATCH}
    for name in matched:
        field = extracted.fields.get(name)
        if field and field.label:
            store.record(name, field.label)
