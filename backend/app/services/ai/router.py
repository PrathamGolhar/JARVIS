"""
JARVIS 2.0 — Intelligent Model Router & Task Classifier.
Routes requests across AI providers (Gemini, Groq, OpenAI, Anthropic, Local) based on:
- Capability requirements (coding, math, reasoning, vision, fast conversation, document synthesis)
- Real-time provider availability and circuit breaker health
- Cost, latency tiers, and user-specified manual overrides.
"""
from dataclasses import dataclass
from enum import Enum
import logging
import re
from typing import Any

from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.base import AIChatResponse, AIProvider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.groq_provider import GroqProvider
from app.services.ai.health import provider_health_registry
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
    RESEARCH_ANALYSIS = "research_analysis"
    OFFLINE_LOCAL = "offline_local"


@dataclass
class RouteDecision:
    category: TaskCategory
    provider_name: str
    recommended_model: str
    reason: str
    estimated_latency_tier: str  # "ultra-fast", "standard", "deep"
    estimated_cost_tier: str     # "free", "low", "medium", "high"


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

        text = prompt.lower().strip()

        # Coding / Syntax / Refactoring markers (Checked first to distinguish code functions from math)
        if any(w in text for w in [
            "def ", "class ", "function", "bug", "syntax error", "refactor",
            "unit test", "c++", "python", "javascript", "sql query", "async def",
            "pytest", "git commit", "dockerfile", "endpoint", "api schema"
        ]):
            return TaskCategory.CODING_AND_SYNTAX

        # Math / Computation markers
        if any(w in text for w in [
            "calculate", "derivative", "integral", "matrix", "eigenvalue",
            "solve for x", "determinant", "standard deviation", "quadratic",
            "linear regression", "logarithm", "cosine", "sine"
        ]):
            return TaskCategory.MATHEMATICS_COMPUTE

        # Research / Multi-source markers
        if any(w in text for w in [
            "research", "investigate", "compare sources", "citations", "find papers",
            "academic review", "literature review", "web survey"
        ]):
            return TaskCategory.RESEARCH_ANALYSIS

        # Document synthesis / Study / Presentation
        if has_documents or any(w in text for w in [
            "create presentation", "make notes", "exam prep", "generate pdf",
            "generate docx", "research report", "summarize pdf", "powerpoint", "slide deck"
        ]):
            return TaskCategory.DOCUMENT_SYNTHESIS

        # Simple conversational queries (greetings, quick clarifications, status checks)
        direct_simple = [
            "hello", "hi", "hey", "who are you", "what time is it", "how are you",
            "good morning", "good evening", "thank you", "thanks", "status report"
        ]
        if text in direct_simple or (len(text.split()) <= 15 and not any(w in text for w in ["plan", "build", "execute", "analyze", "why", "how does"])):
            return TaskCategory.SIMPLE_CONVERSATION

        # Deep reasoning fallback
        return TaskCategory.DEEP_REASONING


