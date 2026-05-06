# monitoring-core/app/dashboard/routes.py
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import logging
from datetime import datetime


from ..auth.auth import authenticate, logout_user
from ..storage.elasticsearch import ElasticsearchClient

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/dashboard/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request, username: str = Depends(authenticate)):
    """Main dashboard page"""
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "username": username, "page": "overview"}
    )


@router.get("/services", response_class=HTMLResponse)
async def services_dashboard(request: Request, username: str = Depends(authenticate)):
    """Services monitoring dashboard"""
    return templates.TemplateResponse(
        "services.html",
        {"request": request, "username": username, "page": "services"}
    )

@router.get("/logout")
@router.post("/logout")
async def logout():
    """Logout endpoint"""
    logout_user()

@router.get("/logs", response_class=HTMLResponse)
async def logs_dashboard(request: Request, username: str = Depends(authenticate)):
    """Logs viewing dashboard"""
    return templates.TemplateResponse(
        "logs.html",
        {"request": request, "username": username, "page": "logs"}
    )



@router.get("/ai-insights", response_class=HTMLResponse)
async def ai_insights_dashboard(request: Request, username: str = Depends(authenticate)):
    """AI insights dashboard"""
    return templates.TemplateResponse(
        "ai_insights.html",
        {"request": request, "username": username, "page": "ai"}
    )


@router.get("/api/dashboard-data")
async def get_dashboard_data(username: str = Depends(authenticate)):
    """Get real-time dashboard data"""
    try:
        es_client = ElasticsearchClient()

        # Get recent data
        recent_logs = await es_client.get_recent_logs(hours=1)
        services_status = await es_client.get_services_status()
        recent_anomalies = await es_client.get_anomalies(hours=24)

        # Calculate metrics
        total_requests = len(recent_logs)
        error_count = len([log for log in recent_logs if log.get("level") in ["ERROR", "CRITICAL"]])
        avg_response_time = sum(log.get("response_time", 0) for log in recent_logs) / len(
            recent_logs) if recent_logs else 0

        # Service metrics
        service_metrics = {}
        for service_data in services_status:
            service_name = service_data.get("service_name", service_data.get("service", "unknown"))
            service_logs = [log for log in recent_logs if log.get("service") == service_name]

            service_metrics[service_name] = {
                "request_count": len(service_logs),
                "error_count": len([log for log in service_logs if log.get("level") in ["ERROR", "CRITICAL"]]),
                "avg_response_time": sum(log.get("response_time", 0) for log in service_logs) / len(
                    service_logs) if service_logs else 0,
                "status": "healthy" if len(service_logs) > 0 else "inactive"
            }

        return {
            "overview": {
                "total_requests": total_requests,
                "error_count": error_count,
                "error_rate": round((error_count / total_requests * 100) if total_requests > 0 else 0, 2),
                "avg_response_time": round(avg_response_time, 2),
                "active_services": len([s for s in service_metrics.values() if s["status"] == "healthy"]),
                "anomalies_count": len(recent_anomalies)
            },
            "services": service_metrics,
            "recent_anomalies": recent_anomalies[:10],
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        return {"error": str(e)}
