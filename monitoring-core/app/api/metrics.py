# monitoring-core/app/api/metrics.py
from fastapi import APIRouter, HTTPException, Header, Depends
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta

from ..storage.elasticsearch import ElasticsearchClient
from ..config.settings import settings
from ..auth.auth import authenticate

logger = logging.getLogger(__name__)
router = APIRouter()


def validate_service_auth(x_service_secret: str = Header(...), x_service_name: str = Header(...)):
    """Validate service authentication"""
    if x_service_name not in settings.SERVICE_SECRETS:
        raise HTTPException(status_code=401, detail="Unknown service")

    if settings.SERVICE_SECRETS[x_service_name] != x_service_secret:
        raise HTTPException(status_code=401, detail="Invalid service secret")

    return x_service_name


@router.post("/")
async def receive_metrics(
        metrics_data: dict,
        service_name: str = Depends(validate_service_auth)
):
    """Receive metrics data from microservices"""
    try:
        # Add metadata
        metrics_payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": service_name,
            "metrics": metrics_data,
            "received_at": datetime.utcnow().isoformat()
        }

        # Store in Elasticsearch
        es_client = ElasticsearchClient()
        await es_client.store_metrics(metrics_payload)

        return {"status": "success", "message": "Metrics stored"}

    except Exception as e:
        logger.error(f"Failed to store metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to store metrics")


