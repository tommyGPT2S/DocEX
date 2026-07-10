"""
DocEX Export Connectors

Provides connectors for exporting STRUCTURED DATA from processed documents.
These are different from Storage components (S3Storage, FilesystemStorage) which
handle raw document content storage.

Connectors are for:
- Delivering processed/extracted data to external systems
- Exporting structured results (JSON, CSV) to destinations
- Webhook notifications to external APIs

For raw document storage, use docex.storage components instead:
- docex.storage.S3Storage - S3 document storage
- docex.storage.FilesystemStorage - Local file storage
- docex.services.StorageService - Storage abstraction

Available Connectors:
- Webhook: HTTP POST to external endpoints (with HMAC signing)
- Database: Direct database insertion for structured data
- CSV: Structured data export to CSV files
"""

from .base import BaseConnector, ConnectorConfig, DeliveryResult
from .webhook import WebhookConnector, WebhookConfig
from .database import DatabaseConnector, DatabaseConfig
from .csv_export import CSVExporter, CSVConfig
from .storage_export import (
    StorageExporter, 
    StorageExportConfig,
    export_to_s3,
    export_to_filesystem
)

__all__ = [
    # Base
    'BaseConnector',
    'ConnectorConfig',
    'DeliveryResult',
    
    # Connectors (for structured data export)
    'WebhookConnector',
    'WebhookConfig',
    'DatabaseConnector',
    'DatabaseConfig',
    'CSVExporter',
    'CSVConfig',
    
    # Storage-based export (uses existing DocEX storage infrastructure)
    'StorageExporter',
    'StorageExportConfig',
    'export_to_s3',
    'export_to_filesystem'
]

