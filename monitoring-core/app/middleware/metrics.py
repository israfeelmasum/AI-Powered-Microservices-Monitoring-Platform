# monitoring-core/app/middleware/metrics.py
import time
import psutil
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from collections import defaultdict, deque
import threading


class MetricsCollector:
    """Collects and aggregates system and application metrics"""

    def __init__(self):
        self.metrics = defaultdict(deque)
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(list)
        self.process = psutil.Process()
        self._lock = threading.Lock()

        # Keep metrics for last hour (3600 data points at 1 second intervals)
        self.max_length = 3600

    def increment_counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        with self._lock:
            key = self._make_key(name, tags)
            self.counters[key] += value

    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric"""
        with self._lock:
            key = self._make_key(name, tags)
            self.gauges[key] = value

    def add_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Add a value to a histogram"""
        with self._lock:
            key = self._make_key(name, tags)
            self.histograms[key].append(value)

            # Keep only recent values
            if len(self.histograms[key]) > self.max_length:
                self.histograms[key] = self.histograms[key][-self.max_length:]

    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        try:
            cpu_percent = self.process.cpu_percent()
            memory_info = self.process.memory_info()

            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_rss_mb": memory_info.rss / 1024 / 1024,
                    "memory_vms_mb": memory_info.vms / 1024 / 1024,
                    "memory_percent": self.process.memory_percent(),
                    "num_threads": self.process.num_threads(),
                    "num_fds": len(self.process.open_files()) if hasattr(self.process, 'open_files') else 0,
                    "connections": len(self.process.connections()) if hasattr(self.process, 'connections') else 0
                },
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {k: {
                    "count": len(v),
                    "sum": sum(v),
                    "avg": sum(v) / len(v) if v else 0,
                    "min": min(v) if v else 0,
                    "max": max(v) if v else 0
                } for k, v in self.histograms.items()}
            }

            return metrics

        except Exception as e:
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

    def _make_key(self, name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """Create a metric key with tags"""
        if tags:
            tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
            return f"{name}#{tag_str}"
        return name

    def reset_counters(self):
        """Reset counter metrics"""
        with self._lock:
            self.counters.clear()