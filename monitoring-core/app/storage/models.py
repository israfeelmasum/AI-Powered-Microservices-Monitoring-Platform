# monitoring-core/app/storage/models.py
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime

class LogEntry(BaseModel):
    timestamp: str = Field(..., description="ISO formatted timestamp")
    service: str = Field(..., description="Service name")
    level: str = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    endpoint: Optional[str] = Field(None, description="API endpoint")
    method: Optional[str] = Field(None, description="HTTP method")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    response_time: Optional[float] = Field(None, description="Response time in ms")
    client_ip: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    error_type: Optional[str] = Field(None, description="Error type")
    error_message: Optional[str] = Field(None, description="Error message")
    system_metrics: Optional[Dict[str, Any]] = Field(None, description="System metrics")

class MetricEntry(BaseModel):
    timestamp: str = Field(..., description="ISO formatted timestamp")
    service: str = Field(..., description="Service name")
    metrics: Dict[str, Any] = Field(..., description="Metrics data")

class AnomalyEntry(BaseModel):
    timestamp: str = Field(..., description="ISO formatted timestamp")
    service: Optional[str] = Field(None, description="Affected service")
    anomaly_id: str = Field(..., description="Unique anomaly ID")
    type: str = Field(..., description="Anomaly type")
    severity: str = Field(..., description="Anomaly severity")
    description: str = Field(..., description="Anomaly description")
    recommendation: Optional[str] = Field(None, description="Recommended action")
    detected_by: str = Field(..., description="Detection method")
    model: Optional[str] = Field(None, description="AI model used")
    affected_services: Optional[List[str]] = Field(None, description="Affected services")

class HealthCheckEntry(BaseModel):
    timestamp: str = Field(..., description="ISO formatted timestamp")
    service: str = Field(..., description="Service name")
    status: str = Field(..., description="Health status")
    checks: Dict[str, Any] = Field(..., description="Health check details")
    system_metrics: Optional[Dict[str, Any]] = Field(None, description="System metrics")

class ServiceRegistration(BaseModel):
    service_name: str = Field(..., description="Service name")
    service_url: str = Field(..., description="Service URL")
    secret_key: str = Field(..., description="Service secret key")
    version: str = Field(..., description="Service version")
    endpoints: Optional[List[Dict[str, Any]]] = Field(None, description="Service endpoints")
    capabilities: Optional[List[str]] = Field(None, description="Service capabilities")
    registered_at: str = Field(..., description="Registration timestamp")