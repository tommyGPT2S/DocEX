"""
Rate Limiter

Provides rate limiting and cost tracking for LLM API calls.
Supports:
- Per-tenant request limits
- Token/cost accounting
- Batch request aggregation
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional, TypeVar
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    # Request limits
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    
    # Token limits (optional)
    tokens_per_minute: Optional[int] = None
    tokens_per_day: Optional[int] = None
    
    # Cost limits (optional)
    cost_per_day: Optional[float] = None
    
    # Burst handling
    burst_size: int = 10
    burst_cooldown: float = 1.0  # seconds


@dataclass
class UsageStats:
    """Tracks usage statistics"""
    requests_minute: int = 0
    requests_hour: int = 0
    requests_day: int = 0
    tokens_minute: int = 0
    tokens_day: int = 0
    cost_day: float = 0.0
    
    last_minute_reset: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_hour_reset: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_day_reset: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def reset_if_needed(self) -> None:
        """Reset counters if time windows have passed"""
        now = datetime.now(timezone.utc)
        
        if (now - self.last_minute_reset) >= timedelta(minutes=1):
            self.requests_minute = 0
            self.tokens_minute = 0
            self.last_minute_reset = now
        
        if (now - self.last_hour_reset) >= timedelta(hours=1):
            self.requests_hour = 0
            self.last_hour_reset = now
        
        if (now - self.last_day_reset) >= timedelta(days=1):
            self.requests_day = 0
            self.tokens_day = 0
            self.cost_day = 0.0
            self.last_day_reset = now


class RateLimiter:
    """
    Rate limiter for API calls.
    
    Features:
    - Token bucket algorithm for smooth rate limiting
    - Per-tenant isolation
    - Automatic retry with backoff
    - Usage tracking and reporting
    
    Usage:
        limiter = RateLimiter(config)
        
        # Wait for rate limit
        await limiter.acquire()
        
        # Or use as decorator
        @limiter.limit
        async def call_llm():
            ...
        
        # Record usage
        limiter.record_usage(tokens=1500, cost=0.003)
    """
    
    def __init__(
        self,
        config: Optional[RateLimitConfig] = None,
        tenant_id: Optional[str] = None
    ):
        self.config = config or RateLimitConfig()
        self.tenant_id = tenant_id or 'default'
        
        # Per-tenant usage tracking
        self._usage: Dict[str, UsageStats] = defaultdict(UsageStats)
        
        # Token bucket
        self._tokens = self.config.burst_size
        self._last_update = time.monotonic()
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def acquire(self, tenant_id: Optional[str] = None) -> None:
        """
        Acquire permission to make a request.
        
        Blocks until rate limit allows the request.
        
        Args:
            tenant_id: Optional tenant override
        """
        tenant = tenant_id or self.tenant_id
        
        async with self._lock:
            # Reset counters if needed
            stats = self._usage[tenant]
            stats.reset_if_needed()
            
            # Check limits
            while not self._can_proceed(stats):
                # Calculate wait time
                wait_time = self._calculate_wait_time(stats)
                logger.debug(f"Rate limited, waiting {wait_time:.2f}s")
                
                # Release lock while waiting
                self._lock.release()
                await asyncio.sleep(wait_time)
                await self._lock.acquire()
                
                stats.reset_if_needed()
            
            # Update token bucket
            self._refill_tokens()
            self._tokens -= 1
            
            # Update counters
            stats.requests_minute += 1
            stats.requests_hour += 1
            stats.requests_day += 1
    
    def _can_proceed(self, stats: UsageStats) -> bool:
        """Check if request can proceed"""
        # Token bucket check
        self._refill_tokens()
        if self._tokens < 1:
            return False
        
        # Request rate checks
        if stats.requests_minute >= self.config.requests_per_minute:
            return False
        if stats.requests_hour >= self.config.requests_per_hour:
            return False
        if stats.requests_day >= self.config.requests_per_day:
            return False
        
        # Token checks
        if self.config.tokens_per_minute:
            if stats.tokens_minute >= self.config.tokens_per_minute:
                return False
        if self.config.tokens_per_day:
            if stats.tokens_day >= self.config.tokens_per_day:
                return False
        
        # Cost check
        if self.config.cost_per_day:
            if stats.cost_day >= self.config.cost_per_day:
                return False
        
        return True
    
    def _calculate_wait_time(self, stats: UsageStats) -> float:
        """Calculate time to wait before retry"""
        wait_times = []
        
        # Minute limit
        if stats.requests_minute >= self.config.requests_per_minute:
            until_reset = 60 - (datetime.now(timezone.utc) - stats.last_minute_reset).seconds
            wait_times.append(max(0, until_reset))
        
        # Token bucket refill
        if self._tokens < 1:
            tokens_needed = 1 - self._tokens
            refill_time = tokens_needed / (self.config.requests_per_minute / 60)
            wait_times.append(refill_time)
        
        return min(wait_times) if wait_times else self.config.burst_cooldown
    
    def _refill_tokens(self) -> None:
        """Refill token bucket based on elapsed time"""
        now = time.monotonic()
        elapsed = now - self._last_update
        self._last_update = now
        
        # Calculate tokens to add
        refill_rate = self.config.requests_per_minute / 60  # tokens per second
        tokens_to_add = elapsed * refill_rate
        
        self._tokens = min(self.config.burst_size, self._tokens + tokens_to_add)
    
    def record_usage(
        self,
        tokens: int = 0,
        cost: float = 0.0,
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Record usage after a request.
        
        Args:
            tokens: Tokens used
            cost: Cost incurred
            tenant_id: Optional tenant override
        """
        tenant = tenant_id or self.tenant_id
        stats = self._usage[tenant]
        
        stats.tokens_minute += tokens
        stats.tokens_day += tokens
        stats.cost_day += cost
    
    def get_usage(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Get current usage statistics"""
        tenant = tenant_id or self.tenant_id
        stats = self._usage[tenant]
        stats.reset_if_needed()
        
        return {
            'tenant_id': tenant,
            'requests': {
                'minute': stats.requests_minute,
                'hour': stats.requests_hour,
                'day': stats.requests_day
            },
            'tokens': {
                'minute': stats.tokens_minute,
                'day': stats.tokens_day
            },
            'cost': {
                'day': stats.cost_day
            },
            'limits': {
                'requests_per_minute': self.config.requests_per_minute,
                'requests_per_hour': self.config.requests_per_hour,
                'requests_per_day': self.config.requests_per_day,
                'tokens_per_day': self.config.tokens_per_day,
                'cost_per_day': self.config.cost_per_day
            }
        }
    
    def limit(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator to rate limit a function.
        
        Usage:
            @limiter.limit
            async def call_api():
                ...
        """
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            await self.acquire()
            return await func(*args, **kwargs)
        return wrapper


class BatchAggregator:
    """
    Aggregates multiple requests into batches.
    
    For APIs that support batch operations, this can reduce
    the number of API calls and improve efficiency.
    
    Usage:
        aggregator = BatchAggregator(
            batch_size=10,
            max_wait=1.0,
            process_batch=process_embeddings
        )
        
        # Individual items are batched automatically
        result = await aggregator.add(item)
    """
    
    def __init__(
        self,
        batch_size: int = 10,
        max_wait: float = 1.0,
        process_batch: Callable[[List[Any]], List[Any]] = None
    ):
        self.batch_size = batch_size
        self.max_wait = max_wait
        self.process_batch = process_batch
        
        self._items: List[Any] = []
        self._futures: List[asyncio.Future] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
    
    async def add(self, item: Any) -> Any:
        """
        Add an item to be batched.
        
        Returns:
            Result for this item after batch processing
        """
        future = asyncio.get_event_loop().create_future()
        
        async with self._lock:
            self._items.append(item)
            self._futures.append(future)
            
            # Start flush timer if first item
            if len(self._items) == 1:
                self._flush_task = asyncio.create_task(self._flush_after_wait())
            
            # Flush immediately if batch is full
            if len(self._items) >= self.batch_size:
                await self._flush()
        
        return await future
    
    async def _flush_after_wait(self) -> None:
        """Flush batch after max_wait time"""
        await asyncio.sleep(self.max_wait)
        async with self._lock:
            if self._items:
                await self._flush()
    
    async def _flush(self) -> None:
        """Process the current batch"""
        if not self._items:
            return
        
        items = self._items.copy()
        futures = self._futures.copy()
        self._items.clear()
        self._futures.clear()
        
        if self._flush_task:
            self._flush_task.cancel()
            self._flush_task = None
        
        try:
            # Process batch
            results = await self.process_batch(items)
            
            # Distribute results
            for future, result in zip(futures, results):
                if not future.done():
                    future.set_result(result)
                    
        except Exception as e:
            # Set exception on all futures
            for future in futures:
                if not future.done():
                    future.set_exception(e)


class CostTracker:
    """
    Tracks LLM API costs.
    
    Provides cost estimation and reporting for different models.
    """
    
    # Cost per 1M tokens (example rates)
    MODEL_COSTS = {
        'gpt-4': {'input': 30.0, 'output': 60.0},
        'gpt-4-turbo': {'input': 10.0, 'output': 30.0},
        'gpt-3.5-turbo': {'input': 0.5, 'output': 1.5},
        'claude-3-opus': {'input': 15.0, 'output': 75.0},
        'claude-3-sonnet': {'input': 3.0, 'output': 15.0},
        'claude-3-haiku': {'input': 0.25, 'output': 1.25},
        'llama-3': {'input': 0.0, 'output': 0.0},  # Local/free
    }
    
    def __init__(self):
        self._costs: Dict[str, float] = defaultdict(float)
        self._tokens: Dict[str, Dict[str, int]] = defaultdict(lambda: {'input': 0, 'output': 0})
    
    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Estimate cost for a request.
        
        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Estimated cost in USD
        """
        costs = self.MODEL_COSTS.get(model, {'input': 0, 'output': 0})
        
        input_cost = (input_tokens / 1_000_000) * costs['input']
        output_cost = (output_tokens / 1_000_000) * costs['output']
        
        return input_cost + output_cost
    
    def record(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Record usage and return cost.
        
        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Cost for this request
        """
        cost = self.estimate_cost(model, input_tokens, output_tokens)
        
        self._costs[model] += cost
        self._tokens[model]['input'] += input_tokens
        self._tokens[model]['output'] += output_tokens
        
        return cost
    
    def get_summary(self) -> Dict[str, Any]:
        """Get cost summary"""
        return {
            'total_cost': sum(self._costs.values()),
            'by_model': {
                model: {
                    'cost': cost,
                    'tokens': self._tokens[model]
                }
                for model, cost in self._costs.items()
            }
        }
    
    def reset(self) -> None:
        """Reset all tracking"""
        self._costs.clear()
        self._tokens.clear()

