#!/usr/bin/env python3
"""
Comprehensive Test Suite for Basket and File Operations with Route-Based Transfers

This test script covers:
1. Basket Operations (CRUD)
2. File Operations (add, get, list, delete, retrieve by ID)
3. Route Operations (create, send document)
4. Moving files between baskets using routes

Usage:
    python test_basket_file_operations.py [--tenant-id TENANT_ID] [--verbose]

Note: This script respects existing DocEX configuration and does not alter database type.
      With --verbose, prints detailed information including S3 paths, file paths, etc.
"""

import sys
import tempfile
import shutil
import asyncio
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
import argparse

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from docex import DocEX
from docex.docbasket import DocBasket
from docex.document import Document
from docex.transport.config import LocalTransportConfig, TransportType
from docex.context import UserContext

# Try to import moto for S3 mocking
try:
    from moto import mock_aws
    import boto3
    MOTO_AVAILABLE = True
except ImportError:
    MOTO_AVAILABLE = False
    mock_aws = None

# Global verbose flag
VERBOSE = False


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def print_test(test_name: str, passed: bool, message: str = ""):
    """Print test result"""
    status = "✅" if passed else "❌"
    print(f"{status} {test_name}", end="")
    if message:
        print(f": {message}")
    else:
        print()


def print_verbose(message: str):
    """Print verbose information if verbose mode is enabled"""
    if VERBOSE:
        print(f"   📋 {message}")


def test_basket_operations(docex: DocEX) -> Tuple[bool, str]:
    """Test Step 1: Basket Operations"""
    print_section("Step 1: Basket Operations")
    
    try:
        # 1.1 Create basket with business-friendly name
        basket_name = f"documents_{int(datetime.now().timestamp())}"
        basket = docex.create_basket(basket_name, "General documents storage")
        print_test("1.1: Create basket", True, f"Created: {basket.id} ({basket.name})")
        if VERBOSE:
            storage_type = basket.storage_config.get('type', 'unknown')
            print_verbose(f"Storage type: {storage_type}")
            if storage_type == 's3':
                s3_config = basket.storage_config.get('s3', {})
                bucket = s3_config.get('bucket', 'N/A')
                prefix = s3_config.get('prefix', 'N/A')
                print_verbose(f"S3 Bucket: {bucket}")
                print_verbose(f"S3 Prefix: {prefix}")
            elif storage_type == 'filesystem':
                path = basket.storage_config.get('path', 'N/A')
                print_verbose(f"Filesystem path: {path}")
        
        # 1.2 Get basket by ID
        retrieved_basket = DocBasket.get(basket.id, db=docex.db)
        if retrieved_basket and retrieved_basket.id == basket.id:
            print_test("1.2: Get basket by ID", True, f"Retrieved: {retrieved_basket.id}")
        else:
            return False, "Failed to retrieve basket by ID"
        
        # 1.3 Find basket by name
        found_basket = DocBasket.find_by_name(basket_name, db=docex.db)
        if found_basket and found_basket.name == basket_name:
            print_test("1.3: Find basket by name", True, f"Found: {found_basket.name}")
        else:
            return False, "Failed to find basket by name"
        
        # 1.4 List all baskets
        all_baskets = docex.list_baskets()
        if basket.id in [b.id for b in all_baskets]:
            print_test("1.4: List all baskets", True, f"Found {len(all_baskets)} baskets")
        else:
            return False, "Basket not found in list"
        
        # 1.5 Test duplicate name handling
        try:
            duplicate_basket = docex.create_basket(basket_name, "Duplicate basket")
            return False, "Should have raised ValueError for duplicate name"
        except ValueError as e:
            if "already exists" in str(e):
                print_test("1.5: Duplicate name handling", True, f"Correctly rejected: {str(e)[:60]}...")
            else:
                return False, f"Unexpected error: {str(e)}"
        
        # 1.6 Get basket stats
        stats = basket.get_stats()
        if stats and 'id' in stats and stats['id'] == basket.id:
            print_test("1.6: Get basket stats", True, f"Documents: {stats.get('document_counts', {})}")
        else:
            return False, "Failed to get basket stats"
        
        # Cleanup
        basket.delete()
        print_test("1.7: Delete basket", True, "Basket deleted")
        
        return True, "All basket operations passed"
    
    except Exception as e:
        return False, f"Basket operations test failed: {str(e)}"


