# monitoring-core/app/api/ai_insights.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta

from ..ai.ollama_client import OllamaClient
from ..ai.anomaly_detector import AnomalyDetector
from ..ai.pattern_analyzer import PatternAnalyzer
from ..ai.summarizer import LogSummarizer
from ..storage.elasticsearch import ElasticsearchClient
from ..auth.auth import authenticate

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/anomalies")
async def get_anomalies(
        hours: int = 24,
        severity: Optional[str] = None,
        username: str = Depends(authenticate)
):
    """Get detected anomalies"""
    try:
        es_client = ElasticsearchClient()
        anomalies = await es_client.get_anomalies(hours=hours, severity=severity)

        return {
            "anomalies": anomalies,
            "count": len(anomalies),
            "time_window_hours": hours,
            "severity_filter": severity
        }

    except Exception as e:
        logger.error(f"Failed to get anomalies: {e}")
        raise HTTPException(status_code=500, detail="Failed to get anomalies")


@router.post("/analyze-patterns")
async def analyze_patterns(
        request_data: dict,
        username: str = Depends(authenticate)
):
    """Trigger pattern analysis on recent logs"""
    try:
        hours = request_data.get("hours", 24)
        service = request_data.get("service")

        # Get recent logs
        es_client = ElasticsearchClient()
        logs = await es_client.get_recent_logs(hours=hours, service=service)

        if not logs:
            return {"message": "No logs found for analysis", "patterns": {}}

        # Analyze patterns with AI
        ollama_client = OllamaClient()
        pattern_analyzer = PatternAnalyzer(ollama_client)
        patterns = await pattern_analyzer.analyze_patterns(logs, hours)

        return {
            "patterns": patterns,
            "log_count": len(logs),
            "analysis_timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Pattern analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Pattern analysis failed")


@router.post("/summarize-logs")
async def summarize_logs(
        request_data: dict,
        username: str = Depends(authenticate)
):
    """Generate AI summary of logs"""
    try:
        hours = request_data.get("hours", 24)
        service = request_data.get("service")
        summary_type = request_data.get("type", "general")  # general, error_focus, performance, security

        # Get logs for summary
        es_client = ElasticsearchClient()
        logs = await es_client.get_recent_logs(hours=hours, service=service)

        if not logs:
            return {"message": "No logs found for summarization"}

        # Generate AI summary
        ollama_client = OllamaClient()
        summarizer = LogSummarizer(ollama_client)
        summary = await summarizer.summarize_logs(logs, summary_type)

        return summary

    except Exception as e:
        logger.error(f"Log summarization failed: {e}")
        raise HTTPException(status_code=500, detail="Log summarization failed")


@router.post("/detect-anomalies")
async def trigger_anomaly_detection(
        request_data: dict,
        username: str = Depends(authenticate)
):
    """Manually trigger anomaly detection"""
    try:
        hours = request_data.get("hours", 1)
        service = request_data.get("service")

        # Get recent logs
        es_client = ElasticsearchClient()
        logs = await es_client.get_recent_logs(hours=hours, service=service)

        if not logs:
            return {"message": "No logs found for anomaly detection"}

        # Run anomaly detection
        ollama_client = OllamaClient()
        detector = AnomalyDetector(ollama_client)
        anomalies = await detector.detect_anomalies(logs)

        # Store detected anomalies
        if anomalies:
            await es_client.store_anomalies(anomalies)

        return {
            "detected_anomalies": anomalies,
            "count": len(anomalies),
            "log_count": len(logs),
            "detection_timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        raise HTTPException(status_code=500, detail="Anomaly detection failed")


@router.get("/insights/dashboard")
async def get_dashboard_insights(
        username: str = Depends(authenticate)
):
    """Get AI insights for dashboard"""
    try:
        es_client = ElasticsearchClient()

        # Get various data for insights
        recent_logs = await es_client.get_recent_logs(hours=24)
        recent_anomalies = await es_client.get_anomalies(hours=24)
        services_status = await es_client.get_services_status()

        # Calculate basic insights
        total_logs = len(recent_logs)
        error_logs = len([log for log in recent_logs if log.get("level") in ["ERROR", "CRITICAL"]])
        error_rate = (error_logs / total_logs * 100) if total_logs > 0 else 0

        # Get service health scores
        service_health = {}
        for service_data in services_status:
            service_name = service_data.get("service", "unknown")
            service_logs = [log for log in recent_logs if log.get("service") == service_name]
            service_errors = [log for log in service_logs if log.get("level") in ["ERROR", "CRITICAL"]]

            if service_logs:
                service_error_rate = len(service_errors) / len(service_logs) * 100
                health_score = max(0, 100 - service_error_rate)
            else:
                health_score = 100

            service_health[service_name] = {
                "health_score": round(health_score, 2),
                "total_logs": len(service_logs),
                "error_rate": round(len(service_errors) / len(service_logs) * 100, 2) if service_logs else 0
            }

        insights = {
            "overview": {
                "total_logs": total_logs,
                "error_rate": round(error_rate, 2),
                "active_services": len(services_status),
                "anomalies_count": len(recent_anomalies),
                "system_health": "healthy" if error_rate < 5 else "warning" if error_rate < 15 else "critical"
            },
            "services": service_health,
            "recent_anomalies": recent_anomalies[:5],  # Last 5 anomalies
            "recommendations": await _generate_recommendations(recent_logs, recent_anomalies, service_health),
            "timestamp": datetime.utcnow().isoformat()
        }

        return insights

    except Exception as e:
        logger.error(f"Failed to get dashboard insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to get insights")


async def _generate_recommendations(logs, anomalies, service_health):
    """Generate basic recommendations"""
    recommendations = []

    # High error rate recommendation
    for service, health in service_health.items():
        if health["error_rate"] > 10:
            recommendations.append({
                "type": "error_rate",
                "priority": "high",
                "service": service,
                "message": f"Service {service} has high error rate ({health['error_rate']:.1f}%)",
                "action": "Investigate recent errors and implement fixes"
            })

    # Anomaly recommendations
    critical_anomalies = [a for a in anomalies if a.get("severity") == "critical"]
    if critical_anomalies:
        recommendations.append({
            "type": "anomaly",
            "priority": "critical",
            "message": f"{len(critical_anomalies)} critical anomalies detected",
            "action": "Review and address critical anomalies immediately"
        })

    # Performance recommendations
    slow_logs = [log for log in logs if log.get("response_time", 0) > 1000]
    if len(slow_logs) > len(logs) * 0.1:  # More than 10% slow requests
        recommendations.append({
            "type": "performance",
            "priority": "medium",
            "message": f"{len(slow_logs)} slow requests detected (>1s response time)",
            "action": "Optimize slow endpoints and database queries"
        })

    return recommendations


# monitoring-core/app/dashboard/routes.py
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import logging
from datetime import datetime

from ..auth.auth import authenticate
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
            service_name = service_data.get("service", "unknown")
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
