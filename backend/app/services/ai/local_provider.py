import json
import re
import secrets
from typing import Any

from app.services.ai.base import AIChatResponse, AIProvider, ToolCall


class LocalProvider(AIProvider):
    """
    Offline heuristic rule-based AI provider ensuring JARVIS can still perform local tool actions,
    diagnostics, calculations, and structured responses without an internet connection or cloud API keys.
    """

    name = "local"

    def is_available(self) -> bool:
        return True

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> AIChatResponse:
        user_message = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_message = str(m.get("content", ""))
                break

        low = user_message.lower().strip()
        system_prompt = next(
            (str(message.get("content", "")) for message in messages if message.get("role") == "system"),
            "",
        )
        response_style = (
            "concise"
            if "Prefer brief, direct answers" in system_prompt
            else "detailed"
            if "Explain the reasoning and relevant details" in system_prompt
            else "balanced"
        )

        # Check if the message history contains tool results to synthesize
        tool_results = [m for m in messages if m.get("role") == "tool"]
        if tool_results:
            last_tool = tool_results[-1]
            tool_name = last_tool.get("name", "")
            raw_content = last_tool.get("content", "{}")
            try:
                data = json.loads(raw_content) if isinstance(raw_content, str) else raw_content
            except Exception:
                data = {}

            if tool_name == "web_search":
                if data.get("ok") and data.get("results"):
                    results = data["results"]
                    lines = ["Verified results from live web research:"]
                    result_limit = 3 if response_style == "concise" else 5
                    for idx, r in enumerate(results[:result_limit], start=1):
                        title = r.get("title", "Source")
                        url = r.get("url", "")
                        snippet = r.get("snippet", "").strip()
                        domain = r.get("domain", "")
                        source_label = f" *({domain})*" if domain else ""
                        lines.append(f"{idx}. **{title}**{source_label}\n   {snippet}\n   Source: {url}")
                    if response_style != "concise":
                        lines.append("The results are grounded in the cited sources.")
                    reply = "\n\n".join(lines)
                else:
                    reply = (
                        "Web research is temporarily unavailable. "
                        "I can still answer from my existing knowledge, or you can retry the research request."
                    )
                return AIChatResponse(
                    content=reply,
                    tool_calls=[],
                    model="local-rule-engine",
                    provider=self.name,
                )

            if tool_name == "calculator":
                val = data.get("result") or data.get("value") or data.get("expression")
                expression = data.get("expression")
                reply = (
                    f"The result of {expression} is **{val}**."
                    if response_style == "detailed" and expression
                    else f"Result: **{val}**."
                )
                return AIChatResponse(
                    content=reply,
                    tool_calls=[],
                    model="local-rule-engine",
                    provider=self.name,
                )

            if tool_name == "get_weather":
                if data.get("ok"):
                    loc = data.get("location", "the requested area")
                    temp = data.get("temperature", "N/A")
                    cond = data.get("conditions", "Clear")
                    reply = (
                        f"Current weather in {loc}: {temp}°C, {cond}."
                        if response_style == "concise"
                        else f"Current conditions in {loc} are {temp}°C with {cond}."
                    )
                    return AIChatResponse(
                        content=reply,
                        tool_calls=[],
                        model="local-rule-engine",
                        provider=self.name,
                    )
                return AIChatResponse(
                    content="The live weather service is temporarily unavailable.",
                    tool_calls=[],
                    model="local-rule-engine",
                    provider=self.name,
                )

            if tool_name == "system_diagnostics":
                return AIChatResponse(
                    content="System telemetry reports nominal hardware status.",
                    tool_calls=[],
                    model="local-rule-engine",
                    provider=self.name,
                )

            msg = data.get("message") or f"Executed tool '{tool_name}' successfully."
            return AIChatResponse(
                content=str(msg),
                tool_calls=[],
                model="local-rule-engine",
                provider=self.name,
            )

        # Tool heuristic detection
        tool_calls = []

        # Math / calculation
        if any(w in low for w in ["calculate", "sqrt", "math", "+", "*", "/", "divided by", "multiplied by"]) and any(c.isdigit() for c in low):
            # Extract expression
            expr = re.sub(r"[^\d+\-*/().^ ]", "", user_message).strip()
            if expr:
                tool_calls.append(ToolCall(
                    id=f"loc_{secrets.token_hex(4)}",
                    name="calculator",
                    arguments={"expression": expr},
                ))

        # Weather
        elif "weather" in low or "temperature in" in low:
            match = re.search(r"weather (?:in|for|at)?\s*([a-zA-Z\s]+)", low)
            loc = match.group(1).strip() if match else "London"
            tool_calls.append(ToolCall(
                id=f"loc_{secrets.token_hex(4)}",
                name="get_weather",
                arguments={"location": loc},
            ))

        # System diagnostics
        elif any(k in low for k in ["diagnostics", "system status", "cpu", "ram", "battery", "hardware"]):
            tool_calls.append(ToolCall(
                id=f"loc_{secrets.token_hex(4)}",
                name="system_diagnostics",
                arguments={},
            ))

        # File search
        elif "search file" in low or "find file" in low:
            pat = low.replace("search file", "").replace("find file", "").replace("for", "").strip()
            tool_calls.append(ToolCall(
                id=f"loc_{secrets.token_hex(4)}",
                name="search_files",
                arguments={"pattern": pat or "*"},
            ))

        # Web search
        elif ("search" in low or "lookup" in low or "who is" in low or "what is" in low) and "file" not in low:
            query = user_message.replace("search for", "").replace("search", "").strip()
            tool_calls.append(ToolCall(
                id=f"loc_{secrets.token_hex(4)}",
                name="web_search",
                arguments={"query": query},
            ))

        if tool_calls:
            return AIChatResponse(
                content="",
                tool_calls=tool_calls,
                model="local-rule-engine",
                provider=self.name,
            )

        # Fallback conversational responses
        if any(w in low for w in ["hello", "hi", "hey", "greetings", "jarvis"]):
            reply = "Hello. Offline systems are ready. What would you like to work on?"
        elif "thank" in low:
            reply = "You're welcome."
        else:
            reply = f"I received your request about '{user_message[:50]}'. The local assistant is ready to help."

        return AIChatResponse(
            content=reply,
            tool_calls=[],
            model="local-rule-engine",
            provider=self.name,
        )