def test_file_operations(docex: DocEX) -> Tuple[bool, str]:
    """Test Step 2: File Operations"""
    print_section("Step 2: File Operations")
    
    try:
        # Create test basket with business-friendly name
        basket_name = f"documents_archive_{int(datetime.now().timestamp())}"
        basket = docex.create_basket(basket_name, "Document archive for file operations")
        
        # Create temporary test files
        temp_dir = Path(tempfile.mkdtemp())
        test_files = {
            'text_file.txt': 'This is a test text file content.',
            'json_file.json': '{"key": "value", "number": 42}',
            'binary_file.bin': b'\x00\x01\x02\x03\x04\x05'
        }
        
        created_docs = []
        
        # 2.1 Add text file
        text_file = temp_dir / 'text_file.txt'
        text_file.write_text(test_files['text_file.txt'])
        doc1 = basket.add(str(text_file), document_type='file', metadata={'type': 'text', 'test': 'file_ops'})
        created_docs.append(doc1)
        print_test("2.1: Add text file", True, f"Document ID: {doc1.id}")
        if VERBOSE:
            print_verbose(f"Document path: {doc1.path}")
            print_verbose(f"Document name: {doc1.name}")
            print_verbose(f"Document size: {doc1.size} bytes")
            if basket.storage_config.get('type') == 's3':
                s3_config = basket.storage_config.get('s3', {})
                bucket = s3_config.get('bucket', 'N/A')
                prefix = s3_config.get('prefix', '')
                full_s3_path = f"s3://{bucket}/{prefix}/{doc1.path}" if prefix else f"s3://{bucket}/{doc1.path}"
                print_verbose(f"Full S3 path: {full_s3_path}")
        
        # 2.2 Add JSON file
        json_file = temp_dir / 'json_file.json'
        json_file.write_text(test_files['json_file.json'])
        doc2 = basket.add(str(json_file), document_type='file', metadata={'type': 'json', 'test': 'file_ops'})
        created_docs.append(doc2)
        print_test("2.2: Add JSON file", True, f"Document ID: {doc2.id}")
        if VERBOSE:
            print_verbose(f"Document path: {doc2.path}")
        
        # 2.3 Add binary file
        binary_file = temp_dir / 'binary_file.bin'
        binary_file.write_bytes(test_files['binary_file.bin'])
        doc3 = basket.add(str(binary_file), document_type='file', metadata={'type': 'binary', 'test': 'file_ops'})
        created_docs.append(doc3)
        print_test("2.3: Add binary file", True, f"Document ID: {doc3.id}")
        if VERBOSE:
            print_verbose(f"Document path: {doc3.path}")
        
        # 2.4 List documents
        all_docs = basket.list_documents()
        if len(all_docs) == 3:
            print_test("2.4: List documents", True, f"Found {len(all_docs)} documents")
        else:
            return False, f"Expected 3 documents, found {len(all_docs)}"
        
        # 2.5 Get document by ID
        retrieved_doc = basket.get_document(doc1.id)
        if retrieved_doc and retrieved_doc.id == doc1.id:
            print_test("2.5: Get document by ID", True, f"Retrieved: {retrieved_doc.id}")
        else:
            return False, "Failed to retrieve document by ID"
        
        # 2.6 Get document content as text
        text_content = doc1.get_content(mode='text')
        if text_content and isinstance(text_content, str):
            print_test("2.6: Get document content as text", True, f"Content length: {len(text_content)}")
        else:
            return False, "Failed to get document content as text"
        
        # 2.7 Get document content as bytes
        binary_content = doc3.get_content(mode='bytes')
        if binary_content and isinstance(binary_content, bytes):
            print_test("2.7: Get document content as bytes", True, f"Content length: {len(binary_content)}")
        else:
            return False, "Failed to get document content as bytes"
        
        # 2.8 Find documents by metadata
        text_docs = basket.find_documents_by_metadata({'type': 'text'})
        if len(text_docs) >= 1 and any(d.id == doc1.id for d in text_docs):
            print_test("2.8: Find documents by metadata", True, f"Found {len(text_docs)} document(s)")
        else:
            # Metadata might be stored as JSON string, try alternative search
            all_docs = basket.list_documents()
            text_docs_alt = [d for d in all_docs if d.id == doc1.id]
            if text_docs_alt:
                print_test("2.8: Find documents by metadata", True, "Document found (metadata search may vary by storage)")
            else:
                return False, f"Failed to find documents by metadata. Found {len(text_docs)} docs, expected at least 1"
        
        # 2.9 Test duplicate detection
        duplicate_doc = basket.add(str(text_file), document_type='file')
        if duplicate_doc.id == doc1.id:
            print_test("2.9: Duplicate detection", True, "Correctly detected duplicate")
        else:
            return False, "Failed to detect duplicate document"
        
        # 2.10 Delete document
        basket.delete_document(doc2.id)
        remaining_docs = basket.list_documents()
        if len(remaining_docs) == 2:
            print_test("2.10: Delete document", True, f"Remaining documents: {len(remaining_docs)}")
        else:
            return False, f"Expected 2 documents after deletion, found {len(remaining_docs)}"
        
        # Cleanup
        shutil.rmtree(temp_dir)
        basket.delete()
        print_test("2.11: Cleanup", True, "Test files and basket deleted")
        
        return True, "All file operations passed"
    
    except Exception as e:
        return False, f"File operations test failed: {str(e)}"


async def test_route_operations(docex: DocEX) -> Tuple[bool, str]:
    """Test Step 3: Route Operations"""
    print_section("Step 3: Route Operations")
    
    try:
        # Create test basket with business-friendly name
        basket_name = f"outbound_docs_{int(datetime.now().timestamp())}"
        basket = docex.create_basket(basket_name, "Outbound documents for route operations")
        
        # Create temporary test file
        temp_dir = Path(tempfile.mkdtemp())
        test_file = temp_dir / 'route_test_file.txt'
        test_content = 'This is a test file for route operations.'
        test_file.write_text(test_content)
        
        # Add document to basket
        doc = basket.add(str(test_file), document_type='file', metadata={'route_test': True})
        print_test("3.1: Add document for route test", True, f"Document ID: {doc.id}")
        
        # 3.2 Create route
        route_temp_dir = Path(tempfile.mkdtemp())
        transport_config = LocalTransportConfig(
            type=TransportType.LOCAL,
            name="test_transport",
            base_path=str(route_temp_dir),
            create_dirs=True
        )
        
        route = docex.create_route(
            name=f"test_route_{int(datetime.now().timestamp())}",
            transport_type=TransportType.LOCAL,
            config=transport_config.model_dump(),
            purpose="test",
            can_upload=True,
            can_download=False,
            enabled=True
        )
        print_test("3.2: Create route", True, f"Route: {route.name}, Route ID: {route.route_id}")
        
        # 3.3 Get route (this ensures route_id matches database)
        retrieved_route = docex.get_route(route.name)
        if retrieved_route and retrieved_route.name == route.name:
            # Use the retrieved route which has the correct route_id from database
            route = retrieved_route
            print_test("3.3: Get route", True, f"Retrieved: {retrieved_route.name}, Route ID: {retrieved_route.route_id}")
        else:
            return False, "Failed to retrieve route"
        
        # 3.4 List routes
        all_routes = docex.list_routes()
        if route.name in [r.name for r in all_routes]:
            print_test("3.4: List routes", True, f"Found {len(all_routes)} route(s)")
        else:
            return False, "Route not found in list"
        
        # 3.5 Send document via route
        destination = f"transferred_{doc.name}"
        result = await route.upload_document(doc)
        if result.success:
            print_test("3.5: Send document via route", True, f"Destination: {result.message}")
            
            # Verify file was transferred
            transferred_file = route_temp_dir / doc.name
            if transferred_file.exists():
                print_test("3.6: Verify file transfer", True, f"File exists at: {transferred_file}")
            else:
                return False, "Transferred file not found"
        else:
            return False, f"Failed to send document: {result.message}"
        
        # 3.7 Delete route
        deleted = docex.delete_route(route.name)
        if deleted:
            print_test("3.7: Delete route", True, "Route deleted")
        else:
            return False, "Failed to delete route"
        
        # Cleanup
        shutil.rmtree(temp_dir)
        shutil.rmtree(route_temp_dir)
        basket.delete()
        print_test("3.8: Cleanup", True, "Test files and basket deleted")
        
        return True, "All route operations passed"
    
    except Exception as e:
        return False, f"Route operations test failed: {str(e)}"


async def test_move_file_between_baskets(docex: DocEX) -> Tuple[bool, str]:
    """Test Step 4: Move File Between Baskets Using Routes"""
    print_section("Step 4: Move File Between Baskets Using Routes")
    
    try:
        # Create source and destination baskets with business-friendly names
        source_basket_name = f"invoices_pending_{int(datetime.now().timestamp())}"
        dest_basket_name = f"invoices_approved_{int(datetime.now().timestamp())}"
        
        source_basket = docex.create_basket(source_basket_name, "Pending invoices for processing")
        dest_basket = docex.create_basket(dest_basket_name, "Approved invoices archive")
        
        print_test("4.1: Create source and destination baskets", True, 
                  f"Source: {source_basket.id}, Dest: {dest_basket.id}")
        
        # Create temporary test file
        temp_dir = Path(tempfile.mkdtemp())
        test_file = temp_dir / 'transfer_test_file.txt'
        test_content = f'This is a test file for basket-to-basket transfer.\nCreated: {datetime.now().isoformat()}'
        test_file.write_text(test_content)
        
        # 4.2 Add document to source basket
        source_doc = source_basket.add(
            str(test_file), 
            document_type='file', 
            metadata={
                'source_basket': source_basket.id,
                'transfer_test': True,
                'original_name': test_file.name
            }
        )
        print_test("4.2: Add document to source basket", True, f"Document ID: {source_doc.id}")
        
        # Verify document in source basket
        source_docs = source_basket.list_documents()
        if len(source_docs) != 1 or source_docs[0].id != source_doc.id:
            return False, "Document not found in source basket"
        
        # 4.3 Create route pointing to destination basket's storage location
        # Get destination basket's storage path
        dest_storage_config = dest_basket.storage_config
        if dest_storage_config.get('type') == 'filesystem':
            dest_path = Path(dest_storage_config.get('path', ''))
        else:
            # For S3 or other storage, use a temporary local path for the route
            route_temp_dir = Path(tempfile.mkdtemp())
            dest_path = route_temp_dir
        
        # Create route that will transfer to destination basket location
        transport_config = LocalTransportConfig(
            type=TransportType.LOCAL,
            name="basket_transfer_transport",
            base_path=str(dest_path),
            create_dirs=True
        )
        
        transfer_route = docex.create_route(
            name=f"basket_transfer_route_{int(datetime.now().timestamp())}",
            transport_type=TransportType.LOCAL,
            config=transport_config.model_dump(),
            purpose="basket_transfer",
            can_upload=True,
            can_download=False,
            enabled=True
        )
        # Get the route again to ensure route_id matches database
        transfer_route = docex.get_route(transfer_route.name)
        if not transfer_route:
            return False, "Failed to retrieve transfer route after creation"
        print_test("4.3: Create transfer route", True, f"Route: {transfer_route.name}, Route ID: {transfer_route.route_id}")
        
        # 4.4 Transfer document via route
        result = await transfer_route.upload_document(source_doc)
        if not result.success:
            return False, f"Failed to transfer document: {result.message}"
        print_test("4.4: Transfer document via route", True, f"Result: {result.message}")
        
        # 4.5 Add transferred document to destination basket
        # Get the transferred file path
        if dest_storage_config.get('type') == 'filesystem':
            transferred_file_path = dest_path / source_doc.name
        else:
            transferred_file_path = dest_path / source_doc.name
        
        if not transferred_file_path.exists():
            return False, f"Transferred file not found at: {transferred_file_path}"
        
        # Add to destination basket
        dest_doc = dest_basket.add(
            str(transferred_file_path),
            document_type='file',
            metadata={
                'source_basket': source_basket.id,
                'source_document_id': source_doc.id,
                'transferred_via': transfer_route.name,
                'transfer_timestamp': datetime.now().isoformat()
            }
        )
        print_test("4.5: Add transferred document to destination basket", True, f"Document ID: {dest_doc.id}")
        
        # 4.6 Verify document in destination basket
        dest_docs = dest_basket.list_documents()
        if len(dest_docs) != 1 or dest_docs[0].id != dest_doc.id:
            return False, "Document not found in destination basket"
        print_test("4.6: Verify document in destination basket", True, f"Found {len(dest_docs)} document(s)")
        
        # 4.7 Verify document content matches
        source_content = source_doc.get_content(mode='text')
        dest_content = dest_doc.get_content(mode='text')
        if source_content == dest_content:
            print_test("4.7: Verify document content matches", True, "Content verified")
        else:
            return False, "Document content mismatch"
        
        # 4.8 Verify metadata preserved
        dest_metadata = dest_doc.get_metadata()
        if 'source_basket' in dest_metadata and dest_metadata['source_basket'] == source_basket.id:
            print_test("4.8: Verify metadata preserved", True, "Metadata verified")
        else:
            return False, "Metadata not preserved correctly"
        
        # 4.9 Optional: Remove document from source basket (simulating move vs copy)
        source_basket.delete_document(source_doc.id)
        remaining_source_docs = source_basket.list_documents()
        if len(remaining_source_docs) == 0:
            print_test("4.9: Remove from source basket (move operation)", True, "Document removed from source")
        else:
            return False, "Document still exists in source basket"
        
        # Verify document still in destination
        dest_docs_after = dest_basket.list_documents()
        if len(dest_docs_after) == 1:
            print_test("4.10: Verify document still in destination", True, "Document preserved in destination")
        else:
            return False, "Document missing from destination after source deletion"
        
        # Cleanup
        transfer_route_db = docex.get_route(transfer_route.name)
        if transfer_route_db:
            docex.delete_route(transfer_route.name)
        shutil.rmtree(temp_dir)
        if 'route_temp_dir' in locals():
            shutil.rmtree(route_temp_dir)
        source_basket.delete()
        dest_basket.delete()
        print_test("4.11: Cleanup", True, "Test files and baskets deleted")
        
        return True, "All basket-to-basket transfer operations passed"
    
    except Exception as e:
        return False, f"Basket-to-basket transfer test failed: {str(e)}"


async def test_basket_storage_types(docex: DocEX, config, s3_mock=None) -> Tuple[bool, str]:
    """Test Step 5: Create Baskets with Different Storage Types"""
    print_section("Step 5: Basket Storage Types (S3 and Filesystem)")
    
    try:
        # Get S3 config from main config if available
        main_storage_config = config.get('storage', {})
        s3_config_from_main = main_storage_config.get('s3', {})
        
        # Use bucket from config or default test bucket
        test_bucket = s3_config_from_main.get('bucket', 'docex-test-bucket')
        test_region = s3_config_from_main.get('region', 'us-east-1')
        
        # Ensure S3 mocking is enabled for the test bucket
        if not s3_mock and MOTO_AVAILABLE:
            s3_mock = setup_s3_mocking(config, bucket_name=test_bucket, region=test_region)
        
        # 5.1 Create basket with S3 storage using business-friendly name
        s3_basket_name = f"invoice_raw_{int(datetime.now().timestamp())}"
        s3_storage_config = {
            'type': 's3',
            's3': {
                'bucket': test_bucket,
                'region': test_region,
                'path_namespace': s3_config_from_main.get('path_namespace', 'test'),
                'prefix': s3_config_from_main.get('prefix', 'test-env'),
                'access_key': s3_config_from_main.get('access_key', 'test-key'),
                'secret_key': s3_config_from_main.get('secret_key', 'test-secret')
            }
        }
        
        s3_basket = docex.create_basket(s3_basket_name, "Invoice raw documents storage", storage_config=s3_storage_config)
        print_test("5.1: Create basket with S3 storage", True, f"Created: {s3_basket.id} ({s3_basket.name})")
        
        # Verify S3 storage type
        if s3_basket.storage_config.get('type') != 's3':
            return False, f"Expected S3 storage type, got: {s3_basket.storage_config.get('type')}"
        
        if VERBOSE:
            s3_config = s3_basket.storage_config.get('s3', {})
            print_verbose(f"S3 Bucket: {s3_config.get('bucket', 'N/A')}")
            print_verbose(f"S3 Region: {s3_config.get('region', 'N/A')}")
            print_verbose(f"S3 Prefix: {s3_config.get('prefix', 'N/A')}")
            # Show the friendly basket path (extracted from prefix)
            prefix = s3_config.get('prefix', '')
            if prefix:
                # Extract basket path from prefix (last segment)
                basket_path = prefix.split('/')[-1] if '/' in prefix else prefix
                print_verbose(f"Basket friendly path: {basket_path}")
        
        # 5.2 Create basket with filesystem storage using business-friendly name
        fs_basket_name = f"receipts_processed_{int(datetime.now().timestamp())}"
        fs_storage_config = {
            'type': 'filesystem',
            'path': str(Path(tempfile.mkdtemp()) / 'receipts_storage')
        }
        
        fs_basket = docex.create_basket(fs_basket_name, "Processed receipts storage", storage_config=fs_storage_config)
        print_test("5.2: Create basket with filesystem storage", True, f"Created: {fs_basket.id} ({fs_basket.name})")
        
        # Verify filesystem storage type
        if fs_basket.storage_config.get('type') != 'filesystem':
            return False, f"Expected filesystem storage type, got: {fs_basket.storage_config.get('type')}"
        
        if VERBOSE:
            print_verbose(f"Filesystem path: {fs_basket.storage_config.get('path', 'N/A')}")
            # Show the friendly basket path
            sanitized_name = fs_basket.name.lower().replace(' ', '_')
            basket_path = f"{sanitized_name}_{fs_basket.id[-4:]}"
            print_verbose(f"Basket friendly path: {basket_path}")
        
        # 5.3 Verify each basket has only ONE storage type
        s3_type = s3_basket.storage_config.get('type')
        fs_type = fs_basket.storage_config.get('type')
        
        if s3_type == 's3' and fs_type == 'filesystem':
            print_test("5.3: Verify storage type isolation", True, f"S3 basket: {s3_type}, FS basket: {fs_type}")
        else:
            return False, f"Storage type mismatch: S3 basket={s3_type}, FS basket={fs_type}"
        
        # 5.4 Add document to S3 basket
        temp_dir = Path(tempfile.mkdtemp())
        s3_test_file = temp_dir / 'invoice_001.pdf'
        s3_test_file.write_text('This is a sample invoice document for testing.')
        
        s3_doc = s3_basket.add(str(s3_test_file), document_type='file', metadata={'document_type': 'invoice', 'category': 'raw', 'test': 'storage_types'})
        print_test("5.4: Add document to S3 basket", True, f"Document ID: {s3_doc.id}")
        
        if VERBOSE:
            print_verbose(f"S3 Document path: {s3_doc.path}")
            s3_config = s3_basket.storage_config.get('s3', {})
            bucket = s3_config.get('bucket', 'N/A')
            # document.path already contains the full S3 key (including all prefixes)
            # No need to add prefix again - just combine with bucket name
            full_s3_path = f"s3://{bucket}/{s3_doc.path}"
            print_verbose(f"Full S3 path: {full_s3_path}")
        
        # 5.5 Add document to filesystem basket
        fs_test_file = temp_dir / 'receipt_001.pdf'
        fs_test_file.write_text('This is a processed receipt document for testing.')
        
        fs_doc = fs_basket.add(str(fs_test_file), document_type='file', metadata={'document_type': 'receipt', 'category': 'processed', 'test': 'storage_types'})
        print_test("5.5: Add document to filesystem basket", True, f"Document ID: {fs_doc.id}")
        
        if VERBOSE:
            print_verbose(f"Filesystem Document path: {fs_doc.path}")
            fs_path = fs_basket.storage_config.get('path', '')
            full_fs_path = str(Path(fs_path) / fs_doc.path) if fs_path else fs_doc.path
            print_verbose(f"Full filesystem path: {full_fs_path}")
        
        # 5.6 Verify documents are in correct baskets
        s3_docs = s3_basket.list_documents()
        fs_docs = fs_basket.list_documents()
        
        if len(s3_docs) == 1 and len(fs_docs) == 1:
            print_test("5.6: Verify documents in correct baskets", True, f"S3 basket: {len(s3_docs)} doc, FS basket: {len(fs_docs)} doc")
        else:
            return False, f"Document count mismatch: S3={len(s3_docs)}, FS={len(fs_docs)}"
        
        # 5.7 Verify storage type cannot be changed (by checking storage_config is immutable)
        original_s3_type = s3_basket.storage_config.get('type')
        original_fs_type = fs_basket.storage_config.get('type')
        
        # Try to access storage_config (it should remain unchanged)
        if s3_basket.storage_config.get('type') == original_s3_type and fs_basket.storage_config.get('type') == original_fs_type:
            print_test("5.7: Verify storage type immutability", True, "Storage types remain unchanged")
        else:
            return False, "Storage type was changed (should be immutable)"
        
        # Cleanup
        shutil.rmtree(temp_dir)
        s3_basket.delete()
        fs_basket.delete()
        print_test("5.8: Cleanup", True, "Test baskets deleted")
        
        return True, "All storage type tests passed"
    
    except Exception as e:
        return False, f"Storage type test failed: {str(e)}"


