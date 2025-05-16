from docex import DocEX
from pathlib import Path

def test_basic():
    # Create DocEX instance
    docEX = DocEX()
    
    # Create a test basket
    basket = docEX.basket('test_basket')
    
    # Create a test file
    test_file = Path('test.txt')
    test_file.write_text('Hello DocEX!')
    
    try:
        # Add the document to the basket
        doc = basket.add(str(test_file))
        
        # Print document details
        print("Document added successfully!")
        print(f"Document ID: {doc.id}")
        print(f"Document name: {doc.name}")
        print(f"Document metadata: {doc.get_metadata()}")
        
    finally:
        # Clean up
        if test_file.exists():
            test_file.unlink()

if __name__ == '__main__':
    test_basic() 