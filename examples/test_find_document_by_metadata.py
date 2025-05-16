import os
from docex import DocEX
from docex.db.connection import Database
from docex.db.repository import DocumentRepository

def test_find_document_by_metadata():
    # Initialize DocEX
    docEX = DocEX()
    db = Database()
    doc_repo = DocumentRepository(db)

    # Create a new basket
    basket = docEX.basket('test_basket_metadata')

    # Create a test file
    test_file_path = 'test_metadata.txt'
    with open(test_file_path, 'w') as f:
        f.write('Test content for metadata search')

    # Add the document to the basket with metadata
    doc = basket.add(test_file_path, metadata={'cus_PO': 'PO-000111'})

    # Find documents with the metadata key-value pair
    found_docs = doc_repo.find_document_by_metadata('cus_PO', 'PO-000111')

    # Print the found documents
    print('Found documents:')
    for found_doc in found_docs:
        print(f'Document ID: {found_doc.id}, Name: {found_doc.name}')

    # Clean up
    os.remove(test_file_path)

if __name__ == '__main__':
    test_find_document_by_metadata() 