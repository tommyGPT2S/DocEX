"""
Batch ingestion for DocEX: file a folder of documents in one call.

See :class:`docex.batch.ingest.BatchIngestor`. Duplicate files are skipped
(safe to re-run), per-file errors are collected instead of raised, and content
parsing is parallelized while database writes stay single-threaded.
"""

from docex.batch.ingest import (
    ADDED,
    FAILED,
    SKIPPED_DUPLICATE,
    BatchIngestor,
    BatchReport,
    FileOutcome,
)

__all__ = [
    'BatchIngestor',
    'BatchReport',
    'FileOutcome',
    'ADDED',
    'SKIPPED_DUPLICATE',
    'FAILED',
]
