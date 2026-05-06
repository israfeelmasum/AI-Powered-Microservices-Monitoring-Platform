import asyncio
import logging
import secrets
import ssl
from datetime import datetime, timedelta
from http.client import HTTPException
from typing import List, Dict, Any, Optional
import aiohttp
from ..config.settings import settings

logger = logging.getLogger(__name__)


class ElasticsearchClient:
    """Elasticsearch client for storing and querying monitoring data"""

    def __init__(self, url: str = None):
        self.url = url or settings.ELASTICSEARCH_URL
        self.session = None
        self.indices_created = False

    async def initialize(self):
        """Initialize Elasticsearch client and create indices"""
        if not self.session:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            auth = aiohttp.BasicAuth(
                settings.ELASTICSEARCH_USERNAME,
                settings.ELASTICSEARCH_PASSWORD
            )
            self.session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=ssl_context),
                auth=auth
            )

        if not self.indices_created:
            await self.initialize_indices()
            self.indices_created = True

        return self

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def initialize_indices(self):
        from .elasticsearch_index_config import INDICES_CONFIG as INDICES

        for index_name, config in INDICES.items():
            await self._create_index_template(index_name, config)

    async def _create_index_template(self, index_name: str, config: Dict):
        try:
            if not self.session:
                await self.initialize()

            template_name = f"{index_name}-template"
            template_config = {
                "index_patterns": [f"{index_name}-*"],
                "template": config,
                "priority": 100
            }

            async with self.session.put(
                f"{self.url}/_index_template/{template_name}",
                json=template_config,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    logger.warning(f"Failed to create template {template_name}: {response.status} - {error_text}")
                else:
                    logger.info(f"Index template {template_name} created successfully")

            await self._create_index(index_name, config)

        except Exception as e:
            logger.error(f"Error creating index template {index_name}: {e}")

    async def _create_index(self, index_name: str, config: Dict):
        try:
            async with self.session.put(
                f"{self.url}/{index_name}",
                json=config,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status in [200, 201]:
                    logger.info(f"Index {index_name} created successfully")
                elif response.status == 400:
                    error_text = await response.text()
                    if "already exists" in error_text:
                        logger.info(f"Index {index_name} already exists")
                    else:
                        logger.error(f"Failed to create index {index_name}: {error_text}")
                else:
                    logger.error(f"Failed to create index {index_name}: {response.status}")

        except Exception as e:
            logger.error(f"Error creating index {index_name}: {e}")

    async def get_recent_logs(self, minutes: int = 5) -> List[Dict[str, Any]]:
        """Fetch recent logs from Elasticsearch"""
        try:
            now = datetime.utcnow()
            start_time = now - timedelta(minutes=minutes)

            query = {
                "query": {
                    "range": {
                        "timestamp": {
                            "gte": start_time.isoformat(),
                            "lte": now.isoformat()
                        }
                    }
                },
                "sort": [{"timestamp": "desc"}],
                "size": 1000
            }

            async with self.session.get(
                f"{self.url}/monitoring-logs/_search",
                json=query,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return [hit["_source"] for hit in result.get("hits", {}).get("hits", [])]
                else:
                    logger.error(f"Failed to fetch logs: {response.status}")
        except Exception as e:
            logger.error(f"Error fetching logs: {e}")
        return []

    async def store_service_registration(self, service_data: dict):
        """Store registered service metadata in Elasticsearch"""
        try:
            async with self.session.post(
                f"{self.url}/monitoring-services/_doc",
                json=service_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    logger.error(f"Failed to store service registration: {response.status} - {error_text}")
                else:
                    logger.info("Service registration document indexed successfully")
        except Exception as e:
            logger.error(f"Failed to store service registration: {e}")
            raise

    async def store_log(self, log_data: Dict[str, Any]):
        """Store a log entry in Elasticsearch"""
        try:
            if not self.session:
                await self.initialize()

            index_name = "monitoring-logs"
            document_id = log_data.get("request_id") or secrets.token_hex(16)
            timestamp = log_data.get("timestamp")

            if not timestamp:
                from datetime import datetime
                log_data["timestamp"] = datetime.utcnow().isoformat()

            async with self.session.post(
                f"{self.url}/{index_name}/_doc/{document_id}",
                json=log_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    logger.warning(f"Failed to store log: {response.status} - {error_text}")
                    raise HTTPException(status_code=500, detail="Failed to store log")

            logger.info("Log stored successfully")

        except Exception as e:
            import traceback
            logger.exception("Exception occurred while storing log")
            raise HTTPException(status_code=500, detail="Failed to store log")



    async def store_health_check(self, health_data: Dict[str, Any]):
        """Store health check result in monitoring-health index"""
        try:
            if not self.session:
                await self.initialize()

            async with self.session.post(
                    f"{self.url}/monitoring-health/_doc",
                    json=health_data,
                    headers={"Content-Type": "application/json"}
            ) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    logger.warning(f"Failed to store health check: {response.status} - {error_text}")
                else:
                    logger.info("Health check result stored in Elasticsearch")
        except Exception as e:
            logger.error(f"Error storing health check result: {e}")

    async def store_anomalies(self, anomalies: List[dict]):
        """Store AI anomaly detection results in a separate index"""
        try:
            if not self.session:
                await self.initialize()

            for anomaly in anomalies:
                async with self.session.post(
                        f"{self.url}/monitoring-anomalies/_doc",
                        json=anomaly,
                        headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status not in [200, 201]:
                        text = await response.text()
                        logger.warning(f"Failed to store anomaly: {response.status} - {text}")
        except Exception as e:
            logger.error(f"Error storing anomalies: {e}")

    async def store_metrics(self, metrics: dict):
        """Store metrics into the monitoring-metrics index"""
        try:
            await self.initialize()  # ensure session is set

            index_name = "monitoring-metrics"
            url = f"{self.url}/{index_name}/_doc"

            import aiohttp
            async with self.session.post(
                    url,
                    json=metrics,
                    headers={"Content-Type": "application/json"}
            ) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    raise Exception(f"Failed to store metrics (status={response.status}): {error_text}")

            logger.info("✅ Metrics stored successfully in Elasticsearch")

        except Exception as e:
            logger.error(f"❌ Error storing metrics: {e}")
            raise