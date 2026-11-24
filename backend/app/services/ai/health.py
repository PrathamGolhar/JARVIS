"""
JARVIS 2.0 — Provider Health & Circuit Breaker Abstraction.

Tracks real-time status, latency, error classifications, and circuit breaker states for each AI provider.
Prevents cascading timeouts and resource starvation by failing fast when external APIs degrade.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import logging
import time
from typing import Any

logger = logging.getLogger("jarvis.provider_health")


class ProviderStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"        # Transient errors (rate limit, timeout)
    UNAVAILABLE = "UNAVAILABLE"  # Not configured / missing API key
    FAILED = "FAILED"            # Hard failure (auth error, bad request)
    UNKNOWN = "UNKNOWN"          # Not yet tested


class CircuitState(str, Enum):
    CLOSED = "CLOSED"            # Normal operations: calls pass through
    OPEN = "OPEN"                # Tripped: fail fast without making outbound network requests
    HALF_OPEN = "HALF_OPEN"      # Testing: allow single probe call to test recovery


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
class CircuitBreaker:
    """
    Automated circuit breaker protecting the assistant from unresponsive AI providers.
    Transitions:
      CLOSED -> OPEN (after failure_threshold consecutive errors)
      OPEN -> HALF_OPEN (after cooldown_seconds)
      HALF_OPEN -> CLOSED (on probe success) or OPEN (on probe failure)
    """
    failure_threshold: int = 3
    cooldown_seconds: float = 30.0
    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    last_state_change: float = field(default_factory=time.time)

    def can_execute(self) -> bool:
        """Check if request is permitted to proceed to the provider."""
        now = time.time()
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if now - self.last_state_change >= self.cooldown_seconds:
                logger.info("Circuit breaker entering HALF_OPEN probe state after %.1fs cooldown", self.cooldown_seconds)
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            # In half-open state, allow 1 test call
            return True

        return True

    def record_success(self) -> None:
        """Record successful execution, resetting circuit to CLOSED."""
        if self.state != CircuitState.CLOSED:
            logger.info("Provider recovered! Circuit breaker transitioning from %s to CLOSED", self.state.value)
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.last_state_change = time.time()

    def record_failure(self, category: ErrorCategory) -> None:
        """Record an execution failure and trip circuit if threshold exceeded."""
        self.consecutive_failures += 1
        now = time.time()

        # Immediate trip on fatal authentication or quota errors
        if category in (ErrorCategory.AUTHENTICATION, ErrorCategory.QUOTA_EXHAUSTED):
            self.state = CircuitState.OPEN
            self.last_state_change = now
            logger.warning("Circuit breaker immediately tripped to OPEN on non-retryable error: %s", category.value)
            return

        if self.state == CircuitState.HALF_OPEN:
            # Probe failed — trip back to OPEN
            self.state = CircuitState.OPEN
            self.last_state_change = now
            logger.warning("Circuit breaker probe failed; resetting to OPEN")
            return

        if self.consecutive_failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.last_state_change = now
            logger.warning(
                "Circuit breaker tripped to OPEN after %d consecutive failures",
                self.consecutive_failures,
            )


@dataclass
class ProviderHealthRecord:
    """Live health state and operational telemetry for a single AI provider."""
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
    circuit_breaker: CircuitBreaker = field(default_factory=CircuitBreaker)

    def can_execute(self) -> bool:
        """Check if provider is available and circuit is not open."""
        return self.configured and self.circuit_breaker.can_execute()

    def record_success(self, latency_ms: float) -> None:
        self.status = ProviderStatus.HEALTHY
        self.last_success_ts = time.time()
        self.last_latency_ms = latency_ms
        self.consecutive_failures = 0
        self.error_category = None
        self.error_message = ""
        self.request_count += 1
        self.success_count += 1
        self.circuit_breaker.record_success()

    def record_failure(self, category: ErrorCategory, message: str) -> None:
        self.last_failure_ts = time.time()
        self.error_category = category
        self.error_message = message
        self.consecutive_failures += 1
        self.request_count += 1
        self.circuit_breaker.record_failure(category)

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
            "circuitState": self.circuit_breaker.state.value,
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
