"""
Batch ingestion: file a whole folder of documents in one call and get a report.

Design notes:

* Files already in the basket (same content fingerprint and source path, the
  same rule DocEX's add() uses for duplicates) are skipped, so re-running a
  batch over the same folder is safe and only picks up new files.
* Database writes are deliberately single-threaded: DocEX's connection
  handling is not thread-safe and SQLite serializes writers anyway. Only the
  expensive, database-free work -- reading and parsing document content -- is
  parallelized across a thread pool.
* Per-file errors are recorded in the report instead of raised, so one bad
  file never aborts the batch.
"""

import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# File outcome statuses
ADDED = 'added'
SKIPPED_DUPLICATE = 'skipped_duplicate'
FAILED = 'failed'

# The pure (no database writes) processor methods used for the parallel stage.
_SPLIT_PIPELINE_METHODS = ('read_text', 'extract_from_text', 'save_results')


@dataclass
class FileOutcome:
    """What happened to one file in the batch."""

    path: str
    status: str
    reason: Optional[str] = None
    document_id: Optional[str] = None
    needs_review: bool = False


@dataclass
class BatchReport:
    """Result of a batch run: per-file outcomes plus convenience views."""

    outcomes: List[FileOutcome] = field(default_factory=list)

    @property
    def added(self) -> List[FileOutcome]:
        return [o for o in self.outcomes if o.status == ADDED]

    @property
    def skipped(self) -> List[FileOutcome]:
        return [o for o in self.outcomes if o.status == SKIPPED_DUPLICATE]

    @property
    def failed(self) -> List[FileOutcome]:
        return [o for o in self.outcomes if o.status == FAILED]

    @property
    def processing_failures(self) -> List[FileOutcome]:
        return [o for o in self.outcomes if o.status == ADDED and o.reason]

    @property
    def needs_review(self) -> List[FileOutcome]:
        return [o for o in self.outcomes if o.needs_review]

    def summary(self) -> str:
        parts = [
            f"{len(self.added)} added",
            f"{len(self.skipped)} skipped (duplicates)",
            f"{len(self.failed)} failed",
        ]
        if self.processing_failures:
            parts.append(f"{len(self.processing_failures)} processing failures")
        if self.needs_review:
            parts.append(f"{len(self.needs_review)} need review")
        return ', '.join(parts)


class BatchIngestor:
    """Files every document in a folder into a basket, optionally running a processor."""

    def __init__(self, basket: Any, processor: Optional[Any] = None, max_workers: int = 4):
        """
        Args:
            basket: DocBasket to file documents into.
            processor: Optional DocEX processor to run on each added document.
                A processor exposing read_text/extract_from_text/save_results
                (such as the field extraction processor) gets its content
                parsing parallelized; any other processor is run serially via
                its standard process() method.
            max_workers: Thread pool size for the parallel parsing stage.
        """
        self.basket = basket
        self.processor = processor
        self.max_workers = max_workers

    def ingest_folder(self, folder: str, pattern: str = '*') -> BatchReport:
        """Ingest every file in a folder (non-recursive) and return a report.

        Args:
            folder: Path to the folder to ingest.
            pattern: Optional glob pattern to filter files (e.g. '*.pdf').
        """
        folder_path = Path(folder)
        if not folder_path.is_dir():
            raise ValueError(f"Not a folder: {folder}")

        report = BatchReport()
        added: List[Tuple[FileOutcome, Any]] = []

        # Phase 1 (serial): fingerprint, skip duplicates, file the rest.
        for path in sorted(p for p in folder_path.glob(pattern) if not p.is_dir()):
            outcome, document = self._ingest_file(path)
            report.outcomes.append(outcome)
            if document is not None:
                added.append((outcome, document))

        # Phase 2: run the processor on newly added documents.
        if self.processor and added:
            self._process_documents(added)

        logger.info(f"Batch ingest of {folder}: {report.summary()}")
        return report

    def _ingest_file(self, path: Path) -> Tuple[FileOutcome, Optional[Any]]:
        try:
            checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as e:
            return FileOutcome(str(path), FAILED, reason=f"unreadable: {e}"), None

        if self._already_in_basket(checksum, str(path)):
            return FileOutcome(str(path), SKIPPED_DUPLICATE), None

        try:
            document = self.basket.add(str(path))
        except Exception as e:
            return FileOutcome(str(path), FAILED, reason=f"add failed: {e}"), None

        return FileOutcome(str(path), ADDED, document_id=document.id), document

    def _already_in_basket(self, checksum: str, source: str) -> bool:
        """Same duplicate rule as DocBasket.add(): matching fingerprint and source path."""
        from docex.db.models import Document as DocumentModel

        with self.basket.db.session() as session:
            existing = (
                session.query(DocumentModel)
                .filter_by(basket_id=self.basket.id, checksum=checksum, source=source)
                .first()
            )
            return existing is not None

    def _process_documents(self, added: List[Tuple[FileOutcome, Any]]) -> None:
        if all(hasattr(self.processor, m) for m in _SPLIT_PIPELINE_METHODS):
            self._process_split(added)
        else:
            self._process_serial(added)

    def _process_split(self, added: List[Tuple[FileOutcome, Any]]) -> None:
        """Parallel parsing, serial persistence.

        Workers only read content and extract fields (no database writes);
        results are saved by this (main) thread one document at a time.
        """
        def parse(document):
            return self.processor.extract_from_text(self.processor.read_text(document))

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(parse, document): (outcome, document)
                for outcome, document in added
            }
            for future in as_completed(futures):
                outcome, document = futures[future]
                try:
                    results = future.result()
                except Exception as e:
                    outcome.reason = f"processing failed: {e}"
                    outcome.needs_review = True
                    continue
                metadata = self.processor.save_results(document, results)
                outcome.needs_review = metadata.get('needs_review') == 'true'

    def _process_serial(self, added: List[Tuple[FileOutcome, Any]]) -> None:
        for outcome, document in added:
            try:
                result = self.processor.process(document)
            except Exception as e:
                outcome.reason = f"processing failed: {e}"
                outcome.needs_review = True
                continue
            if not getattr(result, 'success', False):
                outcome.reason = f"processing failed: {getattr(result, 'error', 'unknown error')}"
                outcome.needs_review = True
            else:
                outcome.needs_review = (result.metadata or {}).get('needs_review') == 'true'
