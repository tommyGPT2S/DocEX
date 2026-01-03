"""
Base Connector

Abstract base class for all export connectors.
Provides common functionality for delivery tracking and exactly-once semantics.

IMPORTANT: Connectors vs Storage
--------------------------------
Connectors export STRUCTURED DATA (JSON, CSV) to external systems.
Storage components (docex.storage) handle raw DOCUMENT CONTENT.

Use Connectors for:
- Webhook notifications with extracted invoice data
- Exporting parsed data to external databases  
- CSV exports of processing results

Use Storage (docex.storage) for:
- Storing original document files (PDF, Word, etc.)
- S3/filesystem document storage
- Document retrieval and archival

For S3 structured data export, use StorageExporter from storage_export.py
which leverages existing S3Storage infrastructure.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from docex.db.connection import Database
from docex.db.models import Operation

logger = logging.getLogger(__name__)


class DeliveryStatus(str, Enum):
    """Delivery status"""
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


@dataclass
class ConnectorConfig:
    """Base connector configuration"""
    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    
    # Timeout
    timeout_seconds: float = 30.0
    
    # Batch settings
    batch_size: int = 100
    
    # Exactly-once delivery
    enable_deduplication: bool = True
    
    # Custom config
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeliveryResult:
    """Result of a delivery operation"""
    success: bool
    delivery_id: str = field(default_factory=lambda: f"dlv_{uuid4().hex[:12]}")
    status: DeliveryStatus = DeliveryStatus.PENDING
    
    # Response data
    response_data: Optional[Dict[str, Any]] = None
    response_code: Optional[int] = None
    
    # Timing
    delivered_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    
    # Error
    error: Optional[str] = None
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'delivery_id': self.delivery_id,
            'success': self.success,
            'status': self.status.value,
            'response_code': self.response_code,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'duration_ms': self.duration_ms,
            'error': self.error,
            'retry_count': self.retry_count
        }


class DeliveryTracker:
    """
    Tracks deliveries for exactly-once semantics.
    
    Uses the Operation model to record delivery receipts.
    """
    
    def __init__(self, db: Database):
        self.db = db
    
    def record_delivery(
        self,
        document_id: str,
        connector_type: str,
        result: DeliveryResult
    ) -> str:
        """
        Record a delivery attempt.
        
        Args:
            document_id: Document that was delivered
            connector_type: Type of connector used
            result: Delivery result
            
        Returns:
            Operation ID
        """
        operation_id = f"ope_{uuid4().hex}"
        
        with self.db.transaction() as session:
            operation = Operation(
                id=operation_id,
                document_id=document_id,
                operation_type=f'DELIVERY_{connector_type.upper()}',
                status='COMPLETED' if result.success else 'FAILED',
                details={
                    'delivery_id': result.delivery_id,
                    'connector_type': connector_type,
                    **result.to_dict()
                },
                error=result.error,
                created_at=datetime.now(timezone.utc),
                completed_at=result.delivered_at or datetime.now(timezone.utc)
            )
            session.add(operation)
            session.commit()
        
        return operation_id
    
    def check_delivered(
        self,
        document_id: str,
        connector_type: str
    ) -> bool:
        """
        Check if document was already delivered to this connector.
        
        Args:
            document_id: Document ID
            connector_type: Connector type
            
        Returns:
            True if already delivered
        """
        from sqlalchemy import select, and_
        
        with self.db.session() as session:
            query = select(Operation).where(
                and_(
                    Operation.document_id == document_id,
                    Operation.operation_type == f'DELIVERY_{connector_type.upper()}',
                    Operation.status == 'COMPLETED'
                )
            )
            
            result = session.execute(query).scalar_one_or_none()
            return result is not None
    
    def get_delivery_history(
        self,
        document_id: str
    ) -> List[Dict[str, Any]]:
        """Get delivery history for a document"""
        from sqlalchemy import select, and_
        
        with self.db.session() as session:
            query = select(Operation).where(
                and_(
                    Operation.document_id == document_id,
                    Operation.operation_type.like('DELIVERY_%')
                )
            ).order_by(Operation.created_at.desc())
            
            operations = session.execute(query).scalars().all()
            
            return [
                {
                    'operation_id': op.id,
                    'connector_type': op.operation_type.replace('DELIVERY_', ''),
                    'status': op.status,
                    'details': op.details,
                    'error': op.error,
                    'created_at': op.created_at.isoformat() if op.created_at else None
                }
                for op in operations
            ]


class BaseConnector(ABC):
    """
    Abstract base class for export connectors.
    
    Subclasses must implement:
    - deliver(): Deliver a single document
    - deliver_batch(): Deliver multiple documents
    """
    
    def __init__(self, config: ConnectorConfig, db: Optional[Database] = None):
        self.config = config
        self.db = db
        self._tracker = DeliveryTracker(db) if db else None
    
    @property
    @abstractmethod
    def connector_type(self) -> str:
        """Return the connector type identifier"""
        pass
    
    @abstractmethod
    async def deliver(
        self,
        document_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> DeliveryResult:
        """
        Deliver a single document.
        
        Args:
            document_id: Document ID
            data: Data to deliver
            metadata: Optional metadata
            
        Returns:
            DeliveryResult
        """
        pass
    
    async def deliver_batch(
        self,
        items: List[Dict[str, Any]]
    ) -> List[DeliveryResult]:
        """
        Deliver multiple documents.
        
        Default implementation calls deliver() for each item.
        Subclasses can override for batch-optimized delivery.
        
        Args:
            items: List of items with document_id, data, metadata
            
        Returns:
            List of DeliveryResult
        """
        results = []
        
        for item in items:
            result = await self.deliver(
                document_id=item['document_id'],
                data=item['data'],
                metadata=item.get('metadata')
            )
            results.append(result)
        
        return results
    
    async def deliver_with_retry(
        self,
        document_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> DeliveryResult:
        """
        Deliver with automatic retry on failure.
        
        Args:
            document_id: Document ID
            data: Data to deliver
            metadata: Optional metadata
            
        Returns:
            DeliveryResult
        """
        import asyncio
        
        last_result = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                result = await self.deliver(document_id, data, metadata)
                result.retry_count = attempt
                
                if result.success:
                    # Record successful delivery
                    if self._tracker:
                        self._tracker.record_delivery(
                            document_id,
                            self.connector_type,
                            result
                        )
                    return result
                
                last_result = result
                
            except Exception as e:
                last_result = DeliveryResult(
                    success=False,
                    status=DeliveryStatus.FAILED,
                    error=str(e),
                    retry_count=attempt
                )
            
            # Wait before retry
            if attempt < self.config.max_retries:
                delay = self.config.retry_delay_seconds * (2 ** attempt)
                await asyncio.sleep(delay)
        
        # Record failed delivery
        if self._tracker and last_result:
            self._tracker.record_delivery(
                document_id,
                self.connector_type,
                last_result
            )
        
        return last_result or DeliveryResult(
            success=False,
            status=DeliveryStatus.FAILED,
            error="Max retries exceeded"
        )
    
    def should_deliver(self, document_id: str) -> bool:
        """
        Check if document should be delivered (deduplication).
        
        Args:
            document_id: Document ID
            
        Returns:
            True if should deliver
        """
        if not self.config.enable_deduplication:
            return True
        
        if not self._tracker:
            return True
        
        return not self._tracker.check_delivered(document_id, self.connector_type)

