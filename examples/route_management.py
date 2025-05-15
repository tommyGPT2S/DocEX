"""
Route Management Example for DocEX

This example demonstrates:
1. Creating different types of routes
2. Managing route configurations
3. Listing and retrieving routes
4. Deleting routes
5. Working with route operations

Note: DocEX must be initialized first using the CLI command 'docex init'
"""

from docex import DocFlow
from docex.transport.config import TransportType, LocalTransportConfig
from pathlib import Path
import json
import os
import shutil
import sys

def print_route_info(route):
    """Print detailed route information."""
    print(f"\nRoute Information:")
    print(f"Name: {route.name}")
    print(f"Purpose: {route.purpose}")
    print(f"Protocol: {route.protocol}")
    print(f"Enabled: {route.enabled}")
    print(f"Capabilities:")
    print(f"  - Upload: {route.can_upload}")
    print(f"  - Download: {route.can_download}")
    print(f"  - List: {route.can_list}")
    print(f"  - Delete: {route.can_delete}")
    
    if route.other_party:
        print("\nOther Party:")
        print(f"  ID: {route.other_party.id}")
        print(f"  Name: {route.other_party.name}")
        print(f"  Type: {route.other_party.type}")

def main():
    try:
        # Create DocEX instance (will check initialization internally)
        docflow = DocFlow()
        
        # Create test directory for local routes
        test_dir = Path("test_data")
        if test_dir.exists():
            shutil.rmtree(test_dir)
        test_dir.mkdir()
        
        # 1. Create a local route for outbound files
        print("\n=== Creating Local Outbound Route ===")
        outbound_config = LocalTransportConfig(
            type=TransportType.LOCAL,
            name="outbound_transport",
            base_path=str(test_dir / "outbound"),
            create_dirs=True
        )
        
        outbound_route = docflow.create_route(
            name="outbound_route",
            transport_type=TransportType.LOCAL,
            config=outbound_config.model_dump(),
            other_party={
                "id": "partner1",
                "name": "Test Partner",
                "type": "customer"
            }
        )
        print_route_info(outbound_route)
        
        # 2. Create a local route for inbound files
        print("\n=== Creating Local Inbound Route ===")
        inbound_config = LocalTransportConfig(
            type=TransportType.LOCAL,
            name="inbound_transport",
            base_path=str(test_dir / "inbound"),
            create_dirs=True
        )
        
        inbound_route = docflow.create_route(
            name="inbound_route",
            transport_type=TransportType.LOCAL,
            config=inbound_config.model_dump(),
            other_party={
                "id": "partner1",
                "name": "Test Partner",
                "type": "customer"
            }
        )
        print_route_info(inbound_route)
        
        # 3. List all routes
        print("\n=== Listing All Routes ===")
        routes = docflow.list_routes()
        print(f"Found {len(routes)} routes:")
        for route in routes:
            print(f"- {route.name} ({route.protocol})")
        
        # 4. Get a specific route
        print("\n=== Getting Specific Route ===")
        retrieved_route = docflow.get_route("outbound_route")
        if retrieved_route:
            print(f"Successfully retrieved route: {retrieved_route.name}")
        
        # 5. Delete a route
        print("\n=== Deleting Route ===")
        result = docflow.delete_route("inbound_route")
        if result:
            print("Successfully deleted inbound_route")
        
        # 6. List routes again to verify deletion
        print("\n=== Verifying Route Deletion ===")
        routes = docflow.list_routes()
        print(f"Remaining routes: {len(routes)}")
        for route in routes:
            print(f"- {route.name} ({route.protocol})")
        
        # 7. Recreate the deleted route
        print("\n=== Recreating Deleted Route ===")
        inbound_route = docflow.create_route(
            name="inbound_route",
            transport_type=TransportType.LOCAL,
            config=inbound_config.model_dump(),
            other_party={
                "id": "partner1",
                "name": "Test Partner",
                "type": "customer"
            }
        )
        print_route_info(inbound_route)
        
        # 8. List routes one final time
        print("\n=== Final Route List ===")
        routes = docflow.list_routes()
        print(f"Total routes: {len(routes)}")
        for route in routes:
            print(f"- {route.name} ({route.protocol})")
        
        # 9. Get available transport types
        print("\n=== Available Transport Types ===")
        transport_types = docflow.get_available_transport_types()
        print("Available transport types:")
        for t_type in transport_types:
            print(f"- {t_type}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 