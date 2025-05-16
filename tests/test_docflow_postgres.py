import os
import shutil
import unittest
from pathlib import Path
from docCore import DocFlow
from docex.config.docflow_config import DocFlowConfig
from docex.db.models import Base
from docex.db.connection import Database
from docex.docbasket import DocBasket

class TestDocFlowPostgres(unittest.TestCase):
    """Test DocFlow functionality with PostgreSQL configuration"""
    
    def setUp(self):
        """Set up test environment"""
        # Clean up any existing test data
        self.test_dir = Path('test_data')
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(mode=0o755)  # Set directory permissions
        
        # Set up DocFlow with PostgreSQL configuration
        DocFlow.setup(
            database={
                'type': 'postgres',
                'postgres': {
                    'host': 'localhost',
                    'port': 5444,
                    'database': 'scm_simulation',
                    'user': 'gpt2s',
                    'password': '9pt2s2025!',
                    'schema': 'docflow'
                }
            },
            logging={
                'level': 'DEBUG'
            }
        )
        
        # Create database tables
        self.docflow = DocFlow()
        self.db = Database()
        Base.metadata.create_all(self.db.get_engine())
    
    def tearDown(self):
        """Clean up test environment"""
        # Drop all tables
        Base.metadata.drop_all(self.db.get_engine())
        
        # Clean up test directory
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_database_configuration(self):
        """Test database configuration changes"""
        # Verify initial PostgreSQL configuration
        config = DocFlowConfig()
        self.assertEqual(config.get('database.type'), 'postgres')
        pg_config = config.get('database.postgres', {})
        self.assertEqual(pg_config['host'], 'localhost')
        self.assertEqual(pg_config['port'], 5444)
        self.assertEqual(pg_config['database'], 'scm_simulation')
        self.assertEqual(pg_config['user'], 'gpt2s')
        self.assertEqual(pg_config['schema'], 'docflow')
        
        # Set up SQLite as default database
        DocFlow.setup_database('sqlite',
            path='test.db',
            is_default_db=True
        )
        
        # Verify SQLite is now default
        config = DocFlowConfig()
        self.assertEqual(config.get('database.type'), 'sqlite')
        sqlite_config = config.get('database.sqlite', {})
        self.assertEqual(sqlite_config['path'], 'test.db')
        
        # Switch back to PostgreSQL as default
        DocFlow.setup_database('postgres',
            host='localhost',
            port=5444,
            database='scm_simulation',
            user='gpt2s',
            password='9pt2s2025!',
            schema='docflow',
            is_default_db=True
        )
        
        # Verify PostgreSQL is default again
        config = DocFlowConfig()
        self.assertEqual(config.get('database.type'), 'postgres')
        pg_config = config.get('database.postgres', {})
        self.assertEqual(pg_config['host'], 'localhost')
        self.assertEqual(pg_config['port'], 5444)
        self.assertEqual(pg_config['database'], 'scm_simulation')
        self.assertEqual(pg_config['user'], 'gpt2s')
        self.assertEqual(pg_config['schema'], 'docflow')
    
    def test_default_configuration(self):
        """Test default configuration"""
        config = DocFlowConfig()
        self.assertEqual(config.get('database.type'), 'postgres')
    
    def test_create_basket_with_default_storage(self):
        """Test creating a basket with default storage configuration"""
        basket = self.docflow.create_basket('test_basket', 'Test basket')
        self.assertIsNotNone(basket)
        self.assertEqual(basket.name, 'test_basket')
        self.assertEqual(basket.description, 'Test basket')
        self.assertEqual(basket.storage_config['type'], 'filesystem')
        self.assertIsNotNone(basket.storage_config['path'])
    
    def test_create_basket_with_custom_storage(self):
        """Test creating a basket with custom storage configuration"""
        custom_storage = {
            'type': 'filesystem',
            'path': 'custom_storage/test_basket'
        }
        
        basket = self.docflow.create_basket(
            'test_basket',
            'Test basket',
            storage_config=custom_storage
        )
        
        self.assertIsNotNone(basket)
        self.assertEqual(basket.name, 'test_basket')
        self.assertEqual(basket.description, 'Test basket')
        self.assertEqual(basket.storage_config['type'], 'filesystem')
        self.assertEqual(basket.storage_config['path'], 'custom_storage/test_basket')
    
    def test_add_document_to_basket(self):
        """Test adding a document to a basket"""
        # Create test file
        test_file = self.test_dir / 'test.txt'
        test_file.write_text('Test content')
        
        # Create basket and add document
        basket = self.docflow.create_basket('test_basket')
        doc = basket.add(str(test_file))
        
        self.assertIsNotNone(doc)
        self.assertEqual(doc.name, 'test.txt')
        self.assertEqual(doc.content_type, 'text/plain')
        self.assertEqual(doc.size, len('Test content'))
    
    def test_list_baskets(self):
        """Test listing all baskets"""
        # Create multiple baskets
        basket1 = self.docflow.create_basket('basket1')
        basket2 = self.docflow.create_basket('basket2')
        
        # List baskets
        baskets = self.docflow.list_baskets()
        
        self.assertEqual(len(baskets), 2)
        self.assertEqual(baskets[0].name, 'basket1')
        self.assertEqual(baskets[1].name, 'basket2')
    
    def test_delete_basket(self):
        """Test deleting a basket"""
        # Create basket and add document
        basket = self.docflow.create_basket('test_basket')
        
        # Delete basket
        basket.delete()
        
        # Try to get deleted basket
        deleted_basket = self.docflow.get_basket(basket.id)
        self.assertIsNone(deleted_basket)

    def test_find_basket_by_name(self):
        """Test finding a basket by name"""
        # Create a basket
        basket = self.docflow.create_basket('find_by_name_test')
        
        # Find the basket by name
        found_basket = DocBasket.find_by_name('find_by_name_test')
        
        self.assertIsNotNone(found_basket)
        self.assertEqual(found_basket.id, basket.id)
        self.assertEqual(found_basket.name, 'find_by_name_test')
        
        # Test non-existent basket
        non_existent = DocBasket.find_by_name('non_existent_basket')
        self.assertIsNone(non_existent)

    def test_update_document(self):
        """Test updating a document"""
        # Create basket and add document
        basket = self.docflow.create_basket('update_test')
        test_file = self.test_dir / 'test.txt'
        test_file.write_text('Initial content')
        doc = basket.add(str(test_file))
        
        # Update document with new content
        new_file = self.test_dir / 'new_test.txt'
        new_file.write_text('Updated content')
        updated_doc = basket.update_document(doc.id, str(new_file))
        
        self.assertIsNotNone(updated_doc)
        self.assertEqual(updated_doc.name, 'new_test.txt')
        self.assertEqual(updated_doc.content_type, 'text/plain')
        self.assertEqual(updated_doc.size, len('Updated content'))

    def test_delete_document(self):
        """Test deleting a document"""
        # Create basket and add document
        basket = self.docflow.create_basket('delete_doc_test')
        test_file = self.test_dir / 'test.txt'
        test_file.write_text('Test content')
        doc = basket.add(str(test_file))
        
        # Delete document
        basket.delete_document(doc.id)
        
        # Try to get deleted document
        deleted_doc = basket.get_document(doc.id)
        self.assertIsNone(deleted_doc)

    def test_get_basket_stats(self):
        """Test getting basket statistics"""
        # Create basket and add documents
        basket = self.docflow.create_basket('stats_test')
        
        # Add multiple documents with different types and statuses
        test_file1 = self.test_dir / 'test1.txt'
        test_file1.write_text('Content 1')
        doc1 = basket.add(str(test_file1), document_type='text')
        
        test_file2 = self.test_dir / 'test2.json'
        test_file2.write_text('{"key": "value"}')
        doc2 = basket.add(str(test_file2), document_type='json')
        
        # Get stats
        stats = basket.get_stats()
        
        self.assertIsNotNone(stats)
        self.assertEqual(stats['name'], 'stats_test')
        self.assertEqual(stats['document_counts']['RECEIVED'], 2)
        self.assertIn('text', stats['type_counts'])
        self.assertIn('json', stats['type_counts'])

    def test_find_documents_by_metadata(self):
        """Test finding documents by metadata"""
        # Create basket and add document with metadata
        basket = self.docflow.create_basket('metadata_test')
        test_file = self.test_dir / 'test.txt'
        test_file.write_text('Test content')
        
        metadata = {
            'author': 'test_author',
            'category': 'test_category'
        }
        doc = basket.add(str(test_file), metadata=metadata)
        
        # Find documents by metadata
        found_docs = basket.find_documents_by_metadata({'author': 'test_author'})
        self.assertEqual(len(found_docs), 1)
        self.assertEqual(found_docs[0].id, doc.id)
        
        # Test with non-existent metadata
        no_docs = basket.find_documents_by_metadata({'author': 'non_existent'})
        self.assertEqual(len(no_docs), 0)

    def test_document_details(self):
        """Test document details and content retrieval"""
        # Create basket and add document
        basket = self.docflow.create_basket('details_test')
        test_file = self.test_dir / 'test.txt'
        test_file.write_text('Test content')
        doc = basket.add(str(test_file))
        
        # Get document details
        details = doc.get_details()
        self.assertIsNotNone(details)
        self.assertEqual(details['name'], 'test.txt')
        self.assertEqual(details['content_type'], 'text/plain')
        self.assertEqual(details['status'], 'RECEIVED')
        self.assertIn('created_at', details)
        self.assertIn('updated_at', details)
        
        # Get document content
        content = doc.get_content()
        self.assertIsNotNone(content)
        self.assertEqual(content['content'], 'Test content')

if __name__ == '__main__':
    unittest.main() 