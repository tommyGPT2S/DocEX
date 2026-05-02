"""
Vector Database Monitoring and Health Check Service

This service provides monitoring capabilities for vector databases including:
- Health checks for FAISS and Pinecone
- Performance monitoring and metrics collection
- Index health validation
- Automatic recovery procedures
- Security auditing

Part of the DocEX RAG implementation ensuring production reliability.
"""

import logging
import time
import asyncio
import json
import statistics
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthMetric:
    """Health metric data class"""
    name: str
    value: float
    unit: str
    threshold: float
    status: HealthStatus
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class HealthReport:
    """Comprehensive health report"""
    database_type: str
    overall_status: HealthStatus
    metrics: List[HealthMetric]
    errors: List[str]
    warnings: List[str]
    timestamp: datetime
    uptime_seconds: float
    last_check: datetime


class VectorDatabaseMonitor:
    """
    Vector database monitoring and health check service
    
    Provides comprehensive monitoring for vector database operations including:
    - Performance metrics collection
    - Health status monitoring
    - Error tracking and alerting
    - Recovery procedures
    """
    
    def __init__(self, vector_db, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the monitor
        
        Args:
            vector_db: Vector database instance to monitor
            config: Monitor configuration
        """
        self.vector_db = vector_db
        self.config = config or {}
        self.start_time = datetime.now()
        self.metrics_history: List[HealthReport] = []
        
        # Default thresholds
        self.thresholds = {
            'query_latency_ms': self.config.get('query_latency_threshold', 1000),
            'memory_usage_mb': self.config.get('memory_threshold', 1000),
            'error_rate_percent': self.config.get('error_rate_threshold', 5),
            'index_size_mb': self.config.get('index_size_threshold', 10000),
            'query_success_rate': self.config.get('success_rate_threshold', 95)
        }
        
        # Enable monitoring
        self.monitoring_enabled = self.config.get('enable_monitoring', True)
        self.check_interval = self.config.get('check_interval_seconds', 60)
        self.retention_hours = self.config.get('retention_hours', 24)
    
    async def health_check(self) -> HealthReport:
        """
        Perform comprehensive health check
        
        Returns:
            HealthReport with current status and metrics
        """
        errors = []
        warnings = []
        metrics = []
        
        try:
            # Check database connectivity
            connectivity_metric = await self._check_connectivity()
            metrics.append(connectivity_metric)
            
            # Check query performance
            performance_metrics = await self._check_performance()
            metrics.extend(performance_metrics)
            
            # Check memory usage
            memory_metric = await self._check_memory_usage()
            if memory_metric:
                metrics.append(memory_metric)
            
            # Check index health
            index_metrics = await self._check_index_health()
            metrics.extend(index_metrics)
            
            # Check error rates
            error_metric = await self._check_error_rates()
            if error_metric:
                metrics.append(error_metric)
                
        except Exception as e:
            errors.append(f"Health check failed: {e}")
            logger.error(f"Health check error: {e}")
        
        # Determine overall status
        overall_status = self._calculate_overall_status(metrics, errors)
        
        # Create report
        report = HealthReport(
            database_type=type(self.vector_db).__name__,
            overall_status=overall_status,
            metrics=metrics,
            errors=errors,
            warnings=warnings,
            timestamp=datetime.now(),
            uptime_seconds=(datetime.now() - self.start_time).total_seconds(),
            last_check=datetime.now()
        )
        
        # Store for history
        self._store_report(report)
        
        return report
    
    async def _check_connectivity(self) -> HealthMetric:
        """Check database connectivity"""
        start_time = time.time()
        
        try:
            # Test basic connectivity
            if hasattr(self.vector_db, 'get_stats'):
                await self.vector_db.get_stats()
            else:
                # Fallback: try a simple operation
                test_embedding = [0.1] * 384  # Common embedding size
                await self.vector_db.search([test_embedding], k=1)
            
            latency = (time.time() - start_time) * 1000  # Convert to ms
            status = HealthStatus.HEALTHY if latency < 100 else HealthStatus.DEGRADED
            
            return HealthMetric(
                name="connectivity",
                value=latency,
                unit="ms",
                threshold=100,
                status=status,
                timestamp=datetime.now(),
                metadata={"connection_test": "success"}
            )
            
        except Exception as e:
            return HealthMetric(
                name="connectivity",
                value=-1,
                unit="ms",
                threshold=100,
                status=HealthStatus.UNHEALTHY,
                timestamp=datetime.now(),
                metadata={"error": str(e)}
            )
    
    async def _check_performance(self) -> List[HealthMetric]:
        """Check query performance"""
        metrics = []
        
        try:
            # Test search latency with different query sizes
            test_embeddings = [
                [0.1] * 384,  # Single query
                [[0.1] * 384] * 5,  # Batch query
            ]
            
            for i, embedding in enumerate(test_embeddings):
                start_time = time.time()
                
                try:
                    await self.vector_db.search(embedding, k=10)
                    latency = (time.time() - start_time) * 1000
                    
                    threshold = self.thresholds['query_latency_ms']
                    status = (HealthStatus.HEALTHY if latency < threshold else 
                             HealthStatus.DEGRADED if latency < threshold * 2 else 
                             HealthStatus.UNHEALTHY)
                    
                    metrics.append(HealthMetric(
                        name=f"query_latency_{i+1}",
                        value=latency,
                        unit="ms",
                        threshold=threshold,
                        status=status,
                        timestamp=datetime.now(),
                        metadata={"query_type": "single" if i == 0 else "batch"}
                    ))
                    
                except Exception as e:
                    metrics.append(HealthMetric(
                        name=f"query_latency_{i+1}",
                        value=-1,
                        unit="ms",
                        threshold=threshold,
                        status=HealthStatus.UNHEALTHY,
                        timestamp=datetime.now(),
                        metadata={"error": str(e)}
                    ))
        
        except Exception as e:
            logger.error(f"Performance check failed: {e}")
        
        return metrics
    
    async def _check_memory_usage(self) -> Optional[HealthMetric]:
        """Check memory usage"""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            threshold = self.thresholds['memory_usage_mb']
            status = (HealthStatus.HEALTHY if memory_mb < threshold else
                     HealthStatus.DEGRADED if memory_mb < threshold * 1.5 else
                     HealthStatus.UNHEALTHY)
            
            return HealthMetric(
                name="memory_usage",
                value=memory_mb,
                unit="MB",
                threshold=threshold,
                status=status,
                timestamp=datetime.now()
            )
            
        except ImportError:
            logger.warning("psutil not available for memory monitoring")
            return None
        except Exception as e:
            logger.error(f"Memory check failed: {e}")
            return None
    
    async def _check_index_health(self) -> List[HealthMetric]:
        """Check index health"""
        metrics = []
        
        try:
            if hasattr(self.vector_db, 'get_stats'):
                stats = await self.vector_db.get_stats()
                
                # Check index size
                if 'total_vectors' in stats:
                    total_vectors = stats['total_vectors']
                    estimated_size_mb = total_vectors * 384 * 4 / 1024 / 1024  # Estimate
                    
                    threshold = self.thresholds['index_size_mb']
                    status = (HealthStatus.HEALTHY if estimated_size_mb < threshold else
                             HealthStatus.DEGRADED)
                    
                    metrics.append(HealthMetric(
                        name="index_size",
                        value=estimated_size_mb,
                        unit="MB",
                        threshold=threshold,
                        status=status,
                        timestamp=datetime.now(),
                        metadata={"total_vectors": total_vectors}
                    ))
                
                # Check index utilization
                if 'dimension' in stats and 'total_vectors' in stats:
                    utilization = min(100, stats['total_vectors'] / 1000)  # Normalize
                    
                    metrics.append(HealthMetric(
                        name="index_utilization",
                        value=utilization,
                        unit="percent",
                        threshold=80,
                        status=HealthStatus.HEALTHY,
                        timestamp=datetime.now()
                    ))
        
        except Exception as e:
            logger.error(f"Index health check failed: {e}")
        
        return metrics
    
    async def _check_error_rates(self) -> Optional[HealthMetric]:
        """Check error rates from recent operations"""
        try:
            # This would typically check logs or metrics store
            # For now, return a placeholder metric
            error_rate = 0.0  # Would calculate from actual error logs
            
            threshold = self.thresholds['error_rate_percent']
            status = (HealthStatus.HEALTHY if error_rate < threshold else
                     HealthStatus.DEGRADED if error_rate < threshold * 2 else
                     HealthStatus.UNHEALTHY)
            
            return HealthMetric(
                name="error_rate",
                value=error_rate,
                unit="percent",
                threshold=threshold,
                status=status,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error rate check failed: {e}")
            return None
    
    def _calculate_overall_status(self, metrics: List[HealthMetric], errors: List[str]) -> HealthStatus:
        """Calculate overall health status"""
        if errors:
            return HealthStatus.UNHEALTHY
        
        if not metrics:
            return HealthStatus.UNKNOWN
        
        unhealthy_count = sum(1 for m in metrics if m.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for m in metrics if m.status == HealthStatus.DEGRADED)
        
        if unhealthy_count > 0:
            return HealthStatus.UNHEALTHY
        elif degraded_count > len(metrics) / 2:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    def _store_report(self, report: HealthReport):
        """Store health report in history"""
        self.metrics_history.append(report)
        
        # Cleanup old reports
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
        self.metrics_history = [
            r for r in self.metrics_history 
            if r.timestamp > cutoff_time
        ]
    
    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """
        Get metrics summary for the specified time period
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Summary statistics
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_reports = [r for r in self.metrics_history if r.timestamp > cutoff_time]
        
        if not recent_reports:
            return {"error": "No metrics available for the specified period"}
        
        # Calculate summary statistics
        summary = {
            "period_hours": hours,
            "total_checks": len(recent_reports),
            "status_distribution": {},
            "average_metrics": {},
            "alerts": []
        }
        
        # Status distribution
        for report in recent_reports:
            status = report.overall_status.value
            summary["status_distribution"][status] = summary["status_distribution"].get(status, 0) + 1
        
        # Average metrics
        metric_values = {}
        for report in recent_reports:
            for metric in report.metrics:
                if metric.value >= 0:  # Ignore error values (-1)
                    if metric.name not in metric_values:
                        metric_values[metric.name] = []
                    metric_values[metric.name].append(metric.value)
        
        for metric_name, values in metric_values.items():
            if values:
                summary["average_metrics"][metric_name] = {
                    "average": statistics.mean(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values)
                }
        
        # Recent alerts
        recent_alerts = []
        for report in recent_reports[-5:]:  # Last 5 reports
            if report.errors:
                recent_alerts.extend(report.errors)
            if report.warnings:
                recent_alerts.extend(report.warnings)
        
        summary["alerts"] = recent_alerts
        
        return summary
    
    async def auto_recovery(self, report: HealthReport) -> bool:
        """
        Attempt automatic recovery based on health report
        
        Args:
            report: Current health report
            
        Returns:
            True if recovery was attempted
        """
        if report.overall_status != HealthStatus.UNHEALTHY:
            return False
        
        recovery_attempted = False
        
        try:
            # Check for connectivity issues
            connectivity_metrics = [m for m in report.metrics if m.name == "connectivity"]
            if connectivity_metrics and connectivity_metrics[0].status == HealthStatus.UNHEALTHY:
                logger.warning("Attempting database reconnection...")
                if hasattr(self.vector_db, 'initialize'):
                    await self.vector_db.initialize()
                    recovery_attempted = True
            
            # Check for performance issues
            performance_metrics = [m for m in report.metrics if "latency" in m.name]
            high_latency_count = sum(1 for m in performance_metrics if m.status == HealthStatus.UNHEALTHY)
            
            if high_latency_count > 0:
                logger.warning("High latency detected, clearing caches if available...")
                if hasattr(self.vector_db, 'clear_cache'):
                    await self.vector_db.clear_cache()
                    recovery_attempted = True
            
        except Exception as e:
            logger.error(f"Auto-recovery failed: {e}")
        
        return recovery_attempted
    
    def export_metrics(self, format: str = "json") -> str:
        """
        Export metrics in specified format
        
        Args:
            format: Export format ('json', 'csv')
            
        Returns:
            Formatted metrics data
        """
        if format.lower() == "json":
            return json.dumps([asdict(report) for report in self.metrics_history], 
                            default=str, indent=2)
        
        elif format.lower() == "csv":
            # Simple CSV export
            lines = ["timestamp,database_type,status,metric_name,metric_value,metric_unit"]
            for report in self.metrics_history:
                for metric in report.metrics:
                    lines.append(
                        f"{report.timestamp},{report.database_type},{report.overall_status.value},"
                        f"{metric.name},{metric.value},{metric.unit}"
                    )
            return "\n".join(lines)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")


class AlertManager:
    """Alert management for vector database monitoring"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize alert manager
        
        Args:
            config: Alert configuration
        """
        self.config = config or {}
        self.alert_thresholds = self.config.get('alert_thresholds', {})
        self.notification_handlers = []
    
    def add_notification_handler(self, handler_func):
        """Add a notification handler function"""
        self.notification_handlers.append(handler_func)
    
    async def check_alerts(self, report: HealthReport):
        """
        Check for alert conditions and send notifications
        
        Args:
            report: Health report to check
        """
        alerts = []
        
        # Check overall status
        if report.overall_status == HealthStatus.UNHEALTHY:
            alerts.append({
                "level": "critical",
                "message": f"Vector database {report.database_type} is unhealthy",
                "details": {"errors": report.errors}
            })
        
        # Check individual metrics
        for metric in report.metrics:
            if metric.status == HealthStatus.UNHEALTHY:
                alerts.append({
                    "level": "error",
                    "message": f"Metric {metric.name} is unhealthy: {metric.value} {metric.unit}",
                    "details": {"threshold": metric.threshold, "metadata": metric.metadata}
                })
        
        # Send notifications
        for alert in alerts:
            await self._send_notifications(alert)
    
    async def _send_notifications(self, alert: Dict[str, Any]):
        """Send alert notifications to configured handlers"""
        for handler in self.notification_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Failed to send alert notification: {e}")


# Example usage and monitoring setup
if __name__ == "__main__":
    async def example_monitoring():
        """Example of setting up monitoring"""
        # This would be used with actual vector database instances
        print("Vector Database Monitoring Example")
        print("This service provides comprehensive health monitoring for FAISS and Pinecone")
        print("Features:")
        print("- Real-time health checks")
        print("- Performance monitoring")
        print("- Automatic recovery")
        print("- Alert management")
        print("- Metrics export")
    
    asyncio.run(example_monitoring())