class ModelRouter:
    """Intelligently routes task requests to the best available model provider."""

    @classmethod
    def _is_provider_healthy(cls, provider: AIProvider, name: str) -> bool:
        if not provider.is_available():
            return False
        rec = provider_health_registry.get(name)
        rec.configured = True
        return rec.can_execute()

    @classmethod
    def route(
        cls,
        prompt: str,
        has_images: bool = False,
        has_documents: bool = False,
        user_override: str | None = None,
    ) -> RouteDecision:
        # 0. Check User Override
        if user_override and user_override.lower() != "auto":
            prov_name = user_override.lower()
            model_map = {
                "gemini": settings.gemini_model,
                "groq": settings.groq_chat_model,
                "openai": settings.openai_model,
                "anthropic": settings.anthropic_model,
                "local": "local-rule-engine",
            }
            return RouteDecision(
                category=TaskCategory.DEEP_REASONING,
                provider_name=prov_name,
                recommended_model=model_map.get(prov_name, "default"),
                reason="User explicitly selected manual model provider override",
                estimated_latency_tier="standard",
                estimated_cost_tier="medium",
            )

        category = TaskClassifier.classify(prompt, has_images=has_images, has_documents=has_documents)

        # 1. Vision & Multimodal -> Gemini (Highest multimodal vision fidelity)
        if category == TaskCategory.VISION_MULTIMODAL:
            gemini = GeminiProvider()
            if cls._is_provider_healthy(gemini, "gemini"):
                return RouteDecision(
                    category=category,
                    provider_name="gemini",
                    recommended_model=gemini.model,
                    reason="Optimal native multimodal vision & document understanding",
                    estimated_latency_tier="standard",
                    estimated_cost_tier="low",
                )

        # 2. Simple Conversational / Low-Latency -> Groq (Llama-3.3 ultra-fast inference)
        if category == TaskCategory.SIMPLE_CONVERSATION:
            groq = GroqProvider()
            if cls._is_provider_healthy(groq, "groq"):
                return RouteDecision(
                    category=category,
                    provider_name="groq",
                    recommended_model=groq.model,
                    reason="Sub-second ultra-low latency conversational response",
                    estimated_latency_tier="ultra-fast",
                    estimated_cost_tier="low",
                )

        # 3. Coding, Math & Complex Reasoning -> Gemini -> Anthropic -> OpenAI -> Groq
        if category in (TaskCategory.CODING_AND_SYNTAX, TaskCategory.MATHEMATICS_COMPUTE, TaskCategory.DEEP_REASONING):
            gemini = GeminiProvider()
            if cls._is_provider_healthy(gemini, "gemini"):
                return RouteDecision(
                    category=category,
                    provider_name="gemini",
                    recommended_model=gemini.model,
                    reason="Top-tier long-context reasoning, tool synthesis & structured schemas",
                    estimated_latency_tier="standard",
                    estimated_cost_tier="low",
                )

            anthropic = AnthropicProvider()
            if cls._is_provider_healthy(anthropic, "anthropic"):
                return RouteDecision(
                    category=category,
                    provider_name="anthropic",
                    recommended_model=anthropic.model,
                    reason="High precision code generation and architectural reasoning",
                    estimated_latency_tier="standard",
                    estimated_cost_tier="high",
                )

            openai_prov = OpenAIProvider()
            if cls._is_provider_healthy(openai_prov, "openai"):
                return RouteDecision(
                    category=category,
                    provider_name="openai",
                    recommended_model=openai_prov.model,
                    reason="High accuracy instruction following and coding syntax",
                    estimated_latency_tier="standard",
                    estimated_cost_tier="medium",
                )

            groq = GroqProvider()
            if cls._is_provider_healthy(groq, "groq"):
                return RouteDecision(
                    category=category,
                    provider_name="groq",
                    recommended_model=groq.model,
                    reason="Fast open-weights coding fallback with high token throughput",
                    estimated_latency_tier="ultra-fast",
                    estimated_cost_tier="low",
                )

        # 4. Document Synthesis & Research -> Gemini (Large context window) -> OpenAI
        if category in (TaskCategory.DOCUMENT_SYNTHESIS, TaskCategory.RESEARCH_ANALYSIS):
            gemini = GeminiProvider()
            if cls._is_provider_healthy(gemini, "gemini"):
                return RouteDecision(
                    category=category,
                    provider_name="gemini",
                    recommended_model=gemini.model,
                    reason="Large context window (1M+ tokens) ideal for multi-document synthesis",
                    estimated_latency_tier="standard",
                    estimated_cost_tier="low",
                )

        # Fallback cascade: Gemini -> Groq -> OpenAI -> Anthropic -> Local
        gemini = GeminiProvider()
        if cls._is_provider_healthy(gemini, "gemini"):
            return RouteDecision(
                category=category,
                provider_name="gemini",
                recommended_model=gemini.model,
                reason="Default primary provider",
                estimated_latency_tier="standard",
                estimated_cost_tier="low",
            )

        groq = GroqProvider()
        if cls._is_provider_healthy(groq, "groq"):
            return RouteDecision(
                category=category,
                provider_name="groq",
                recommended_model=groq.model,
                reason="Fast primary fallback",
                estimated_latency_tier="ultra-fast",
                estimated_cost_tier="low",
            )

        openai_prov = OpenAIProvider()
        if cls._is_provider_healthy(openai_prov, "openai"):
            return RouteDecision(
                category=category,
                provider_name="openai",
                recommended_model=openai_prov.model,
                reason="Commercial API fallback",
                estimated_latency_tier="standard",
                estimated_cost_tier="medium",
            )

        # Final offline rule-engine fallback
        local = LocalProvider()
        return RouteDecision(
            category=TaskCategory.OFFLINE_LOCAL,
            provider_name="local",
            recommended_model="local-rule-engine",
            reason="Offline rule engine fallback when cloud providers are unconfigured or degraded",
            estimated_latency_tier="ultra-fast",
            estimated_cost_tier="free",
        )
