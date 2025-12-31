"""
Storage Export Utilities

Provides utilities for exporting structured data using existing DocEX storage components.
This bridges the gap between connectors (structured data) and storage (raw content).

For document storage, use docex.storage directly.
For structured data export to S3/filesystem, use these utilities.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from docex.storage.storage_factory import StorageFactory
from .base import BaseConnector, ConnectorConfig, DeliveryResult, DeliveryStatus

logger = logging.getLogger(__name__)


class StorageExportConfig(ConnectorConfig):
    """Configuration for storage-based export"""
    
    def __init__(
        self,
        storage_type: str = 'filesystem',
        storage_config: Dict[str, Any] = None,
        key_template: str = "exports/{date}/{document_id}.json",
        **kwargs
    ):
        """
        Initialize storage export config.
        
        Args:
            storage_type: 'filesystem' or 's3'
            storage_config: Storage-specific configuration
                For filesystem: {'path': '/path/to/exports'}
                For S3: {'bucket': 'my-bucket', 'prefix': 'exports/'}
            key_template: Template for generating storage keys
                Supports: {date}, {document_id}, {timestamp}
        """
        super().__init__(**kwargs)
        self.storage_type = storage_type
        self.storage_config = storage_config or {}
        self.key_template = key_template


class StorageExporter(BaseConnector):
    """
    Export structured data using existing DocEX storage infrastructure.
    
    This uses S3Storage or FilesystemStorage under the hood, but provides
    a connector-style interface for structured data export.
    
    Usage:
        # Export to S3 using existing storage
        config = StorageExportConfig(
            storage_type='s3',
            storage_config={
                'bucket': 'my-exports-bucket',
                'prefix': 'invoices/'
            }
        )
        exporter = StorageExporter(config)
        result = await exporter.deliver(doc_id, invoice_data)
        
        # Export to filesystem
        config = StorageExportConfig(
            storage_type='filesystem',
            storage_config={'path': './exports'}
        )
        exporter = StorageExporter(config)
        result = await exporter.deliver(doc_id, invoice_data)
    """
    
    def __init__(self, config: StorageExportConfig, db=None):
        super().__init__(config, db)
        self.export_config = config
        
        # Create storage using existing factory
        storage_config = {
            'type': config.storage_type,
            **config.storage_config
        }
        self._storage = StorageFactory.create_storage(storage_config)
    
    @property
    def connector_type(self) -> str:
        return f"STORAGE_{self.export_config.storage_type.upper()}"
    
    def _generate_key(self, document_id: str) -> str:
        """Generate storage key from template"""
        now = datetime.now(timezone.utc)
        return self.export_config.key_template.format(
            date=now.strftime('%Y/%m/%d'),
            document_id=document_id,
            timestamp=now.strftime('%Y%m%d_%H%M%S')
        )
    
    async def deliver(
        self,
        document_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> DeliveryResult:
        """
        Export structured data to storage.
        
        Args:
            document_id: Document ID
            data: Structured data to export
            metadata: Optional metadata
            
        Returns:
            DeliveryResult
        """
        import time
        start_time = time.time()
        
        try:
            # Generate storage key
            key = self._generate_key(document_id)
            
            # Build export payload
            payload = {
                'document_id': document_id,
                'data': data,
                'metadata': metadata or {},
                'exported_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Use existing storage to save
            content = json.dumps(payload, indent=2, default=str)
            self._storage.save(key, content)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return DeliveryResult(
                success=True,
                status=DeliveryStatus.DELIVERED,
                response_data={
                    'storage_type': self.export_config.storage_type,
                    'key': key
                },
                delivered_at=datetime.now(timezone.utc),
                duration_ms=duration_ms
            )
            
        except Exception as e:
            logger.exception(f"Storage export failed: {e}")
            return DeliveryResult(
                success=False,
                status=DeliveryStatus.FAILED,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000)
            )


def export_to_s3(
    document_id: str,
    data: Dict[str, Any],
    bucket: str,
    prefix: str = "exports/",
    **s3_config
) -> DeliveryResult:
    """
    Convenience function to export data to S3 using existing storage.
    
    Args:
        document_id: Document ID
        data: Data to export
        bucket: S3 bucket name
        prefix: S3 key prefix
        **s3_config: Additional S3 configuration
        
    Returns:
        DeliveryResult
    """
    import asyncio
    
    config = StorageExportConfig(
        storage_type='s3',
        storage_config={
            'bucket': bucket,
            'prefix': prefix,
            **s3_config
        }
    )
    
    exporter = StorageExporter(config)
    
    # Run async deliver
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(exporter.deliver(document_id, data))


def export_to_filesystem(
    document_id: str,
    data: Dict[str, Any],
    path: str = "./exports"
) -> DeliveryResult:
    """
    Convenience function to export data to filesystem using existing storage.
    
    Args:
        document_id: Document ID
        data: Data to export
        path: Export directory path
        
    Returns:
        DeliveryResult
    """
    import asyncio
    
    config = StorageExportConfig(
        storage_type='filesystem',
        storage_config={'path': path}
    )
    
    exporter = StorageExporter(config)
    
    # Run async deliver
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(exporter.deliver(document_id, data))

