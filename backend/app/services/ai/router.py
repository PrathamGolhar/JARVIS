"""
JARVIS 2.0 — Intelligent Model Router & Task Classifier.
Routes requests across AI providers (Gemini, Groq, OpenAI, Local) based on task complexity,
vision/multimodal requirements, coding capabilities, and latency priorities.
"""
from dataclasses import dataclass
from enum import Enum
import logging
import re
from typing import Any

from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.base import AIChatResponse, AIProvider
from app.services.ai.factory import get_ai_provider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.groq_provider import GroqProvider
from app.services.ai.local_provider import LocalProvider
from app.services.ai.openai_provider import OpenAIProvider
from app.settings import settings

logger = logging.getLogger("jarvis.model_router")


class TaskCategory(str, Enum):
    SIMPLE_CONVERSATION = "simple_conversation"
    DEEP_REASONING = "deep_reasoning"
    VISION_MULTIMODAL = "vision_multimodal"
    CODING_AND_SYNTAX = "coding_and_syntax"
    DOCUMENT_SYNTHESIS = "document_synthesis"
    MATHEMATICS_COMPUTE = "mathematics_compute"
    OFFLINE_LOCAL = "offline_local"


@dataclass
class RouteDecision:
    category: TaskCategory
    provider_name: str
    recommended_model: str
    reason: str
    estimated_latency_tier: str  # "ultra-fast", "standard", "deep"


class TaskClassifier:
    """Classifies user intent and payload to determine the optimal model capability requirement."""

    @staticmethod
    def classify(
        prompt: str,
        has_images: bool = False,
        has_documents: bool = False,
        force_local: bool = False,
    ) -> TaskCategory:
        if force_local or settings.ai_provider == "local":
            return TaskCategory.OFFLINE_LOCAL

        if has_images:
            return TaskCategory.VISION_MULTIMODAL

        text = prompt.lower()

        # Math / Computation markers
        if any(w in text for w in ["calculate", "derivative", "integral", "matrix", "eigenvalue", "equation", "solve for x", "determinant"]):
            return TaskCategory.MATHEMATICS_COMPUTE

        # Coding markers
        if any(w in text for w in ["def ", "class ", "function", "bug", "syntax error", "refactor", "unit test", "c++", "python", "javascript", "sql query"]):
            return TaskCategory.CODING_AND_SYNTAX

        # Document synthesis / Study / Presentation
        if has_documents or any(w in text for w in ["create presentation", "make notes", "exam prep", "generate pdf", "generate docx", "research report", "summarize pdf"]):
            return TaskCategory.DOCUMENT_SYNTHESIS

        # Deep reasoning / Research
        if any(w in text for w in ["research", "compare sources", "analyze why", "explain mechanism", "theoretical", "implications"]):
            return TaskCategory.DEEP_REASONING

        # Simple conversational queries
        if len(prompt.split()) < 30 and not any(w in text for w in ["plan", "build", "execute"]):
            return TaskCategory.SIMPLE_CONVERSATION

        return TaskCategory.DEEP_REASONING


class ModelRouter:
    """Intelligently routes task requests to the best available model provider."""

    @classmethod
    def route(
        cls,
        prompt: str,
        has_images: bool = False,
        has_documents: bool = False,
        user_override: str | None = None,
    ) -> RouteDecision:
        if user_override and user_override.lower() != "auto":
            prov_name = user_override.lower()
            return RouteDecision(
                category=TaskCategory.DEEP_REASONING,
                provider_name=prov_name,
                recommended_model=settings.gemini_model if prov_name == "gemini" else "default",
                reason="User explicitly selected model provider override",
                estimated_latency_tier="standard",
            )

        category = TaskClassifier.classify(prompt, has_images=has_images, has_documents=has_documents)

        # 1. Vision & Multimodal -> Gemini 2.5 Flash
        if category == TaskCategory.VISION_MULTIMODAL:
            gemini = GeminiProvider()
            if gemini.is_available():
                return RouteDecision(
                    category=category,
                    provider_name="gemini",
                    recommended_model=gemini.model,
                    reason="Optimal multimodal & visual diagram comprehension",
                    estimated_latency_tier="standard",
                )

        # 2. Simple Conversational -> Groq (Ultra-Low Latency) or Gemini
        if category == TaskCategory.SIMPLE_CONVERSATION:
            groq = GroqProvider()
            if groq.is_available():
                return RouteDecision(
                    category=category,
                    provider_name="groq",
                    recommended_model=groq.model,
                    reason="Sub-second low-latency conversational response",
                    estimated_latency_tier="ultra-fast",
                )

        # 3. Coding, Document Synthesis, Deep Reasoning -> Gemini -> Groq -> OpenAI -> Local
        gemini = GeminiProvider()
        if gemini.is_available():
            return RouteDecision(
                category=category,
                provider_name="gemini",
                recommended_model=gemini.model,
                reason="High-capability long-context reasoning & structured JSON output",
                estimated_latency_tier="standard",
            )

        groq = GroqProvider()
        if groq.is_available():
            return RouteDecision(
                category=category,
                provider_name="groq",
                recommended_model=groq.model,
                reason="Ultra-fast Llama-3.3 high capability fallback",
                estimated_latency_tier="ultra-fast",
            )

        openai_prov = OpenAIProvider()
        if openai_prov.is_available():
            return RouteDecision(
                category=category,
                provider_name="openai",
                recommended_model=openai_prov.model,
                reason="OpenAI GPT reasoning fallback",
                estimated_latency_tier="standard",
            )

        anthropic_prov = AnthropicProvider()
        if anthropic_prov.is_available():
            return RouteDecision(
                category=category,
                provider_name="anthropic",
                recommended_model=anthropic_prov.model,
                reason="Anthropic Claude reasoning fallback",
                estimated_latency_tier="standard",
            )

        return RouteDecision(
            category=TaskCategory.OFFLINE_LOCAL,
            provider_name="local",
            recommended_model="local-rule-engine",
            reason="Offline deterministic local engine active",
            estimated_latency_tier="ultra-fast",
        )

    @classmethod
    def execute(
        cls,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        user_override: str | None = None,
        has_images: bool = False,
        has_documents: bool = False,
    ) -> AIChatResponse:
        """Route and execute chat request via the optimal AI provider."""
        last_prompt = messages[-1].get("content", "") if messages else ""
        decision = cls.route(
            last_prompt,
            has_images=has_images,
            has_documents=has_documents,
            user_override=user_override,
        )
        logger.info("JARVIS Model Router: category=%s -> provider=%s (%s)", decision.category.value, decision.provider_name, decision.reason)
        provider = get_ai_provider(preferred=decision.provider_name)
        return provider.chat(messages, tools=tools)
