from dataclasses import dataclass, field
from typing import Any, AsyncGenerator


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class AIChatResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw_response: dict[str, Any] = field(default_factory=dict)
    model: str = ""
    provider: str = ""


class AIProvider:
    """Base abstract interface for all AI model providers."""

    name: str = "base"

    def is_available(self) -> bool:
        """Check if this provider is configured and available."""
        raise NotImplementedError

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> AIChatResponse:
        """Execute a synchronous or blocking chat completion."""
        raise NotImplementedError
