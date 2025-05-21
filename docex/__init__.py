"""
DocEX - Document Management Library

This library provides a flexible and extensible document management system
with support for multiple storage backends and metadata handling.

Basic usage:
    from docex import DocEX

    # Setup DocEX with configuration
    DocEX.setup(
        database={
            'type': 'sqlite',
            'sqlite': {'path': 'docex.db'}
        }
    )

    # Create a document basket
    docex = DocEX()
    basket = docex.create_basket('my_basket')

    # Add documents
    doc = basket.add('path/to/document.txt')

    # Work with documents
    print(doc.get_details())

    # Get available metadata keys
    print(DocEX.get_metadata_keys())
"""

from .docCore import DocEX
from docex.docbasket import DocBasket, Document

__all__ = [
    'DocEX',          # Main entry point
    'DocBasket',        # Document basket management
    'Document',         # Document operations
]

__version__ = '2.0.1'
