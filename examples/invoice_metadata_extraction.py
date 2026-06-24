"""
Example: Structured Invoice Metadata Extraction

This example demonstrates how DocEX document processors can be
composed with lightweight business logic to transform unstructured
PDF text into strongly typed invoice metadata suitable for semantic
search, agent workflows, and downstream integrations.

The PDF processor remains generic (PDF -> text), while invoice-specific
logic is layered on top to preserve separation of concerns.
"""

from dataclasses import asdict, dataclass
import json
import logging
import re
import sys

from docex import DocEX
from docex.context import UserContext
from docex.processors.factory import factory
from custom_processors.my_pdf_text_processor import MyPDFTextProcessor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class InvoiceMetadata:
    invoice_number: str | None
    po_number: str | None
    invoice_date: str | None
    total_amount: float | None

def pdf_rule(document, db=None):
    if document.name.lower().endswith(".pdf"):
        return MyPDFTextProcessor
    return None

def first_match(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def extract_invoice_metadata(text: str) -> InvoiceMetadata:
    """
    Convert raw PDF text into structured invoice metadata.

    This example demonstrates how document processors can feed
    downstream business workflows by extracting typed fields from
    unstructured document content.
    """
    invoice_number = first_match(text, r"Invoice no\.\s+(\d+)")
    po_number = first_match(text, r"PO number\s+([A-Z]+-\d+)")
    invoice_date = first_match(text, r"Date\s+([\d/]+)")
    
    # Use the final currency value as the invoice total.
    # The sample invoice lists line-item amounts first and the grand total last.
    amounts = [
        float(value.replace(",", ""))
        for value in re.findall(r"\$([\d,]+\.\d{2})", text)
    ]
    total_amount = amounts[-1] if amounts else None

    return InvoiceMetadata(
        invoice_number=invoice_number,
        po_number=po_number,
        invoice_date=invoice_date,
        total_amount=total_amount,
    )

def process_invoice(pdf_path: str):
    """
    Process an invoice PDF and extract structured invoice metadata.
    
    Args:
        pdf_path (str): Path to the PDF invoice file
    """
    try:
        factory.mapper.rules.insert(0, pdf_rule)

        # 1. Create UserContext for audit logging
        user_context = UserContext(
            user_id="invoice_processor",
            user_email="processor@example.com",
            tenant_id="example_tenant",  # Optional: for multi-tenant applications
            roles=["processor"]
        )
        
        # 2. Create DocEX instance with UserContext (enables audit logging)
        docEX = DocEX(user_context=user_context)

        # 3. Create or get the 'invoice' basket
        basket = docEX.basket('invoice')

        # 4. Add the PDF document with custom metadata
        metadata = {'biz_doc_type': 'invoice'}
        doc = basket.add(pdf_path, metadata=metadata)

        # 5. Get the processor for this document
        processor_cls = factory.map_document_to_processor(doc)
        if not processor_cls:
            logger.error('No processor found for this document.')
            return None
        processor = processor_cls(config={})

        # 6. Run the processor
        result = processor.process(doc)

        # 7. Print the output
        if result.success:
            logger.info('Extracted Text:')
            logger.info(result.content)
            logger.info('\nMetadata:')
            logger.info(result.metadata)

            structured_metadata = extract_invoice_metadata(result.content)

            logger.info("\nStructured Invoice Metadata:")
            logger.info(json.dumps(asdict(structured_metadata), indent=2))
            
            # 8. Print the document's metadata
            logger.info('\nDocument Metadata:')
            doc_metadata = doc.get_metadata()
            logger.info(doc_metadata)
            
            return doc
        else:
            logger.error(f'Processing failed: {result.error}')
            return None
            
    except Exception as e:
        logger.error(f'Error: {e}')
        return None

def main():
    # Process the sample invoice
    pdf_path = 'examples/sample_data/invoice_2001321.pdf'
    doc = process_invoice(pdf_path)
    
    if doc:
        logger.info("\nProcessing completed successfully!")
    else:
        logger.error("\nProcessing failed!")
        sys.exit(1)

if __name__ == '__main__':
    main() 