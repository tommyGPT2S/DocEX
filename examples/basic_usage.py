"""
Basic usage example for DocEX library.

This example demonstrates:
1. Using default configuration
2. Creating and managing document baskets
3. Adding and updating documents
4. Working with document metadata
5. Getting basket statistics

Note: DocEX must be initialized first using the CLI command 'DocEX init'
"""

from docex import DocEX
from pathlib import Path
import json
import yaml
import sys

def main():
    try:
        
        # Create DocEX instance (will check initialization internally)
        docEX = DocEX()
        
        # Create or get a document basket (uses default storage config)
        basket_name = 'example_basket'
        basket = docEX.basket(basket_name)
        
        # Create some example documents
        docs_dir = Path('example_docs')
        docs_dir.mkdir(exist_ok=True)
        
        # Text document
        text_file = docs_dir / 'document.txt'
        text_file.write_text('This is a sample text document.')
        
        # JSON document
        json_file = docs_dir / 'data.json'
        json_file.write_text(json.dumps({'key': 'value'}))
        
        # Add documents with metadata
        text_doc = basket.add(
            str(text_file),
            document_type='text',
            metadata={
                'author': 'John Doe',
                'category': 'documentation'
            }
        )
        
        json_doc = basket.add(
            str(json_file),
            document_type='json',
            metadata={
                'author': 'Jane Smith',
                'category': 'data'
            }
        )
        
        # Get document details
        print("\nDocument Details:")
        print(text_doc.get_details())
        
        # Get document metadata
        print("\nDocument Metadata:")
        print(text_doc.get_metadata())
        
        # Find documents by metadata
        docs = basket.find_documents_by_metadata({'author': 'John Doe'})
        print("\nDocuments by John Doe:", len(docs))
        
        # Update a document
        text_file.write_text('Updated content')
        updated_doc = basket.update_document(text_doc.id, str(text_file))
        
        # Get basket statistics
        stats = basket.get_stats()
        print("\nBasket Statistics:")
        print(json.dumps(stats, indent=2, default=str))
        
        # List all baskets
        all_baskets = docEX.list_baskets()
        print("\nAll Baskets:")
        for b in all_baskets:
            print(f"- {b.name}: {b.description}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 