# scripts/create_structure.sh
#!/bin/bash

echo "📁 Creating complete project structure..."

# Create main directories
mkdir -p centralized-monitoring/{monitoring-core,microservices,shared,infrastructure,docs,scripts}

# Monitoring core structure
mkdir -p centralized-monitoring/monitoring-core/app/{auth,middleware,ai,storage,dashboard,api,config}
mkdir -p centralized-monitoring/monitoring-core/app/dashboard/{templates,static/{css,js}}

# Note service structure
mkdir -p centralized-monitoring/microservices/note-service/app/{models,routes,middleware,config}

# Shared components
mkdir -p centralized-monitoring/shared/{monitoring_sdk,utils}

# Infrastructure
mkdir -p centralized-monitoring/infrastructure/{elasticsearch/config,kibana/config,ollama/models,nginx}

# Create empty __init__.py files
find centralized-monitoring -type d -name "app" -o -name "auth" -o -name "middleware" -o -name "ai" -o -name "storage" -o -name "dashboard" -o -name "api" -o -name "config" -o -name "models" -o -name "routes" -o -name "monitoring_sdk" -o -name "utils" -o -name "shared" | xargs -I {} touch {}/__init__.py

echo "✅ Project structure created successfully!"

# Environment template files

# .env.example
# Monitoring Core Configuration
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
DEBUG=false

# External Services
ELASTICSEARCH_URL=http://localhost:9200
REDIS_URL=redis://localhost:6379
OLLAMA_URL=http://localhost:11434

# Security
MONITORING_SECRET_KEY=monitoring_master_key_2024
JWT_SECRET=jwt_secret_key_2024

# Service Secrets
NOTE_SERVICE_SECRET=note_secret_key_2024
USER_SERVICE_SECRET=user_secret_key_2024
ORDER_SERVICE_SECRET=order_secret_key_2024

# AI Configuration
OLLAMA_MODELS=mistral,llama2
AI_ANALYSIS_INTERVAL=300

# Performance Settings
LOG_RETENTION_DAYS=30
METRICS_RETENTION_DAYS=90
MAX_CONCURRENT_AI_REQUESTS=5

# microservices/note-service/.env.example
PORT=8001
MONITORING_URL=http://localhost:8000
NOTE_SERVICE_SECRET=note_secret_key_2024
DATABASE_URL=sqlite:///./notes.db

# Development vs Production
ENVIRONMENT=development

# Additional monitoring configuration file
# monitoring-core/app/config/monitoring.yaml
monitoring:
  collection:
    batch_size: 100
    flush_interval: 5
    max_queue_size: 10000

  retention:
    logs: 30d
    metrics: 90d
    traces: 7d
    anomalies: 365d

  ai:
    models:
      - name: mistral
        use_for: [anomaly_detection, summarization]
        temperature: 0.1
      - name: llama2
        use_for: [pattern_analysis, predictions]
        temperature: 0.1

    analysis:
      anomaly_detection_interval: 300  # 5 minutes
      pattern_analysis_interval: 3600  # 1 hour
      prediction_interval: 86400       # 24 hours

  alerts:
    channels:
      - type: webhook
        url: http://localhost:9000/alerts
      - type: email
        smtp_server: localhost:587

    rules:
      - name: high_error_rate
        condition: error_rate > 5%
        window: 5m
        severity: warning

      - name: critical_error_rate
        condition: error_rate > 15%
        window: 5m
        severity: critical

  services:
    discovery:
      enabled: true
      refresh_interval: 30s

    health_checks:
      enabled: true
      interval: 30s
      timeout: 10s

# Complete package.json for frontend dependencies (if needed)
# monitoring-core/app/dashboard/static/package.json
{
  "name": "monitoring-dashboard",
  "version": "1.0.0",
  "description": "Frontend assets for monitoring dashboard",
  "dependencies": {
    "bootstrap": "^5.3.0",
    "chart.js": "^4.4.0",
    "@fortawesome/fontawesome-free": "^6.4.0"
  },
  "devDependencies": {
    "sass": "^1.69.0",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.31"
  },
  "scripts": {
    "build-css": "sass static/scss/main.scss static/css/dashboard.css",
    "watch-css": "sass --watch static/scss/main.scss static/css/dashboard.css"
  }
}

# VS Code settings for development
# .vscode/settings.json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/venv": true,
        "**/.env": true
    },
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}

# .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Monitoring Core",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/monitoring-core/app/main.py",
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}/monitoring-core",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/monitoring-core"
            }
        },
        {
            "name": "Note Service",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/microservices/note-service/app/main.py",
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}/microservices/note-service",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/microservices/note-service"
            }
        }
    ]
}

# Git configuration
# .gitignore
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Virtual environments
venv/
env/
ENV/

# Environment variables
.env
.env.local
.env.production

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs
logs/
*.log

# Database
*.db
*.sqlite3

# Docker
.dockerignore

# Node modules (if using npm for frontend)
node_modules/

# Coverage reports
htmlcov/
.coverage

# pytest
.pytest_cache/

# Distribution / packaging
build/
dist/
*.egg-info/

# OS
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.temp