#!/usr/bin/env python3
"""
Monitoring and alerting system for production environment
Tracks API performance, errors, and system health
"""

import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from functools import wraps
import asyncio


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: float
    value: float
    labels: Dict[str, str]


class MetricsCollector:
    """Collects and stores application metrics"""
    
    def __init__(self, retention_hours: int = 24):
        self.metrics: Dict[str, List[MetricPoint]] = {}
        self.retention_hours = retention_hours
        self._counters: Dict[str, float] = {}
    
    def record(self, metric_name: str, value: float, labels: Optional[Dict] = None):
        """Record a metric value"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        
        point = MetricPoint(
            timestamp=time.time(),
            value=value,
            labels=labels or {}
        )
        
        self.metrics[metric_name].append(point)
        
        # Clean old data
        self._cleanup_old_data(metric_name)
    
    def increment_counter(self, counter_name: str, value: float = 1.0):
        """Increment a counter metric"""
        self._counters[counter_name] = self._counters.get(counter_name, 0) + value
    
    def get_counter(self, counter_name: str) -> float:
        """Get counter value"""
        return self._counters.get(counter_name, 0)
    
    def _cleanup_old_data(self, metric_name: str):
        """Remove metrics older than retention period"""
        cutoff = time.time() - (self.retention_hours * 3600)
        self.metrics[metric_name] = [
            p for p in self.metrics[metric_name]
            if p.timestamp > cutoff
        ]
    
    def get_stats(self, metric_name: str, minutes: int = 60) -> Dict:
        """Get statistics for a metric over time period"""
        if metric_name not in self.metrics:
            return {}
        
        cutoff = time.time() - (minutes * 60)
        points = [p.value for p in self.metrics[metric_name] if p.timestamp > cutoff]
        
        if not points:
            return {}
        
        return {
            'count': len(points),
            'min': min(points),
            'max': max(points),
            'avg': sum(points) / len(points),
            'last': points[-1]
        }
    
    def export_metrics(self) -> Dict:
        """Export all metrics for monitoring systems"""
        export = {
            'timestamp': datetime.utcnow().isoformat(),
            'counters': self._counters.copy(),
            'gauges': {}
        }
        
        for metric_name, points in self.metrics.items():
            if points:
                export['gauges'][metric_name] = {
                    'latest': points[-1].value,
                    'count': len(points)
                }
        
        return export


# Global metrics collector
metrics = MetricsCollector()


def timed(metric_name: str, labels: Optional[Dict] = None):
    """Decorator to time function execution"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start
                metrics.record(f"{metric_name}_duration_seconds", duration, labels)
                metrics.increment_counter(f"{metric_name}_total")
                return result
            except Exception as e:
                duration = time.time() - start
                metrics.record(f"{metric_name}_duration_seconds", duration, labels)
                metrics.increment_counter(f"{metric_name}_errors")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                metrics.record(f"{metric_name}_duration_seconds", duration, labels)
                metrics.increment_counter(f"{metric_name}_total")
                return result
            except Exception as e:
                duration = time.time() - start
                metrics.record(f"{metric_name}_duration_seconds", duration, labels)
                metrics.increment_counter(f"{metric_name}_errors")
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


class HealthChecker:
    """System health monitoring"""
    
    def __init__(self):
        self.checks: Dict[str, callable] = {}
        self.status: Dict[str, bool] = {}
        self.last_check: Dict[str, datetime] = {}
    
    def register_check(self, name: str, check_func):
        """Register a health check function"""
        self.checks[name] = check_func
    
    async def run_checks(self) -> Dict:
        """Run all health checks"""
        results = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }
        
        all_healthy = True
        
        for name, check_func in self.checks.items():
            try:
                healthy = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
                self.status[name] = healthy
                self.last_check[name] = datetime.utcnow()
                
                results['checks'][name] = {
                    'status': 'healthy' if healthy else 'unhealthy',
                    'last_check': self.last_check[name].isoformat()
                }
                
                if not healthy:
                    all_healthy = False
                    
            except Exception as e:
                self.status[name] = False
                results['checks'][name] = {
                    'status': 'error',
                    'error': str(e)
                }
                all_healthy = False
        
        results['status'] = 'healthy' if all_healthy else 'unhealthy'
        return results


# Global health checker
health_checker = HealthChecker()


# Pre-defined health checks
async def check_database_health():
    """Check database connectivity"""
    try:
        from backend.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        print(f"[HEALTH CHECK] Database error: {e}")
        return False


async def check_redis_health():
    """Check Redis connectivity"""
    try:
        from backend.cache import get_redis_client
        client = get_redis_client()
        if client:
            await client.ping()
            return True
        return False
    except Exception as e:
        print(f"[HEALTH CHECK] Redis error: {e}")
        return False


def check_disk_space(threshold_percent: float = 90.0):
    """Check available disk space"""
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        used_percent = (used / total) * 100
        return used_percent < threshold_percent
    except Exception as e:
        print(f"[HEALTH CHECK] Disk check error: {e}")
        return False


# Register default health checks
health_checker.register_check('database', check_database_health)
health_checker.register_check('redis', check_redis_health)
health_checker.register_check('disk_space', check_disk_space)


class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(self):
        self.alert_history: List[Dict] = []
        self.alert_thresholds = {
            'error_rate': 0.1,  # 10% error rate
            'response_time': 5.0,  # 5 seconds
            'disk_usage': 90.0  # 90% disk usage
        }
    
    def check_thresholds(self, metrics_data: Dict) -> List[Dict]:
        """Check if any metrics exceed thresholds"""
        alerts = []
        
        # Check error rate
        if 'api_requests_errors' in metrics_data.get('counters', {}):
            total = metrics_data['counters'].get('api_requests_total', 1)
            errors = metrics_data['counters']['api_requests_errors']
            error_rate = errors / total if total > 0 else 0
            
            if error_rate > self.alert_thresholds['error_rate']:
                alerts.append({
                    'severity': 'warning',
                    'metric': 'error_rate',
                    'value': error_rate,
                    'threshold': self.alert_thresholds['error_rate'],
                    'message': f'High error rate: {error_rate:.2%}'
                })
        
        # Check response time
        if 'api_request_duration_seconds' in metrics_data.get('gauges', {}):
            avg_time = metrics_data['gauges']['api_request_duration_seconds'].get('avg', 0)
            if avg_time > self.alert_thresholds['response_time']:
                alerts.append({
                    'severity': 'warning',
                    'metric': 'response_time',
                    'value': avg_time,
                    'threshold': self.alert_thresholds['response_time'],
                    'message': f'High response time: {avg_time:.2f}s'
                })
        
        return alerts
    
    def record_alert(self, alert: Dict):
        """Record an alert"""
        alert['timestamp'] = datetime.utcnow().isoformat()
        self.alert_history.append(alert)
        
        # Print alert
        print(f"[ALERT] {alert['severity'].upper()}: {alert['message']}")


# Global alert manager
alert_manager = AlertManager()


async def get_system_status() -> Dict:
    """Get complete system status"""
    return {
        'health': await health_checker.run_checks(),
        'metrics': metrics.export_metrics(),
        'alerts': alert_manager.check_thresholds(metrics.export_metrics())
    }


if __name__ == "__main__":
    # Test monitoring
    async def test():
        print("Testing monitoring system...")
        
        # Record some metrics
        for i in range(10):
            metrics.record('test_metric', i * 1.5, {'source': 'test'})
            metrics.increment_counter('test_counter')
        
        # Get stats
        stats = metrics.get_stats('test_metric', minutes=60)
        print(f"Test metric stats: {stats}")
        
        # Run health checks
        health = await health_checker.run_checks()
        print(f"\nHealth status: {health['status']}")
        for check, result in health['checks'].items():
            print(f"  {check}: {result['status']}")
        
        # Export metrics
        exported = metrics.export_metrics()
        print(f"\nExported {len(exported['gauges'])} metrics")
    
    asyncio.run(test())
