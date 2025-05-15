"""
Example of using a custom PDF processor with DocEX.

This example shows how to:
1. Create a custom processor outside the main package
2. Patch the processor factory mapping
3. Use the custom processor with DocEX
"""

from docex import DocFlow
from docex.processors.factory import factory
from my_pdf_text_processor import MyPDFTextProcessor
import sys

def pdf_rule(document):
    # Use our custom processor for any PDF file
    if document.name.lower().endswith('.pdf'):
        return MyPDFTextProcessor
    return None

def main():
    try:
        # 1. Patch the processor factory mapping by adding our rule
        print("Patching processor factory mapping...")
        factory.mapper.rules.insert(0, pdf_rule)  # Highest priority
        
        # 2. Create DocEX instance
        print("\nCreating DocEX instance...")
        docflow = DocFlow()
        
        # 3. Create or get a basket
        print("Creating basket 'custom_pdf'...")
        basket = docflow.basket('custom_pdf')
        
        # 4. Add the PDF document
        pdf_path = 'examples/sample_data/invoice_2001321.pdf'
        print(f"\nAdding PDF document: {pdf_path}")
        doc = basket.add(pdf_path)
        
        # 5. Get and run the processor
        print("\nGetting processor...")
        processor_cls = factory.map_document_to_processor(doc)
        if not processor_cls:
            print("No processor found for this document.")
            sys.exit(1)
            
        print("Creating processor instance...")
        processor = processor_cls(config={})
        
        print("\nProcessing document...")
        result = processor.process(doc)
        
        # 6. Print results
        if result.success:
            print("\nExtracted Text:")
            print("-" * 40)
            print(result.content)
            print("-" * 40)
            
            print("\nProcessing Metadata:")
            for key, value in result.metadata.items():
                print(f"{key}: {value}")
        else:
            print(f"\nProcessing failed: {result.error}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 