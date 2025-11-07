import os
import json
import logging
import time
from typing import Dict, Any, Optional, Union, BinaryIO, List
from datetime import datetime, timedelta
from pathlib import Path
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config
from io import BytesIO

from .abstract_storage import AbstractStorage

logger = logging.getLogger(__name__)

class S3Storage(AbstractStorage):
    """
    S3 implementation of the storage backend
    
    Stores document content in Amazon S3.
    Supports multiple credential sources: config, environment variables, IAM roles.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize S3 storage
        
        Args:
            config: Configuration dictionary with:
                - bucket: S3 bucket name (required)
                - access_key: AWS access key (optional if using IAM/env vars)
                - secret_key: AWS secret key (optional if using IAM/env vars)
                - session_token: AWS session token (optional, for temporary credentials)
                - region: AWS region (default: us-east-1)
                - prefix: Optional S3 key prefix for organizing files
                - max_retries: Maximum retry attempts (default: 3)
                - retry_delay: Delay between retries in seconds (default: 1.0)
                - connect_timeout: Connection timeout in seconds (default: 60)
                - read_timeout: Read timeout in seconds (default: 60)
        """
        self.config = config
        
        # Validate required parameters
        self.bucket = config.get('bucket')
        if not self.bucket:
            raise ValueError("S3 bucket name is required in configuration")
        
        # Get credentials with fallback to environment variables and IAM
        credentials = self._get_credentials(config)
        
        # Extract configuration
        self.region = credentials['region']
        self.prefix = config.get('prefix', '').strip('/')
        if self.prefix and not self.prefix.endswith('/'):
            self.prefix += '/'
        
        # Retry configuration
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 1.0)
        
        # Boto3 client configuration
        boto_config = Config(
            retries={
                'max_attempts': self.max_retries,
                'mode': 'adaptive'
            },
            connect_timeout=config.get('connect_timeout', 60),
            read_timeout=config.get('read_timeout', 60)
        )
        
        # Initialize S3 client
        client_kwargs = {
            'service_name': 's3',
            'region_name': self.region,
            'config': boto_config
        }
        
        # Add credentials if provided (otherwise boto3 uses IAM role or default profile)
        if credentials['access_key'] and credentials['secret_key']:
            client_kwargs['aws_access_key_id'] = credentials['access_key']
            client_kwargs['aws_secret_access_key'] = credentials['secret_key']
            if credentials['session_token']:
                client_kwargs['aws_session_token'] = credentials['session_token']
        
        self.s3 = boto3.client(**client_kwargs)
        
        # Ensure bucket exists
        self.ensure_storage_exists()
    
    def _get_credentials(self, config: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """
        Get AWS credentials from config, environment variables, or IAM role.
        
        Priority order:
        1. Config file credentials (highest priority)
        2. Environment variables
        3. IAM role / instance profile (lowest priority, handled by boto3)
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Dictionary with credentials and region
        """
        credentials = {
            'access_key': config.get('access_key'),
            'secret_key': config.get('secret_key'),
            'session_token': config.get('session_token'),
            'region': config.get('region', 'us-east-1')
        }
        
        # Fallback to environment variables
        if not credentials['access_key']:
            credentials['access_key'] = os.getenv('AWS_ACCESS_KEY_ID')
        if not credentials['secret_key']:
            credentials['secret_key'] = os.getenv('AWS_SECRET_ACCESS_KEY')
        if not credentials['session_token']:
            credentials['session_token'] = os.getenv('AWS_SESSION_TOKEN')
        if credentials['region'] == 'us-east-1':
            credentials['region'] = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        # If still no credentials, boto3 will use IAM role or default profile
        logger.info(f"S3 storage initialized with bucket: {self.bucket}, region: {credentials['region']}")
        if credentials['access_key']:
            logger.debug("Using credentials from config or environment variables")
        else:
            logger.debug("Using IAM role or default AWS profile")
        
        return credentials
    
    def _get_full_key(self, path: str) -> str:
        """
        Get full S3 key with prefix
        
        Args:
            path: Relative path/key
            
        Returns:
            Full S3 key with prefix
        """
        # Remove leading slash if present
        path = path.lstrip('/')
        return f"{self.prefix}{path}" if self.prefix else path
    
    def _retry_on_error(self, func, *args, **kwargs):
        """
        Retry a function call on transient errors
        
        Args:
            func: Function to retry
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries fail
        """
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except (ClientError, BotoCoreError) as e:
                last_exception = e
                error_code = None
                if isinstance(e, ClientError):
                    error_code = e.response.get('Error', {}).get('Code', '')
                
                # Retry on transient errors
                retryable_errors = ['500', '503', '502', '504', 'Throttling', 
                                   'RequestTimeout', 'ServiceUnavailable']
                if error_code in retryable_errors or 'timeout' in str(e).lower():
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"S3 operation failed (attempt {attempt + 1}/{self.max_retries}): {e}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                
                # Non-retryable error or max retries reached
                raise
        
        # If we get here, all retries failed
        raise last_exception
    
    def ensure_storage_exists(self) -> None:
        """Ensure S3 bucket exists"""
        try:
            self._retry_on_error(self.s3.head_bucket, Bucket=self.bucket)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    create_params = {'Bucket': self.bucket}
                    if self.region != 'us-east-1':
                        create_params['CreateBucketConfiguration'] = {
                            'LocationConstraint': self.region
                        }
                    self._retry_on_error(self.s3.create_bucket, **create_params)
                    logger.info(f"Created S3 bucket: {self.bucket}")
                except ClientError as create_error:
                    logger.error(f"Failed to create S3 bucket {self.bucket}: {create_error}")
                    raise
            else:
                logger.error(f"Failed to access S3 bucket {self.bucket}: {e}")
                raise
    
    def save(self, path: str, content: Union[str, Dict, bytes, BinaryIO]) -> None:
        """
        Save content to S3
        
        Args:
            path: S3 key (relative path, prefix will be added automatically)
            content: Content to save
        """
        key = self._get_full_key(path)
        
        if isinstance(content, dict):
            data = json.dumps(content).encode('utf-8')
        elif isinstance(content, str):
            data = content.encode('utf-8')
        elif isinstance(content, bytes):
            data = content
        elif isinstance(content, BinaryIO):
            data = content.read()
        else:
            raise ValueError(f"Unsupported content type: {type(content)}")
        
        try:
            self._retry_on_error(
                self.s3.put_object,
                Bucket=self.bucket,
                Key=key,
                Body=data
            )
            logger.debug(f"Saved content to S3: {key}")
        except ClientError as e:
            error_msg = f"Failed to save content to S3 key {key}: {e}"
            logger.error(error_msg)
            raise IOError(error_msg) from e
    
    def load(self, path: str) -> Union[Dict, bytes]:
        """
        Load content from S3
        
        Args:
            path: S3 key (relative path, prefix will be added automatically)
            
        Returns:
            Content as dictionary or bytes
        """
        key = self._get_full_key(path)
        
        try:
            response = self._retry_on_error(
                self.s3.get_object,
                Bucket=self.bucket,
                Key=key
            )
            content = response['Body'].read()
            
            try:
                # Try to parse as JSON
                return json.loads(content)
            except json.JSONDecodeError:
                # Return raw bytes if not JSON
                return content
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchKey':
                raise FileNotFoundError(f"File not found in S3: {key}")
            error_msg = f"Failed to load content from S3 key {key}: {e}"
            logger.error(error_msg)
            raise IOError(error_msg) from e
    
    def delete(self, path: str) -> bool:
        """
        Delete content from S3
        
        Args:
            path: S3 key (relative path, prefix will be added automatically)
            
        Returns:
            True if successful, False otherwise
        """
        key = self._get_full_key(path)
        
        try:
            self._retry_on_error(
                self.s3.delete_object,
                Bucket=self.bucket,
                Key=key
            )
            logger.debug(f"Deleted content from S3: {key}")
            return True
        except ClientError as e:
            error_msg = f"Failed to delete content from S3 key {key}: {e}"
            logger.warning(error_msg)
            return False
    
    def exists(self, path: str) -> bool:
        """
        Check if content exists in S3
        
        Args:
            path: S3 key (relative path, prefix will be added automatically)
            
        Returns:
            True if content exists, False otherwise
        """
        key = self._get_full_key(path)
        
        try:
            self._retry_on_error(
                self.s3.head_object,
                Bucket=self.bucket,
                Key=key
            )
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                return False
            # For other errors, log and return False
            logger.warning(f"Error checking existence of S3 key {key}: {e}")
            return False
    
    def create_directory(self, path: str) -> bool:
        """
        Create a directory in S3 (S3 doesn't have real directories, but we create an empty marker)
        
        Args:
            path: S3 key (relative path, prefix will be added automatically)
            
        Returns:
            True if successful, False otherwise
        """
        key = self._get_full_key(path)
        
        # Ensure path ends with /
        if not key.endswith('/'):
            key += '/'
        
        try:
            self._retry_on_error(
                self.s3.put_object,
                Bucket=self.bucket,
                Key=key,
                Body=b''
            )
            logger.debug(f"Created directory marker in S3: {key}")
            return True
        except ClientError as e:
            error_msg = f"Failed to create directory in S3: {key}: {e}"
            logger.warning(error_msg)
            return False
    
    def list_directory(self, path: str) -> List[str]:
        """
        List contents of a directory in S3
        
        Args:
            path: S3 key prefix (relative path, prefix will be added automatically)
            
        Returns:
            List of keys in the directory (without prefix)
        """
        key = self._get_full_key(path)
        
        # Ensure path ends with /
        if not key.endswith('/'):
            key += '/'
        
        try:
            paginator = self.s3.get_paginator('list_objects_v2')
            keys = []
            
            for page in paginator.paginate(Bucket=self.bucket, Prefix=key):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        full_key = obj['Key']
                        if full_key != key:  # Skip the directory marker itself
                            # Remove prefix from returned keys
                            if self.prefix and full_key.startswith(self.prefix):
                                relative_key = full_key[len(self.prefix):]
                            else:
                                relative_key = full_key
                            keys.append(relative_key)
            
            return keys
        except ClientError as e:
            error_msg = f"Failed to list directory in S3: {key}: {e}"
            logger.warning(error_msg)
            return []
    
    def get_metadata(self, path: str) -> Dict[str, Any]:
        """
        Get metadata for an object in S3
        
        Args:
            path: S3 key (relative path, prefix will be added automatically)
            
        Returns:
            Dictionary of metadata
        """
        key = self._get_full_key(path)
        
        try:
            response = self._retry_on_error(
                self.s3.head_object,
                Bucket=self.bucket,
                Key=key
            )
            return {
                'size': response['ContentLength'],
                'created_at': response['LastModified'],
                'etag': response['ETag'],
                'content_type': response.get('ContentType', 'application/octet-stream'),
                'metadata': response.get('Metadata', {})
            }
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                raise FileNotFoundError(f"File not found: {key}")
            error_msg = f"Failed to get metadata for S3 key {key}: {e}"
            logger.error(error_msg)
            raise IOError(error_msg) from e
    
    def get_url(self, path: str, expires_in: Optional[int] = 3600) -> str:
        """
        Get a presigned URL for accessing the object
        
        Args:
            path: S3 key (relative path, prefix will be added automatically)
            expires_in: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL
        """
        key = self._get_full_key(path)
        
        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': key
                },
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            error_msg = f"Failed to generate presigned URL for {key}: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
    
    def copy(self, source_path: str, dest_path: str) -> bool:
        """
        Copy an object in S3
        
        Args:
            source_path: Source S3 key (relative path, prefix will be added automatically)
            dest_path: Destination S3 key (relative path, prefix will be added automatically)
            
        Returns:
            True if successful, False otherwise
        """
        source_key = self._get_full_key(source_path)
        dest_key = self._get_full_key(dest_path)
        
        try:
            self._retry_on_error(
                self.s3.copy_object,
                CopySource={'Bucket': self.bucket, 'Key': source_key},
                Bucket=self.bucket,
                Key=dest_key
            )
            logger.debug(f"Copied S3 object from {source_key} to {dest_key}")
            return True
        except ClientError as e:
            error_msg = f"Failed to copy S3 object from {source_key} to {dest_key}: {e}"
            logger.warning(error_msg)
            return False
    
    def move(self, source_path: str, dest_path: str) -> bool:
        """
        Move an object in S3
        
        Args:
            source_path: Source S3 key (relative path, prefix will be added automatically)
            dest_path: Destination S3 key (relative path, prefix will be added automatically)
            
        Returns:
            True if successful, False otherwise
        """
        if self.copy(source_path, dest_path):
            return self.delete(source_path)
        return False
    
    def store(self, source_path: str, document_path: str) -> str:
        """
        Store a document from source path to S3
        
        Args:
            source_path: Path to source document file
            document_path: S3 key (relative path, prefix will be added automatically)
            
        Returns:
            Path where document was stored (relative path without prefix)
        """
        try:
            # Read source file
            source_file = Path(source_path)
            if not source_file.exists():
                raise FileNotFoundError(f"Source file not found: {source_path}")
            
            with open(source_file, 'rb') as f:
                content = f.read()
            
            # Save to S3
            self.save(document_path, content)
            
            # Return the relative path (without prefix) for consistency with filesystem storage
            return document_path
        except Exception as e:
            logger.error(f"Failed to store document to S3 path {document_path}: {e}")
            raise
    
    def retrieve(self, path: str) -> Optional[Union[str, bytes]]:
        """
        Retrieve content from the specified path
        
        Args:
            path: S3 key (relative path, prefix will be added automatically)
            
        Returns:
            Content as string or bytes, or None if not found
        """
        try:
            return self.load(path)
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve content from S3 path {path}: {e}")
            return None
    
    def set_metadata(self, path: str, metadata: Dict[str, Any]) -> bool:
        """
        Set metadata for an object in S3
        
        Args:
            path: S3 key (relative path, prefix will be added automatically)
            metadata: Dictionary of metadata to set
            
        Returns:
            True if successful, False otherwise
        """
        key = self._get_full_key(path)
        
        try:
            # Copy object to itself with new metadata
            self._retry_on_error(
                self.s3.copy_object,
                CopySource={'Bucket': self.bucket, 'Key': key},
                Bucket=self.bucket,
                Key=key,
                Metadata=metadata,
                MetadataDirective='REPLACE'
            )
            logger.debug(f"Set metadata for S3 object: {key}")
            return True
        except ClientError as e:
            error_msg = f"Failed to set metadata for S3 key {key}: {e}"
            logger.warning(error_msg)
            return False
    
    def cleanup(self) -> None:
        """
        Clean up storage (delete all objects in bucket with prefix)
        
        WARNING: This will delete all objects with the configured prefix!
        """
        try:
            # Only delete objects with the configured prefix
            prefix = self.prefix if self.prefix else ''
            paginator = self.s3.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                if 'Contents' in page:
                    objects = [{'Key': obj['Key']} for obj in page['Contents']]
                    if objects:
                        self.s3.delete_objects(
                            Bucket=self.bucket,
                            Delete={'Objects': objects}
                        )
                        logger.info(f"Deleted {len(objects)} objects from S3 bucket {self.bucket} with prefix {prefix}")
        except ClientError as e:
            error_msg = f"Failed to cleanup S3 bucket {self.bucket}: {e}"
            logger.error(error_msg)
            raise IOError(error_msg) from e 