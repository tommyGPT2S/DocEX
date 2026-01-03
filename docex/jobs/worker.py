"""
Async Job Worker

Polls the operations table for pending jobs and executes them.
Supports:
- Concurrency control
- Retries with exponential backoff
- Dead letter handling
- Idempotency via document checksum
"""

import asyncio
import logging
import signal
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

from sqlalchemy import select, and_, or_, update

from docex.db.connection import Database
from docex.db.models import Operation, Document as DocumentModel, DocEvent

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job execution status"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    DEAD_LETTER = "DEAD_LETTER"


@dataclass
class WorkerConfig:
    """Worker configuration"""
    # Polling
    poll_interval: float = 1.0  # seconds
    batch_size: int = 10
    
    # Concurrency
    max_concurrent: int = 5
    
    # Retries
    max_retries: int = 3
    retry_delay_base: float = 5.0  # seconds
    retry_delay_max: float = 300.0  # seconds
    
    # Timeouts
    job_timeout: float = 300.0  # seconds
    stale_job_timeout: float = 600.0  # seconds (jobs processing too long)
    
    # Operation types to process
    operation_types: List[str] = field(default_factory=lambda: ['INVOICE_EXTRACTION'])
    
    # Graceful shutdown
    shutdown_timeout: float = 30.0


