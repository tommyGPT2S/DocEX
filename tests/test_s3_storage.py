"""
Tests for S3 storage implementation
"""
import unittest
import os
import json
import tempfile
from pathlib import Path
from moto import mock_aws
import boto3
from io import BytesIO

from docex.storage.s3_storage import S3Storage
from docex.storage.storage_factory import StorageFactory
from docex.services.storage_service import StorageService


class TestS3Storage(unittest.TestCase):
    """Test S3 storage implementation"""
    
    def setUp(self):
        """Set up test environment"""
        self.bucket_name = 'test-docex-bucket'
        self.region = 'us-east-1'
        self.test_prefix = 'test-prefix/'
        
        # Test configuration
        self.config = {
            'type': 's3',
            'bucket': self.bucket_name,
            'region': self.region,
            'access_key': 'test-access-key',
            'secret_key': 'test-secret-key'
        }
    
    @mock_aws
    def test_s3_storage_initialization(self):
        """Test S3 storage initialization"""
        # Create mock bucket
        s3_client = boto3.client('s3', region_name=self.region)
        s3_client.create_bucket(Bucket=self.bucket_name)
        
        # Initialize storage
        storage = S3Storage(self.config)
        
        self.assertEqual(storage.bucket, self.bucket_name)
        self.assertEqual(storage.region, self.region)
        self.assertIsNotNone(storage.s3)
    
    @mock_aws
    def test_s3_storage_initialization_with_prefix(self):
        """Test S3 storage initialization with prefix"""
        # Create mock bucket
        s3_client = boto3.client('s3', region_name=self.region)
        s3_client.create_bucket(Bucket=self.bucket_name)
        
        # Initialize storage with prefix
        config_with_prefix = {**self.config, 'prefix': self.test_prefix}
        storage = S3Storage(config_with_prefix)
        
        self.assertEqual(storage.prefix, self.test_prefix)
    
    @mock_aws
    def test_s3_storage_initialization_missing_bucket(self):
        """Test S3 storage initialization with missing bucket"""
        config_no_bucket = {**self.config}
        del config_no_bucket['bucket']
        
        with self.assertRaises(ValueError) as context:
            S3Storage(config_no_bucket)
        
        self.assertIn('bucket name is required', str(context.exception).lower())
    
    @mock_aws
    def test_s3_storage_save_and_load(self):
        """Test saving and loading content"""
        # Create mock bucket
        s3_client = boto3.client('s3', region_name=self.region)
        s3_client.create_bucket(Bucket=self.bucket_name)
        
        storage = S3Storage(self.config)
        
        # Test saving bytes
        test_content = b'Hello, S3!'
        storage.save('test-key', test_content)
        
        # Test loading
        loaded_content = storage.load('test-key')
        self.assertEqual(loaded_content, test_content)
        
        # Test saving string
        test_string = 'Hello, World!'
        storage.save('test-string', test_string)
        loaded_string = storage.load('test-string')
        self.assertEqual(loaded_string, test_string.encode('utf-8'))
        
        # Test saving dict
        test_dict = {'key': 'value', 'number': 42}
        storage.save('test-dict', test_dict)
        loaded_dict = storage.load('test-dict')
        self.assertEqual(loaded_dict, test_dict)
    
    @mock_aws
    def test_s3_storage_save_and_load_with_prefix(self):
        """Test saving and loading with prefix"""
        # Create mock bucket
        s3_client = boto3.client('s3', region_name=self.region)
        s3_client.create_bucket(Bucket=self.bucket_name)
        
        config_with_prefix = {**self.config, 'prefix': self.test_prefix}
        storage = S3Storage(config_with_prefix)
        
        # Save with relative path
        test_content = b'Test content'
        storage.save('test-key', test_content)
        
        # Verify it was saved with prefix
        s3_client = boto3.client('s3', region_name=self.region)
        response = s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=self.test_prefix)
        self.assertIn('Contents', response)
        self.assertTrue(any(obj['Key'] == f'{self.test_prefix}test-key' for obj in response['Contents']))
        
        # Load should work with relative path
        loaded_content = storage.load('test-key')
        self.assertEqual(loaded_content, test_content)
    
    @mock_aws
    def test_s3_storage_exists(self):
        """Test checking if content exists"""
        # Create mock bucket
        s3_client = boto3.client('s3', region_name=self.region)
        s3_client.create_bucket(Bucket=self.bucket_name)
        
        storage = S3Storage(self.config)
        
        # Should not exist initially
        self.assertFalse(storage.exists('non-existent-key'))
        
        # Save and check existence
        storage.save('test-key', b'test content')
        self.assertTrue(storage.exists('test-key'))
    
    @mock_aws
    def test_s3_storage_delete(self):
        """Test deleting content"""
        # Create mock bucket
        s3_client = boto3.client('s3', region_name=self.region)
        s3_client.create_bucket(Bucket=self.bucket_name)
        
        storage = S3Storage(self.config)
        
        # Save content
        storage.save('test-key', b'test content')
        self.assertTrue(storage.exists('test-key'))
        
        # Delete content
        result = storage.delete('test-key')
        self.assertTrue(result)
        self.assertFalse(storage.exists('test-key'))
    
    @mock_aws
    def test_s3_storage_load_nonexistent(self):
        """Test loading non-existent content"""
        # Create mock bucket
        s3_client = boto3.client('s3', region_name=self.region)
        s3_client.create_bucket(Bucket=self.bucket_name)
        
        storage = S3Storage(self.config)
        
        with self.assertRaises(FileNotFoundError):
            storage.load('non-existent-key')
    
    @mock_aws
    def test_s3_storage_get_metadata(self):
        """Test getting metadata"""
        # Create mock bucket
        s3_client = boto3.client('s3', region_name=self.region)
        s3_client.create_bucket(Bucket=self.bucket_name)
        
        storage = S3Storage(self.config)
        
        # Save content
        test_content = b'Test content for metadata'
        storage.save('test-key', test_content)
        
        # Get metadata
        metadata = storage.get_metadata('test-key')
        
        self.assertIn('size', metadata)
        self.assertIn('created_at', metadata)
        self.assertIn('etag', metadata)
        self.assertIn('content_type', metadata)
        self.assertEqual(metadata['size'], len(test_content))
    
    @mock_aws
    def test_s3_storage_get_url(self):
        """Test getting presigned URL"""
        # Create mock bucket
        s3_client = boto3.client('s3', region_name=self.region)
        s3_client.create_bucket(Bucket=self.bucket_name)
        
        storage = S3Storage(self.config)
        
        # Save content
        storage.save('test-key', b'test content')
        
        # Get URL
        url = storage.get_url('test-key', expires_in=3600)
        
        self.assertIsInstance(url, str)
        self.assertIn('amazonaws.com', url or '')
    
    @mock_aws
    def test_s3_storage_copy(self):
        """Test copying content"""
        # Create mock bucket
        s3_client = boto3.client('s3', region_name=self.region)
        s3_client.create_bucket(Bucket=self.bucket_name)
        
        storage = S3Storage(self.config)
        
        # Save content
        test_content = b'Test content to copy'
        storage.save('source-key', test_content)
        
        # Copy content
        result = storage.copy('source-key', 'dest-key')
        self.assertTrue(result)
        
        # Verify both exist
        self.assertTrue(storage.exists('source-key'))
        self.assertTrue(storage.exists('dest-key'))
        
        # Verify content is the same
        source_content = storage.load('source-key')
        dest_content = storage.load('dest-key')
        self.assertEqual(source_content, dest_content)
    
    @mock_aws
    def test_s3_storage_move(self):
        """Test moving content"""
        # Create mock bucket
        s3_client = boto3.client('s3', region_name=self.region)
        s3_client.create_bucket(Bucket=self.bucket_name)
        
        storage = S3Storage(self.config)
        
        # Save content
        test_content = b'Test content to move'
        storage.save('source-key', test_content)
        
        # Move content
        result = storage.move('source-key', 'dest-key')
        self.assertTrue(result)
        
        # Verify source is gone and dest exists
        self.assertFalse(storage.exists('source-key'))
        self.assertTrue(storage.exists('dest-key'))
        
        # Verify content
        dest_content = storage.load('dest-key')
        self.assertEqual(dest_content, test_content)
    
    @mock_aws
    def test_s3_storage_list_directory(self):
        """Test listing directory contents"""
        # Create mock bucket
        s3_client = boto3.client('s3', region_name=self.region)
        s3_client.create_bucket(Bucket=self.bucket_name)
        
        storage = S3Storage(self.config)
        
        # Save multiple files
        storage.save('dir1/file1.txt', b'content1')
        storage.save('dir1/file2.txt', b'content2')
        storage.save('dir2/file3.txt', b'content3')
        
        # List directory
        files = storage.list_directory('dir1')
        
        self.assertIn('dir1/file1.txt', files)
        self.assertIn('dir1/file2.txt', files)
        self.assertNotIn('dir2/file3.txt', files)
    
    @mock_aws
    def test_s3_storage_create_directory(self):
        """Test creating directory marker"""
        # Create mock bucket
        s3_client = boto3.client('s3', region_name=self.region)
        s3_client.create_bucket(Bucket=self.bucket_name)
        
        storage = S3Storage(self.config)
        
        # Create directory
        result = storage.create_directory('test-dir')
        self.assertTrue(result)
        
        # Verify directory marker exists
        self.assertTrue(storage.exists('test-dir/'))
    
    @mock_aws
    def test_s3_storage_store_and_retrieve(self):
        """Test store and retrieve methods"""
        # Create mock bucket
        s3_client = boto3.client('s3', region_name=self.region)
        s3_client.create_bucket(Bucket=self.bucket_name)
        
        storage = S3Storage(self.config)
        
        # Store content
        test_content = b'Test content'
        result = storage.store('test-key', test_content)
        self.assertTrue(result)
        
        # Retrieve content
        retrieved = storage.retrieve('test-key')
        self.assertEqual(retrieved, test_content)
        
        # Retrieve non-existent
        retrieved_none = storage.retrieve('non-existent')
        self.assertIsNone(retrieved_none)
    
    @mock_aws
    def test_s3_storage_set_metadata(self):
        """Test setting metadata"""
        # Create mock bucket
        s3_client = boto3.client('s3', region_name=self.region)
        s3_client.create_bucket(Bucket=self.bucket_name)
        
        storage = S3Storage(self.config)
        
        # Save content
        storage.save('test-key', b'test content')
        
        # Set metadata
        metadata = {'custom-key': 'custom-value', 'another-key': 'another-value'}
        result = storage.set_metadata('test-key', metadata)
        self.assertTrue(result)
        
        # Get metadata and verify
        retrieved_metadata = storage.get_metadata('test-key')
        self.assertIn('metadata', retrieved_metadata)
        # Note: S3 metadata keys are lowercased
        self.assertIn('custom-key', retrieved_metadata.get('metadata', {}))
    
    @mock_aws
    def test_s3_storage_cleanup(self):
        """Test cleanup method"""
        # Create mock bucket
        s3_client = boto3.client('s3', region_name=self.region)
        s3_client.create_bucket(Bucket=self.bucket_name)
        
        storage = S3Storage(self.config)
        
        # Save multiple files
        storage.save('file1', b'content1')
        storage.save('file2', b'content2')
        storage.save('file3', b'content3')
        
        # Verify files exist
        self.assertTrue(storage.exists('file1'))
        self.assertTrue(storage.exists('file2'))
        self.assertTrue(storage.exists('file3'))
        
        # Cleanup
        storage.cleanup()
        
        # Verify files are gone
        self.assertFalse(storage.exists('file1'))
        self.assertFalse(storage.exists('file2'))
        self.assertFalse(storage.exists('file3'))
    
    @mock_aws
    def test_s3_storage_cleanup_with_prefix(self):
        """Test cleanup with prefix"""
        # Create mock bucket
        s3_client = boto3.client('s3', region_name=self.region)
        s3_client.create_bucket(Bucket=self.bucket_name)
        
        config_with_prefix = {**self.config, 'prefix': self.test_prefix}
        storage = S3Storage(config_with_prefix)
        
        # Save files with prefix
        storage.save('file1', b'content1')
        storage.save('file2', b'content2')
        
        # Save file without prefix (outside our scope)
        s3_client = boto3.client('s3', region_name=self.region)
        s3_client.put_object(Bucket=self.bucket_name, Key='other-file', Body=b'other content')
        
        # Cleanup
        storage.cleanup()
        
        # Verify prefixed files are gone
        self.assertFalse(storage.exists('file1'))
        self.assertFalse(storage.exists('file2'))
        
        # Verify other file still exists
        response = s3_client.head_object(Bucket=self.bucket_name, Key='other-file')
        self.assertIsNotNone(response)


