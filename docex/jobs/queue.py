"""
Job Queue

Provides an interface for queueing document processing jobs.
Uses the Operation model for persistence.
"""

import logging
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import select, and_, or_

from docex.db.connection import Database
from docex.db.models import Operation, OperationDependency, Document as DocumentModel

logger = logging.getLogger(__name__)


class JobPriority(IntEnum):
    """Job priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class JobQueue:
    """
    Queue for document processing jobs.
    
    Provides methods for:
    - Enqueuing jobs
    - Job dependencies
    - Priority-based ordering
    - Idempotency checking
    
    Usage:
        queue = JobQueue(db)
        
        # Enqueue a job
        job_id = queue.enqueue(
            document_id='doc_123',
            operation_type='INVOICE_EXTRACTION',
            priority=JobPriority.HIGH
        )
        
        # Enqueue with dependency
        job2_id = queue.enqueue(
            document_id='doc_123',
            operation_type='INVOICE_VALIDATION',
            depends_on=[job_id]
        )
    """
    
    def __init__(self, db: Database):
        self.db = db
    
    def enqueue(
        self,
        document_id: str,
        operation_type: str,
        priority: JobPriority = JobPriority.NORMAL,
        depends_on: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None
    ) -> str:
        """
        Enqueue a job for processing.
        
        Args:
            document_id: Document to process
            operation_type: Type of operation
            priority: Job priority
            depends_on: List of operation IDs this job depends on
            details: Additional job details
            idempotency_key: Key for duplicate prevention
            
        Returns:
            Operation ID
        """
        # Check idempotency
        if idempotency_key:
            existing = self._find_by_idempotency_key(idempotency_key)
            if existing:
                logger.debug(f"Duplicate job detected: {idempotency_key}")
                return existing.id
        
        operation_id = f"ope_{uuid4().hex}"
        
        with self.db.transaction() as session:
            # Create operation
            operation = Operation(
                id=operation_id,
                document_id=document_id,
                operation_type=operation_type,
                status='PENDING',
                details={
                    **(details or {}),
                    'priority': priority.value,
                    'idempotency_key': idempotency_key,
                    'enqueued_at': datetime.now(timezone.utc).isoformat()
                },
                created_at=datetime.now(timezone.utc)
            )
            session.add(operation)
            
            # Add dependencies
            if depends_on:
                for dep_id in depends_on:
                    dependency = OperationDependency(
                        operation_id=operation_id,
                        depends_on=dep_id
                    )
                    session.add(dependency)
            
            session.commit()
        
        logger.info(f"Enqueued job {operation_id} for document {document_id}")
        return operation_id
    
    def enqueue_batch(
        self,
        jobs: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Enqueue multiple jobs.
        
        Args:
            jobs: List of job specifications
                Each job should have: document_id, operation_type
                Optional: priority, depends_on, details, idempotency_key
                
        Returns:
            List of operation IDs
        """
        operation_ids = []
        
        with self.db.transaction() as session:
            for job in jobs:
                operation_id = f"ope_{uuid4().hex}"
                
                # Check idempotency
                idempotency_key = job.get('idempotency_key')
                if idempotency_key:
                    existing = self._find_by_idempotency_key(idempotency_key)
                    if existing:
                        operation_ids.append(existing.id)
                        continue
                
                operation = Operation(
                    id=operation_id,
                    document_id=job['document_id'],
                    operation_type=job['operation_type'],
                    status='PENDING',
                    details={
                        **(job.get('details') or {}),
                        'priority': job.get('priority', JobPriority.NORMAL.value),
                        'idempotency_key': idempotency_key,
                        'enqueued_at': datetime.now(timezone.utc).isoformat()
                    },
                    created_at=datetime.now(timezone.utc)
                )
                session.add(operation)
                
                # Add dependencies
                depends_on = job.get('depends_on', [])
                for dep_id in depends_on:
                    dependency = OperationDependency(
                        operation_id=operation_id,
                        depends_on=dep_id
                    )
                    session.add(dependency)
                
                operation_ids.append(operation_id)
            
            session.commit()
        
        logger.info(f"Enqueued {len(operation_ids)} jobs")
        return operation_ids
    
    def get_pending_count(
        self,
        operation_type: Optional[str] = None
    ) -> int:
        """Get count of pending jobs"""
        with self.db.session() as session:
            query = select(Operation).where(Operation.status == 'PENDING')
            
            if operation_type:
                query = query.where(Operation.operation_type == operation_type)
            
            result = session.execute(query).scalars().all()
            return len(result)
    
    def get_job_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a job"""
        with self.db.session() as session:
            operation = session.get(Operation, operation_id)
            
            if not operation:
                return None
            
            return {
                'id': operation.id,
                'document_id': operation.document_id,
                'operation_type': operation.operation_type,
                'status': operation.status,
                'error': operation.error,
                'details': operation.details,
                'created_at': operation.created_at.isoformat() if operation.created_at else None,
                'completed_at': operation.completed_at.isoformat() if operation.completed_at else None
            }
    
    def cancel_job(self, operation_id: str) -> bool:
        """
        Cancel a pending job.
        
        Returns:
            True if cancelled, False if not found or not pending
        """
        with self.db.transaction() as session:
            operation = session.get(Operation, operation_id)
            
            if not operation or operation.status != 'PENDING':
                return False
            
            operation.status = 'CANCELLED'
            operation.completed_at = datetime.now(timezone.utc)
            session.commit()
            
        logger.info(f"Cancelled job {operation_id}")
        return True
    
    def retry_failed(
        self,
        operation_id: str,
        reset_retry_count: bool = False
    ) -> bool:
        """
        Retry a failed job.
        
        Args:
            operation_id: Operation to retry
            reset_retry_count: Whether to reset the retry count
            
        Returns:
            True if reset to pending
        """
        with self.db.transaction() as session:
            operation = session.get(Operation, operation_id)
            
            if not operation:
                return False
            
            if operation.status not in ('FAILED', 'DEAD_LETTER'):
                return False
            
            operation.status = 'PENDING'
            operation.error = None
            operation.completed_at = None
            
            if reset_retry_count:
                details = operation.details or {}
                details['retry_count'] = 0
                operation.details = details
            
            session.commit()
        
        logger.info(f"Reset job {operation_id} to pending")
        return True
    
    def get_dead_letter_jobs(
        self,
        operation_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get jobs in dead letter status"""
        with self.db.session() as session:
            query = select(Operation).where(Operation.status == 'DEAD_LETTER')
            
            if operation_type:
                query = query.where(Operation.operation_type == operation_type)
            
            query = query.order_by(Operation.completed_at.desc()).limit(limit)
            
            operations = session.execute(query).scalars().all()
            
            return [
                {
                    'id': op.id,
                    'document_id': op.document_id,
                    'operation_type': op.operation_type,
                    'error': op.error,
                    'details': op.details,
                    'completed_at': op.completed_at.isoformat() if op.completed_at else None
                }
                for op in operations
            ]
    
    def clear_completed(
        self,
        older_than_days: int = 30
    ) -> int:
        """
        Clear completed jobs older than specified days.
        
        Returns:
            Number of jobs cleared
        """
        from datetime import timedelta
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        
        with self.db.transaction() as session:
            query = select(Operation).where(
                and_(
                    Operation.status == 'COMPLETED',
                    Operation.completed_at < cutoff
                )
            )
            
            operations = session.execute(query).scalars().all()
            count = len(operations)
            
            for op in operations:
                session.delete(op)
            
            session.commit()
        
        logger.info(f"Cleared {count} completed jobs")
        return count
    
    def _find_by_idempotency_key(self, key: str) -> Optional[Operation]:
        """Find operation by idempotency key"""
        with self.db.session() as session:
            # Search in details JSON
            query = select(Operation).where(
                Operation.status.in_(['PENDING', 'PROCESSING', 'COMPLETED'])
            )
            
            operations = session.execute(query).scalars().all()
            
            for op in operations:
                if op.details and op.details.get('idempotency_key') == key:
                    return op
            
            return None
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        with self.db.session() as session:
            # Count by status
            query = select(Operation)
            operations = session.execute(query).scalars().all()
            
            stats = {
                'total': len(operations),
                'by_status': {},
                'by_type': {}
            }
            
            for op in operations:
                # By status
                status = op.status or 'UNKNOWN'
                stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
                
                # By type
                op_type = op.operation_type or 'UNKNOWN'
                stats['by_type'][op_type] = stats['by_type'].get(op_type, 0) + 1
            
            return stats


def create_invoice_extraction_job(
    db: Database,
    document_id: str,
    priority: JobPriority = JobPriority.NORMAL
) -> str:
    """
    Convenience function to create an invoice extraction job.
    
    Args:
        db: Database instance
        document_id: Document to process
        priority: Job priority
        
    Returns:
        Operation ID
    """
    queue = JobQueue(db)
    
    # Use document checksum as idempotency key
    with db.session() as session:
        doc = session.get(DocumentModel, document_id)
        idempotency_key = f"invoice_extraction:{doc.checksum}" if doc else None
    
    return queue.enqueue(
        document_id=document_id,
        operation_type='INVOICE_EXTRACTION',
        priority=priority,
        idempotency_key=idempotency_key
    )

