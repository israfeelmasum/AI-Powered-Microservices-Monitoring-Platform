import asyncio
import logging
import psutil
from datetime import datetime
from typing import Dict, Any, Optional, Callable
import aiohttp
import ssl
import redis.asyncio as redis

from ..config.settings import settings
from aiohttp import BasicAuth

logger = logging.getLogger(__name__)


class HealthChecker:
    """Health check system for monitoring services and dependencies"""

    def __init__(self):
        self.checks: Dict[str, HealthCheck] = {}
        self.process = psutil.Process()

    def register_check(self, name: str, check_func: Callable, interval: int = 30):
        """Register a health check"""
        self.checks[name] = HealthCheck(name, check_func, interval)

    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all registered health checks"""
        results = {}

        # System health
        results["system"] = await self._check_system_health()

        # Custom checks
        for name, check in self.checks.items():
            try:
                result = await check.run()
                results[name] = result
            except Exception as e:
                results[name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }

        # Overall status
        overall_status = "healthy"
        for result in results.values():
            if result.get("status") != "healthy":
                overall_status = "unhealthy"
                break

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": results
        }

    async def _check_system_health(self) -> Dict[str, Any]:
        """Check system health metrics"""
        try:
            cpu_percent = self.process.cpu_percent()
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()

            # Determine health based on thresholds
            status = "healthy"
            issues = []

            if cpu_percent > 80:
                status = "unhealthy"
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            elif cpu_percent > 60:
                status = "degraded"
                issues.append(f"Elevated CPU usage: {cpu_percent:.1f}%")

            if memory_percent > 90:
                status = "unhealthy"
                issues.append(f"High memory usage: {memory_percent:.1f}%")
            elif memory_percent > 75:
                if status == "healthy":
                    status = "degraded"
                issues.append(f"Elevated memory usage: {memory_percent:.1f}%")

            return {
                "status": status,
                "issues": issues,
                "metrics": {
                    "cpu_percent": cpu_percent,
                    "memory_rss_mb": memory_info.rss / 1024 / 1024,
                    "memory_percent": memory_percent,
                    "num_threads": self.process.num_threads()
                },
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


class HealthCheck:
    """Individual health check"""

    def __init__(self, name: str, check_func: Callable, interval: int = 30):
        self.name = name
        self.check_func = check_func
        self.interval = interval
        self.last_run: Optional[datetime] = None
        self.last_result: Optional[Dict[str, Any]] = None

    async def run(self) -> Dict[str, Any]:
        """Run the health check"""
        try:
            if asyncio.iscoroutinefunction(self.check_func):
                result = await self.check_func()
            else:
                result = self.check_func()

            self.last_run = datetime.utcnow()

            if isinstance(result, bool):
                self.last_result = {
                    "status": "healthy" if result else "unhealthy",
                    "timestamp": self.last_run.isoformat()
                }
            elif isinstance(result, dict):
                result["timestamp"] = self.last_run.isoformat()
                self.last_result = result
            else:
                self.last_result = {
                    "status": "healthy",
                    "result": str(result),
                    "timestamp": self.last_run.isoformat()
                }

            return self.last_result

        except Exception as e:
            self.last_run = datetime.utcnow()
            self.last_result = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": self.last_run.isoformat()
            }
            return self.last_result


async def check_elasticsearch_health(url: str = settings.ELASTICSEARCH_URL) -> dict:
    """Check Elasticsearch health"""
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        auth = BasicAuth(settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD)

        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=ssl_context),
            auth=auth
        ) as session:
            async with session.get(f"{url}/_cluster/health", timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "healthy" if data.get("status") in ["green", "yellow"] else "unhealthy",
                        "cluster_status": data.get("status"),
                        "number_of_nodes": data.get("number_of_nodes"),
                        "active_shards": data.get("active_shards")
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status}"
                    }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_ollama_health(url: str = "http://localhost:11434") -> Dict[str, Any]:
    """Check Ollama health"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{url}/api/tags", timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "healthy",
                        "models_available": len(data.get("models", []))
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status}"
                    }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_redis_health() -> Dict[str, Any]:
    """Check Redis health with password authentication"""
    try:
        r = redis.from_url(settings.REDIS_URL, password=settings.REDIS_PASSWORD)
        pong = await r.ping()
        return {"status": "healthy"} if pong else {"status": "unreachable"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_microservice_health(name: str, url: str) -> Dict[str, Any]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "healthy",
                        "microservice": name,
                        "details": data
                    }
                return {
                    "status": "unhealthy",
                    "microservice": name,
                    "error": f"HTTP {response.status}"
                }
    except Exception as e:
        return {
            "status": "unhealthy",
            "microservice": name,
            "error": str(e)
        }