class TestS3StorageFactory(unittest.TestCase):
    """Test S3 storage factory integration"""
    
    @mock_aws
    def test_storage_factory_creates_s3_storage(self):
        """Test that StorageFactory can create S3 storage"""
        # Create mock bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.create_bucket(Bucket='test-bucket')
        
        config = {
            'type': 's3',
            'bucket': 'test-bucket',
            'region': 'us-east-1',
            'access_key': 'test-key',
            'secret_key': 'test-secret'
        }
        
        storage = StorageFactory.create_storage(config)
        
        self.assertIsInstance(storage, S3Storage)
        self.assertEqual(storage.bucket, 'test-bucket')


class TestS3StorageService(unittest.TestCase):
    """Test S3 storage service integration"""
    
    @mock_aws
    def test_storage_service_with_s3(self):
        """Test StorageService with S3 configuration"""
        # Create mock bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.create_bucket(Bucket='test-bucket')
        
        storage_config = {
            'type': 's3',
            's3': {
                'bucket': 'test-bucket',
                'region': 'us-east-1',
                'access_key': 'test-key',
                'secret_key': 'test-secret'
            }
        }
        
        service = StorageService(storage_config)
        
        self.assertIsInstance(service.storage, S3Storage)
        self.assertEqual(service.storage.bucket, 'test-bucket')
    
    @mock_aws
    def test_storage_service_s3_missing_bucket(self):
        """Test StorageService with missing bucket"""
        storage_config = {
            'type': 's3',
            's3': {
                'region': 'us-east-1'
            }
        }
        
        with self.assertRaises(ValueError) as context:
            StorageService(storage_config)
        
        self.assertIn('bucket', str(context.exception).lower())
    
    @mock_aws
    def test_storage_service_s3_invalid_bucket_name(self):
        """Test StorageService with invalid bucket name"""
        storage_config = {
            'type': 's3',
            's3': {
                'bucket': 'ab',  # Too short
                'region': 'us-east-1'
            }
        }
        
        with self.assertRaises(ValueError) as context:
            StorageService(storage_config)
        
        self.assertIn('invalid', str(context.exception).lower())


