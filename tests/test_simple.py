from docex.docbasket import DocBasket
from docex.models.metadata_keys import MetadataKey
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
    """Test metadata verification for newly added files"""
    print("\n=== Testing Metadata Verification ===\n")
    
    # Create test basket
    basket_name = f"test_basket_metadata_verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Creating test basket for metadata verification: {basket_name}")
    test_basket = DocBasket.create(basket_name)
    
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

def test_duplicate_file_handling():
    """Test handling of duplicate files"""
    print("\n=== Testing Duplicate File Handling ===\n")
    
    # Create test basket
    basket_name = f"test_basket_duplicate_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Creating test basket for duplicate file handling: {basket_name}")
    test_basket = DocBasket.create(basket_name)
    
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

if __name__ == "__main__":
    test_metadata_verification()
    test_duplicate_file_handling() 