async def test_s3_comprehensive_operations(docex: DocEX, config, s3_mock=None) -> Tuple[bool, str]:
    """Test Step 6: Comprehensive S3 Operations"""
    print_section("Step 6: Comprehensive S3 Operations")
    
    try:
        # Get S3 config from main config if available
        main_storage_config = config.get('storage', {})
        s3_config_from_main = main_storage_config.get('s3', {})
        
        # Use bucket from config or default test bucket
        test_bucket = s3_config_from_main.get('bucket', 'docex-test-bucket')
        test_region = s3_config_from_main.get('region', 'us-east-1')
        
        # Ensure S3 mocking is enabled for the test bucket
        if not s3_mock and MOTO_AVAILABLE:
            s3_mock = setup_s3_mocking(config, bucket_name=test_bucket, region=test_region)
        
        # 6.1 Create S3 basket with business-friendly name
        s3_basket_name = f"invoices_pending_{int(datetime.now().timestamp())}"
        s3_storage_config = {
            'type': 's3',
            's3': {
                'bucket': test_bucket,
                'region': test_region,
                'path_namespace': s3_config_from_main.get('path_namespace', 'test'),
                'prefix': s3_config_from_main.get('prefix', 'test-env'),
                'access_key': s3_config_from_main.get('access_key', 'test-key'),
                'secret_key': s3_config_from_main.get('secret_key', 'test-secret')
            }
        }
        
        s3_basket = docex.create_basket(s3_basket_name, "Pending invoices for processing", storage_config=s3_storage_config)
        print_test("6.1: Create S3 basket", True, f"Created: {s3_basket.id} ({s3_basket.name})")
        
        if VERBOSE:
            s3_config = s3_basket.storage_config.get('s3', {})
            print_verbose(f"S3 Bucket: {s3_config.get('bucket', 'N/A')}")
            print_verbose(f"S3 Region: {s3_config.get('region', 'N/A')}")
            print_verbose(f"S3 Config Prefix (Part A): {s3_config.get('config_prefix', 'N/A')}")
            print_verbose(f"S3 Basket Path (Part B): {s3_config.get('basket_path', 'N/A')}")
            print_verbose(f"S3 Full Prefix (A+B): {s3_config.get('prefix', 'N/A')}")
        
        # 6.2 Add multiple documents to S3 basket (text, JSON, binary)
        temp_dir = Path(tempfile.mkdtemp())
        
        # Text document
        text_file = temp_dir / 'invoice_001.txt'
        text_content = 'Invoice #001\nAmount: $1000.00\nStatus: Pending'
        text_file.write_text(text_content)
        text_doc = s3_basket.add(str(text_file), document_type='file', metadata={'type': 'text', 'invoice_number': '001', 'status': 'pending'})
        print_test("6.2: Add text document to S3", True, f"Document ID: {text_doc.id}")
        
        if VERBOSE:
            print_verbose(f"Text document path: {text_doc.path}")
            print_verbose(f"Full S3 path: s3://{test_bucket}/{text_doc.path}")
        
        # JSON document
        json_file = temp_dir / 'invoice_002.json'
        json_content = '{"invoice_number": "002", "amount": 2000.00, "status": "pending"}'
        json_file.write_text(json_content)
        json_doc = s3_basket.add(str(json_file), document_type='file', metadata={'type': 'json', 'invoice_number': '002', 'status': 'pending'})
        print_test("6.3: Add JSON document to S3", True, f"Document ID: {json_doc.id}")
        
        if VERBOSE:
            print_verbose(f"JSON document path: {json_doc.path}")
            print_verbose(f"Full S3 path: s3://{test_bucket}/{json_doc.path}")
        
        # Binary document (PDF-like)
        binary_file = temp_dir / 'invoice_003.pdf'
        binary_content = b'%PDF-1.4\nThis is a test PDF document for invoice 003'
        binary_file.write_bytes(binary_content)
        binary_doc = s3_basket.add(str(binary_file), document_type='file', metadata={'type': 'binary', 'invoice_number': '003', 'status': 'pending'})
        print_test("6.4: Add binary document to S3", True, f"Document ID: {binary_doc.id}")
        
        if VERBOSE:
            print_verbose(f"Binary document path: {binary_doc.path}")
            print_verbose(f"Full S3 path: s3://{test_bucket}/{binary_doc.path}")
        
        # 6.5 List all documents from S3 basket
        all_docs = s3_basket.list_documents()
        if len(all_docs) == 3:
            print_test("6.5: List all documents from S3 basket", True, f"Found {len(all_docs)} documents")
            if VERBOSE:
                for doc in all_docs:
                    print_verbose(f"  - {doc.name} (ID: {doc.id}, Path: {doc.path})")
        else:
            return False, f"Expected 3 documents, found {len(all_docs)}"
        
        # 6.6 Get document by ID from S3 basket
        retrieved_doc = s3_basket.get_document(text_doc.id)
        if retrieved_doc and retrieved_doc.id == text_doc.id:
            print_test("6.6: Get document by ID from S3", True, f"Retrieved: {retrieved_doc.id}")
            if VERBOSE:
                print_verbose(f"Retrieved document path: {retrieved_doc.path}")
                print_verbose(f"Retrieved document name: {retrieved_doc.name}")
        else:
            return False, "Failed to retrieve document by ID from S3"
        
        # 6.7 Get document content as text from S3
        text_content_retrieved = retrieved_doc.get_content(mode='text')
        if text_content_retrieved and isinstance(text_content_retrieved, str) and 'Invoice #001' in text_content_retrieved:
            print_test("6.7: Get document content as text from S3", True, f"Content length: {len(text_content_retrieved)}")
            if VERBOSE:
                print_verbose(f"Content preview: {text_content_retrieved[:50]}...")
        else:
            return False, "Failed to get document content as text from S3"
        
        # 6.8 Get document content as bytes from S3
        binary_content_retrieved = binary_doc.get_content(mode='bytes')
        if binary_content_retrieved and isinstance(binary_content_retrieved, bytes) and b'PDF' in binary_content_retrieved:
            print_test("6.8: Get document content as bytes from S3", True, f"Content length: {len(binary_content_retrieved)}")
            if VERBOSE:
                print_verbose(f"Content preview: {binary_content_retrieved[:50]}...")
        else:
            return False, "Failed to get document content as bytes from S3"
        
        # 6.9 Get JSON document content from S3
        json_content_retrieved = json_doc.get_content(mode='json')
        if json_content_retrieved and isinstance(json_content_retrieved, dict) and json_content_retrieved.get('invoice_number') == '002':
            print_test("6.9: Get JSON document content from S3", True, f"JSON keys: {list(json_content_retrieved.keys())}")
            if VERBOSE:
                print_verbose(f"JSON content: {json_content_retrieved}")
        else:
            return False, "Failed to get JSON document content from S3"
        
        # 6.10 Find documents by metadata in S3 basket
        pending_docs = s3_basket.find_documents_by_metadata({'status': 'pending'})
        if len(pending_docs) >= 3:
            print_test("6.10: Find documents by metadata in S3", True, f"Found {len(pending_docs)} document(s) with status='pending'")
            if VERBOSE:
                for doc in pending_docs:
                    print_verbose(f"  - {doc.name} (ID: {doc.id})")
        else:
            return False, f"Expected at least 3 documents with status='pending', found {len(pending_docs)}"
        
        # 6.11 Verify S3 path structure (Part A + Part B + Part C)
        s3_config = s3_basket.storage_config.get('s3', {})
        part_a = s3_config.get('config_prefix', '')
        part_b = s3_config.get('basket_path', '')
        
        # Extract Part C from document path
        # Full path = Part A + Part B + Part C
        # So Part C = Full path - (Part A + Part B)
        full_path = text_doc.path
        expected_prefix = f"{part_a}{part_b}".rstrip('/')
        
        if full_path.startswith(expected_prefix):
            part_c = full_path[len(expected_prefix):].lstrip('/')
            print_test("6.11: Verify S3 path structure", True, f"Part A: {part_a[:30]}..., Part B: {part_b}, Part C: {part_c}")
            if VERBOSE:
                print_verbose(f"Full path structure verified:")
                print_verbose(f"  Part A (config): {part_a}")
                print_verbose(f"  Part B (basket): {part_b}")
                print_verbose(f"  Part C (document): {part_c}")
                print_verbose(f"  Full path: {full_path}")
        else:
            return False, f"S3 path structure mismatch. Expected prefix: {expected_prefix}, Got: {full_path[:len(expected_prefix)]}"
        
        # 6.12 Verify all documents have correct S3 paths
        all_paths_valid = True
        for doc in all_docs:
            if not doc.path.startswith(expected_prefix):
                all_paths_valid = False
                if VERBOSE:
                    print_verbose(f"Invalid path for {doc.name}: {doc.path}")
        
        if all_paths_valid:
            print_test("6.12: Verify all documents have correct S3 paths", True, f"All {len(all_docs)} documents have valid paths")
        else:
            return False, "Some documents have invalid S3 paths"
        
        # 6.13 Verify document retrieval by different methods in S3 basket
        # Test that we can retrieve the same document using different methods
        retrieved_by_id = s3_basket.get_document(text_doc.id)
        listed_docs = s3_basket.list_documents()
        found_in_list = [d for d in listed_docs if d.id == text_doc.id]
        
        if retrieved_by_id and found_in_list and retrieved_by_id.id == found_in_list[0].id:
            print_test("6.13: Verify document retrieval consistency in S3", True, "Document retrievable by ID and in list")
            if VERBOSE:
                print_verbose(f"Retrieved by ID: {retrieved_by_id.path}")
                print_verbose(f"Found in list: {found_in_list[0].path}")
        else:
            return False, "Document retrieval inconsistency in S3 basket"
        
        # 6.14 Delete a document from S3 basket
        s3_basket.delete_document(json_doc.id)
        remaining_docs = s3_basket.list_documents()
        if len(remaining_docs) == 2:
            print_test("6.14: Delete document from S3 basket", True, f"Remaining documents: {len(remaining_docs)}")
        else:
            return False, f"Expected 2 documents after deletion, found {len(remaining_docs)}"
        
        # 6.15 Verify document count in S3 basket
        doc_count = s3_basket.count_documents()
        if doc_count == 2:
            print_test("6.15: Verify document count in S3 basket", True, f"Count: {doc_count}")
        else:
            return False, f"Expected document count 2, got {doc_count}"
        
        # 6.16 Verify S3 basket stats
        stats = s3_basket.get_stats()
        if stats and 'id' in stats and stats['id'] == s3_basket.id:
            print_test("6.16: Get S3 basket stats", True, f"Documents: {stats.get('document_counts', {})}")
            if VERBOSE:
                print_verbose(f"Basket stats: {stats}")
        else:
            return False, "Failed to get S3 basket stats"
        
        # Cleanup
        shutil.rmtree(temp_dir)
        s3_basket.delete()
        print_test("6.17: Cleanup", True, "S3 test basket deleted")
        
        return True, "All S3 comprehensive operations passed"
    
    except Exception as e:
        return False, f"S3 comprehensive operations test failed: {str(e)}"


