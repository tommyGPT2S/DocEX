from docflow import DocFlow
from docflow.processors.factory import factory
from pathlib import Path
import sys
from docflow.db.models import DocBasket

def main():
    try:
        # 1. Create DocFlow instance
        docflow = DocFlow()

        # 2. Create or get the 'invoice' basket
        basket = docflow.basket('invoice')

        # 3. Add the PDF document with custom metadata
        pdf_path = 'examples/sample_data/invoice_2001321.pdf'
        metadata = {'biz_doc_type': 'invoice'}
        doc = basket.add(pdf_path, metadata=metadata)

        # 4. Get the processor for this document
        processor_cls = factory.map_document_to_processor(doc)
        if not processor_cls:
            print('No processor found for this document.')
            sys.exit(1)
        processor = processor_cls(config={})

        # 5. Run the processor
        result = processor.process(doc)

        # 6. Print the output
        if result.success:
            print('Extracted Text:')
            print(result.content)
            print('\nMetadata:')
            print(result.metadata)
        else:
            print(f'Processing failed: {result.error}')

        # 7. Print the document's metadata (should include cus_PO if found)
        print('\nDocument Metadata:')
        print(doc.get_metadata())
    except Exception as e:
        print(f'Error: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main() 