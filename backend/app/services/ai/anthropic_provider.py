import json
import logging
from typing import Any
import requests

from app.services.ai.base import AIChatResponse, AIProvider, ToolCall
from app.settings import settings

logger = logging.getLogger("jarvis.anthropic")


class AnthropicProvider(AIProvider):
    name = "anthropic"
    URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.anthropic_model or "claude-3-5-sonnet-20241022"

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> AIChatResponse:
        if not self.is_available():
            raise RuntimeError("Anthropic API key is not configured.")

        system_prompt = ""
        anthropic_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_prompt += f"{content}\n\n"
            elif role in ("user", "assistant"):
                anthropic_messages.append({
                    "role": role,
                    "content": content,
                })

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_prompt.strip():
            payload["system"] = system_prompt.strip()

        if tools:
            anthropic_tools = []
            for t in tools:
                fn = t.get("function", {})
                anthropic_tools.append({
                    "name": fn.get("name"),
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
                })
            if anthropic_tools:
                payload["tools"] = anthropic_tools

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        resp = requests.post(self.URL, headers=headers, json=payload, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Anthropic API error ({resp.status_code}): {resp.text}")

        data = resp.json()
        content_blocks = data.get("content", [])

        text_pieces = []
        tool_calls_extracted = []

        for block in content_blocks:
            if block.get("type") == "text":
                text_pieces.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls_extracted.append(ToolCall(
                    id=block.get("id", "call_anthropic"),
                    name=block.get("name", ""),
                    arguments=block.get("input", {}),
                ))

        return AIChatResponse(
            content="".join(text_pieces).strip(),
            tool_calls=tool_calls_extracted,
            raw_response=data,
            model=self.model,
            provider=self.name,
        )