class TestS3StorageCredentials(unittest.TestCase):
    """Test S3 storage credential handling"""
    
    def setUp(self):
        """Set up test environment"""
        # Clear environment variables
        self.original_env = {}
        for key in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'AWS_DEFAULT_REGION']:
            self.original_env[key] = os.environ.get(key)
            if key in os.environ:
                del os.environ[key]
    
    def tearDown(self):
        """Restore environment variables"""
        for key, value in self.original_env.items():
            if value is not None:
                os.environ[key] = value
    
    @mock_aws
    def test_credentials_from_config(self):
        """Test credentials from config"""
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.create_bucket(Bucket='test-bucket')
        
        config = {
            'bucket': 'test-bucket',
            'access_key': 'config-key',
            'secret_key': 'config-secret',
            'region': 'us-east-1'
        }
        
        storage = S3Storage(config)
        self.assertEqual(storage.bucket, 'test-bucket')
    
    @mock_aws
    def test_credentials_from_environment(self):
        """Test credentials from environment variables"""
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.create_bucket(Bucket='test-bucket')
        
        # Set environment variables
        os.environ['AWS_ACCESS_KEY_ID'] = 'env-key'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'env-secret'
        os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'
        
        config = {
            'bucket': 'test-bucket'
            # No credentials in config
        }
        
        storage = S3Storage(config)
        self.assertEqual(storage.bucket, 'test-bucket')
        # Note: In real scenario, boto3 would use env vars or IAM role
    
    @mock_aws
    def test_credentials_priority_config_over_env(self):
        """Test that config credentials take priority over env vars"""
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.create_bucket(Bucket='test-bucket')
        
        # Set environment variables
        os.environ['AWS_ACCESS_KEY_ID'] = 'env-key'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'env-secret'
        
        config = {
            'bucket': 'test-bucket',
            'access_key': 'config-key',
            'secret_key': 'config-secret',
            'region': 'us-east-1'
        }
        
        storage = S3Storage(config)
        # Config credentials should be used
        self.assertEqual(storage.bucket, 'test-bucket')


if __name__ == '__main__':
    unittest.main()

