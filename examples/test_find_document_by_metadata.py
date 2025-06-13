import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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

            
            

            
            po_match = re.search(r'PO(?:\s*number)?[:\s-]+([\w-]+)', text, re.IGNORECASE)
            po_number = po_match.group(1) if po_match else None

            invoice_match = re.search(r'Invoice(?:\s*[Nn]o\.?)?[:\s]*(\d+)', text, re.IGNORECASE | re.DOTALL)
            invoice_number = invoice_match.group(1).strip() if invoice_match else None

            payee_match = re.search(r'Bill\s*To[:\s]*\n*([\w\s,.\[\]]+?)(?=\nInvoice)', text, re.IGNORECASE)
            payee_name = payee_match.group(1).strip() if payee_match else None

            
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

    #  DocEX instance
    docEX = DocEX()

    # create/ get basket
    basket = docEX.basket('incomingInvoice')
    print(f"Basket '{basket.name}' created/retrieved with ID: {basket.id}")

    print("#please modify the line below this and add your own path")
    x_folder_path = Path('DocEX/examples/sample_data') #please modify this and add your own path
    document_path = x_folder_path / 'invoice_2001321.pdf' 

    if not document_path.exists():
        print(f"Error: Document not found at {document_path}")
        doc = None
    else:
        doc = basket.add(str(document_path))
        print(f"Document '{doc.name}' added to basket '{basket.name}' with ID: {doc.id}")

    factory.register(InvoiceProcessor) 

    factory.mapper.rules.insert(0, invoice_rule)

    if doc:
        processor_cls = factory.map_document_to_processor(doc)
        if processor_cls:
            processor = processor_cls(config={})
            result = await processor.process(doc)
            print(f"Processing result: {result.content[:200]}...") 

            
            print("Stored metadata for the document:")
            for key, value in doc.get_metadata().items():
                print(f"  {key}: {value}")

            
            invoice_number = result.metadata['invoice_number'].extra['value']
            print(f"Searching for invoice number: {invoice_number}")
            search_results = basket.find_documents_by_metadata({'invoice_number': invoice_number})
            print(search_results)

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