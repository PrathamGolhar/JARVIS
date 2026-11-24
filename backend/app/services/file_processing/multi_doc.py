"""
JARVIS 2.0 — Multi-Document Reasoning & Comparative Synthesis Agent.
Enables cross-file comparison across multiple documents (PDF, DOCX, TXT, Research papers),
extracting commonalities, contradictions, methodologies, results, and comparison tables.
"""
from dataclasses import dataclass, field
import json
import logging
from typing import Any, Literal

from app.services.ai.factory import get_ai_provider

logger = logging.getLogger("jarvis.multi_doc")


@dataclass
class ComparisonResult:
    topic: str
    documents_analyzed: list[str]
    commonalities: list[str]
    differences: list[str]
    comparison_table: list[dict[str, Any]]
    synthesis_markdown: str
    status: Literal["success", "partial_success", "failure"]
    confidence: float | None = None
    omitted_documents: list[str] = field(default_factory=list)
    truncated_documents: list[str] = field(default_factory=list)
    error: str | None = None


class MultiDocumentReasoner:
    """Performs comparative intelligence across multiple uploaded documents."""

    @classmethod
    def compare_documents(
        cls,
        documents: list[dict[str, str]],  # [{"filename": "doc1.pdf", "content": "..."}, ...]
        focus_topic: str = "General Comparison",
    ) -> ComparisonResult:
        usable_documents = [
            document
            for document in documents
            if isinstance(document.get("content"), str) and document["content"].strip()
        ]
        if len(usable_documents) < 2:
            return ComparisonResult(
                topic=focus_topic,
                documents_analyzed=[],
                commonalities=[],
                differences=[],
                comparison_table=[],
                synthesis_markdown="",
                status="failure",
                error="At least two documents with readable text are required for comparison.",
            )

        selected_documents = usable_documents[:5]
        filenames = [
            document.get("filename") or f"Doc_{index + 1}"
            for index, document in enumerate(selected_documents)
        ]
        omitted_documents = [
            document.get("filename") or f"Doc_{index + 1}"
            for index, document in enumerate(usable_documents[5:], start=5)
        ]
        truncated_documents = [
            filename
            for filename, document in zip(filenames, selected_documents)
            if len(document["content"]) > 6000
        ]

        combined_text = ""
        for i, document in enumerate(selected_documents):
            combined_text += f"\n\n=== DOCUMENT {i+1}: {filenames[i]} ===\n{document['content'][:6000]}"

        system_prompt = (
            "You are JARVIS in MULTI-DOCUMENT REASONING MODE.\n"
            "Analyze the provided documents, extract core similarities, differences, methodologies, and formulate a structured comparison table.\n"
            "Return valid JSON matching this schema:\n"
            "{\n"
            '  "topic": "Comparison topic",\n'
            '  "commonalities": ["Shared finding 1", "Shared finding 2"],\n'
            '  "differences": ["Disagreement or differing approach 1", ...],\n'
            '  "comparisonTable": [\n'
            '    {"dimension": "Methodology", "doc1": "Details", "doc2": "Details"}\n'
            "  ],\n"
            '  "synthesisMarkdown": "# Multi-Document Comparative Report\\n\\n..."\n'
            "}"
        )

        user_prompt = f"Focus Topic: {focus_topic}\n\nDocuments to compare:\n{combined_text}"

        try:
            provider = get_ai_provider()
            res = provider.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=3500,
            )

            raw = res.content.strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]

            data = json.loads(raw.strip())
            if not isinstance(data, dict):
                raise ValueError("The provider response was not a JSON object.")
            commonalities = data.get("commonalities")
            differences = data.get("differences")
            comparison_table = data.get("comparisonTable")
            synthesis_markdown = data.get("synthesisMarkdown")
            if (
                not isinstance(commonalities, list)
                or not all(isinstance(item, str) for item in commonalities)
                or not isinstance(differences, list)
                or not all(isinstance(item, str) for item in differences)
                or not isinstance(comparison_table, list)
                or not all(isinstance(item, dict) for item in comparison_table)
                or not isinstance(synthesis_markdown, str)
                or not synthesis_markdown.strip()
                or not isinstance(data.get("topic", focus_topic), str)
                or not data.get("topic", focus_topic).strip()
            ):
                raise ValueError("The provider response did not contain a complete comparison.")
            return ComparisonResult(
                topic=data.get("topic", focus_topic),
                documents_analyzed=filenames,
                commonalities=commonalities,
                differences=differences,
                comparison_table=comparison_table,
                synthesis_markdown=synthesis_markdown,
                status="partial_success" if omitted_documents or truncated_documents else "success",
                omitted_documents=omitted_documents,
                truncated_documents=truncated_documents,
            )
        except Exception as exc:
            logger.warning("Multi-document AI comparison failed: %s", exc)
            return ComparisonResult(
                topic=focus_topic,
                documents_analyzed=[],
                commonalities=[],
                differences=[],
                comparison_table=[],
                synthesis_markdown="",
                status="failure",
                error="AI comparison failed; no similarities or differences were produced.",
            )
