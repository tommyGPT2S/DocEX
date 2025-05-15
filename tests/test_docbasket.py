import os
import shutil
import pytest
from pathlib import Path
from datetime import datetime, timedelta
import json

from docex.docbasket import DocBasket, Document
from docex.models.metadata_keys import MetadataKey
from docex.db.connection import Database, Base
from docex.db.models import DocBasket as DocBasketModel
from sqlalchemy import select

# Test configuration
TEST_BASKET_NAME = "test_basket"
TEST_STORAGE_PATH = "data/test_storage"
TEST_DB_URL = "postgresql://gpt2s:9pt2s2025!@localhost:5444/scm_simulation"

@pytest.fixture
def db():
    """Fixture to provide database connection"""
    return Database()

@pytest.fixture
def test_basket(db):
    """Fixture to create and cleanup a test basket"""
    # Setup
    setup_test_environment()
    
    # Clean up any existing test basket
    with db.transaction() as session:
        existing_basket = session.execute(
            select(DocBasketModel).where(DocBasketModel.name == TEST_BASKET_NAME)
        ).scalar_one_or_none()
        if existing_basket:
            session.delete(existing_basket)
            session.commit()
    
    # Create new basket
    basket = DocBasket.create(
        name=TEST_BASKET_NAME,
        description="Test basket",
        storage_config={
            'type': 'filesystem',
            'path': TEST_STORAGE_PATH
        }
    )
    
    yield basket
    
    # Teardown
    cleanup_test_environment()
    
    # Clean up basket in database
    with db.transaction() as session:
        existing_basket = session.execute(
            select(DocBasketModel).where(DocBasketModel.name == TEST_BASKET_NAME)
        ).scalar_one_or_none()
        if existing_basket:
            session.delete(existing_basket)
            session.commit()

@pytest.fixture
def sample_documents(test_basket):
    """Fixture to create sample test documents"""
    documents = []
    test_files = {
        "test1.pdf": "This is a test PDF document",
        "test2.docx": "This is a test Word document",
        "test3.txt": "This is a test text document"
    }
    
    for filename, content in test_files.items():
        file_path = os.path.join(TEST_STORAGE_PATH, filename)
        with open(file_path, 'w') as f:
            f.write(content)
        doc = test_basket.add(file_path)
        documents.append(doc)
    
    return documents

def setup_test_environment():
    """Set up test environment"""
    os.makedirs(TEST_STORAGE_PATH, exist_ok=True)

def cleanup_test_environment():
    """Clean up test environment"""
    if os.path.exists(TEST_STORAGE_PATH):
        shutil.rmtree(TEST_STORAGE_PATH)

def test_basket_creation():
    """Test basket creation and configuration"""
    basket = DocBasket(
        name="config_test_basket",
        config={
            'storage': {
                'type': 'filesystem',
                'config': {'base_path': TEST_STORAGE_PATH}
            },
            'database': {
                'type': 'postgres',
                'config': {'database_url': TEST_DB_URL}
            }
        }
    )
    
    assert basket.basket is not None
    assert basket.basket.name == "config_test_basket"
    
    # Test basket info
    info = basket.info()
    assert isinstance(info, dict)
    assert 'total_documents' in info
    assert 'by_status' in info
    assert 'by_type' in info

def test_document_addition(test_basket):
    """Test adding documents to basket"""
    # Create a test file
    test_file = os.path.join(TEST_STORAGE_PATH, "test_doc.txt")
    content = "Test document content"
    with open(test_file, 'w') as f:
        f.write(content)
    
    # Add document with metadata
    custom_metadata = {
        "author": "Test Author",
        "department": "Test Dept",
        "tags": ["test", "document"]
    }
    
    doc = test_basket.add(test_file, metadata=custom_metadata)
    
    assert isinstance(doc, Document)
    assert doc.id is not None
    
    # Verify metadata
    metadata = doc.get_metadata()
    assert metadata["author"] == "Test Author"
    assert metadata["department"] == "Test Dept"
    assert metadata[MetadataKey.FILE_TYPE.value] == "TXT"
    assert metadata[MetadataKey.ORIGINAL_PATH.value] == test_file

def test_document_listing(test_basket, sample_documents):
    """Test document listing functionality"""
    # List all documents
    all_docs = test_basket.list_documents()
    assert len(all_docs) == len(sample_documents)
    
    # Add a document with specific status
    test_file = os.path.join(TEST_STORAGE_PATH, "status_test.txt")
    with open(test_file, 'w') as f:
        f.write("Status test document")
    
    doc = test_basket.add(test_file)
    doc.add_metadata({"status": "PROCESSED"})
    
    # List documents by status
    processed_docs = test_basket.list_documents(status="PROCESSED")
    assert len(processed_docs) == 1
    assert processed_docs[0].id == doc.id

def test_document_metadata(test_basket):
    """Test document metadata operations"""
    # Create test document
    test_file = os.path.join(TEST_STORAGE_PATH, "metadata_test.txt")
    with open(test_file, 'w') as f:
        f.write("Metadata test content")
    
    doc = test_basket.add(test_file)
    
    # Test adding metadata
    metadata = {
        "test_key": "test_value",
        "nested_data": {
            "key1": "value1",
            "key2": ["item1", "item2"]
        },
        "timestamp": datetime.now().isoformat()
    }
    doc.add_metadata(metadata)
    
    # Verify metadata
    stored_metadata = doc.get_metadata()
    assert stored_metadata["test_key"] == "test_value"
    assert stored_metadata["nested_data"]["key1"] == "value1"
    
    # Test updating metadata
    updated_value = "updated_value"
    doc.add_metadata({"test_key": updated_value})
    assert doc.get_metadata("test_key") == updated_value
    
    # Test metadata ID format
    metadata_id = doc.get_metadata_id("test_key")
    assert metadata_id.startswith("dm_")
    assert len(metadata_id) == 36 + 4

