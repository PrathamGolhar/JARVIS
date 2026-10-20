import json
import logging
import random
import time
from typing import Any
import requests

from app.endpoints import GROQ_CHAT_URL
from app.services.ai.base import AIChatResponse, AIProvider, ToolCall
from app.settings import settings

logger = logging.getLogger("jarvis.groq")

_GROQ_RETRY_DELAYS = [1.5]  # Single fast retry before attempting fallback


class GroqProvider(AIProvider):
    name = "groq"
    URL = GROQ_CHAT_URL

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_chat_model or "openai/gpt-oss-20b"
        self.fallback_model = settings.groq_fallback_model or "openai/gpt-oss-120b"

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

        resp = self._post_with_retry(headers, payload)

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

    def _post_with_retry(
        self,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> requests.Response:
        """
        POST to Groq with rapid retry on transient 429 rate limits.
        If a daily token limit (TPD) is encountered or the required wait exceeds 5s,
        immediately cascades to fallback models without wasting time.
        """
        models_to_try = [payload["model"]]
        if self.fallback_model and self.fallback_model != payload["model"]:
            models_to_try.append(self.fallback_model)

        last_error: str = ""
        for model in models_to_try:
            payload["model"] = model
            for attempt, delay in enumerate([0.0] + _GROQ_RETRY_DELAYS):
                if delay > 0:
                    jitter = random.uniform(0, 0.3)
                    sleep_time = delay + jitter
                    logger.warning(
                        "Groq rate limit hit on %s (attempt %d). Retrying in %.1fs.",
                        model, attempt, sleep_time,
                    )
                    time.sleep(sleep_time)

                try:
                    resp = requests.post(self.URL, headers=headers, json=payload, timeout=25)
                except requests.RequestException as exc:
                    last_error = f"Network failure: {exc}"
                    logger.debug("Groq network error (attempt %d): %s", attempt, exc)
                    continue

                if resp.status_code == 200:
                    return resp

                if resp.status_code == 429:
                    resp_text = resp.text.lower()
                    # Daily token quota exhaustion (TPD): immediate model switch, no retry delay
                    if "tokens per day" in resp_text or "tpd" in resp_text or "daily" in resp_text:
                        logger.warning("Groq daily token limit reached for %s. Immediately switching to fallback.", model)
                        last_error = f"Rate limit (TPD): {resp.text[:200]}"
                        break

                    # Extract server-suggested reset time (x-ratelimit-reset-tokens or retry-after)
                    reset_header = resp.headers.get("x-ratelimit-reset-tokens") or resp.headers.get("retry-after")
                    if reset_header:
                        try:
                            clean_str = reset_header.strip().rstrip("s")
                            server_wait = float(clean_str)
                            if server_wait <= 5.0:
                                logger.info("Groq rate limit token reset in %.2fs on %s; waiting...", server_wait, model)
                                time.sleep(server_wait + 0.2)
                                continue
                            else:
                                logger.info("Groq retry wait %.1fs too long for %s; switching model.", server_wait, model)
                                last_error = f"Rate limit wait too long ({server_wait}s)"
                                break
                        except (ValueError, TypeError):
                            pass

                    last_error = f"Rate limit (429): {resp.text[:200]}"
                    continue

                # Non-retryable error — switch model immediately
                last_error = f"Groq API error ({resp.status_code}): {resp.text[:300]}"
                logger.warning("Groq %s returned %d: switching model.", model, resp.status_code)
                break

        raise RuntimeError(f"Groq provider exhausted all retries and fallbacks. Last error: {last_error}")
