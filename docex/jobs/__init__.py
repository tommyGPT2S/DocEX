"""
DocEX Jobs Module

Provides async job execution for document processing at scale.

Components:
- Worker: Polls operations table and executes pending jobs
- JobQueue: Interface for queueing and managing jobs
- RateLimiter: Controls LLM API call rates
- CostTracker: Tracks LLM API costs
"""

from .worker import Worker, WorkerConfig, run_worker
from .queue import JobQueue, JobPriority, create_invoice_extraction_job
from .rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    BatchAggregator,
    CostTracker
)

__all__ = [
    # Worker
    'Worker',
    'WorkerConfig',
    'run_worker',
    
    # Queue
    'JobQueue',
    'JobPriority',
    'create_invoice_extraction_job',
    
    # Rate limiting
    'RateLimiter',
    'RateLimitConfig',
    'BatchAggregator',
    'CostTracker'
]

