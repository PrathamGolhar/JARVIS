import json
import logging
import re
from typing import Any

from app.schemas import SlideContent
from app.services.ai.factory import get_ai_provider
from app.services.document_generation.docx_generator import generate_docx_document
from app.services.document_generation.excel_generator import generate_excel_spreadsheet
from app.services.document_generation.pdf_generator import generate_pdf_document
from app.services.document_generation.pptx_generator import generate_pptx_presentation

logger = logging.getLogger("jarvis.document_agent")


class DocumentAgent:
    """
    Dedicated agent for orchestrating multi-format document generation (PDF, PPTX, DOCX, XLSX).
    """

    @staticmethod
    def create_presentation_from_prompt(
        topic: str,
        num_slides: int = 6,
        theme_color: str = "cyan",
        context: str = "",
    ) -> dict[str, Any]:
        provider = get_ai_provider()

        system_prompt = (
            "You are JARVIS Executive Presentation Designer.\n"
            f"Generate a structured {num_slides}-slide outline and content for a presentation on '{topic}'.\n"
            "Return ONLY JSON matching this format:\n"
            "{\n"
            '  "topic": "Presentation Title",\n'
            '  "slides": [\n'
            '    {"title": "Slide Title", "subtitle": "Optional subtitle", "bullets": ["Point 1", "Point 2", "Point 3"], "speakerNotes": "What the presenter should say"}\n'
            "  ]\n"
            "}"
        )

        user_prompt = f"Topic: {topic}\nNumber of slides: {num_slides}\nContext: {context[:5000]}"

        try:
            res = provider.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=2500,
            )
            content = res.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            data = json.loads(content.strip())
            slides = [
                SlideContent(
                    title=s.get("title", f"Slide {i+1}"),
                    subtitle=s.get("subtitle", ""),
                    bullets=s.get("bullets", []),
                    speakerNotes=s.get("speakerNotes", ""),
                )
                for i, s in enumerate(data.get("slides", []))
            ]
        except Exception as exc:
            logger.warning("Presentation generation fallback: %s", exc)
            slides = [
                SlideContent(
                    title="Executive Overview",
                    subtitle="Strategic Imperatives",
                    bullets=[f"Primary objectives for {topic}", "Key architectural principles", "Operational milestones"],
                    speakerNotes="Welcome everyone. Today we are exploring the foundational concepts.",
                ),
                SlideContent(
                    title="Core Architecture & Implementation",
                    subtitle="Engineering Standards",
                    bullets=["High modularity and robust isolation", "Zero latency execution", "Continuous automated verification"],
                    speakerNotes="Moving on to technical details, our architecture is built for resiliency.",
                ),
                SlideContent(
                    title="Strategic Summary & Next Steps",
                    subtitle="Action Items",
                    bullets=["Deploy to production environment", "Continuous monitoring & feedback loop", "Next phase capabilities"],
                    speakerNotes="In conclusion, our systems stand ready for execution.",
                ),
            ]

        pptx_path = generate_pptx_presentation(topic=topic, slides=slides, theme_color=theme_color)

        return {
            "file": {
                "id": pptx_path.name,
                "filename": pptx_path.name,
                "fileType": "pptx",
                "sizeBytes": pptx_path.stat().st_size,
                "downloadUrl": f"/api/files/download/{pptx_path.name}",
                "description": f"Widescreen 16:9 PowerPoint Deck ({len(slides)} slides)",
            },
            "slides_count": len(slides),
        }


document_agent = DocumentAgent()