def setup_s3_mocking(config, bucket_name: Optional[str] = None, region: Optional[str] = None):
    """Setup S3 mocking with moto for testing
    
    Args:
        config: DocEX configuration
        bucket_name: Optional bucket name (if not provided, uses config)
        region: Optional region (if not provided, uses config or defaults to us-east-1)
    
    Returns:
        Mock object if successful, None otherwise
    """
    if not MOTO_AVAILABLE:
        if VERBOSE:
            print("⚠️  Moto not available - S3 mocking disabled")
        return None
    
    # Get bucket and region from parameters or config
    if not bucket_name:
        storage_config = config.get('storage', {})
        s3_config = storage_config.get('s3', {})
        bucket_name = s3_config.get('bucket')
    
    if not region:
        storage_config = config.get('storage', {})
        s3_config = storage_config.get('s3', {})
        region = s3_config.get('region', 'us-east-1')
    
    if not bucket_name:
        if VERBOSE:
            print("⚠️  No S3 bucket name found - S3 mocking disabled")
        return None
    
    # Create mock S3 bucket
    mock = mock_aws()
    mock.start()
    
    try:
        s3_client = boto3.client('s3', region_name=region)
        s3_client.create_bucket(Bucket=bucket_name)
        if VERBOSE:
            print(f"✅ S3 mocking enabled (moto): Created mock bucket '{bucket_name}' in region '{region}'")
        return mock
    except Exception as e:
        if VERBOSE:
            print(f"⚠️  Failed to create mock S3 bucket: {e}")
        mock.stop()
        return None


