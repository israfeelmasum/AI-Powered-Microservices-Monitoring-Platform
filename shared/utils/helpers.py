# shared/utils/helpers.py
import hashlib
import secrets
import time
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
import psutil


def generate_correlation_id(service_name: str) -> str:
    """Generate a unique correlation ID"""
    timestamp = int(time.time() * 1000)
    random_part = secrets.token_hex(4)
    return f"{service_name}_{timestamp}_{random_part}"


def hash_secret(secret: str) -> str:
    """Hash a secret key using SHA-256"""
    return hashlib.sha256(secret.encode()).hexdigest()


def get_utc_timestamp() -> str:
    """Get current UTC timestamp in ISO format"""
    return datetime.now(timezone.utc).isoformat()


def sanitize_log_message(message: str, max_length: int = 1000) -> str:
    """Sanitize and truncate log messages"""
    if not isinstance(message, str):
        message = str(message)

    # Remove sensitive information patterns
    sanitized = re.sub(r'(password|token|secret|key)\s*[:=]\s*[^\s]+', r'\1=***', message, flags=re.IGNORECASE)
    sanitized = re.sub(r'Bearer\s+[^\s]+', 'Bearer ***', sanitized, flags=re.IGNORECASE)

    # Truncate if too long
    if len(sanitized) > max_length:
        return sanitized[:max_length] + "..."
    return sanitized


def format_bytes(bytes_value: int) -> str:
    """Format bytes into human readable format"""
    if bytes_value == 0:
        return "0 B"

    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def calculate_percentile(values: List[float], percentile: float) -> float:
    """Calculate percentile of a list of values"""
    if not values:
        return 0.0

    sorted_values = sorted(values)
    index = (percentile / 100.0) * (len(sorted_values) - 1)

    if index.is_integer():
        return sorted_values[int(index)]
    else:
        lower = sorted_values[int(index)]
        upper = sorted_values[int(index) + 1]
        return lower + (upper - lower) * (index - int(index))


def get_system_info() -> Dict[str, Any]:
    """Get comprehensive system information"""
    try:
        process = psutil.Process()

        return {
            "cpu": {
                "percent": round(process.cpu_percent(), 2),
                "count": psutil.cpu_count(),
                "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            },
            "memory": {
                "rss_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "vms_mb": round(process.memory_info().vms / 1024 / 1024, 2),
                "percent": round(process.memory_percent(), 2),
                "system_total_gb": round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 2),
                "system_available_gb": round(psutil.virtual_memory().available / 1024 / 1024 / 1024, 2)
            },
            "disk": {
                "usage_percent": round(psutil.disk_usage('/').percent, 2),
                "total_gb": round(psutil.disk_usage('/').total / 1024 / 1024 / 1024, 2),
                "free_gb": round(psutil.disk_usage('/').free / 1024 / 1024 / 1024, 2)
            },
            "network": {
                "connections": len(process.connections()) if hasattr(process, 'connections') else 0
            },
            "process": {
                "pid": process.pid,
                "threads": process.num_threads(),
                "open_files": len(process.open_files()) if hasattr(process, 'open_files') else 0,
                "create_time": process.create_time()
            }
        }
    except Exception as e:
        return {"error": str(e)}


def validate_json(data: str) -> tuple[bool, Optional[Dict]]:
    """Validate JSON string and return parsed data"""
    try:
        parsed = json.loads(data)
        return True, parsed
    except json.JSONDecodeError as e:
        return False, {"error": str(e)}


def safe_dict_get(data: Dict, key_path: str, default: Any = None) -> Any:
    """Safely get nested dictionary values using dot notation"""
    keys = key_path.split('.')
    current = data

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def flatten_dict(data: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    """Flatten nested dictionary"""
    items = []

    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key

        if isinstance(value, dict):
            items.extend(flatten_dict(value, new_key, sep=sep).items())
        else:
            items.append((new_key, value))

    return dict(items)


def calculate_error_rate(total_requests: int, error_count: int) -> float:
    """Calculate error rate percentage"""
    if total_requests == 0:
        return 0.0
    return round((error_count / total_requests) * 100, 2)


def calculate_throughput(request_count: int, time_window_seconds: int) -> float:
    """Calculate requests per second"""
    if time_window_seconds == 0:
        return 0.0
    return round(request_count / time_window_seconds, 2)


def format_duration(milliseconds: float) -> str:
    """Format duration in milliseconds to human readable format"""
    if milliseconds < 1000:
        return f"{milliseconds:.0f}ms"
    elif milliseconds < 60000:
        return f"{milliseconds / 1000:.1f}s"
    elif milliseconds < 3600000:
        return f"{milliseconds / 60000:.1f}m"
    else:
        return f"{milliseconds / 3600000:.1f}h"


def extract_error_info(exception: Exception) -> Dict[str, Any]:
    """Extract comprehensive error information from exception"""
    return {
        "type": type(exception).__name__,
        "message": str(exception),
        "module": getattr(exception, '__module__', None),
        "args": exception.args,
        "traceback": None  # Will be filled by caller if needed
    }


def generate_service_secret(service_name: str) -> str:
    """Generate a secure secret key for a service"""
    timestamp = int(time.time())
    random_part = secrets.token_urlsafe(32)
    return f"{service_name}_{timestamp}_{random_part}"


def is_valid_service_name(name: str) -> bool:
    """Validate service name format"""
    pattern = r'^[a-z][a-z0-9-]*[a-z0-9]$'
    return bool(re.match(pattern, name)) and len(name) <= 50


def normalize_metric_name(name: str) -> str:
    """Normalize metric name to standard format"""
    # Convert to lowercase and replace invalid characters
    normalized = re.sub(r'[^a-z0-9_]', '_', name.lower())
    # Remove multiple underscores
    normalized = re.sub(r'_+', '_', normalized)
    # Remove leading/trailing underscores
    return normalized.strip('_')


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks of specified size"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying functions on failure"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff

            raise last_exception

        return wrapper

    return decorator


def get_health_status(metrics: Dict[str, float]) -> str:
    """Determine health status based on metrics"""
    error_rate = metrics.get('error_rate', 0)
    cpu_usage = metrics.get('cpu_usage', 0)
    memory_usage = metrics.get('memory_usage', 0)
    response_time = metrics.get('avg_response_time', 0)

    # Critical conditions
    if error_rate > 20 or cpu_usage > 90 or memory_usage > 95 or response_time > 5000:
        return 'critical'

    # Warning conditions
    elif error_rate > 10 or cpu_usage > 75 or memory_usage > 85 or response_time > 2000:
        return 'warning'

    # Degraded conditions
    elif error_rate > 5 or cpu_usage > 60 or memory_usage > 70 or response_time > 1000:
        return 'degraded'

    # Healthy
    else:
        return 'healthy'