"""
DocFlow - Document Management Library

This library provides a flexible and extensible document management system
with support for multiple storage backends and metadata handling.

Basic usage:
    from docflow import DocFlow

    # Setup DocFlow with configuration
    DocFlow.setup(
        database={
            'type': 'sqlite',
            'sqlite': {'path': 'docflow.db'}
        }
    )

    # Create a document basket
    docflow = DocFlow()
    basket = docflow.create_basket('my_basket')

    # Add documents
    doc = basket.add('path/to/document.txt')

    # Work with documents
    print(doc.get_details())

    # Get available metadata keys
    print(DocFlow.get_metadata_keys())
"""

from docflow.docflow import DocFlow
from docflow.docbasket import DocBasket, Document

__all__ = [
    'DocFlow',          # Main entry point
    'DocBasket',        # Document basket management
    'Document',         # Document operations
]

__version__ = '0.1.0'
