# microservices/note-service/app/config/settings.py
import os
from pydantic_settings import BaseSettings




class Settings(BaseSettings):
    # Service configuration
    PORT: int = int(os.getenv("PORT", "8001"))
    HOST: str = "0.0.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Monitoring configuration
    MONITORING_URL: str = os.getenv("MONITORING_URL", "http://localhost:8000")
    NOTE_SERVICE_SECRET: str = os.getenv("NOTE_SERVICE_SECRET", "")
    MONITORING_ADMIN_USERNAME: str = os.getenv("MONITORING_ADMIN_USERNAME", "")
    MONITORING_ADMIN_PASSWORD: str = os.getenv("MONITORING_ADMIN_PASSWORD", "")

    # Database configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./notes.db")

    # Service information
    SERVICE_NAME: str = "note-service"
    SERVICE_VERSION: str = "1.0.0"

    # Performance settings
    REQUEST_TIMEOUT: int = 30
    MAX_CONNECTIONS: int = 100
    ENVIRONMENT: str = "development"
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()