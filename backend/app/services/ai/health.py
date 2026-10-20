"""
JARVIS 2.0 — Provider Health Abstraction.

Tracks real-time status, latency, and error classifications for each AI provider.
This ensures the HUD and orchestrator report truthful provider state.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("jarvis.provider_health")


class ProviderStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"        # Transient errors (rate limit, timeout)
    UNAVAILABLE = "UNAVAILABLE"  # Not configured / missing API key
    FAILED = "FAILED"            # Hard failure (auth error, bad request)
    UNKNOWN = "UNKNOWN"          # Not yet tested


class ErrorCategory(str, Enum):
    AUTHENTICATION = "authentication"   # 401/403 — do NOT retry
    RATE_LIMIT = "rate_limit"           # 429 — retry with backoff
    TIMEOUT = "timeout"                 # Network/request timeout — retry
    NETWORK = "network"                 # Connection error — retry
    MODEL_UNAVAILABLE = "model_unavailable"  # 404 model — switch model
    INVALID_REQUEST = "invalid_request" # 400 — do NOT retry same request
    SERVER_ERROR = "server_error"       # 5xx — retry
    QUOTA_EXHAUSTED = "quota_exhausted" # Daily/monthly quota — do NOT retry
    UNKNOWN = "unknown"


@dataclass
class ProviderHealthRecord:
    """Live health state for a single AI provider."""
    provider_name: str
    status: ProviderStatus = ProviderStatus.UNKNOWN
    configured: bool = False
    last_success_ts: float = 0.0
    last_failure_ts: float = 0.0
    last_latency_ms: float = 0.0
    error_category: ErrorCategory | None = None
    error_message: str = ""
    consecutive_failures: int = 0
    request_count: int = 0
    success_count: int = 0

    def record_success(self, latency_ms: float) -> None:
        self.status = ProviderStatus.HEALTHY
        self.last_success_ts = time.time()
        self.last_latency_ms = latency_ms
        self.consecutive_failures = 0
        self.error_category = None
        self.error_message = ""
        self.request_count += 1
        self.success_count += 1

    def record_failure(self, category: ErrorCategory, message: str) -> None:
        self.last_failure_ts = time.time()
        self.error_category = category
        self.error_message = message
        self.consecutive_failures += 1
        self.request_count += 1
        # Non-retryable errors go straight to FAILED
        if category in (ErrorCategory.AUTHENTICATION, ErrorCategory.QUOTA_EXHAUSTED):
            self.status = ProviderStatus.FAILED
        else:
            self.status = ProviderStatus.DEGRADED

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "status": self.status.value,
            "configured": self.configured,
            "lastSuccessAgo": f"{int(time.time() - self.last_success_ts)}s ago" if self.last_success_ts else "never",
            "lastLatencyMs": round(self.last_latency_ms, 1),
            "consecutiveFailures": self.consecutive_failures,
            "errorCategory": self.error_category.value if self.error_category else None,
            "errorMessage": self.error_message,
            "requestCount": self.request_count,
            "successCount": self.success_count,
        }


def classify_http_error(status_code: int, response_text: str) -> ErrorCategory:
    """Classify an HTTP error response into a retryability category."""
    text_lower = response_text.lower()
    if status_code in (401, 403):
        return ErrorCategory.AUTHENTICATION
    if status_code == 429:
        if any(k in text_lower for k in ["tokens per day", "tpd", "daily quota", "monthly quota", "quota exceeded"]):
            return ErrorCategory.QUOTA_EXHAUSTED
        return ErrorCategory.RATE_LIMIT
    if status_code == 404:
        return ErrorCategory.MODEL_UNAVAILABLE
    if status_code == 400:
        return ErrorCategory.INVALID_REQUEST
    if status_code >= 500:
        return ErrorCategory.SERVER_ERROR
    return ErrorCategory.UNKNOWN


# Singleton health registry — lightweight in-process state store
class _ProviderHealthRegistry:
    def __init__(self) -> None:
        self._records: dict[str, ProviderHealthRecord] = {}

    def get(self, provider_name: str) -> ProviderHealthRecord:
        if provider_name not in self._records:
            self._records[provider_name] = ProviderHealthRecord(provider_name=provider_name)
        return self._records[provider_name]

    def all_records(self) -> list[ProviderHealthRecord]:
        return list(self._records.values())

    def summary(self) -> dict[str, Any]:
        return {name: rec.to_dict() for name, rec in self._records.items()}


provider_health_registry = _ProviderHealthRegistry()
