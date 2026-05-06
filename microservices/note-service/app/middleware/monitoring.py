
import time
import logging
import asyncio
import psutil
import os
from datetime import datetime
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import aiohttp
from typing import Callable

logger = logging.getLogger(__name__)

class NoteServiceMonitoring(BaseHTTPMiddleware):
    def __init__(self, app, monitoring_url: str = None, secret_key: str = None):
        super().__init__(app)
        self.monitoring_url = monitoring_url or os.getenv("MONITORING_URL", "http://localhost:8010")
        self.service_name = "note-service"
        self.secret_key = secret_key or os.getenv("NOTE_SERVICE_SECRET", "note_secret_key_2024")
        self.process = psutil.Process()
        self.exclude_paths = ["/health", "/metrics", "/favicon.ico"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        start_time = time.time()
        correlation_id = f"{self.service_name}_{int(time.time() * 1000)}"
        cpu_before = self.process.cpu_percent()
        memory_before = self.process.memory_info().rss / 1024 / 1024
        request.state.correlation_id = correlation_id

        # Get real client IP (supporting reverse proxies)
        client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown").split(",")[0].strip()
        user_agent = request.headers.get("user-agent", "unknown")
        location_data = await self._get_geolocation(client_ip)

        try:
            response = await call_next(request)
            response_time = (time.time() - start_time) * 1000
            cpu_after = self.process.cpu_percent()
            memory_after = self.process.memory_info().rss / 1024 / 1024

            monitoring_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "service": self.service_name,
                "correlation_id": correlation_id,
                "level": self._get_log_level(response.status_code),
                "message": f"{request.method} {request.url.path} - {response.status_code}",
                "endpoint": f"{request.method} {request.url.path}",
                "method": request.method,
                "path": str(request.url.path),
                "query_params": dict(request.query_params),
                "status_code": response.status_code,
                "response_time": round(response_time, 2),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "device_info": {
                    **location_data,
                    "user_agent": user_agent
                },
                "system_metrics": {
                    "cpu_usage_percent": round((cpu_before + cpu_after) / 2, 2),
                    "memory_usage_mb": round((memory_before + memory_after) / 2, 2),
                    "memory_change_mb": round(memory_after - memory_before, 2),
                    "threads": self.process.num_threads()
                },
                "request_size": len(await self._get_request_body(request)) if request.method in ["POST", "PUT"] else 0,
                "response_size": self._get_response_size(response)
            }

            if response.status_code >= 400:
                monitoring_data["error_type"] = self._get_error_type(response.status_code)

            asyncio.create_task(self._send_monitoring_data(monitoring_data))
            self._log_locally(monitoring_data)
            return response

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            error_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "service": self.service_name,
                "correlation_id": correlation_id,
                "level": "CRITICAL",
                "message": f"Unhandled exception in {request.method} {request.url.path}: {str(e)}",
                "endpoint": f"{request.method} {request.url.path}",
                "method": request.method,
                "path": str(request.url.path),
                "status_code": 500,
                "response_time": round(response_time, 2),
                "error_type": "internal_server_error",
                "error_message": str(e),
                "exception_type": type(e).__name__,
                "client_ip": client_ip,
                "device_info": {
                    **location_data,
                    "user_agent": user_agent
                }
            }
            asyncio.create_task(self._send_monitoring_data(error_data))
            error_data.pop("message", None)
            logger.critical(f"Unhandled exception: {e}", extra=error_data)
            raise e

    async def _get_geolocation(self, ip: str) -> dict:
        try:
            if ip.startswith("127.") or ip.lower() == "localhost":
                return {"ip": ip, "country": "Local", "region": "Loopback", "city": "Localhost", "device_type": "local"}
            url = f"https://ipwho.is/{ip}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "ip": ip,
                            "country": data.get("country", "Unknown"),
                            "region": data.get("region", "Unknown"),
                            "city": data.get("city", "Unknown"),
                            "device_type": "pc" if data.get("type") == "IPv4" else "mobile"
                        }
        except Exception as e:
            logger.warning(f"Geolocation lookup failed for IP {ip}: {e}")
        return {"ip": ip, "country": "Unknown", "region": "Unknown", "city": "Unknown", "device_type": "Unknown"}

    def _get_log_level(self, status_code: int) -> str:
        return "ERROR" if status_code >= 500 else "WARNING" if status_code >= 400 else "INFO"

    def _get_error_type(self, status_code: int) -> str:
        return {
            400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found",
            405: "method_not_allowed", 422: "validation_error", 429: "rate_limit_exceeded",
            500: "internal_server_error", 502: "bad_gateway", 503: "service_unavailable",
            504: "gateway_timeout"
        }.get(status_code, f"http_error_{status_code}")

    async def _get_request_body(self, request: Request) -> bytes:
        try:
            return await request.body()
        except:
            return b""

    def _get_response_size(self, response: Response) -> int:
        try:
            return len(response.body) if hasattr(response, 'body') else 0
        except:
            return 0

    async def _send_monitoring_data(self, data: dict):
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "X-Service-Secret": self.secret_key,
                    "X-Service-Name": self.service_name
                }
                async with session.post(
                    f"{self.monitoring_url}/api/v1/monitoring/logs",
                    json=data,
                    headers=headers,
                    timeout=5
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Monitoring data send failed: {response.status}")
        except Exception as e:
            logger.warning(f"Monitoring send error: {e}")

    def _log_locally(self, data: dict):
        log_level = data.get("level", "INFO")
        message = data.get("message", "")
        data["log_message"] = data.pop("message", "")
        getattr(logger, log_level.lower(), logger.info)(message, extra=data)
