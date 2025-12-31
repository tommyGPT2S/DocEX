"""
S3 Connector

Delivers processed documents to AWS S3 buckets.
Supports:
- Custom bucket and key prefix
- Server-side encryption
- Metadata tagging
- Batch uploads
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseConnector, ConnectorConfig, DeliveryResult, DeliveryStatus

logger = logging.getLogger(__name__)

# Optional boto3
try:
    import boto3
    from botocore.config import Config as BotoConfig
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


@dataclass
class S3Config(ConnectorConfig):
    """S3 connector configuration"""
    # Bucket
    bucket: str = ""
    key_prefix: str = "invoices/"
    
    # AWS credentials (optional, uses default chain if not provided)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    
    # Upload options
    content_type: str = "application/json"
    server_side_encryption: Optional[str] = "AES256"  # or "aws:kms"
    kms_key_id: Optional[str] = None
    
    # Storage class
    storage_class: str = "STANDARD"  # STANDARD, STANDARD_IA, GLACIER, etc.
    
    # Tagging
    tags: Dict[str, str] = field(default_factory=dict)


class S3Connector(BaseConnector):
    """
    Connector for delivering documents to AWS S3.
    
    Usage:
        config = S3Config(
            bucket="my-invoices-bucket",
            key_prefix="processed/2024/",
            aws_region="us-west-2"
        )
        
        connector = S3Connector(config)
        result = await connector.deliver(doc_id, invoice_data)
    """
    
    def __init__(self, config: S3Config, db=None):
        super().__init__(config, db)
        self.s3_config = config
        
        if not HAS_BOTO3:
            raise ImportError(
                "S3 connector requires 'boto3'. "
                "Install with: pip install boto3"
            )
        
        # Initialize S3 client
        self._client = self._create_client()
    
    @property
    def connector_type(self) -> str:
        return "S3"
    
    def _create_client(self):
        """Create S3 client"""
        kwargs = {
            'region_name': self.s3_config.aws_region,
            'config': BotoConfig(
                connect_timeout=self.config.timeout_seconds,
                read_timeout=self.config.timeout_seconds,
                retries={'max_attempts': 0}  # We handle retries ourselves
            )
        }
        
        if self.s3_config.aws_access_key_id:
            kwargs['aws_access_key_id'] = self.s3_config.aws_access_key_id
            kwargs['aws_secret_access_key'] = self.s3_config.aws_secret_access_key
        
        return boto3.client('s3', **kwargs)
    
    async def deliver(
        self,
        document_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> DeliveryResult:
        """
        Upload document data to S3.
        
        Args:
            document_id: Document ID
            data: Data to upload
            metadata: Optional metadata
            
        Returns:
            DeliveryResult
        """
        # Check deduplication
        if not self.should_deliver(document_id):
            logger.info(f"Document {document_id} already delivered, skipping")
            return DeliveryResult(
                success=True,
                status=DeliveryStatus.DELIVERED,
                response_data={'skipped': 'already_delivered'}
            )
        
        start_time = time.time()
        
        try:
            # Build S3 key
            timestamp = datetime.now(timezone.utc).strftime('%Y/%m/%d')
            key = f"{self.s3_config.key_prefix}{timestamp}/{document_id}.json"
            
            # Build upload payload
            payload = {
                'document_id': document_id,
                'data': data,
                'metadata': metadata or {},
                'uploaded_at': datetime.now(timezone.utc).isoformat()
            }
            
            body = json.dumps(payload, indent=2, default=str)
            
            # Build upload args
            put_args = {
                'Bucket': self.s3_config.bucket,
                'Key': key,
                'Body': body.encode('utf-8'),
                'ContentType': self.s3_config.content_type,
                'StorageClass': self.s3_config.storage_class
            }
            
            # Add encryption
            if self.s3_config.server_side_encryption:
                put_args['ServerSideEncryption'] = self.s3_config.server_side_encryption
                if self.s3_config.server_side_encryption == 'aws:kms' and self.s3_config.kms_key_id:
                    put_args['SSEKMSKeyId'] = self.s3_config.kms_key_id
            
            # Add metadata
            s3_metadata = {
                'document-id': document_id,
                'source': 'docex-connector'
            }
            if metadata:
                for k, v in metadata.items():
                    # S3 metadata values must be strings
                    s3_metadata[k.replace('_', '-')] = str(v)[:1024]
            put_args['Metadata'] = s3_metadata
            
            # Add tags
            if self.s3_config.tags:
                tag_set = '&'.join(f"{k}={v}" for k, v in self.s3_config.tags.items())
                put_args['Tagging'] = tag_set
            
            # Upload (using sync client in async context - boto3 doesn't have async)
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.put_object(**put_args)
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return DeliveryResult(
                success=True,
                status=DeliveryStatus.DELIVERED,
                response_data={
                    's3_key': key,
                    'bucket': self.s3_config.bucket,
                    'etag': response.get('ETag', '').strip('"'),
                    'version_id': response.get('VersionId')
                },
                delivered_at=datetime.now(timezone.utc),
                duration_ms=duration_ms
            )
            
        except Exception as e:
            logger.exception(f"S3 upload failed: {e}")
            return DeliveryResult(
                success=False,
                status=DeliveryStatus.FAILED,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000)
            )
    
    async def deliver_batch(
        self,
        items: List[Dict[str, Any]]
    ) -> List[DeliveryResult]:
        """
        Upload multiple documents to S3.
        
        Uses concurrent uploads for efficiency.
        
        Args:
            items: List of items to upload
            
        Returns:
            List of DeliveryResult
        """
        import asyncio
        
        # Process in batches with concurrency limit
        semaphore = asyncio.Semaphore(10)  # Max 10 concurrent uploads
        
        async def upload_with_limit(item):
            async with semaphore:
                return await self.deliver(
                    document_id=item['document_id'],
                    data=item['data'],
                    metadata=item.get('metadata')
                )
        
        tasks = [upload_with_limit(item) for item in items]
        return await asyncio.gather(*tasks)
    
    def get_object_url(self, document_id: str) -> str:
        """
        Get the S3 URL for a document.
        
        Note: This returns the S3 URI, not a signed URL.
        Use get_presigned_url() for temporary access URLs.
        """
        timestamp = datetime.now(timezone.utc).strftime('%Y/%m/%d')
        key = f"{self.s3_config.key_prefix}{timestamp}/{document_id}.json"
        return f"s3://{self.s3_config.bucket}/{key}"
    
    def get_presigned_url(
        self,
        key: str,
        expires_in: int = 3600
    ) -> str:
        """
        Generate a presigned URL for temporary access.
        
        Args:
            key: S3 object key
            expires_in: URL expiration in seconds
            
        Returns:
            Presigned URL
        """
        return self._client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self.s3_config.bucket,
                'Key': key
            },
            ExpiresIn=expires_in
        )

