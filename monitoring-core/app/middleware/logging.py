import logging
import logging.config
import json
import sys
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add extra fields if present
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id
        if hasattr(record, 'service'):
            log_data['service'] = record.service
        if hasattr(record, 'endpoint'):
            log_data['endpoint'] = record.endpoint
        if hasattr(record, 'response_time'):
            log_data['response_time'] = record.response_time
        if hasattr(record, 'status_code'):
            log_data['status_code'] = record.status_code

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO"):
    """Setup structured logging configuration"""

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "()": StructuredFormatter
            },
            "simple": {
                "format": "%(asctime)s - %(levelname)s - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "structured",
                "stream": sys.stdout
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "structured",
                "filename": "logs/monitoring-core.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            }
        },
        "loggers": {
            "": {  # Root logger
                "level": log_level,
                "handlers": ["console", "file"],
                "propagate": False
            }
        }
    }

    logging.config.dictConfig(logging_config)


class StructuredLogger:
    """Structured logger wrapper"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def log(self, level: str, message: str, **kwargs):
        """Log with structured data"""
        extra = {k: v for k, v in kwargs.items() if k not in ['level', 'message']}
        getattr(self.logger, level.lower())(message, extra=extra)

    def info(self, message: str, **kwargs):
        self.log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs):
        self.log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs):
        self.log("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs):
        self.log("CRITICAL", message, **kwargs)
