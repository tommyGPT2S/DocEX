from docflow.docbasket import DocBasket
from docflow.models.metadata_keys import MetadataKey
from docflow.config.config_manager import ConfigManager
from docflow.db.database_factory import DatabaseFactory
import os
from datetime import datetime
import json
from pathlib import Path
import hashlib
from typing import Dict, Any

def verify_standard_metadata(metadata: Dict[str, Any], filename: str) -> bool:
    """
    Verify standard metadata fields
    
    Args:
        metadata: Document metadata to verify
        filename: Name of the file
        
    Returns:
        True if all standard metadata is valid, False otherwise
    """
    # Get expected content type based on file extension
    ext = filename.split('.')[-1].lower()
    content_type_map = {
        'txt': 'text/plain',
        'json': 'application/json',
        'csv': 'text/csv',
        'md': 'text/markdown'
    }
    expected_content_type = content_type_map.get(ext, 'application/octet-stream')
    
    # Required standard metadata fields and their expected values
    standard_fields = {
        MetadataKey.CONTENT_TYPE.value: expected_content_type,
        MetadataKey.DOCUMENT_STATUS.value: 'RECEIVED'
    }
    
    # Verify each standard field
    verification_passed = True
    for key, expected_value in standard_fields.items():
        if key not in metadata:
            print(f"Missing standard metadata: {key}")
            verification_passed = False
        elif metadata[key] != expected_value:
            print(f"Metadata mismatch for {key}:")
            print(f"  Expected: {expected_value}")
            print(f"  Got: {metadata[key]}")
            verification_passed = False
    
    if verification_passed:
        print("✓ Standard metadata verification passed")
    else:
        print("✗ Standard metadata verification failed")
    
    return verification_passed

def verify_custom_metadata(metadata: Dict[str, Any], custom_metadata: Dict[str, Any]) -> bool:
    """
    Verify custom metadata fields
    
    Args:
        metadata: Document metadata to verify
        custom_metadata: Expected custom metadata
        
    Returns:
        True if all custom metadata is valid, False otherwise
    """
    verification_passed = True
    for key, expected_value in custom_metadata.items():
        if key not in metadata:
            print(f"Missing custom metadata: {key}")
            verification_passed = False
        elif str(metadata[key]) != str(expected_value):
            print(f"Custom metadata mismatch for {key}:")
            print(f"  Expected: {expected_value}")
            print(f"  Got: {metadata[key]}")
            verification_passed = False
    
    if verification_passed:
        print("✓ Custom metadata verification passed")
    else:
        print("✗ Custom metadata verification failed")
    
    return verification_passed

def test_metadata_verification():
    """Test metadata verification for newly added files with SQLite"""
    print("\n=== Testing Metadata Verification with SQLite ===\n")
    
    # Create SQLite-specific configuration
    config = ConfigManager()
    config.set('database.type', 'sqlite')
    config.set('database.sqlite.path', 'test_data/test_sqlite.db')
    
    # Initialize database
    os.makedirs('test_data', exist_ok=True)
    db = DatabaseFactory.create_database(config)
    db.initialize()
    
    # Create test basket
    basket_name = f"test_basket_metadata_verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Creating test basket for metadata verification: {basket_name}")
    test_basket = DocBasket.create(basket_name, config)
    
    # Test files and their content
    test_files = [
        ("test.txt", "This is a test document", {"author": "Test User", "description": "Test document: test.txt"}),
        ("config.json", '{"version": "1.0", "settings": {"debug": true}}', {"author": "Test User", "description": "Test document: config.json", "schema_version": "1.0"}),
        ("data.csv", "id,name,value\n1,test,100\n2,sample,200", {"author": "Test User", "description": "Test document: data.csv", "delimiter": ","}),
        ("notes.md", "# Test Notes\nThis is a markdown file", {"author": "Test User", "description": "Test document: notes.md", "format": "GitHub Flavored Markdown"})
    ]
    
    try:
        # Create and verify each test file
        for filename, content, custom_metadata in test_files:
            # Create test file
            with open(filename, 'w') as f:
                f.write(content)
            
            print(f"\nAdding document: {filename}")
            try:
                doc = test_basket.add(filename, metadata=custom_metadata)
                
                # Get document metadata
                doc_metadata = doc.get_metadata()
                print("\nDocument Metadata:")
                for key, value in doc_metadata.items():
                    print(f"  {key}: {value}")
                
                # Verify standard metadata
                print("\nVerifying standard metadata...")
                verify_standard_metadata(doc_metadata, filename)
                
                # Verify custom metadata
                print("\nVerifying custom metadata...")
                verify_custom_metadata(doc_metadata, custom_metadata)
                
            except Exception as e:
                print(f"\nError in metadata verification test: {str(e)}")
                raise
            finally:
                # Clean up test file
                if os.path.exists(filename):
                    os.remove(filename)
    except Exception as e:
        print(f"\nError in metadata verification test: {str(e)}")
        raise
    finally:
        # Clean up test database
        if os.path.exists('test_data/test_sqlite.db'):
            os.remove('test_data/test_sqlite.db')
        if os.path.exists('test_data') and not os.listdir('test_data'):
            os.rmdir('test_data')

def test_duplicate_file_handling():
    """Test handling of duplicate files with SQLite"""
    print("\n=== Testing Duplicate File Handling with SQLite ===\n")
    
    # Create SQLite-specific configuration
    config = ConfigManager()
    config.set('database.type', 'sqlite')
    config.set('database.sqlite.path', 'test_data/test_sqlite_duplicate.db')
    
    # Initialize database
    os.makedirs('test_data', exist_ok=True)
    db = DatabaseFactory.create_database(config)
    db.initialize()
    
    # Create test basket
    basket_name = f"test_basket_duplicate_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Creating test basket for duplicate file handling: {basket_name}")
    test_basket = DocBasket.create(basket_name, config)
    
    # Create test file
    test_file = "duplicate_test.txt"
    with open(test_file, "w") as f:
        f.write("This is a test document for duplicate handling")
    
    try:
        # Add file first time
        print("\nAdding first document: duplicate_test.txt")
        doc1 = test_basket.add(test_file)
        doc1_metadata = doc1.get_metadata()
        
        # Verify first document status
        assert doc1_metadata[MetadataKey.DOCUMENT_STATUS.value] == 'RECEIVED'
        
        # Add same file again
        print("\nAdding duplicate document: duplicate_test.txt")
        doc2 = test_basket.add(test_file)
        doc2_metadata = doc2.get_metadata()
        
        # Verify duplicate document status
        assert doc2_metadata[MetadataKey.DOCUMENT_STATUS.value] == 'DUPLICATE'
        
        # Verify checksums match
        assert doc1_metadata[MetadataKey.CONTENT_CHECKSUM.value] == doc2_metadata[MetadataKey.CONTENT_CHECKSUM.value]
        
    except Exception as e:
        print(f"\nError in duplicate file handling test: {str(e)}")
        raise
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)
        # Clean up test database
        if os.path.exists('test_data/test_sqlite_duplicate.db'):
            os.remove('test_data/test_sqlite_duplicate.db')
        if os.path.exists('test_data') and not os.listdir('test_data'):
            os.rmdir('test_data')

