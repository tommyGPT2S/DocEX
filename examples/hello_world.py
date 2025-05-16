"""
Minimal DocFlow example - Hello World!

This example shows the absolute minimum steps needed to get started with DocFlow:
1. Create a basket
2. Add a document
3. Get document details

Note: DocFlow must be initialized first using the CLI command 'docflow init'
"""

from docex import DocEX
from pathlib import Path
import os
import sys

def main():
    try:
        # Create DocEX instance (will check initialization internally)
        docEX = DocEX()
        
        # Create a basket
        basket = docEX.basket('mybasket')
        
        # Create a simple text file
        hello_file = Path('hello.txt')
        hello_file.write_text('Hello scos.ai!')
        
        # Add the document to the basket
        doc = basket.add(str(hello_file))
        
        # Print document details
        print("\nDocument Details:")
        print(doc.get_details())
        
        hello_file.unlink()
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 