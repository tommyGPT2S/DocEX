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

from docex.docCore import DocEX  # Updated to use docCore instead of docex
from docex.config.docex_config import DocEXConfig  # Updated import

__all__ = ['DocEX', 'DocEXConfig']

__version__ = '2.2.0'
