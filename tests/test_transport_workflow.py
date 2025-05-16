from docex import DocFlow
from pathlib import Path
import json
import asyncio
from datetime import datetime
import os
from docex.db.connection import Database
from docex.transport.models import RouteOperation
from sqlalchemy import text

# Get environment from environment variable or default to development
env = os.getenv('DOCFLOW_ENV', 'development')

# Setup DocFlow with default configuration
DocFlow.setup()

# Create DocFlow instance
docflow = DocFlow()

def print_document_info(doc):
    """Helper function to print document information"""
    print(f"\nDocument Information:")
    print(f"Name: {doc.model.name}")
    print(f"Source: {doc.model.source}")
    print(f"Status: {doc.model.status}")
    print(f"Size: {doc.model.size} bytes")
    print(f"Checksum: {doc.model.checksum}")
    print("\nMetadata:")
    for key, value in doc.get_metadata().items():
        print(f"  {key}: {value}")
    
    # Print document operations
    print("\nDocument Operations:")
    for op in doc.get_operations():
        print(f"  - Type: {op['type']}")
        print(f"    Status: {op['status']}")
        print(f"    Created: {op['created_at']}")
        print(f"    Completed: {op['completed_at']}")
        if op.get('error'):
            print(f"    Error: {op['error']}")
        if op.get('details'):
            print(f"    Details: {json.dumps(op['details'], indent=2)}")
    
    # Print route operations
    print("\nRoute Operations:")
    for op in doc.get_route_operations():
        print(f"  - Type: {op['type']}")
        print(f"    Status: {op['status']}")
        print(f"    Created: {op['created_at']}")
        print(f"    Completed: {op['completed_at']}")
        if op.get('error'):
            print(f"    Error: {op['error']}")
        if op.get('details'):
            try:
                details = json.loads(op['details']) if isinstance(op['details'], str) else op['details']
                print(f"    Details: {json.dumps(details, indent=2)}")
            except (json.JSONDecodeError, TypeError):
                print(f"    Details: {op['details']}")

async def main():
    # Step 1: Get the download route
    download_route = docflow.get_route("download_route")
    if not download_route:
        raise Exception("Download route not found")

    # Step 2: Create a temporary location for downloaded file
    temp_download_path = Path('temp_download')
    temp_download_path.mkdir(exist_ok=True)
    local_file_path = temp_download_path / 'test_file.txt'

    # Step 3: Download the file using download route
    print("\n=== Downloading file using download route ===")
    result = await download_route.download('test_file.txt', local_file_path)
    if not result.success:
        raise Exception(f"Failed to download file: {result.error}")
    print("File downloaded successfully")

    # Step 4: Create a basket and add the downloaded file
    print("\n=== Creating basket and adding file ===")
    basket = docflow.create_basket("test_basket")
    doc = basket.add(
        str(local_file_path),
        metadata={
            'source_route': 'download_route',
            'download_time': datetime.now().isoformat(),
            'test_workflow': 'transport_test'
        }
    )
    print("Document added to basket")

    # Step 5: Get the upload route
    upload_route = docflow.get_route("upload_route")
    if not upload_route:
        raise Exception("Upload route not found")

    # Step 6: Upload the document using upload route
    print("\n=== Uploading document using upload route ===")
    result = await upload_route.upload_document(doc)
    if not result.success:
        raise Exception(f"Failed to upload document: {result.error}")
    print("Document uploaded successfully")

    # Add a small delay to allow database operations to complete
    await asyncio.sleep(0.1)

    # Step 7: Print document information
    print("\n=== Final Document Status ===")
    print_document_info(doc)

if __name__ == '__main__':
    asyncio.run(main()) 