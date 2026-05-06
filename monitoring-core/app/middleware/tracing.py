# monitoring-core/app/middleware/tracing.py
import uuid
import time
import logging
from datetime import datetime
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TracingMiddleware(BaseHTTPMiddleware):
    """Distributed tracing middleware"""

    def __init__(self, app, service_name: str = "monitoring-core"):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next):
        # Extract or generate trace ID
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        parent_span_id = request.headers.get("X-Parent-Span-ID")

        # Create span
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            service_name=self.service_name,
            operation_name=f"{request.method} {request.url.path}",
            start_time=time.time()
        )

        # Add trace info to request
        request.state.trace_id = trace_id
        request.state.span_id = span_id
        request.state.span = span

        try:
            # Add tracing headers to response
            response = await call_next(request)

            # Finish span
            span.finish(
                status_code=response.status_code,
                tags={
                    "http.method": request.method,
                    "http.url": str(request.url),
                    "http.status_code": response.status_code,
                    "user_agent": request.headers.get("user-agent", "unknown")
                }
            )

            # Add trace headers to response
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Span-ID"] = span_id

            # Log trace information
            logger.info(
                f"Trace completed: {trace_id}",
                extra={
                    "trace_id": trace_id,
                    "span_id": span_id,
                    "parent_span_id": parent_span_id,
                    "service": self.service_name,
                    "operation": span.operation_name,
                    "duration_ms": span.duration_ms,
                    "status_code": response.status_code
                }
            )

            return response

        except Exception as e:
            # Finish span with error
            span.finish(
                error=True,
                error_message=str(e),
                tags={
                    "http.method": request.method,
                    "http.url": str(request.url),
                    "error": True,
                    "error.type": type(e).__name__
                }
            )

            logger.error(
                f"Trace failed: {trace_id}",
                extra={
                    "trace_id": trace_id,
                    "span_id": span_id,
                    "service": self.service_name,
                    "operation": span.operation_name,
                    "duration_ms": span.duration_ms,
                    "error": str(e)
                }
            )

            raise e


class Span:
    """Represents a single span in a distributed trace"""

    def __init__(self,
                 trace_id: str,
                 span_id: str,
                 service_name: str,
                 operation_name: str,
                 start_time: float,
                 parent_span_id: Optional[str] = None):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.service_name = service_name
        self.operation_name = operation_name
        self.start_time = start_time
        self.end_time: Optional[float] = None
        self.duration_ms: Optional[float] = None
        self.tags: Dict[str, Any] = {}
        self.error = False
        self.error_message: Optional[str] = None

    def finish(self,
               status_code: Optional[int] = None,
               error: bool = False,
               error_message: Optional[str] = None,
               tags: Optional[Dict[str, Any]] = None):
        """Finish the span"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.error = error
        self.error_message = error_message

        if tags:
            self.tags.update(tags)

        if status_code:
            self.tags["http.status_code"] = status_code

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "service_name": self.service_name,
            "operation_name": self.operation_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "tags": self.tags,
            "error": self.error,
            "error_message": self.error_message,
            "timestamp": datetime.utcnow().isoformat()
        }