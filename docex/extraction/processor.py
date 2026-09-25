"""
DocEX processor that extracts configured fields and saves them as metadata.

For every field that is found, three metadata rows are written so the result
is fully traceable:

    total                12500.00
    total_source         regex          (or: llm)
    total_source_label   Total Due      (the label text that identified it)

One additional row, ``needs_review``, is 'true' whenever any configured field
is missing or produced conflicting values -- a single metadata search then
returns every document that a person should look at.
"""

import io
import logging
from typing import Any, Dict, Optional

from docex.db.connection import Database
from docex.document import Document
from docex.extraction.config import ExtractionConfig
from docex.extraction.engine import FOUND, NOT_FOUND, FieldResult, RulesEngine
from docex.extraction.llm import LLMFn, extract_missing
from docex.processors.base import BaseProcessor, ProcessingResult
from docex.services.metadata_service import MetadataService

logger = logging.getLogger(__name__)


class FieldExtractionProcessor(BaseProcessor):
    """Extracts configured fields from a document and stores them as metadata."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        db: Optional[Database] = None,
        extraction_config: Optional[ExtractionConfig] = None,
        llm_fn: Optional[LLMFn] = None,
    ):
        """
        Args:
            config: Standard processor config dict. May contain 'fields' (inline
                field definitions) or 'config_file' (path to a YAML config).
            db: Optional tenant-aware database instance.
            extraction_config: Explicit ExtractionConfig; takes precedence over
                anything in ``config``. Defaults to the packaged CRE invoice set.
            llm_fn: Optional callable mapping a prompt string to a response
                string. When provided, fields the rules tier cannot find are
                requested from it in a single call per document.
        """
        super().__init__(config or {}, db)
        if extraction_config is not None:
            self.extraction_config = extraction_config
        elif self.config.get('fields'):
            self.extraction_config = ExtractionConfig.from_dict(self.config['fields'])
        elif self.config.get('config_file'):
            self.extraction_config = ExtractionConfig.from_yaml(self.config['config_file'])
        else:
            self.extraction_config = ExtractionConfig.default()
        self.llm_fn = llm_fn
        self.engine = RulesEngine(self.extraction_config)

    def can_process(self, document: Document) -> bool:
        return document.name.lower().endswith(('.pdf', '.txt', '.text', '.md'))

    def read_text(self, document: Document) -> str:
        """Get the document's text (PDF via pdfminer, everything else as stored text).

        This performs no database writes, so it is safe to call from worker threads.
        """
        if document.name.lower().endswith('.pdf'):
            try:
                from pdfminer.high_level import extract_text
            except ImportError:
                raise ImportError(
                    "PDF extraction requires 'pdfminer.six'. Install it with: pip install docex[pdf]"
                )
            return extract_text(io.BytesIO(self.get_document_bytes(document)))
        return self.get_document_text(document)

    def extract_from_text(self, text: str) -> Dict[str, FieldResult]:
        """Run the rules tier, then the LLM fallback for whatever is still missing.

        This performs no database writes, so it is safe to call from worker threads.
        """
        results = self.engine.extract(text)
        if self.llm_fn:
            missing = [
                spec for spec in self.extraction_config.fields
                if results[spec.name].status == NOT_FOUND
            ]
            results.update(extract_missing(self.llm_fn, text, missing))
        return results

    @staticmethod
    def build_metadata(results: Dict[str, FieldResult]) -> Dict[str, str]:
        """Convert field results into the metadata rows to store."""
        metadata: Dict[str, str] = {}
        needs_review = False
        for result in results.values():
            if result.status == FOUND:
                metadata[result.name] = result.value
                metadata[f'{result.name}_source'] = result.source
                metadata[f'{result.name}_source_label'] = result.label
            else:
                needs_review = True
        metadata['needs_review'] = 'true' if needs_review else 'false'
        return metadata

    def save_results(self, document: Document, results: Dict[str, FieldResult]) -> Dict[str, str]:
        """Write extraction results to document metadata and record the operation."""
        metadata = self.build_metadata(results)
        MetadataService(self.db).update_metadata(document.id, metadata)
        self._record_operation(document, 'success', output_metadata=metadata)
        return metadata

    def process(self, document: Document, text: Optional[str] = None) -> ProcessingResult:
        """Extract fields from the document and save them as metadata.

        Args:
            document: Document to process.
            text: Optional pre-extracted document text; when provided the
                document content is not read again.
        """
        try:
            if text is None:
                text = self.read_text(document)
            results = self.extract_from_text(text)
            metadata = self.save_results(document, results)
            return ProcessingResult(success=True, content=text, metadata=metadata)
        except Exception as e:
            logger.error(f"Field extraction failed for document {document.id}: {e}")
            return ProcessingResult(success=False, error=str(e))
