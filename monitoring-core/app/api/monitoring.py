# monitoring-core/app/api/monitoring.py
from fastapi import APIRouter, HTTPException, Header, Depends
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta

from ..storage.elasticsearch import ElasticsearchClient
from ..config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def validate_service_auth(x_service_secret: str = Header(...), x_service_name: str = Header(...)):
    """Validate service authentication"""
    if x_service_name not in settings.SERVICE_SECRETS:
        raise HTTPException(status_code=401, detail="Unknown service")

    if settings.SERVICE_SECRETS[x_service_name] != x_service_secret:
        raise HTTPException(status_code=401, detail="Invalid service secret")

    return x_service_name


@router.post("/logs")
async def receive_logs(
        log_data: dict,
        service_name: str = Depends(validate_service_auth)
):
    """Receive log data from microservices"""
    try:
        # Add metadata
        log_data["received_at"] = datetime.utcnow().isoformat()
        log_data["validated_service"] = service_name

        # Store in Elasticsearch
        # Note: In a real implementation, you'd inject this dependency
        es_client = ElasticsearchClient()
        await es_client.store_log(log_data)

        return {"status": "success", "message": "Log stored"}

    except Exception as e:
        logger.error(f"Failed to store log: {e}")
        raise HTTPException(status_code=500, detail="Failed to store log")


@router.post("/health")
async def receive_health_check(
        health_data: dict,
        service_name: str = Depends(validate_service_auth)
):
    """Receive health check data from microservices"""
    try:
        health_payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": service_name,
            "health_data": health_data,
            "received_at": datetime.utcnow().isoformat()
        }

        # Store in Elasticsearch
        es_client = ElasticsearchClient()
        await es_client.store_health_check(health_payload)

        return {"status": "success", "message": "Health check stored"}

    except Exception as e:
        logger.error(f"Failed to store health check: {e}")
        raise HTTPException(status_code=500, detail="Failed to store health check")


@router.get("/logs")
async def get_logs(
        service: Optional[str] = None,
        level: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100
):
    """Get logs with filtering"""
    try:
        es_client = ElasticsearchClient()
        logs = await es_client.query_logs(
            service=service,
            level=level,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )

        return {
            "logs": logs,
            "count": len(logs),
            "filters": {
                "service": service,
                "level": level,
                "start_time": start_time,
                "end_time": end_time
            }
        }

    except Exception as e:
        logger.error(f"Failed to retrieve logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve logs")


@router.get("/services")
async def get_services():
    """Get list of registered services and their status"""
    try:
        es_client = ElasticsearchClient()
        services = await es_client.get_services_status()

        return {
            "services": services,
            "count": len(services),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get services: {e}")
        raise HTTPException(status_code=500, detail="Failed to get services")



