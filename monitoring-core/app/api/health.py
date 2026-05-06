from fastapi import APIRouter
from ..middleware.health import (
    HealthChecker,
    check_elasticsearch_health,
    check_redis_health,
    check_ollama_health,
    check_microservice_health,
)
from ..storage.elasticsearch import ElasticsearchClient

router = APIRouter()
health_checker = HealthChecker()
es_client = ElasticsearchClient()

# Register health checks
health_checker.register_check("elasticsearch", check_elasticsearch_health)
health_checker.register_check("redis", check_redis_health)
health_checker.register_check("ollama", check_ollama_health)

# Register microservice health check using proper async function
async def note_service_health():
    return await check_microservice_health("note-service", "http://127.0.0.1:8001/health")

health_checker.register_check("note-service", note_service_health)

@router.get("/health", tags=["Monitoring"], summary="System & service health check")
async def get_health_status():
    result = await health_checker.run_all_checks()

    try:
        await es_client.initialize()
        await es_client.store_health_check(result)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to store health check: {e}")

    return result
