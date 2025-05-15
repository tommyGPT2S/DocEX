from docex import DocFlow
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

def find_documents_by_po(po_number: str):
    """
    Find documents that have a specific PO number in their metadata.
    
    Args:
        po_number (str): The purchase order number to search for
    """
    try:
        # Initialize DocEX
        df = DocFlow()
        db = Database()
        
        # SQL query to find documents with matching PO metadata
        query = text("""
            SELECT d.id, d.name, d.document_type, d.created_at, dm.value as metadata_json
            FROM document d
            JOIN document_metadata dm ON d.id = dm.document_id
            WHERE dm.key = 'cus_PO'
        """)
        
        # Execute query
        with db.get_engine().connect() as conn:
            result = conn.execute(query)
            documents = result.fetchall()
            
        # Filter documents with matching PO number
        matching_docs = []
        for doc in documents:
            try:
                metadata = json.loads(doc.metadata_json)
                if metadata.get('extra', {}).get('value') == po_number:
                    matching_docs.append(doc)
            except json.JSONDecodeError:
                continue
            
        if not matching_docs:
            logger.info(f"No documents found with PO number: {po_number}")
            return
            
        # Print results
        logger.info(f"Found {len(matching_docs)} documents with PO number {po_number}:")
        for doc in matching_docs:
            logger.info(f"""
Document ID: {doc.id}
Name: {doc.name}
Type: {doc.document_type}
Created: {doc.created_at}
------------------------""")
            
    except Exception as e:
        logger.error(f"Error searching for documents: {str(e)}")
        raise

def process_invoice(pdf_path: str):
    """
    Process an invoice PDF and extract PO number.
    
    Args:
        pdf_path (str): Path to the PDF invoice file
    """
    try:
        # 1. Create DocEX instance
        docflow = DocFlow()

        # 2. Create or get the 'invoice' basket
        basket = docflow.basket('invoice')

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