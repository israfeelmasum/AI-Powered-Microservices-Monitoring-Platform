# monitoring-core/app/middleware/monitoring.py

import time
import logging
import asyncio
from datetime import datetime
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Optional
import psutil

logger = logging.getLogger(__name__)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Central monitoring middleware for the monitoring system itself"""

    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/static", "/favicon.ico"]
        self.process = psutil.Process()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip monitoring for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Start timing
        start_time = time.time()
        correlation_id = f"monitoring_core_{int(time.time() * 1000)}"

        # Add correlation ID to request state
        request.state.correlation_id = correlation_id

        # Get initial CPU percent with a short interval for accuracy
        cpu_before = self.process.cpu_percent(interval=0.1)
        memory_before = self.process.memory_info().rss / 1024 / 1024  # in MB

        try:
            response = await call_next(request)

            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000

            # Get CPU and memory after request
            cpu_after = self.process.cpu_percent(interval=0.1)
            memory_after = self.process.memory_info().rss / 1024 / 1024  # in MB

            # Prepare log data
            log_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "service": "monitoring-core",
                "correlation_id": correlation_id,
                "level": (
                    "ERROR" if response.status_code >= 500
                    else "WARNING" if response.status_code >= 400
                    else "INFO"
                ),
                "log_message": f"{request.method} {request.url.path} - {response.status_code}",
                "endpoint": f"{request.method} {request.url.path}",
                "method": request.method,
                "path": str(request.url.path),
                "query_params": dict(request.query_params),
                "status_code": response.status_code,
                "response_time_ms": round(response_time_ms, 2),
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
                "system_metrics": {
                    "cpu_usage_percent_avg": round((cpu_before + cpu_after) / 2, 2),
                    "memory_usage_mb_avg": round((memory_before + memory_after) / 2, 2),
                    "memory_change_mb": round(memory_after - memory_before, 2)
                }
            }

            # Store monitoring data if Elasticsearch is configured
            if hasattr(request.app.state, "elasticsearch") and callable(getattr(request.app.state.elasticsearch, "store_log", None)):
                asyncio.create_task(
                    request.app.state.elasticsearch.store_log(log_data)
                )

            # Local logging
            log_level = log_data["level"].lower()
            getattr(logger, log_level)(log_data["log_message"], extra=log_data)

            return response

        except Exception as e:
            # Calculate response time on exception
            response_time_ms = (time.time() - start_time) * 1000

            error_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "service": "monitoring-core",
                "correlation_id": correlation_id,
                "level": "CRITICAL",
                "log_message": f"Exception in {request.method} {request.url.path}: {str(e)}",
                "endpoint": f"{request.method} {request.url.path}",
                "method": request.method,
                "path": str(request.url.path),
                "status_code": 500,
                "response_time_ms": round(response_time_ms, 2),
                "error_type": "internal_server_error",
                "error_message": str(e),
                "exception_type": type(e).__name__,
            }

            # Store error data in Elasticsearch if available
            if hasattr(request.app.state, "elasticsearch") and callable(getattr(request.app.state.elasticsearch, "store_log", None)):
                asyncio.create_task(
                    request.app.state.elasticsearch.store_log(error_data)
                )

            logger.critical(error_data["log_message"], extra=error_data)
            raise e
