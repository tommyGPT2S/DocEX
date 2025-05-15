"""
DocEX - Document Management Library

This library provides a robust, extensible document management and transport system.
"""

from docex.docex import DocEX

# Setup DocEX with configuration
DocEX.setup(
    database={
        'type': 'sqlite',
        'sqlite': {'path': 'docex.db'}
    }
)

# Create DocEX instance
docex = DocEX()
basket = docex.create_basket('my_basket')

# Get available metadata keys
print(DocEX.get_metadata_keys())

__all__ = [
    'DocEX',          # Main entry point
    'DocBasket',      # Document basket
    'Document',       # Document class
    'Route',          # Transport route
    'UserContext',    # User context for auditing
]

__version__ = '0.1.9'
