"""
Centralized Error Architecture, Consistent Error Identifiers, and Exception Handlers for JARVIS.

Ensures:
1. Every API error returns consistent HTTP status codes and structured payloads.
2. 100% backward compatibility: Returns both standard 'detail' string and structured 'error' object.
3. Every error response includes the active Request ID for end-to-end tracing.
4. Internal server error tracebacks and sensitive credentials are never leaked to clients.
"""

from enum import Enum
import logging
import traceback
from typing import Any, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("jarvis.errors")


class ErrorCode(str, Enum):
    # Authentication & Permissions
    UNAUTHENTICATED = "UNAUTHENTICATED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    CONFIRMATION_INVALID = "CONFIRMATION_INVALID"
    EMERGENCY_STOP_ACTIVE = "EMERGENCY_STOP_ACTIVE"

    # Validation & Requests
    VALIDATION_ERROR = "VALIDATION_ERROR"
    BAD_REQUEST = "BAD_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    REQUEST_TIMEOUT = "REQUEST_TIMEOUT"
    REQUEST_CANCELLED = "REQUEST_CANCELLED"

    # AI & Providers
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_RATE_LIMIT = "PROVIDER_RATE_LIMIT"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_AUTH_ERROR = "PROVIDER_AUTH_ERROR"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"

    # Tools & Execution
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    SANDBOX_ERROR = "SANDBOX_ERROR"
    SSRF_BLOCKED = "SSRF_BLOCKED"

    # System & Database
    DATABASE_ERROR = "DATABASE_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


class JARVISError(Exception):
    """Base application exception for JARVIS backend."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class ResourceNotFoundError(JARVISError):
    def __init__(self, resource_type: str, identifier: str) -> None:
        super().__init__(
            message=f"{resource_type} '{identifier}' not found.",
            error_code=ErrorCode.NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource_type": resource_type, "identifier": identifier},
        )


class PermissionDeniedError(JARVISError):
    def __init__(self, message: str = "Operation not permitted in current permission mode.") -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.PERMISSION_DENIED,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ToolExecutionTimeoutError(JARVISError):
    def __init__(self, tool_name: str, timeout_seconds: float) -> None:
        super().__init__(
            message=f"Execution of tool '{tool_name}' timed out after {timeout_seconds:.1f}s.",
            error_code=ErrorCode.TOOL_TIMEOUT,
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            details={"tool_name": tool_name, "timeout_seconds": timeout_seconds},
        )


def _build_error_payload(
    message: str,
    error_code: str,
    request_id: str,
    status_code: int,
    details: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Constructs a backward-compatible and structured error JSON payload.
    Provides 'detail' for standard FastAPI/Swagger clients, and 'error' dict for rich UI.
    """
    return {
        "ok": False,
        "detail": message,  # Backward compatibility for existing frontend & unit tests
        "error": {
            "code": error_code,
            "message": message,
            "statusCode": status_code,
            "requestId": request_id,
            "details": details or {},
        },
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Register centralized FastAPI exception handlers."""

    @app.exception_handler(JARVISError)
    async def jarvis_error_handler(request: Request, exc: JARVISError) -> JSONResponse:
        req_id = getattr(request.state, "request_id", "unknown_req")
        logger.warning(
            "[%s] JARVISError: %s (code=%s, status=%d)",
            req_id,
            exc.message,
            exc.error_code.value,
            exc.status_code,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_build_error_payload(
                message=exc.message,
                error_code=exc.error_code.value,
                request_id=req_id,
                status_code=exc.status_code,
                details=exc.details,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        req_id = getattr(request.state, "request_id", "unknown_req")
        error_code = ErrorCode.BAD_REQUEST.value
        if exc.status_code == 401:
            error_code = ErrorCode.UNAUTHENTICATED.value
        elif exc.status_code == 403:
            error_code = ErrorCode.PERMISSION_DENIED.value
        elif exc.status_code == 404:
            error_code = ErrorCode.NOT_FOUND.value
        elif exc.status_code == 408 or exc.status_code == 504:
            error_code = ErrorCode.REQUEST_TIMEOUT.value
        elif exc.status_code == 422:
            error_code = ErrorCode.VALIDATION_ERROR.value
        elif exc.status_code >= 500:
            error_code = ErrorCode.INTERNAL_SERVER_ERROR.value

        detail_str = str(exc.detail) if exc.detail else "An HTTP error occurred."
        return JSONResponse(
            status_code=exc.status_code,
            content=_build_error_payload(
                message=detail_str,
                error_code=error_code,
                request_id=req_id,
                status_code=exc.status_code,
            ),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        req_id = getattr(request.state, "request_id", "unknown_req")
        errors = exc.errors()
        messages = []
        for err in errors:
            loc = " -> ".join(str(l) for l in err.get("loc", []))
            messages.append(f"{loc}: {err.get('msg', 'invalid value')}")
        summary_msg = "; ".join(messages) if messages else "Invalid request parameters."

        logger.info("[%s] Validation error: %s", req_id, summary_msg)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_build_error_payload(
                message=summary_msg,
                error_code=ErrorCode.VALIDATION_ERROR.value,
                request_id=req_id,
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                details={"errors": errors},
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        req_id = getattr(request.state, "request_id", "unknown_req")
        logger.error(
            "[%s] Unhandled server exception: %s\n%s",
            req_id,
            exc,
            traceback.format_exc(),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_build_error_payload(
                message="An internal server error occurred. Please consult system logs.",
                error_code=ErrorCode.INTERNAL_SERVER_ERROR.value,
                request_id=req_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )
