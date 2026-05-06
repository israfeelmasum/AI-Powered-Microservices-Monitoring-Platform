# shared/monitoring_sdk/client.py
import asyncio
import aiohttp
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import psutil
import os

logger = logging.getLogger(__name__)


class MonitoringClient:
    """Central monitoring client for microservices"""

    def __init__(self,
                 monitoring_url: str,
                 service_name: str,
                 secret_key: str,
                 timeout: int = 5):
        self.monitoring_url = monitoring_url.rstrip('/')
        self.service_name = service_name
        self.secret_key = secret_key
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """Initialize the monitoring client"""
        self.session = aiohttp.ClientSession()
        await self.register_service()

    async def close(self):
        """Close the monitoring client"""
        if self.session:
            await self.session.close()

    async def register_service(self) -> bool:
        """Register this service with the monitoring system"""
        try:
            registration_data = {
                "service_name": self.service_name,
                "service_url": f"http://localhost:{os.getenv('PORT', '8000')}",
                "secret_key": self.secret_key,
                "version": "1.0.0",
                "registered_at": datetime.utcnow().isoformat(),
                "capabilities": ["logging", "metrics", "health_checks"]
            }

            async with self.session.post(
                    f"{self.monitoring_url}/api/v1/register-service",
                    json=registration_data,
                    auth=aiohttp.BasicAuth("admin", "admin"),
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status == 200:
                    logger.info(f"Service {self.service_name} registered successfully")
                    return True
                else:
                    logger.error(f"Service registration failed: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Failed to register service: {e}")
            return False

    async def send_log(self, log_data: Dict[str, Any]) -> bool:
        """Send log data to monitoring system"""
        try:
            headers = {
                "Content-Type": "application/json",
                "X-Service-Secret": self.secret_key,
                "X-Service-Name": self.service_name
            }

            # Ensure required fields
            log_data.setdefault("timestamp", datetime.utcnow().isoformat())
            log_data.setdefault("service", self.service_name)

            async with self.session.post(
                    f"{self.monitoring_url}/api/v1/monitoring/logs",
                    json=log_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                return response.status == 200

        except Exception as e:
            logger.warning(f"Failed to send log: {e}")
            return False

    async def send_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Send metrics to monitoring system"""
        try:
            headers = {
                "Content-Type": "application/json",
                "X-Service-Secret": self.secret_key,
                "X-Service-Name": self.service_name
            }

            metrics_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "service": self.service_name,
                "metrics": metrics
            }

            async with self.session.post(
                    f"{self.monitoring_url}/api/v1/metrics",
                    json=metrics_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                return response.status == 200

        except Exception as e:
            logger.warning(f"Failed to send metrics: {e}")
            return False

    async def send_health_check(self, health_data: Dict[str, Any]) -> bool:
        """Send health check data"""
        try:
            headers = {
                "Content-Type": "application/json",
                "X-Service-Secret": self.secret_key,
                "X-Service-Name": self.service_name
            }

            health_payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "service": self.service_name,
                "health": health_data,
                "system_metrics": self.get_system_metrics()
            }

            async with self.session.post(
                    f"{self.monitoring_url}/api/v1/monitoring/health",
                    json=health_payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                return response.status == 200

        except Exception as e:
            logger.warning(f"Failed to send health check: {e}")
            return False

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            process = psutil.Process()

            return {
                "cpu_percent": round(process.cpu_percent(), 2),
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "memory_percent": round(process.memory_percent(), 2),
                "open_files": len(process.open_files()) if hasattr(process, 'open_files') else 0,
                "connections": len(process.connections()) if hasattr(process, 'connections') else 0,
                "threads": process.num_threads(),
                "create_time": process.create_time()
            }
        except Exception as e:
            logger.warning(f"Failed to get system metrics: {e}")
            return {}


# shared/monitoring_sdk/middleware.py
import time
import logging
import asyncio
from datetime import datetime
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional

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
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/favicon.ico"]
        self._initialized = False

    async def dispatch(self, request: Request, call_next):
        # Initialize client on first request
        if not self._initialized:
            await self.monitoring_client.initialize()
            self._initialized = True

        # Skip monitoring for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Start timing
        start_time = time.time()
        correlation_id = f"{self.monitoring_client.service_name}_{int(time.time() * 1000)}"

        # Add correlation ID to request state
        request.state.correlation_id = correlation_id

        try:
            response = await call_next(request)

            # Calculate response time
            response_time = (time.time() - start_time) * 1000

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
                "user_agent": request.headers.get("user-agent", "unknown")
            }

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


# shared/monitoring_sdk/models.py
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime


class LogEntry(BaseModel):
    timestamp: str = Field(..., description="ISO formatted timestamp")
    service: str = Field(..., description="Service name")
    level: str = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    endpoint: Optional[str] = Field(None, description="API endpoint")
    method: Optional[str] = Field(None, description="HTTP method")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    response_time: Optional[float] = Field(None, description="Response time in ms")
    client_ip: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    error_type: Optional[str] = Field(None, description="Error type")
    error_message: Optional[str] = Field(None, description="Error message")
    system_metrics: Optional[Dict[str, Any]] = Field(None, description="System metrics")


class MetricsEntry(BaseModel):
    timestamp: str = Field(..., description="ISO formatted timestamp")
    service: str = Field(..., description="Service name")
    metrics: Dict[str, Any] = Field(..., description="Metrics data")


class HealthCheckEntry(BaseModel):
    timestamp: str = Field(..., description="ISO formatted timestamp")
    service: str = Field(..., description="Service name")
    status: str = Field(..., description="Health status")
    checks: Dict[str, Any] = Field(..., description="Health check details")
    system_metrics: Dict[str, Any] = Field(..., description="System metrics")


class ServiceRegistration(BaseModel):
    service_name: str = Field(..., description="Service name")
    service_url: str = Field(..., description="Service URL")
    secret_key: str = Field(..., description="Service secret key")
    version: str = Field(..., description="Service version")
    endpoints: Optional[List[Dict[str, Any]]] = Field(None, description="Service endpoints")
    capabilities: Optional[List[str]] = Field(None, description="Service capabilities")
    registered_at: str = Field(..., description="Registration timestamp")


# shared/utils/helpers.py
import hashlib
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Dict


def generate_correlation_id(service_name: str) -> str:
    """Generate a unique correlation ID"""
    timestamp = int(time.time() * 1000)
    random_part = secrets.token_hex(4)
    return f"{service_name}_{timestamp}_{random_part}"


def hash_secret(secret: str) -> str:
    """Hash a secret key"""
    return hashlib.sha256(secret.encode()).hexdigest()


def get_utc_timestamp() -> str:
    """Get current UTC timestamp in ISO format"""
    return datetime.now(timezone.utc).isoformat()


def sanitize_log_message(message: str, max_length: int = 1000) -> str:
    """Sanitize and truncate log messages"""
    if len(message) > max_length:
        return message[:max_length] + "..."
    return message


def format_bytes(bytes_value: int) -> str:
    """Format bytes into human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} TB"


def calculate_percentile(values: list, percentile: float) -> float:
    """Calculate percentile of a list of values"""
    if not values:
        return 0.0

    sorted_values = sorted(values)
    index = (percentile / 100.0) * (len(sorted_values) - 1)

    if index.is_integer():
        return sorted_values[int(index)]
    else:
        lower = sorted_values[int(index)]
        upper = sorted_values[int(index) + 1]
        return lower + (upper - lower) * (index - int(index))