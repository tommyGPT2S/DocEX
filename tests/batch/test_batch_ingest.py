"""Batch ingestion: counts, duplicate skipping, error capture, processor stages."""

import threading

import pytest

from docex.batch import BatchIngestor
from docex.processors.base import BaseProcessor, ProcessingResult
from docex.services.metadata_service import MetadataService


@pytest.fixture()
def basket(docex_instance, request):
    return docex_instance.basket(f'batch_test_{request.node.name}')


@pytest.fixture()
def invoice_folder(tmp_path):
    folder = tmp_path / 'inbox'
    folder.mkdir()
    for i in range(3):
        (folder / f'invoice_{i}.txt').write_text(f"Invoice No.: 2024-000{i}\nTotal Due: $1,{i}00.00\n")
    return folder


class SplitStubProcessor(BaseProcessor):
    """Stub with the split pipeline API (parallel parse stage, serial save stage)."""

    def __init__(self, db=None, fail_on=None):
        super().__init__({}, db)
        self.fail_on = fail_on or set()
        self.parse_threads = set()
        self.save_threads = set()

    def can_process(self, document):
        return True

    def read_text(self, document):
        if document.name in self.fail_on:
            raise ValueError('cannot parse this document')
        return self.get_document_text(document)

    def extract_from_text(self, text):
        self.parse_threads.add(threading.current_thread().name)
        return {'parsed_chars': str(len(text))}

    def save_results(self, document, results):
        self.save_threads.add(threading.current_thread().name)
        metadata = dict(results)
        metadata['needs_review'] = 'false'
        MetadataService(self.db).update_metadata(document.id, metadata)
        return metadata

    def process(self, document):
        return ProcessingResult(success=True, metadata=self.save_results(document, self.extract_from_text(self.read_text(document))))


class PlainStubProcessor(BaseProcessor):
    """Stub with only the standard process() method (generic serial path)."""

    def can_process(self, document):
        return True

    def process(self, document):
        metadata = {'needs_review': 'true'}
        MetadataService(self.db).update_metadata(document.id, metadata)
        return ProcessingResult(success=True, metadata=metadata)


def test_folder_ingested_and_rerun_skips_everything(basket, invoice_folder):
    ingestor = BatchIngestor(basket)

    first = ingestor.ingest_folder(str(invoice_folder))
    assert len(first.added) == 3
    assert len(first.skipped) == 0
    assert len(first.failed) == 0

    # Re-running the same folder is idempotent: nothing filed twice.
    second = ingestor.ingest_folder(str(invoice_folder))
    assert len(second.added) == 0
    assert len(second.skipped) == 3
    assert basket.count_documents() == 3


def test_new_file_picked_up_on_rerun(basket, invoice_folder):
    ingestor = BatchIngestor(basket)
    ingestor.ingest_folder(str(invoice_folder))

    (invoice_folder / 'invoice_late.txt').write_text("Invoice No.: 2024-9999\n")
    report = ingestor.ingest_folder(str(invoice_folder))
    assert len(report.added) == 1
    assert report.added[0].path.endswith('invoice_late.txt')


def test_unreadable_file_recorded_not_raised(basket, invoice_folder, tmp_path):
    (invoice_folder / 'broken.txt').symlink_to(tmp_path / 'does_not_exist.txt')

    report = BatchIngestor(basket).ingest_folder(str(invoice_folder))
    assert len(report.added) == 3
    assert len(report.failed) == 1
    assert 'unreadable' in report.failed[0].reason


def test_split_processor_parses_in_workers_and_saves_in_main_thread(basket, invoice_folder):
    processor = SplitStubProcessor()
    report = BatchIngestor(basket, processor=processor, max_workers=3).ingest_folder(str(invoice_folder))

    assert len(report.added) == 3
    # Parsing ran in worker threads; all database writes stayed on the main thread.
    assert all('ThreadPoolExecutor' in name for name in processor.parse_threads)
    assert processor.save_threads == {threading.main_thread().name}
    # Extraction results were persisted as metadata.
    doc = basket.get_document(report.added[0].document_id)
    assert 'parsed_chars' in doc.get_metadata()


def test_processing_failure_flags_file_and_batch_continues(basket, invoice_folder):
    processor = SplitStubProcessor(fail_on={'invoice_1.txt'})
    report = BatchIngestor(basket, processor=processor).ingest_folder(str(invoice_folder))

    assert len(report.added) == 3
    assert len(report.processing_failures) == 1
    assert 'processing failed' in report.processing_failures[0].reason
    assert report.processing_failures[0].needs_review


def test_plain_processor_runs_serially_and_review_flags_reported(basket, invoice_folder):
    report = BatchIngestor(basket, processor=PlainStubProcessor({})).ingest_folder(str(invoice_folder))

    assert len(report.added) == 3
    assert len(report.needs_review) == 3
    assert 'need review' in report.summary()


def test_glob_pattern_filters_files(basket, invoice_folder):
    (invoice_folder / 'notes.md').write_text('not an invoice')

    report = BatchIngestor(basket).ingest_folder(str(invoice_folder), pattern='*.txt')
    assert all(outcome.path.endswith('.txt') for outcome in report.outcomes)
