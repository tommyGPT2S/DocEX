"""
Route File Transfer Example for DocEX

This example demonstrates:
1. Using existing routes created by route_management.py
2. Downloading files using a route
3. Adding downloaded files to a basket
4. Uploading documents using a route
5. Tracking document operations and status

Note: 
1. DocEX must be initialized first using the CLI command 'docex init'
2. Routes must be created first by running 'python examples/route_management.py'
"""

from docex import DocFlow
from docex.transport.config import RouteConfig, TransportType
from pathlib import Path
import json
import asyncio
from datetime import datetime
import sys
import shutil

def print_document_info(doc):
    """Print document and operation information."""
    print(f"\nDocument Information:")
    print(f"Name: {doc.model.name}")
    print(f"Source: {doc.model.source}")
    print(f"Status: {doc.model.status}")
    print(f"Size: {doc.model.size} bytes")
    print(f"Checksum: {doc.model.checksum}")
    print("\nMetadata:")
    for key, value in doc.get_metadata().items():
        print(f"  {key}: {value}")

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
    try:
        # Create DocEX instance (will check initialization internally)
        docflow = DocFlow()
        
        # Create test directories
        test_dir = Path("test_data")
        if test_dir.exists():
            shutil.rmtree(test_dir)
        test_dir.mkdir()
        
        # 1. Get the outbound route (will be used for download)
        outbound_route = docflow.get_route("outbound_route")
        if not outbound_route:
            print("Error: outbound_route not found.")
            print("Please run 'python examples/route_management.py' first to create the required routes.")
            sys.exit(1)

        # 2. Get the inbound route (will be used for upload)
        inbound_route = docflow.get_route("inbound_route")
        if not inbound_route:
            print("Error: inbound_route not found.")
            print("Please run 'python examples/route_management.py' first to create the required routes.")
            sys.exit(1)

        # 3. Prepare a local path for the downloaded file
        temp_download_path = test_dir / 'temp_download'
        temp_download_path.mkdir(exist_ok=True)
        local_file_path = temp_download_path / 'test_file.txt'

        # Create a test file to download
        test_file = Path(outbound_route.config['base_path']) / 'test_file.txt'
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text('This is a test file for download.')

        # 4. Download the file using the outbound route
        print("\n=== Downloading file using outbound route ===")
        result = await outbound_route.download('test_file.txt', local_file_path)
        if not result.success:
            raise RuntimeError(f"Failed to download file: {result.error}")
        print("File downloaded successfully")

        # 5. Get or create a basket
        print("\n=== Getting or creating basket ===")
        basket_name = "example_basket"
        try:
            basket = docflow.basket(basket_name)
            print(f"Created new basket: {basket_name}")
        except ValueError as e:
            print(f"Using existing basket: {basket_name}")
            # Get the existing basket
            baskets = docflow.list_baskets()
            basket = next((b for b in baskets if b.name == basket_name), None)
            if not basket:
                raise RuntimeError(f"Failed to get basket: {basket_name}")

        # 6. Add the downloaded file
        print("\n=== Adding file to basket ===")
        doc = basket.add(
            str(local_file_path),
            metadata={
                'source_route': 'outbound_route',
                'download_time': datetime.now().isoformat(),
                'example': 'route_file_transfer'
            }
        )
        print("Document added to basket")

        # 7. Upload the document using the inbound route
        print("\n=== Uploading document using inbound route ===")
        result = await inbound_route.upload_document(doc)
        if not result.success:
            raise RuntimeError(f"Failed to upload document: {result.error}")
        print("Document uploaded successfully")

        # 8. Print document information and operations
        print("\n=== Final Document Status ===")
        print_document_info(doc)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
