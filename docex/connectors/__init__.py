"""
DocEX Export Connectors

Provides connectors for exporting processed documents to various destinations:
- Webhook: HTTP POST to external endpoints
- S3: AWS S3 bucket storage
- Database: Direct database insertion
- CSV: File export
"""

from .base import BaseConnector, ConnectorConfig, DeliveryResult
from .webhook import WebhookConnector, WebhookConfig
from .s3 import S3Connector, S3Config
from .database import DatabaseConnector, DatabaseConfig
from .csv_export import CSVExporter, CSVConfig

__all__ = [
    # Base
    'BaseConnector',
    'ConnectorConfig',
    'DeliveryResult',
    
    # Connectors
    'WebhookConnector',
    'WebhookConfig',
    'S3Connector',
    'S3Config',
    'DatabaseConnector',
    'DatabaseConfig',
    'CSVExporter',
    'CSVConfig'
]

