import json
import logging
import secrets
from typing import Any
import requests

from app.services.ai.base import AIChatResponse, AIProvider, ToolCall
from app.settings import settings

logger = logging.getLogger("jarvis.gemini")


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.google_api_key
        self.model = model or settings.gemini_model or "gemini-2.5-flash"

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
            raise RuntimeError("Google Gemini API key is not configured.")

        # Convert standard OpenAI/Chat messages into Gemini generateContent format
        system_instruction = ""
        contents = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_instruction += (content + "\n\n")
            elif role == "assistant":
                # Check for tool calls or text
                parts = []
                if content:
                    parts.append({"text": content})
                tool_calls = msg.get("tool_calls")
                if tool_calls:
                    for tc in tool_calls:
                        fn = tc.get("function", {})
                        args = fn.get("arguments", {})
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except Exception:
                                args = {}
                        parts.append({
                            "functionCall": {
                                "name": fn.get("name", ""),
                                "args": args,
                            }
                        })
                contents.append({"role": "model", "parts": parts or [{"text": ""}]})
            elif role == "tool":
                tool_name = msg.get("name", "tool")
                raw_res = content
                try:
                    res_dict = json.loads(raw_res) if isinstance(raw_res, str) else raw_res
                except Exception:
                    res_dict = {"output": raw_res}
                contents.append({
                    "role": "function",
                    "parts": [{
                        "functionResponse": {
                            "name": tool_name,
                            "response": {"name": tool_name, "content": res_dict},
                        }
                    }]
                })
            else:  # user
                contents.append({"role": "user", "parts": [{"text": str(content)}]})

        # Format tools for Gemini API
        gemini_tools = None
        if tools:
            function_declarations = []
            for t in tools:
                fn = t.get("function", {})
                params = fn.get("parameters", {"type": "object", "properties": {}})
                function_declarations.append({
                    "name": fn.get("name"),
                    "description": fn.get("description", ""),
                    "parameters": params,
                })
            if function_declarations:
                gemini_tools = [{"function_declarations": function_declarations}]

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_instruction.strip():
            payload["system_instruction"] = {
                "parts": [{"text": system_instruction.strip()}]
            }
        if gemini_tools:
            payload["tools"] = gemini_tools

        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API error ({resp.status_code}): {resp.text}")

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return AIChatResponse(content="Master, I have processed the request.", model=self.model, provider=self.name)

        first_cand = candidates[0]
        content_obj = first_cand.get("content", {})
        parts = content_obj.get("parts", [])

        text_pieces = []
        tool_calls_extracted = []

        for p in parts:
            if "text" in p:
                text_pieces.append(p["text"])
            if "functionCall" in p:
                fn_call = p["functionCall"]
                tool_calls_extracted.append(ToolCall(
                    id=f"gemini_call_{secrets.token_hex(4)}",
                    name=fn_call.get("name", ""),
                    arguments=fn_call.get("args", {}),
                ))

        reply_text = "".join(text_pieces).strip()
        return AIChatResponse(
            content=reply_text,
            tool_calls=tool_calls_extracted,
            raw_response=data,
            model=self.model,
            provider=self.name,
        )