@router.get("/")
async def get_metrics(
        service: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
        username: str = Depends(authenticate)
):
    """Get metrics with filtering"""
    try:
        es_client = ElasticsearchClient()

        # Build query for metrics
        query = {
            "size": limit,
            "sort": [{"timestamp": {"order": "desc"}}],
            "query": {"bool": {"must": []}}
        }

        if service:
            query["query"]["bool"]["must"].append({"term": {"service": service}})

        if start_time or end_time:
            range_query = {"range": {"timestamp": {}}}
            if start_time:
                range_query["range"]["timestamp"]["gte"] = start_time
            if end_time:
                range_query["range"]["timestamp"]["lte"] = end_time
            query["query"]["bool"]["must"].append(range_query)

        if not query["query"]["bool"]["must"]:
            query["query"]["bool"]["must"].append({
                "range": {"timestamp": {"gte": "now-24h"}}
            })

        # Query metrics from Elasticsearch
        if not hasattr(es_client, 'session') or es_client.session is None:
            await es_client.initialize()

        import aiohttp
        async with es_client.session.post(
                f"{es_client.url}/monitoring-metrics-*/_search",
                json=query,
                headers={"Content-Type": "application/json"}
        ) as response:
            if response.status == 200:
                data = await response.json()
                metrics = [hit["_source"] for hit in data["hits"]["hits"]]
            else:
                metrics = []

        return {
            "metrics": metrics,
            "count": len(metrics),
            "filters": {
                "service": service,
                "start_time": start_time,
                "end_time": end_time
            }
        }

    except Exception as e:
        logger.error(f"Failed to retrieve metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.get("/aggregated")
async def get_aggregated_metrics(
        service: Optional[str] = None,
        hours: int = 24,
        username: str = Depends(authenticate)
):
    """Get aggregated metrics"""
    try:
        es_client = ElasticsearchClient()

        # Build aggregation query
        query = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [
                        {"range": {"timestamp": {"gte": f"now-{hours}h"}}}
                    ]
                }
            },
            "aggs": {
                "total_requests": {
                    "sum": {"field": "metrics.request_count"}
                },
                "avg_response_time": {
                    "avg": {"field": "metrics.avg_response_time"}
                },
                "error_rate": {
                    "avg": {"field": "metrics.error_rate"}
                },
                "services": {
                    "terms": {"field": "service"},
                    "aggs": {
                        "avg_cpu": {"avg": {"field": "metrics.cpu_usage"}},
                        "avg_memory": {"avg": {"field": "metrics.memory_usage"}}
                    }
                },
                "timeline": {
                    "date_histogram": {
                        "field": "timestamp",
                        "calendar_interval": "hour"
                    },
                    "aggs": {
                        "avg_response_time": {"avg": {"field": "metrics.avg_response_time"}},
                        "total_requests": {"sum": {"field": "metrics.request_count"}}
                    }
                }
            }
        }

        if service:
            query["query"]["bool"]["must"].append({"term": {"service": service}})

        # Execute aggregation query
        if not hasattr(es_client, 'session') or es_client.session is None:
            await es_client.initialize()

        import aiohttp
        async with es_client.session.post(
                f"{es_client.url}/monitoring-metrics-*/_search",
                json=query,
                headers={"Content-Type": "application/json"}
        ) as response:
            if response.status == 200:
                data = await response.json()
                aggregations = data.get("aggregations", {})

                aggregated_data = {
                    "service": service or "all",
                    "time_window_hours": hours,
                    "aggregations": {
                        "total_requests": aggregations.get("total_requests", {}).get("value", 0),
                        "avg_response_time": round(aggregations.get("avg_response_time", {}).get("value", 0), 2),
                        "error_rate": round(aggregations.get("error_rate", {}).get("value", 0), 2),
                        "throughput_per_hour": round(aggregations.get("total_requests", {}).get("value", 0) / hours, 2)
                    },
                    "services": [
                        {
                            "service": bucket["key"],
                            "doc_count": bucket["doc_count"],
                            "avg_cpu": round(bucket.get("avg_cpu", {}).get("value", 0), 2),
                            "avg_memory": round(bucket.get("avg_memory", {}).get("value", 0), 2)
                        }
                        for bucket in aggregations.get("services", {}).get("buckets", [])
                    ],
                    "timeline": [
                        {
                            "timestamp": bucket["key_as_string"],
                            "avg_response_time": round(bucket.get("avg_response_time", {}).get("value", 0), 2),
                            "total_requests": bucket.get("total_requests", {}).get("value", 0)
                        }
                        for bucket in aggregations.get("timeline", {}).get("buckets", [])
                    ],
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                aggregated_data = {
                    "service": service or "all",
                    "time_window_hours": hours,
                    "aggregations": {
                        "total_requests": 0,
                        "avg_response_time": 0,
                        "error_rate": 0,
                        "throughput_per_hour": 0
                    },
                    "services": [],
                    "timeline": [],
                    "timestamp": datetime.utcnow().isoformat()
                }

        return aggregated_data

    except Exception as e:
        logger.error(f"Failed to get aggregated metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get aggregated metrics")


@router.get("/system")
async def get_system_metrics(
        service: Optional[str] = None,
        hours: int = 24,
        username: str = Depends(authenticate)
):
    """Get system metrics (CPU, memory, etc.)"""
    try:
        es_client = ElasticsearchClient()

        # Build query for system metrics
        query = {
            "size": 100,
            "sort": [{"timestamp": {"order": "desc"}}],
            "query": {
                "bool": {
                    "must": [
                        {"range": {"timestamp": {"gte": f"now-{hours}h"}}},
                        {"exists": {"field": "metrics.cpu_usage"}}
                    ]
                }
            }
        }

        if service:
            query["query"]["bool"]["must"].append({"term": {"service": service}})

        # Execute query
        if not hasattr(es_client, 'session') or es_client.session is None:
            await es_client.initialize()

        import aiohttp
        async with es_client.session.post(
                f"{es_client.url}/monitoring-metrics-*/_search",
                json=query,
                headers={"Content-Type": "application/json"}
        ) as response:
            if response.status == 200:
                data = await response.json()
                system_metrics = [hit["_source"] for hit in data["hits"]["hits"]]
            else:
                system_metrics = []

        return {
            "system_metrics": system_metrics,
            "count": len(system_metrics),
            "service": service,
            "time_window_hours": hours
        }

    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system metrics")


@router.get("/health")
async def metrics_health_check():
    """Health check for metrics endpoint"""
    try:
        es_client = ElasticsearchClient()
        health = await es_client.health_check()

        return {
            "status": "healthy" if health["status"] == "healthy" else "unhealthy",
            "elasticsearch": health,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Metrics health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }