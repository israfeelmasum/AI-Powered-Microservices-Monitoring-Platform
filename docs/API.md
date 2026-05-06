# docs/API.md

# Centralized Monitoring System API Documentation

## Overview

The Centralized Monitoring System provides REST APIs for collecting, analyzing, and retrieving monitoring data from microservices.

## Authentication

### Basic Authentication
- **Admin Access**: Username: `admin`, Password: `admin`
- **Service Authentication**: Uses secret keys in headers

### Service Authentication Headers
```
X-Service-Name: service-name
X-Service-Secret: service-secret-key
```

## Core APIs

### 1. Service Registration

**POST** `/api/v1/register-service`

Register a new microservice with the monitoring system.

**Request Body:**
```json
{
  "service_name": "note-service",
  "service_url": "http://localhost:8001",
  "secret_key": "note_secret_key_2024",
  "version": "1.0.0",
  "endpoints": [
    {"path": "/notes", "methods": ["GET", "POST"]},
    {"path": "/notes/{id}", "methods": ["GET", "PUT", "DELETE"]}
  ],
  "capabilities": ["logging", "metrics", "health_checks"]
}
```

**Response:**
```json
{
  "status": "registered",
  "service": "note-service"
}
```

### 2. Log Collection

**POST** `/api/v1/monitoring/logs`

Collect log data from microservices.

**Headers:**
- `X-Service-Name`: Service name
- `X-Service-Secret`: Service secret key

**Request Body:**
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "message": "GET /notes - 200",
  "correlation_id": "abc123",
  "endpoint": "GET /notes",
  "status_code": 200,
  "response_time": 45.2,
  "client_ip": "192.168.1.1",
  "system_metrics": {
    "cpu_percent": 25.5,
    "memory_mb": 128.4
  }
}
```

### 3. Metrics Collection

**POST** `/api/v1/metrics`

Collect metrics data from microservices.

**Headers:**
- `X-Service-Name`: Service name
- `X-Service-Secret`: Service secret key

**Request Body:**
```json
{
  "metrics": {
    "request_count": 1500,
    "error_count": 12,
    "avg_response_time": 85.3,
    "memory_usage": 256.7,
    "cpu_usage": 15.2
  }
}
```

### 4. Health Checks

**POST** `/api/v1/monitoring/health`

Submit health check data.

**Request Body:**
```json
{
  "status": "healthy",
  "checks": {
    "database": "healthy",
    "cache": "healthy",
    "external_api": "degraded"
  },
  "system_metrics": {
    "uptime": 86400,
    "memory_usage": 45.2,
    "disk_usage": 67.8
  }
}
```

## Query APIs

### 1. Get Logs

**GET** `/api/v1/monitoring/logs`

Retrieve logs with optional filtering.

**Query Parameters:**
- `service`: Filter by service name
- `level`: Filter by log level (INFO, WARNING, ERROR, CRITICAL)
- `start_time`: Start time (ISO format)
- `end_time`: End time (ISO format)
- `limit`: Maximum results (default: 100)

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2024-01-01T12:00:00Z",
      "service": "note-service",
      "level": "INFO",
      "message": "GET /notes - 200"
    }
  ],
  "count": 1,
  "filters": {
    "service": "note-service",
    "level": "INFO"
  }
}
```

### 2. Get Services

**GET** `/api/v1/monitoring/services`

Get list of registered services and their status.

**Response:**
```json
{
  "services": [
    {
      "service": "note-service",
      "status": "healthy",
      "last_seen": "2024-01-01T12:00:00Z",
      "version": "1.0.0"
    }
  ],
  "count": 1
}
```

## AI Insights APIs

### 1. Get Anomalies

**GET** `/api/v1/ai/anomalies`

Get detected anomalies.

**Query Parameters:**
- `hours`: Time window in hours (default: 24)
- `severity`: Filter by severity (low, medium, high, critical)

**Response:**
```json
{
  "anomalies": [
    {
      "id": "anomaly_20240101_120000",
      "type": "error_spike",
      "severity": "high",
      "description": "Unusual increase in error rate",
      "recommendation": "Investigate recent deployments"
    }
  ],
  "count": 1
}
```

### 2. Analyze Patterns

**POST** `/api/v1/ai/analyze-patterns`

Trigger pattern analysis on recent logs.

**Request Body:**
```json
{
  "hours": 24,
  "service": "note-service"
}
```

**Response:**
```json
{
  "patterns": {
    "temporal_patterns": {...},
    "service_patterns": {...},
    "error_patterns": {...}
  },
  "log_count": 1500
}
```

### 3. Summarize Logs

**POST** `/api/v1/ai/summarize-logs`

Generate AI summary of logs.

**Request Body:**
```json
{
  "hours": 24,
  "service": "note-service",
  "type": "error_focus"
}
```

**Response:**
```json
{
  "summary": "System experienced 12 errors in the last 24 hours...",
  "critical_errors": [...],
  "recommendations": [...]
}
```

### 4. Dashboard Insights

**GET** `/api/v1/ai/insights/dashboard`

Get AI insights for dashboard display.

**Response:**
```json
{
  "overview": {
    "total_logs": 15000,
    "error_rate": 2.5,
    "active_services": 3,
    "system_health": "healthy"
  },
  "services": {...},
  "recommendations": [...]
}
```

## Dashboard APIs

### 1. Dashboard Data

**GET** `/dashboard/api/dashboard-data`

Get real-time dashboard data.

**Response:**
```json
{
  "overview": {
    "total_requests": 1500,
    "error_count": 12,
    "error_rate": 0.8,
    "avg_response_time": 85.3
  },
  "services": {...},
  "recent_anomalies": [...]
}
```

## Error Responses

All APIs return appropriate HTTP status codes:

- `200`: Success
- `400`: Bad Request
- `401`: Unauthorized
- `404`: Not Found
- `500`: Internal Server Error

**Error Response Format:**
```json
{
  "detail": "Error message description"
}
```

## Rate Limiting

- Dashboard APIs: 100 requests per minute
- Data collection APIs: 1000 requests per minute
- Query APIs: 200 requests per minute

## WebSocket Support

Real-time updates are available via WebSocket connections:

- **Endpoint**: `/ws/dashboard`
- **Events**: `log_update`, `anomaly_detected`, `service_status_change`

---

# docs/DEPLOYMENT.md

# Deployment Guide

## Prerequisites

- Docker and Docker Compose
- Python 3.11+
- 4GB+ RAM
- 10GB+ disk space

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd centralized-monitoring
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### 2. Environment Configuration

Create environment files:

```bash
# monitoring-core/.env
ELASTICSEARCH_URL=http://localhost:9200
REDIS_URL=redis://localhost:6379
OLLAMA_URL=http://localhost:11434
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin

# microservices/note-service/.env
MONITORING_URL=http://localhost:8000
NOTE_SERVICE_SECRET=note_secret_key_2024
```

### 3. Start Infrastructure

```bash
cd infrastructure
docker-compose up -d
```

### 4. Verify Deployment

```bash
./scripts/deploy.sh
```

## Production Deployment

### 1. Security Configuration

**Change Default Credentials:**
```bash
export ADMIN_USERNAME=your_admin_user
export ADMIN_PASSWORD=your_secure_password
```

**Generate Service Secrets:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Configure TLS:**
```yaml
# docker-compose.yml
services:
  monitoring-core:
    environment:
      - SSL_CERT_PATH=/certs/cert.pem
      - SSL_KEY_PATH=/certs/key.pem
    volumes:
      - ./certs:/certs:ro
```

### 2. Scaling Configuration

**Elasticsearch Cluster:**
```yaml
elasticsearch:
  deploy:
    replicas: 3
  environment:
    - discovery.seed_hosts=es01,es02,es03
    - cluster.initial_master_nodes=es01,es02,es03
```

**Load Balancer:**
```yaml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf
```

### 3. Monitoring Resources

**Resource Limits:**
```yaml
services:
  monitoring-core:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

### 4. Backup Strategy

**Elasticsearch Snapshots:**
```bash
# Create snapshot repository
curl -X PUT "localhost:9200/_snapshot/backup_repo" -H 'Content-Type: application/json' -d'
{
  "type": "fs",
  "settings": {
    "location": "/backups"
  }
}'

# Create snapshot
curl -X PUT "localhost:9200/_snapshot/backup_repo/snapshot_1"
```

### 5. Health Checks

**Service Health Check:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

## Kubernetes Deployment

### 1. Helm Chart

```yaml
# values.yaml
monitoring:
  replicaCount: 3
  image:
    repository: monitoring-core
    tag: latest
  
elasticsearch:
  enabled: true
  replicas: 3
  
ollama:
  enabled: true
  models:
    - mistral
    - llama2
```

### 2. Resource Quotas

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: monitoring-quota
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
```

## Troubleshooting

### Common Issues

**1. Elasticsearch Connection Failed**
```bash
# Check Elasticsearch status
curl http://localhost:9200/_cluster/health

# Check logs
docker logs monitoring_elasticsearch
```

**2. Ollama Models Not Loading**
```bash
# Pull models manually
docker exec monitoring_ollama ollama pull mistral
docker exec monitoring_ollama ollama list
```

**3. High Memory Usage**
```bash
# Check container stats
docker stats

# Adjust memory limits
docker-compose down
# Edit docker-compose.yml memory limits
docker-compose up -d
```

### Log Analysis

**Application Logs:**
```bash
# Monitoring core logs
docker logs monitoring_core

# Service logs
docker logs note_service

# Infrastructure logs
docker logs monitoring_elasticsearch
docker logs monitoring_kibana
```

**System Metrics:**
```bash
# Check system resources
htop
df -h
free -h

# Check Docker resources
docker system df
docker system prune
```

---

# docs/ARCHITECTURE.md

# Architecture Documentation

## System Overview

The Centralized Monitoring System follows a microservices architecture with distributed data collection, centralized processing, and AI-powered analysis.

## Core Components

### 1. Monitoring Core
- **Purpose**: Central hub for data collection and analysis
- **Technology**: FastAPI, Python 3.11
- **Responsibilities**:
  - Service registration
  - Log aggregation
  - Metrics processing
  - AI analysis orchestration
  - Dashboard serving

### 2. Data Storage Layer
- **Elasticsearch**: Primary data store for logs and metrics
- **Redis**: Caching and session storage
- **Index Strategy**: Time-based indices (daily rotation)

### 3. AI Analysis Engine
- **Ollama Integration**: Local LLM processing
- **Models**: Mistral 7B, LLaMA 2
- **Capabilities**:
  - Anomaly detection
  - Pattern recognition
  - Predictive insights
  - Log summarization

### 4. Monitoring SDK
- **Purpose**: Standardized monitoring for microservices
- **Components**:
  - Middleware for automatic instrumentation
  - Client library for manual logging
  - Health check framework

## Data Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Microservice│───▶│ Monitoring  │───▶│ Elasticsearch│
│             │    │ Core        │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
                         │                    │
                         ▼                    ▼
                   ┌─────────────┐    ┌─────────────┐
                   │ AI Engine   │    │ Kibana      │
                   │ (Ollama)    │    │ Dashboard   │
                   └─────────────┘    └─────────────┘
                         │
                         ▼
                   ┌─────────────┐
                   │ Insights &  │
                   │ Alerts      │
                   └─────────────┘
```

## Security Architecture

### 1. Authentication Layers
- **Admin Access**: HTTP Basic Authentication
- **Service Authentication**: Secret key validation
- **API Security**: Request signing and validation

### 2. Secret Management
- **Service Secrets**: Unique keys per service
- **Rotation Strategy**: Automated secret rotation
- **Storage**: Environment variables and secure vault

### 3. Network Security
- **Internal Communication**: Service-to-service encryption
- **External Access**: TLS termination at load balancer
- **API Rate Limiting**: Per-service rate limits

## Scalability Design

### 1. Horizontal Scaling
- **Monitoring Core**: Stateless, can run multiple instances
- **Elasticsearch**: Cluster with multiple nodes
- **Microservices**: Independent scaling per service

### 2. Data Partitioning
- **Time-based Indices**: Daily log indices for efficient querying
- **Service-based Sharding**: Separate indices per service type
- **Retention Policies**: Automated data lifecycle management

### 3. Performance Optimization
- **Async Processing**: Non-blocking data ingestion
- **Batch Operations**: Bulk Elasticsearch operations
- **Caching Strategy**: Redis for frequently accessed data

## AI Architecture

### 1. Model Management
- **Local Deployment**: Ollama for privacy and control
- **Model Selection**: Dynamic model selection based on task
- **Resource Management**: GPU scheduling and memory management

### 2. Analysis Pipeline
```
Raw Logs → Preprocessing → Feature Extraction → Model Inference → Results Storage
```

### 3. Feedback Loop
- **Continuous Learning**: Model performance monitoring
- **Human Feedback**: Admin validation of AI insights
- **Model Updates**: Periodic retraining with new data

## Integration Patterns

### 1. Service Registration
```python
# Automatic registration on startup
async def startup():
    await monitoring_client.register_service({
        "name": "my-service",
        "url": "http://localhost:8001",
        "secret": "my-secret-key"
    })
```

### 2. Middleware Integration
```python
# Add monitoring to any FastAPI service
app.add_middleware(
    MonitoringMiddleware,
    monitoring_url="http://monitoring:8000",
    service_name="my-service",
    secret_key="my-secret-key"
)
```

### 3. Custom Metrics
```python
# Send custom business metrics
await monitoring_client.send_metrics({
    "user_registrations": 45,
    "order_total": 12500.00,
    "conversion_rate": 3.2
})
```

## Deployment Architecture

### 1. Container Strategy
- **Base Images**: Python 3.11 slim images
- **Multi-stage Builds**: Optimized container sizes
- **Health Checks**: Built-in health monitoring

### 2. Service Discovery
- **DNS-based**: Service resolution via container names
- **Health-aware**: