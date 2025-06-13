# 1. create a basket, called incomingInvoice
# 2. move document from x folder to this basket
# 3. build a processor that can process this document
# 4. register this processor with the package
# 5. use this processor to create the PDF, PO number, Invoice number and the payee name
# 6. use this info as metadata, search docex, find invoice document and output metadata.

from docex import DocEX
from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document
from docex.processors.factory import factory
from docex.config.docex_config import DocEXConfig
from pathlib import Path
import io
import re
from pdfminer.high_level import extract_text
import asyncio


class InvoiceProcessor(BaseProcessor):
    """
    A processor for extracting information from invoice documents.
    """

    def can_process(self, document: Document) -> bool:
        """
        Checks if the document is a PDF file.
        """
        return document.name.lower().endswith('.pdf')

    async def process(self, document: Document) -> ProcessingResult:
        """
        Extracts PO number, invoice number, and payee name from the document.
        """
        try:
            pdf_bytes = document.get_content(mode='bytes')
            text = extract_text(io.BytesIO(pdf_bytes))

            # Extract information using regular expressions (adjust as needed)
            po_match = re.search(r'PO:\s*(\w+)', text)
            po_number = po_match.group(1) if po_match else None

            invoice_match = re.search(r'Invoice Number:\s*(\w+)', text)
            invoice_number = invoice_match.group(1) if invoice_match else None

            payee_match = re.search(r'Pay to:\s*(.+)', text)
            payee_name = payee_match.group(1) if payee_match else None

            metadata = {
                'po_number': po_number,
                'invoice_number': invoice_number,
                'payee_name': payee_name
            }

            return ProcessingResult(success=True, content=text, metadata=metadata)

        except Exception as e:
            return ProcessingResult(success=False, error=str(e))


def invoice_rule(document):
    """
    Mapping rule to associate InvoiceProcessor with PDF documents.
    """
    if document.name.lower().endswith('.pdf'):
        return InvoiceProcessor
    return None


async def main():
    """
    Main function to demonstrate the invoice processing workflow.
    """
    # Initialize DocEX configuration
    try:
        DocEX.setup(
            database={
                'type': 'sqlite',
                'sqlite': {
                    'path': 'docex.db'
                }
            },
            storage={
                'filesystem': {
                    'path': 'storage'
                }
            },
            logging={
                'level': 'INFO',
                'file': 'docex.log'
            }
        )
    except Exception as e:
        print(f"Failed to initialize DocEX: {str(e)}")
        return

    # Create DocEX instance
    docEX = DocEX()

    # 2. Create or get basket
    basket = docEX.basket('incomingInvoice')
    print(f"Basket '{basket.name}' created/retrieved with ID: {basket.id}")

    # 3. Add document
    x_folder_path = Path('/Users/elliot/Desktop/study/keystoneai/DocEX/examples/sample_data')  # Replace with the actual path
    document_path = x_folder_path / 'invoice_2001321.pdf'  # Replace with the actual document name

    if not document_path.exists():
        print(f"Error: Document not found at {document_path}")
        doc = None
    else:
        doc = basket.add(str(document_path))
        print(f"Document '{doc.name}' added to basket '{basket.name}' with ID: {doc.id}")

    # 4. Register processor
    factory.mapper.rules.insert(0, invoice_rule)  # Highest priority

    # 5. Process document and extract metadata
    if doc:
        processor_cls = factory.map_document_to_processor(doc)
        if processor_cls:
            processor = processor_cls(config={})
            result = await processor.process(doc)
            print(f"Processing result: {result.content[:200]}...")  # Print first 200 characters
            print(f"Metadata: {result.metadata_dict()}")

            # 6. Search and output metadata
            search_results = basket.find_documents_by_metadata({'invoice_number': result.metadata['invoice_number']})

            if search_results:
                found_doc = search_results[0]
                metadata = found_doc.get_metadata()
                print(f"Found document with metadata: {metadata}")
            else:
                print("No documents found with that invoice number.")
        else:
            print('No processor found for this document.')
    else:
        print("No document to process.")


if __name__ == "__main__":
    asyncio.run(main())