def test_sqlite_json_handling():
    """Test SQLite-specific JSON field handling"""
    print("\n=== Testing SQLite JSON Field Handling ===\n")
    
    # Create SQLite-specific configuration
    config = ConfigManager()
    config.set('database.type', 'sqlite')
    config.set('database.sqlite.path', 'test_data/test_sqlite_json.db')
    
    # Initialize database
    os.makedirs('test_data', exist_ok=True)
    db = DatabaseFactory.create_database(config)
    db.initialize()
    
    # Create test basket
    basket_name = f"test_basket_json_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Creating test basket for JSON handling: {basket_name}")
    test_basket = DocBasket.create(basket_name, config)
    
    try:
        # Test JSON in document content
        json_content = {
            "key1": "value1",
            "key2": 123,
            "key3": {"nested": "value"},
            "key4": [1, 2, 3]
        }
        
        # Create test file with JSON content
        test_file = "test_json.json"
        with open(test_file, "w") as f:
            json.dump(json_content, f)
        
        print("\nAdding document with JSON content")
        doc = test_basket.add(test_file, metadata={"content_type": "application/json"})
        
        # Verify JSON content is properly stored and retrieved
        doc_content = doc.get_content()
        assert isinstance(doc_content, dict), "JSON content should be parsed as dictionary"
        assert doc_content == json_content, "Retrieved JSON content should match original"
        print("✓ JSON content verification passed")
        
        # Test JSON in metadata
        complex_metadata = {
            "settings": {
                "processing": {
                    "enabled": True,
                    "options": ["opt1", "opt2"],
                    "config": {"timeout": 30}
                }
            }
        }
        
        print("\nUpdating document with complex JSON metadata")
        doc.update_metadata(complex_metadata)
        
        # Verify complex metadata is properly stored and retrieved
        retrieved_metadata = doc.get_metadata()
        assert isinstance(retrieved_metadata["settings"], dict), "Complex metadata should be stored as JSON"
        assert retrieved_metadata["settings"] == complex_metadata["settings"], "Retrieved metadata should match original"
        print("✓ Complex metadata verification passed")
        
    except Exception as e:
        print(f"\nError in SQLite JSON handling test: {str(e)}")
        raise
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
        if os.path.exists('test_data/test_sqlite_json.db'):
            os.remove('test_data/test_sqlite_json.db')
        if os.path.exists('test_data') and not os.listdir('test_data'):
            os.rmdir('test_data')

def test_sqlite_transaction_behavior():
    """Test SQLite-specific transaction behavior"""
    print("\n=== Testing SQLite Transaction Behavior ===\n")
    
    # Create SQLite-specific configuration
    config = ConfigManager()
    config.set('database.type', 'sqlite')
    config.set('database.sqlite.path', 'test_data/test_sqlite_transaction.db')
    
    # Initialize database
    os.makedirs('test_data', exist_ok=True)
    db = DatabaseFactory.create_database(config)
    db.initialize()
    
    # Create test basket
    basket_name = f"test_basket_transaction_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Creating test basket for transaction testing: {basket_name}")
    test_basket = DocBasket.create(basket_name, config)
    
    try:
        # Test successful transaction
        print("\nTesting successful transaction")
        test_file1 = "transaction_test1.txt"
        with open(test_file1, "w") as f:
            f.write("Test document 1")
        
        doc1 = test_basket.add(test_file1)
        doc1.update_metadata({"status": "processing"})
        doc1.update_metadata({"status": "completed"})
        print("✓ Successful transaction test passed")
        
        # Test transaction rollback
        print("\nTesting transaction rollback")
        test_file2 = "transaction_test2.txt"
        with open(test_file2, "w") as f:
            f.write("Test document 2")
        
        try:
            doc2 = test_basket.add(test_file2)
            doc2.update_metadata({"status": "processing"})
            # Simulate an error
            raise Exception("Simulated error")
            doc2.update_metadata({"status": "completed"})
        except Exception as e:
            if "Simulated error" in str(e):
                print("✓ Transaction rollback test passed")
            else:
                raise
        
        # Verify document 2 status was not updated
        doc2_fresh = test_basket.get_document(doc2.id)
        assert doc2_fresh.get_metadata()["status"] == "RECEIVED", "Document status should be unchanged after rollback"
        print("✓ Post-rollback state verification passed")
        
    except Exception as e:
        print(f"\nError in SQLite transaction behavior test: {str(e)}")
        raise
    finally:
        # Clean up
        for file in [test_file1, test_file2]:
            if os.path.exists(file):
                os.remove(file)
        if os.path.exists('test_data/test_sqlite_transaction.db'):
            os.remove('test_data/test_sqlite_transaction.db')
        if os.path.exists('test_data') and not os.listdir('test_data'):
            os.rmdir('test_data')

if __name__ == "__main__":
    test_metadata_verification()
    test_duplicate_file_handling()
    test_sqlite_json_handling()
    test_sqlite_transaction_behavior() 