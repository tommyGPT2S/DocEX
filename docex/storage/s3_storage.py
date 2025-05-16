import os
import json
from typing import Dict, Any, Optional, Union, BinaryIO, List
from datetime import datetime, timedelta
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from io import BytesIO

from .abstract_storage import AbstractStorage

class S3Storage(AbstractStorage):
    """
    S3 implementation of the storage backend
    
    Stores document content in Amazon S3.
    """
    
    def __init__(self, bucket: str, access_key: str, secret_key: str, region: str = 'us-east-1'):
        """
        Initialize S3 storage
        
        Args:
            bucket: S3 bucket name
            access_key: AWS access key
            secret_key: AWS secret key
            region: AWS region
        """
        self.bucket = bucket
        self.region = region
        
        # Initialize S3 client
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        
        # Ensure bucket exists
        self.ensure_storage_exists()
    
    def ensure_storage_exists(self) -> None:
        """Ensure S3 bucket exists"""
        try:
            self.s3.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                self.s3.create_bucket(
                    Bucket=self.bucket,
                    CreateBucketConfiguration={
                        'LocationConstraint': self.region
                    } if self.region != 'us-east-1' else {}
                )
            else:
                raise
    
    def save(self, path: str, content: Union[str, Dict, bytes, BinaryIO]) -> None:
        """
        Save content to S3
        
        Args:
            path: S3 key
            content: Content to save
        """
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
        
        self.s3.put_object(
            Bucket=self.bucket,
            Key=path,
            Body=data
        )
    
    def load(self, path: str) -> Union[Dict, bytes]:
        """
        Load content from S3
        
        Args:
            path: S3 key
            
        Returns:
            Content as dictionary or bytes
        """
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=path)
            content = response['Body'].read()
            
            try:
                # Try to parse as JSON
                return json.loads(content)
            except json.JSONDecodeError:
                # Return raw bytes if not JSON
                return content
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"File not found in S3: {path}")
            raise
    
    def delete(self, path: str) -> bool:
        """
        Delete content from S3
        
        Args:
            path: S3 key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=path)
            return True
        except ClientError:
            return False
    
    def exists(self, path: str) -> bool:
        """
        Check if content exists in S3
        
        Args:
            path: S3 key
            
        Returns:
            True if content exists, False otherwise
        """
        try:
            self.s3.head_object(Bucket=self.bucket, Key=path)
            return True
        except ClientError:
            return False
    
    def create_directory(self, path: str) -> bool:
        """
        Create a directory in S3 (S3 doesn't have real directories, but we create an empty marker)
        
        Args:
            path: S3 key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure path ends with /
            if not path.endswith('/'):
                path += '/'
            
            # Create empty object to represent directory
            self.s3.put_object(Bucket=self.bucket, Key=path, Body=b'')
            return True
        except ClientError:
            return False
    
    def list_directory(self, path: str) -> List[str]:
        """
        List contents of a directory in S3
        
        Args:
            path: S3 key prefix
            
        Returns:
            List of keys in the directory
        """
        # Ensure path ends with /
        if not path.endswith('/'):
            path += '/'
        
        try:
            paginator = self.s3.get_paginator('list_objects_v2')
            keys = []
            
            for page in paginator.paginate(Bucket=self.bucket, Prefix=path):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        if key != path:  # Skip the directory marker itself
                            keys.append(key)
            
            return keys
        except ClientError:
            return []
    
    def get_metadata(self, path: str) -> Dict[str, Any]:
        """
        Get metadata for an object in S3
        
        Args:
            path: S3 key
            
        Returns:
            Dictionary of metadata
        """
        try:
            response = self.s3.head_object(Bucket=self.bucket, Key=path)
            return {
                'size': response['ContentLength'],
                'created_at': response['LastModified'],
                'etag': response['ETag'],
                'content_type': response.get('ContentType', 'application/octet-stream'),
                'metadata': response.get('Metadata', {})
            }
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise FileNotFoundError(f"File not found: {path}")
            raise
    
    def get_url(self, path: str, expires_in: Optional[int] = 3600) -> str:
        """
        Get a presigned URL for accessing the object
        
        Args:
            path: S3 key
            expires_in: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL
        """
        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': path
                },
                ExpiresIn=expires_in
            )
            return url
        except ClientError:
            raise ValueError(f"Failed to generate URL for {path}")
    
    def copy(self, source_path: str, dest_path: str) -> bool:
        """
        Copy an object in S3
        
        Args:
            source_path: Source S3 key
            dest_path: Destination S3 key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3.copy_object(
                CopySource={'Bucket': self.bucket, 'Key': source_path},
                Bucket=self.bucket,
                Key=dest_path
            )
            return True
        except ClientError:
            return False
    
    def move(self, source_path: str, dest_path: str) -> bool:
        """
        Move an object in S3
        
        Args:
            source_path: Source S3 key
            dest_path: Destination S3 key
            
        Returns:
            True if successful, False otherwise
        """
        if self.copy(source_path, dest_path):
            return self.delete(source_path)
        return False
    
    def store(self, path: str, content: Union[str, bytes, BinaryIO]) -> bool:
        """
        Store content at the specified path
        
        Args:
            path: S3 key
            content: Content to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.save(path, content)
            return True
        except Exception:
            return False
    
    def retrieve(self, path: str) -> Optional[Union[str, bytes]]:
        """
        Retrieve content from the specified path
        
        Args:
            path: S3 key
            
        Returns:
            Content as string or bytes, or None if not found
        """
        try:
            return self.load(path)
        except FileNotFoundError:
            return None
    
    def set_metadata(self, path: str, metadata: Dict[str, Any]) -> bool:
        """
        Set metadata for an object in S3
        
        Args:
            path: S3 key
            metadata: Dictionary of metadata to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Copy object to itself with new metadata
            self.s3.copy_object(
                CopySource={'Bucket': self.bucket, 'Key': path},
                Bucket=self.bucket,
                Key=path,
                Metadata=metadata,
                MetadataDirective='REPLACE'
            )
            return True
        except ClientError:
            return False
    
    def cleanup(self) -> None:
        """Clean up storage (delete all objects in bucket)"""
        try:
            # Delete all objects in the bucket
            paginator = self.s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket):
                if 'Contents' in page:
                    objects = [{'Key': obj['Key']} for obj in page['Contents']]
                    self.s3.delete_objects(
                        Bucket=self.bucket,
                        Delete={'Objects': objects}
                    )
        except ClientError:
            pass 