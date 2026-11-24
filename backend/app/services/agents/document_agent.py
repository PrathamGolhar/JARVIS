import json
import logging
import re
from typing import Any

from app.schemas import SlideContent
from app.services.agents.verifier import output_verifier
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
        if not topic.strip():
            raise ValueError("A presentation topic is required.")
        if not 1 <= num_slides <= 50:
            raise ValueError("Presentation slide count must be between 1 and 50.")

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
            if not isinstance(data, dict) or not isinstance(data.get("slides"), list):
                raise ValueError("The provider response did not contain a slides array.")
            if len(data["slides"]) != num_slides:
                raise ValueError(f"Expected {num_slides} slides, received {len(data['slides'])}.")

            slides = []
            for slide_data in data["slides"]:
                if not isinstance(slide_data, dict):
                    raise ValueError("A slide entry was not an object.")
                if not isinstance(slide_data.get("title"), str) or not slide_data["title"].strip():
                    raise ValueError("A slide is missing its title.")
                if not isinstance(slide_data.get("bullets"), list) or not all(
                    isinstance(bullet, str) for bullet in slide_data["bullets"]
                ):
                    raise ValueError("A slide has an invalid bullets list.")
                slides.append(SlideContent.model_validate(slide_data))
        except Exception as exc:
            logger.warning("Presentation generation failed: %s", exc)
            raise RuntimeError("Presentation generation failed; no presentation was created.") from exc

        pptx_path = generate_pptx_presentation(topic=topic, slides=slides, theme_color=theme_color)
        verification = output_verifier.verify_generated_file(pptx_path, expected_extension=".pptx")
        if not verification.get("verified"):
            raise RuntimeError(f"Presentation file verification failed: {verification.get('reason')}")

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
