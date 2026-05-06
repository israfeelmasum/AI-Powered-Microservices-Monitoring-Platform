# shared/monitoring_sdk/models.py
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

class MetricsEntry(BaseModel):
    timestamp: str = Field(..., description="ISO formatted timestamp")
    service: str = Field(..., description="Service name")
    metrics: Dict[str, Any] = Field(..., description="Metrics data")

class HealthCheckEntry(BaseModel):
    timestamp: str = Field(..., description="ISO formatted timestamp")
    service: str = Field(..., description="Service name")
    status: str = Field(..., description="Health status")
    checks: Dict[str, Any] = Field(..., description="Health check details")
    system_metrics: Dict[str, Any] = Field(..., description="System metrics")

class ServiceRegistration(BaseModel):
    service_name: str = Field(..., description="Service name")
    service_url: str = Field(..., description="Service URL")
    secret_key: str = Field(..., description="Service secret key")
    version: str = Field(..., description="Service version")
    endpoints: Optional[List[Dict[str, Any]]] = Field(None, description="Service endpoints")
    capabilities: Optional[List[str]] = Field(None, description="Service capabilities")
    registered_at: str = Field(..., description="Registration timestamp")

class SystemMetrics(BaseModel):
    cpu_percent: float = Field(..., description="CPU usage percentage")
    memory_mb: float = Field(..., description="Memory usage in MB")
    memory_percent: float = Field(..., description="Memory usage percentage")
    disk_usage_percent: Optional[float] = Field(None, description="Disk usage percentage")
    network_io: Optional[Dict[str, float]] = Field(None, description="Network I/O stats")
    open_files: Optional[int] = Field(None, description="Number of open files")
    connections: Optional[int] = Field(None, description="Number of connections")
    threads: Optional[int] = Field(None, description="Number of threads")

class PerformanceMetrics(BaseModel):
    request_count: int = Field(..., description="Total request count")
    error_count: int = Field(..., description="Total error count")
    avg_response_time: float = Field(..., description="Average response time")
    p95_response_time: Optional[float] = Field(None, description="95th percentile response time")
    p99_response_time: Optional[float] = Field(None, description="99th percentile response time")
    throughput: float = Field(..., description="Requests per second")
    error_rate: float = Field(..., description="Error rate percentage")

class BusinessMetrics(BaseModel):
    """Custom business metrics model - extend as needed"""
    timestamp: str = Field(..., description="ISO formatted timestamp")
    service: str = Field(..., description="Service name")
    metric_name: str = Field(..., description="Metric name")
    metric_value: float = Field(..., description="Metric value")
    metric_type: str = Field(..., description="Metric type (counter, gauge, histogram)")
    tags: Optional[Dict[str, str]] = Field(None, description="Metric tags")
    unit: Optional[str] = Field(None, description="Metric unit")

class AlertRule(BaseModel):
    rule_id: str = Field(..., description="Unique rule ID")
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    service: Optional[str] = Field(None, description="Target service")
    metric: str = Field(..., description="Target metric")
    condition: str = Field(..., description="Alert condition")
    threshold: float = Field(..., description="Alert threshold")
    severity: str = Field(..., description="Alert severity")
    enabled: bool = Field(True, description="Rule enabled status")