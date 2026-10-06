import json
import logging
from typing import Any
import requests

from app.services.ai.base import AIChatResponse, AIProvider, ToolCall
from app.settings import settings

logger = logging.getLogger("jarvis.groq")


class GroqProvider(AIProvider):
    name = "groq"
    URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_chat_model or "openai/gpt-oss-120b"
        self.fallback_model = settings.groq_fallback_model or "openai/gpt-oss-20b"

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
            raise RuntimeError("Groq API key is not configured.")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(self.URL, headers=headers, json=payload, timeout=25)
        except Exception as exc:
            if self.model != self.fallback_model:
                payload["model"] = self.fallback_model
                resp = requests.post(self.URL, headers=headers, json=payload, timeout=25)
            else:
                raise RuntimeError(f"Groq network failure: {exc}") from exc

        if resp.status_code != 200:
            if self.model != self.fallback_model:
                payload["model"] = self.fallback_model
                resp = requests.post(self.URL, headers=headers, json=payload, timeout=25)
            if resp.status_code != 200:
                raise RuntimeError(f"Groq API error ({resp.status_code}): {resp.text}")

        data = resp.json()
        choice = data["choices"][0]
        msg = choice.get("message", {})
        content = msg.get("content") or ""

        tool_calls_extracted = []
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                fn = tc.get("function", {})
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                tool_calls_extracted.append(ToolCall(
                    id=tc.get("id", "call_groq"),
                    name=fn.get("name", ""),
                    arguments=args,
                ))

        return AIChatResponse(
            content=content,
            tool_calls=tool_calls_extracted,
            raw_response=data,
            model=payload["model"],
            provider=self.name,
        )
