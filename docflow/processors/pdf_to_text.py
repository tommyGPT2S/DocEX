import io
import re
from typing import Dict, Any
from docflow.processors.base import BaseProcessor, ProcessingResult
from docflow.document import Document
from pdfminer.high_level import extract_text
from docflow.services.metadata_service import MetadataService
from docflow.db.connection import Database

class MatchingInvoiceToPOProcessor(BaseProcessor):
    """Processor that extracts PO number from invoice PDF and updates document metadata"""
    def can_process(self, document: Document) -> bool:
        return document.name.lower().endswith('.pdf')

    def process(self, document: Document) -> ProcessingResult:
        try:
            # Get PDF content as bytes
            pdf_bytes = self.get_document_bytes(document)
            # Use pdfminer to extract text
            text = extract_text(io.BytesIO(pdf_bytes))
            # Find PO number using regex (e.g., PO-000111)
            po_match = re.search(r'PO[-\s]?([0-9]{6,})', text, re.IGNORECASE)
            po_number = po_match.group(0) if po_match else None
            # Add PO number to document metadata if found
            if po_number:
                db = Database()
                service = MetadataService(db)
                service.update_metadata(document.id, {'cus_PO': po_number})
            return ProcessingResult(
                success=True,
                content=text,
                metadata={
                    'input_format': 'pdf',
                    'output_format': 'text',
                    'length': len(text),
                    'cus_PO': po_number
                }
            )
        except Exception as e:
            return ProcessingResult(success=False, error=str(e)) 