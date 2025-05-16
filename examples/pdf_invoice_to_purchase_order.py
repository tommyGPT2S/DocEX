from docex import DocEX
from docex.processors.factory import factory
from pathlib import Path
import sys
import json
import logging
from docex.db.models import DocBasket
from docex.db.connection import Database
from sqlalchemy import text

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_invoice(pdf_path: str):
    """
    Process an invoice PDF and extract PO number.
    
    Args:
        pdf_path (str): Path to the PDF invoice file
    """
    try:
        # 1. Create DocEX instance
        docEX = DocEX()

        # 2. Create or get the 'invoice' basket
        basket = docEX.basket('invoice')

        # 3. Add the PDF document with custom metadata
        metadata = {'biz_doc_type': 'invoice'}
        doc = basket.add(pdf_path, metadata=metadata)

        # 4. Get the processor for this document
        processor_cls = factory.map_document_to_processor(doc)
        if not processor_cls:
            logger.error('No processor found for this document.')
            return None
        processor = processor_cls(config={})

        # 5. Run the processor
        result = processor.process(doc)

        # 6. Print the output
        if result.success:
            logger.info('Extracted Text:')
            logger.info(result.content)
            logger.info('\nMetadata:')
            logger.info(result.metadata)
            
            # 7. Print the document's metadata
            logger.info('\nDocument Metadata:')
            doc_metadata = doc.get_metadata()
            logger.info(doc_metadata)
            
            # 8. Find documents with the same PO number
            if 'cus_PO' in doc_metadata:
                try:
                    # Get PO number from metadata
                    po_metadata = doc_metadata['cus_PO']
                    po_number = po_metadata.extra.get('value') if hasattr(po_metadata, 'extra') else None
                    
                    if po_number:
                        logger.info(f'\nFound PO Number: {po_number}')
                        # Use basket's find_documents_by_metadata to search for related documents
                        related_docs = basket.find_documents_by_metadata({'cus_PO': po_number})
                        
                        if related_docs:
                            logger.info(f"\nFound {len(related_docs)} related documents:")
                            for related_doc in related_docs:
                                logger.info(f"""
                                Related Document:
                                ID: {related_doc.id}
                                Name: {related_doc.name}
                                Type: {related_doc.document_type}
                                Created: {related_doc.created_at}
                                ------------------------""")
                        else:
                            logger.info(f"No other documents found with PO number: {po_number}")
                except Exception as e:
                    logger.error(f"Error finding related documents: {str(e)}")
            
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