"""
Minimal DocEX example - Hello World!

This example shows the absolute minimum steps needed to get started with DocEX:
1. Create a basket
2. Add a document
3. Get document details
4. Use UserContext for audit logging

Note: DocEX must be initialized first using the CLI command 'docex init'

Security Best Practices:
- Always use UserContext for audit logging
- UserContext enables operation tracking
"""

from docex import DocEX
from docex.context import UserContext
from pathlib import Path
import os
import sys

def main():
    try:
        # Create UserContext for audit logging
        user_context = UserContext(
            user_id="hello_user",
            user_email="hello@example.com"
        )
        
        # Create DocEX instance with UserContext (enables audit logging)
        docEX = DocEX(user_context=user_context)
        
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