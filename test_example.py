from docex import DocEX
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_example():
    try:
        # Create DocEX instance
        docEX = DocEX()
        logger.info("Created DocEX instance")

        # Create or get a basket
        basket = docEX.basket('example_basket')
        logger.info(f"Created/retrieved basket: {basket.name}")

        # Create a test file
        test_file = Path('example.txt')
        test_file.write_text('This is a test document for DocEX.')
        logger.info(f"Created test file: {test_file}")

        # Add the document with metadata
        metadata = {'source': 'test', 'type': 'example'}
        doc = basket.add(str(test_file), metadata=metadata)
        logger.info(f"Added document with ID: {doc.id}")

        # List all baskets
        logger.info("\nListing all baskets:")
        for b in docEX.list_baskets():
            logger.info(f"- {b.name}")

        # List documents in our basket
        logger.info("\nListing documents in our basket:")
        for d in basket.list():
            logger.info(f"- {d.name} (ID: {d.id})")

        # Get document details
        logger.info("\nDocument details:")
        details = doc.get_details()
        logger.info(f"Details: {details}")

        # Get document content
        logger.info("\nDocument content:")
        content = doc.get_content(mode='text')
        logger.info(f"Content: {content}")

        # Get document metadata
        logger.info("\nDocument metadata:")
        meta = doc.get_metadata()
        logger.info(f"Metadata: {meta}")

    except Exception as e:
        logger.error(f"Error during test: {str(e)}")
        raise
    finally:
        # Clean up
        if test_file.exists():
            test_file.unlink()
            logger.info(f"Cleaned up test file: {test_file}")

if __name__ == '__main__':
    test_example() 