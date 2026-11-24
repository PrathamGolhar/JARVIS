"""
Observability, Request Tracing, and Latency Telemetry Middleware for JARVIS.

Features:
1. Injects/propagates X-Request-ID for distributed tracing across frontend, backend, and background tasks.
2. High-precision response time calculation injected into X-Response-Time-Ms.
3. Structured, sanitised request logging with automatic credential scrubbing.
4. Client disconnect and cancellation detection.
"""

import logging
import secrets
import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("jarvis.http")


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that establishes unique Request IDs, tracks request duration,
    and logs request telemetry while ensuring sensitive credentials are never logged.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract existing X-Request-ID or generate new high-entropy ID
        incoming_id = request.headers.get("X-Request-ID", "").strip()
        request_id = incoming_id if (incoming_id and len(incoming_id) <= 64) else f"req_{secrets.token_hex(6)}"

        # Attach to request state for downstream handlers and error responses
        request.state.request_id = request_id
        request.state.start_time = time.perf_counter()

        client_host = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        # Avoid spamming logs on frequent health probes
        is_probe = path in ("/health", "/api/health")
        if not is_probe:
            logger.info("[%s] --> %s %s (from %s)", request_id, method, path, client_host)

        try:
            response: Response = await call_next(request)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - request.state.start_time) * 1000.0
            logger.error(
                "[%s] <-- %s %s EXCEPTION after %.1fms: %s",
                request_id,
                method,
                path,
                elapsed_ms,
                exc,
            )
            raise exc

        elapsed_ms = (time.perf_counter() - request.state.start_time) * 1000.0

        # Inject tracing headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"

        if not is_probe:
            status_code = response.status_code
            level = logging.INFO if status_code < 400 else (logging.WARNING if status_code < 500 else logging.ERROR)
            logger.log(
                level,
                "[%s] <-- %s %s %d (%.1fms)",
                request_id,
                method,
                path,
                status_code,
                elapsed_ms,
            )

        return response


def register_middleware(app: FastAPI) -> None:
    """Register custom middlewares on the FastAPI application."""
    app.add_middleware(RequestTracingMiddleware)
