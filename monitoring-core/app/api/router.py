import dashboard
from fastapi import APIRouter
from ..api import health, monitoring, metrics, ai_insights  # etc.

router = APIRouter()

router.include_router(health.router)
router.include_router(monitoring.router)
router.include_router(metrics.router)
router.include_router(ai_insights.router)
# Add others if needed
