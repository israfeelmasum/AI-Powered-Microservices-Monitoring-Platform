# shared/monitoring_sdk/middleware.py
import time
import logging
import asyncio
from datetime import datetime
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional
import psutil
import aiohttp

from .client import MonitoringClient

logger = logging.getLogger(__name__)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Reusable monitoring middleware for FastAPI services"""

    def __init__(self,
                 app,
                 monitoring_url: str,
                 service_name: str,
                 secret_key: str,
                 exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.monitoring_client = MonitoringClient(monitoring_url, service_name, secret_key)
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/favicon.ico", "/docs", "/openapi.json"]
        self._initialized = False
        self.process = psutil.Process()

    async def dispatch(self, request: Request, call_next):
        # Initialize client on first request
        if not self._initialized:
            try:
                await self.monitoring_client.initialize()
                self._initialized = True
            except Exception as e:
                logger.warning(f"Failed to initialize monitoring client: {e}")

        # Skip monitoring for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Start timing
        start_time = time.time()
        correlation_id = f"{self.monitoring_client.service_name}_{int(time.time() * 1000)}"

        # Get system metrics before request
        try:
            cpu_before = self.process.cpu_percent()
            memory_before = self.process.memory_info().rss / 1024 / 1024  # MB
        except:
            cpu_before = 0
            memory_before = 0

        # Add correlation ID to request state
        request.state.correlation_id = correlation_id

        try:
            response = await call_next(request)

            # Calculate response time
            response_time = (time.time() - start_time) * 1000

            # Get system metrics after request
            try:
                cpu_after = self.process.cpu_percent()
                memory_after = self.process.memory_info().rss / 1024 / 1024  # MB
            except:
                cpu_after = cpu_before
                memory_after = memory_before

            # Create monitoring data
            monitoring_data = {
                "correlation_id": correlation_id,
                "level": "ERROR" if response.status_code >= 500 else "WARNING" if response.status_code >= 400 else "INFO",
                "message": f"{request.method} {request.url.path} - {response.status_code}",
                "endpoint": f"{request.method} {request.url.path}",
                "method": request.method,
                "path": str(request.url.path),
                "query_params": dict(request.query_params),
                "status_code": response.status_code,
                "response_time": round(response_time, 2),
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
                "system_metrics": {
                    "cpu_usage_percent": round((cpu_before + cpu_after) / 2, 2),
                    "memory_usage_mb": round((memory_before + memory_after) / 2, 2),
                    "memory_change_mb": round(memory_after - memory_before, 2)
                }
            }

            # Add error details if needed
            if response.status_code >= 400:
                monitoring_data["error_type"] = self._get_error_type(response.status_code)

            # Send monitoring data (fire and forget)
            asyncio.create_task(self.monitoring_client.send_log(monitoring_data))

            return response

        except Exception as e:
            # Handle exceptions
            response_time = (time.time() - start_time) * 1000

            error_data = {
                "correlation_id": correlation_id,
                "level": "CRITICAL",
                "message": f"Exception in {request.method} {request.url.path}: {str(e)}",
                "endpoint": f"{request.method} {request.url.path}",
                "method": request.method,
                "path": str(request.url.path),
                "status_code": 500,
                "response_time": round(response_time, 2),
                "error_type": "internal_server_error",
                "error_message": str(e),
                "exception_type": type(e).__name__
            }

            # Send error data
            asyncio.create_task(self.monitoring_client.send_log(error_data))

            # Re-raise exception
            raise e

    def _get_error_type(self, status_code: int) -> str:
        """Get error type based on status code"""
        error_types = {
            400: "bad_request",
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            405: "method_not_allowed",
            422: "validation_error",
            429: "rate_limit_exceeded",
            500: "internal_server_error",
            502: "bad_gateway",
            503: "service_unavailable",
            504: "gateway_timeout"
        }
        return error_types.get(status_code, f"http_error_{status_code}")