def test_document_history(test_basket, sample_documents):
    """Test document history tracking"""
    doc = sample_documents[0]
    
    # Get initial history
    initial_history = doc.get_history()
    assert isinstance(initial_history, list)
    
    # Perform some operations
    doc.add_metadata({"status": "PROCESSING"})
    doc.add_metadata({"status": "PROCESSED"})
    
    # Check updated history
    updated_history = doc.get_history()
    assert len(updated_history) > len(initial_history)

def test_cleanup_operations(test_basket, sample_documents):
    """Test cleanup operations"""
    # Add some old documents
    old_docs = []
    for i in range(3):
        test_file = os.path.join(TEST_STORAGE_PATH, f"old_doc_{i}.txt")
        with open(test_file, 'w') as f:
            f.write(f"Old document {i}")
        doc = test_basket.add(test_file)
        # Mark as old by updating metadata
        doc.add_metadata({
            MetadataKey.CREATED_AT.value: (datetime.now() - timedelta(days=31)).isoformat()
        })
        old_docs.append(doc)
    
    # Run cleanup
    cleanup_result = test_basket.cleanup_old_documents(days_old=30)
    assert cleanup_result['deleted_count'] > 0
    
    # Verify cleanup
    remaining_docs = test_basket.list_documents()
    assert len(remaining_docs) == len(sample_documents)

def test_error_handling(test_basket):
    """Test error handling scenarios"""
    # Test adding non-existent file
    with pytest.raises(FileNotFoundError):
        test_basket.add("non_existent_file.txt")
    
    # Test invalid document ID
    with pytest.raises(ValueError):
        test_basket.get_document("invalid_id")
    
    # Test duplicate basket name
    with pytest.raises(ValueError):
        DocBasket(name=TEST_BASKET_NAME)  # Should fail as basket already exists

def test_retry_failed_documents(test_basket):
    """Test retrying failed documents"""
    # Create a failed document
    test_file = os.path.join(TEST_STORAGE_PATH, "failed_doc.txt")
    with open(test_file, 'w') as f:
        f.write("Failed document content")
    
    doc = test_basket.add(test_file)
    doc.add_metadata({
        "status": "ERROR",
        "error_message": "Test error",
        "processing_attempts": 1
    })
    
    # Try retry
    retry_results = test_basket.retry_failed_documents(max_attempts=3)
    assert isinstance(retry_results, list)
    assert len(retry_results) > 0

def test_id_generation(test_basket):
    """Test ID generation for different entities"""
    # Test basket ID format
    assert test_basket.basket.id.startswith("bas_")
    id_without_prefix = test_basket.basket.id[4:]  # Remove prefix
    assert 35 <= len(id_without_prefix) <= 36
    
    # Test document ID format
    test_file = os.path.join(TEST_STORAGE_PATH, "id_test.txt")
    with open(test_file, 'w') as f:
        f.write("ID test content")
    
    doc = test_basket.add(test_file)
    assert doc.id.startswith("doc_")
    id_without_prefix = doc.id[4:]  # Remove prefix
    assert 35 <= len(id_without_prefix) <= 36
    
    # Test file history ID format
    history = doc.get_history()
    assert history[0].id.startswith("fh_")
    id_without_prefix = history[0].id[3:]  # Remove prefix
    assert 35 <= len(id_without_prefix) <= 36

def test_operation_dependencies(test_basket):
    """Test operation dependencies"""
    # Create test document
    test_file = os.path.join(TEST_STORAGE_PATH, "op_test.txt")
    with open(test_file, 'w') as f:
        f.write("Operation test content")
    
    doc = test_basket.add(test_file)
    
    # Create operations
    op1 = doc.create_operation("PROCESS", "PENDING")
    op2 = doc.create_operation("VALIDATE", "PENDING")
    
    # Test operation ID format
    assert op1.id.startswith("op_")
    id_without_prefix = op1.id[3:]  # Remove prefix
    assert 35 <= len(id_without_prefix) <= 36
    
    # Add dependency
    op2.add_dependency(op1)
    
    # Verify dependency
    deps = op2.get_dependencies()
    assert len(deps) == 1
    assert deps[0].id == op1.id
    
    # Test dependency ID format
    dep_id = deps[0].id
    assert dep_id.startswith("od_")
    id_without_prefix = dep_id[3:]  # Remove prefix
    assert 35 <= len(id_without_prefix) <= 36

def test_document_events(test_basket):
    """Test document event tracking"""
    # Create test document
    test_file = os.path.join(TEST_STORAGE_PATH, "event_test.txt")
    with open(test_file, 'w') as f:
        f.write("Event test content")
    
    doc = test_basket.add(test_file)
    
    # Create event
    event = doc.create_event("PROCESSING_STARTED", {"stage": "initial"})
    
    # Test event ID format
    assert event.id.startswith("ev_")
    id_without_prefix = event.id[3:]  # Remove prefix
    assert 35 <= len(id_without_prefix) <= 36
    
    # Verify event details
    assert event.event_type == "PROCESSING_STARTED"
    assert event.data["stage"] == "initial"

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 