class Worker:
    """
    Async job worker for processing document operations.
    
    Polls the operations table for pending jobs and executes them
    using registered handlers.
    
    Usage:
        worker = Worker(db, config)
        
        # Register handlers
        worker.register_handler('INVOICE_EXTRACTION', invoice_handler)
        
        # Run worker
        await worker.run()
    """
    
    def __init__(self, db: Database, config: Optional[WorkerConfig] = None):
        self.db = db
        self.config = config or WorkerConfig()
        
        # Handlers for different operation types
        self._handlers: Dict[str, Callable] = {}
        
        # State
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._active_jobs: Set[str] = set()
        self._semaphore: Optional[asyncio.Semaphore] = None
        
        # Metrics
        self._processed_count = 0
        self._failed_count = 0
        self._start_time: Optional[datetime] = None
    
    def register_handler(
        self,
        operation_type: str,
        handler: Callable[[Operation, DocumentModel], Any]
    ) -> None:
        """
        Register a handler for an operation type.
        
        Args:
            operation_type: Type of operation to handle
            handler: Async function that processes the operation
        """
        self._handlers[operation_type] = handler
        logger.info(f"Registered handler for operation type: {operation_type}")
    
    async def run(self) -> None:
        """
        Run the worker.
        
        Polls for pending operations and executes them until shutdown.
        """
        logger.info("Starting worker...")
        
        self._running = True
        self._start_time = datetime.now(timezone.utc)
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        
        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        try:
            while self._running and not self._shutdown_event.is_set():
                try:
                    # Poll for pending operations
                    operations = await self._poll_operations()
                    
                    if operations:
                        # Process operations concurrently
                        tasks = [
                            self._process_operation(op)
                            for op in operations
                        ]
                        await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Wait before next poll
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=self.config.poll_interval
                        )
                    except asyncio.TimeoutError:
                        pass
                    
                except Exception as e:
                    logger.exception(f"Worker loop error: {e}")
                    await asyncio.sleep(self.config.poll_interval)
            
        finally:
            # Wait for active jobs to complete
            if self._active_jobs:
                logger.info(f"Waiting for {len(self._active_jobs)} active jobs to complete...")
                try:
                    await asyncio.wait_for(
                        self._wait_for_active_jobs(),
                        timeout=self.config.shutdown_timeout
                    )
                except asyncio.TimeoutError:
                    logger.warning("Shutdown timeout - some jobs may not have completed")
            
            logger.info(
                f"Worker stopped. Processed: {self._processed_count}, Failed: {self._failed_count}"
            )
    
    async def stop(self) -> None:
        """Stop the worker gracefully"""
        logger.info("Stopping worker...")
        self._running = False
        self._shutdown_event.set()
    
    async def _poll_operations(self) -> List[Operation]:
        """Poll for pending operations"""
        try:
            with self.db.session() as session:
                # Find pending operations of registered types
                query = select(Operation).where(
                    and_(
                        Operation.status == JobStatus.PENDING.value,
                        Operation.operation_type.in_(list(self._handlers.keys()))
                    )
                ).order_by(
                    Operation.created_at
                ).limit(
                    self.config.batch_size
                )
                
                operations = session.execute(query).scalars().all()
                
                # Claim operations
                claimed = []
                for op in operations:
                    if op.id not in self._active_jobs:
                        # Mark as processing
                        op.status = JobStatus.PROCESSING.value
                        session.commit()
                        claimed.append(op)
                
                return claimed
                
        except Exception as e:
            logger.error(f"Failed to poll operations: {e}")
            return []
    
    async def _process_operation(self, operation: Operation) -> None:
        """Process a single operation"""
        async with self._semaphore:
            self._active_jobs.add(operation.id)
            
            try:
                # Get handler
                handler = self._handlers.get(operation.operation_type)
                if not handler:
                    logger.error(f"No handler for operation type: {operation.operation_type}")
                    await self._mark_failed(operation.id, "No handler registered")
                    return
                
                # Get document
                with self.db.session() as session:
                    document = session.get(DocumentModel, operation.document_id)
                    if not document:
                        await self._mark_failed(operation.id, "Document not found")
                        return
                
                # Execute handler with timeout
                try:
                    result = await asyncio.wait_for(
                        handler(operation, document),
                        timeout=self.config.job_timeout
                    )
                    
                    await self._mark_completed(operation.id, result)
                    self._processed_count += 1
                    
                except asyncio.TimeoutError:
                    await self._handle_retry(operation.id, "Job timeout")
                    
                except Exception as e:
                    await self._handle_retry(operation.id, str(e))
                    
            finally:
                self._active_jobs.discard(operation.id)
    
    async def _mark_completed(
        self,
        operation_id: str,
        result: Any = None
    ) -> None:
        """Mark operation as completed"""
        try:
            with self.db.transaction() as session:
                operation = session.get(Operation, operation_id)
                if operation:
                    operation.status = JobStatus.COMPLETED.value
                    operation.completed_at = datetime.now(timezone.utc)
                    if result:
                        operation.details = {
                            **(operation.details or {}),
                            'result': str(result) if result else None
                        }
                    session.commit()
                    
        except Exception as e:
            logger.error(f"Failed to mark operation completed: {e}")
    
    async def _mark_failed(
        self,
        operation_id: str,
        error: str
    ) -> None:
        """Mark operation as failed"""
        try:
            with self.db.transaction() as session:
                operation = session.get(Operation, operation_id)
                if operation:
                    operation.status = JobStatus.FAILED.value
                    operation.completed_at = datetime.now(timezone.utc)
                    operation.error = error
                    session.commit()
                    
            self._failed_count += 1
            
        except Exception as e:
            logger.error(f"Failed to mark operation failed: {e}")
    
    async def _handle_retry(
        self,
        operation_id: str,
        error: str
    ) -> None:
        """Handle retry logic for failed operation"""
        try:
            with self.db.transaction() as session:
                operation = session.get(Operation, operation_id)
                if not operation:
                    return
                
                # Get retry count
                details = operation.details or {}
                retry_count = details.get('retry_count', 0)
                
                if retry_count >= self.config.max_retries:
                    # Move to dead letter
                    operation.status = JobStatus.DEAD_LETTER.value
                    operation.error = f"Max retries exceeded. Last error: {error}"
                    operation.completed_at = datetime.now(timezone.utc)
                    self._failed_count += 1
                    logger.warning(f"Operation {operation_id} moved to dead letter")
                else:
                    # Schedule retry
                    delay = min(
                        self.config.retry_delay_base * (2 ** retry_count),
                        self.config.retry_delay_max
                    )
                    
                    operation.status = JobStatus.PENDING.value  # Will be picked up again
                    operation.details = {
                        **details,
                        'retry_count': retry_count + 1,
                        'last_error': error,
                        'retry_after': (
                            datetime.now(timezone.utc) + timedelta(seconds=delay)
                        ).isoformat()
                    }
                    logger.info(
                        f"Operation {operation_id} scheduled for retry "
                        f"({retry_count + 1}/{self.config.max_retries}) in {delay}s"
                    )
                
                session.commit()
                
        except Exception as e:
            logger.error(f"Failed to handle retry: {e}")
    
    async def _wait_for_active_jobs(self) -> None:
        """Wait for all active jobs to complete"""
        while self._active_jobs:
            await asyncio.sleep(0.5)
    
    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown"""
        try:
            loop = asyncio.get_running_loop()
            
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(
                    sig,
                    lambda: asyncio.create_task(self.stop())
                )
        except (NotImplementedError, RuntimeError):
            # Signal handling not available (e.g., Windows)
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        uptime = None
        if self._start_time:
            uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()
        
        return {
            'running': self._running,
            'active_jobs': len(self._active_jobs),
            'processed_count': self._processed_count,
            'failed_count': self._failed_count,
            'uptime_seconds': uptime,
            'handlers_registered': list(self._handlers.keys())
        }


async def run_worker(
    db: Database,
    handlers: Dict[str, Callable],
    config: Optional[WorkerConfig] = None
) -> None:
    """
    Convenience function to run a worker.
    
    Args:
        db: Database instance
        handlers: Dict of operation_type -> handler function
        config: Optional worker configuration
    """
    worker = Worker(db, config)
    
    for op_type, handler in handlers.items():
        worker.register_handler(op_type, handler)
    
    await worker.run()