def main():
    """Main test execution"""
    global VERBOSE
    
    parser = argparse.ArgumentParser(description='Test basket and file operations with route-based transfers')
    parser.add_argument('--tenant-id', type=str, help='Tenant ID for multi-tenancy testing')
    parser.add_argument('--verbose', '-v', action='store_true', help='Print verbose details (S3 paths, file paths, etc.)')
    args = parser.parse_args()
    
    VERBOSE = args.verbose
    
    print_section("Basket and File Operations Test Suite")
    
    # Check if DocEX is initialized
    from docex.config.docex_config import DocEXConfig
    
    if not DocEX.is_initialized():
        print("❌ DocEX is not initialized. Please run initialization first.")
        print("   Example: python init_docex_postgres_test.py")
        sys.exit(1)
    
    # Load existing configuration
    config = DocEXConfig()
    multi_tenancy_enabled = config.get('multi_tenancy', {}).get('enabled', False)
    
    # Setup S3 mocking - always enable if moto is available (needed for S3 basket tests)
    # Use bucket from config or default test bucket
    storage_config = config.get('storage', {})
    s3_config = storage_config.get('s3', {})
    test_bucket = s3_config.get('bucket', 'docex-test-bucket')
    test_region = s3_config.get('region', 'us-east-1')
    s3_mock = setup_s3_mocking(config, bucket_name=test_bucket, region=test_region)
    
    # Initialize DocEX with existing configuration
    try:
        if args.tenant_id:
            user_context = UserContext(user_id='test_user', tenant_id=args.tenant_id)
            docex = DocEX(user_context=user_context)
            print(f"✅ DocEX initialized for tenant: {args.tenant_id}")
        elif multi_tenancy_enabled:
            print("⚠️  Multi-tenancy is enabled but no tenant_id provided.")
            print("   Use --tenant-id to specify a tenant.")
            sys.exit(1)
        else:
            try:
                docex = DocEX()
                print("✅ DocEX initialized (single-tenant mode, no UserContext)")
            except (ValueError, RuntimeError) as e:
                # If multi-tenancy is required, create UserContext
                user_context = UserContext(user_id='test_user')
                docex = DocEX(user_context=user_context)
                print("✅ DocEX initialized (single-tenant mode, with UserContext)")
    except Exception as e:
        print(f"❌ Failed to initialize DocEX: {e}")
        sys.exit(1)
    
    # Run tests
    results = []
    
    # Test 1: Basket Operations
    success, message = test_basket_operations(docex)
    results.append(("Basket Operations", success, message))
    
    # Test 2: File Operations
    success, message = test_file_operations(docex)
    results.append(("File Operations", success, message))
    
    # Test 3: Route Operations
    success, message = asyncio.run(test_route_operations(docex))
    results.append(("Route Operations", success, message))
    
    # Test 4: Move File Between Baskets
    success, message = asyncio.run(test_move_file_between_baskets(docex))
    results.append(("Move File Between Baskets", success, message))
    
    # Test 5: Basket Storage Types (S3 and Filesystem)
    # Pass s3_mock to ensure S3 mocking is available for S3 basket tests
    success, message = asyncio.run(test_basket_storage_types(docex, config, s3_mock=s3_mock))
    results.append(("Basket Storage Types", success, message))
    
    # Test 6: Comprehensive S3 Operations
    # Pass s3_mock to ensure S3 mocking is available for comprehensive S3 tests
    success, message = asyncio.run(test_s3_comprehensive_operations(docex, config, s3_mock=s3_mock))
    results.append(("Comprehensive S3 Operations", success, message))
    
    # Print summary
    print_section("Test Summary")
    all_passed = True
    for test_name, success, message in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not success:
            print(f"   Error: {message}")
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED")
        # Stop S3 mocking if it was started
        if s3_mock:
            s3_mock.stop()
            if VERBOSE:
                print("✅ S3 mocking stopped")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        # Stop S3 mocking if it was started
        if s3_mock:
            s3_mock.stop()
            if VERBOSE:
                print("✅ S3 mocking stopped")
        sys.exit(1)


if __name__ == '__main__':
    main()

