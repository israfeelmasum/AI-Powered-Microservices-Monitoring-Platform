import os
from pydantic_settings import BaseSettings
from typing import Dict


class Settings(BaseSettings):
    # Basic configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # Authentication — set via environment variables, no defaults
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str
    SECRET_KEY: str

    # External services
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_USERNAME: str = "elastic"
    ELASTICSEARCH_PASSWORD: str = ""

    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PASSWORD: str = ""
    OLLAMA_URL: str = "http://localhost:11434"

    # Service secrets for authentication — set via environment variables
    NOTE_SERVICE_SECRET: str = ""
    USER_SERVICE_SECRET: str = ""
    ORDER_SERVICE_SECRET: str = ""
    PAYMENT_SERVICE_SECRET: str = ""
    INVENTORY_SERVICE_SECRET: str = ""

    # Monitoring configuration
    LOG_RETENTION_DAYS: int = 30
    METRICS_RETENTION_DAYS: int = 90
    AI_ANALYSIS_INTERVAL_MINUTES: int = 5

    # AI Configuration
    OLLAMA_MODELS: list = ["mistral", "llama2"]
    AI_TEMPERATURE: float = 0.1
    MAX_AI_CONTEXT_LENGTH: int = 4000

    # Performance settings
    MAX_CONCURRENT_AI_REQUESTS: int = 5
    REQUEST_TIMEOUT_SECONDS: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
