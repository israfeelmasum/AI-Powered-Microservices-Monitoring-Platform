from datetime import datetime

import aiohttp
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
from contextlib import asynccontextmanager
import logging
import secrets
from .api.router import router as api_router
from .config.settings import settings
from .middleware.monitoring import MonitoringMiddleware
from .middleware.logging import setup_logging
from .api import monitoring, metrics, ai_insights
from .dashboard import routes as dashboard_routes
from .ai.ollama_client import OllamaClient
from .storage.elasticsearch import ElasticsearchClient

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Security
security = HTTPBasic()

# Jinja2 templates
templates = Jinja2Templates(directory="app/dashboard/templates")

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    """Basic authentication for admin access"""
    is_username_correct = secrets.compare_digest(
        credentials.username, settings.ADMIN_USERNAME
    )
    is_password_correct = secrets.compare_digest(
        credentials.password, settings.ADMIN_PASSWORD
    )
    if not (is_username_correct and is_password_correct):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Periodic health check task
async def periodically_check_health():
    """Check the health of monitoring-core using dynamic HOST/PORT from settings."""
    while True:
        try:
            url = f"http://{settings.HOST}:{settings.PORT}/health"
            async with aiohttp.ClientSession() as session:
                response = await session.get(url)
                if response.status == 200:
                    logger.info("Health check stored")
                else:
                    logger.warning(f"Health check failed: {response.status}")
        except Exception as e:
            logger.error(f"Health check error: {e}")
        await asyncio.sleep(60)

# Application lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Centralized Monitoring System")

    try:
        es_client = ElasticsearchClient()
        await es_client.initialize_indices()
        app.state.elasticsearch = es_client
        logger.info("Elasticsearch connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Elasticsearch: {e}")

    try:
        ollama_client = OllamaClient()
        await ollama_client.initialize()
        app.state.ollama = ollama_client
        logger.info("Ollama client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Ollama: {e}")

    monitoring_task = asyncio.create_task(start_ai_monitoring(app))
    health_check_task = asyncio.create_task(periodically_check_health())

    yield

    logger.info("Shutting down Centralized Monitoring System")
    monitoring_task.cancel()
    health_check_task.cancel()
    try:
        await monitoring_task
    except asyncio.CancelledError:
        pass
    try:
        await health_check_task
    except asyncio.CancelledError:
        pass

# AI monitoring
async def start_ai_monitoring(app: FastAPI):
    while True:
        try:
            if hasattr(app.state, 'ollama') and hasattr(app.state, 'elasticsearch'):
                await run_anomaly_detection(app.state.ollama, app.state.elasticsearch)
                await asyncio.sleep(300)
            else:
                await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Error in AI monitoring: {e}")
            await asyncio.sleep(60)

async def run_anomaly_detection(ollama_client, es_client):
    try:
        recent_logs = await es_client.get_recent_logs(minutes=10)
        if recent_logs:
            from .ai.anomaly_detector import AnomalyDetector
            detector = AnomalyDetector(ollama_client)
            anomalies = await detector.detect_anomalies(recent_logs)
            if anomalies:
                await es_client.store_anomalies(anomalies)
                logger.info(f"Detected {len(anomalies)} anomalies")
    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")

# Create FastAPI app
app = FastAPI(
    title="Centralized Monitoring System",
    description="AI-Powered Monitoring for FastAPI Microservices",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
app.add_middleware(MonitoringMiddleware)

app.mount("/static", StaticFiles(directory="app/dashboard/static"), name="static")

app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["Monitoring"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["Metrics"])
app.include_router(ai_insights.router, prefix="/api/v1/ai", tags=["AI Insights"])
app.include_router(dashboard_routes.router, prefix="/dashboard", tags=["Dashboard"])

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, username: str = Depends(authenticate)):
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "username": username,
            "title": "Centralized Monitoring Dashboard"
        }
    )

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "monitoring-core",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/v1/register-service")
async def register_service(service_data: dict, username: str = Depends(authenticate)):
    try:
        service_name = service_data.get("service_name")
        service_secret = service_data.get("secret_key")

        if not validate_service_secret(service_name, service_secret):
            raise HTTPException(status_code=401, detail="Invalid service secret")

        es_client = app.state.elasticsearch
        await es_client.store_service_registration(service_data)

        logger.info(f"Service registered: {service_name}")
        return {"status": "registered", "service": service_name}

    except Exception as e:
        logger.error(f"Service registration failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

def validate_service_secret(service_name: str, secret: str) -> bool:
    return settings.SERVICE_SECRETS.get(service_name) == secret

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
