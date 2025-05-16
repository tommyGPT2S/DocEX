"""
Example demonstrating the use of the CSV to JSON processor.

This example:
1. Creates a test CSV file
2. Creates a document from the CSV file
3. Processes the document using the CSV to JSON processor
4. Displays the processing results
"""

import os
import csv
from pathlib import Path
from docex import DocEX
from docex.processors.factory import factory
from docex.processors.csv_to_json import CSVToJSONProcessor
import shutil

def create_test_csv(file_path: Path) -> Path:
    """Create a test CSV file with sample data and return the file path"""
    csv_file = file_path / 'test_data.csv'
    data = [
        {'name': 'John Doe', 'age': '30', 'city': 'New York'},
        {'name': 'Jane Smith', 'age': '25', 'city': 'Los Angeles'},
        {'name': 'Bob Johnson', 'age': '35', 'city': 'Chicago'}
    ]
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'age', 'city'])
        writer.writeheader()
        writer.writerows(data)
    return csv_file

def main():
    """Run the example"""
    # Initialize DocEX
    docEX = DocEX()
    
    # Create test directory
    test_dir = Path("test_data")
    test_dir.mkdir(exist_ok=True)
    
    try:
        # Create test CSV file
        csv_file = create_test_csv(test_dir)
        print(f"Created test CSV file: {csv_file}")
        
        # Get or create basket (same pattern as basic_usage.py)
        basket_name = "test_basket"
        try:
            basket = docEX.create_basket(basket_name)
            print(f"Created new basket: {basket_name}")
        except ValueError:
            print(f"Using existing basket: {basket_name}")
            baskets = docEX.list_baskets()
            basket = next((b for b in baskets if b.name == basket_name), None)
            if not basket:
                raise RuntimeError(f"Failed to get basket: {basket_name}")
        
        # Add document to basket
        document = basket.add(str(csv_file))
        print(f"Added document to basket: {document.name}")
        
        # Register the processor before getting it
        factory.register(CSVToJSONProcessor)
        # Get CSV to JSON processor using the factory
        processor = factory.get_processor("CSVToJSONProcessor")
        if not processor:
            print("Error: CSVToJSONProcessor not found")
            return
        
        # Process document
        result = processor.process(document)
        
        if result.success:
            print("Processing successful!")
            print(f"Output file: {result.content}")
            print("Metadata:", result.metadata)
        else:
            print("Processing failed:", result.error)
    
    finally:
        # Clean up test files and directories
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print("Cleaned up test files")

if __name__ == '__main__':
    main() 