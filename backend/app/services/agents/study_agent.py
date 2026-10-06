import logging
from typing import Any

from app.schemas import StudyNotesResponse
from app.services.document_generation.docx_generator import generate_docx_document
from app.services.document_generation.pdf_generator import generate_pdf_document
from app.services.study_mode.notes_generator import generate_structured_study_notes

logger = logging.getLogger("jarvis.study_agent")


class StudyAgent:
    """
    Dedicated agent managing Study Mode workflows: detailed notes, formula derivation tables,
    MCQ exam generation, and automatic publication of study documents.
    """

    @staticmethod
    def process_study_request(
        text_or_topic: str,
        subject: str = "General Studies",
        format_output: str = "pdf",
    ) -> dict[str, Any]:
        notes_res = generate_structured_study_notes(
            topic_or_text=text_or_topic,
            subject=subject,
            include_formulas=True,
            include_practice_questions=True,
        )

        generated_files = []

        # Generate PDF version of notes
        pdf_path = generate_pdf_document(
            title=f"Study Notes: {notes_res.title}",
            content_markdown=notes_res.detailed_notes_markdown,
            subtitle=f"Subject: {notes_res.subject}  •  Prepared by JARVIS",
            subject=notes_res.subject,
        )
        generated_files.append({
            "id": pdf_path.name,
            "filename": pdf_path.name,
            "fileType": "pdf",
            "sizeBytes": pdf_path.stat().st_size,
            "downloadUrl": f"/api/files/download/{pdf_path.name}",
            "description": f"Comprehensive Study Notes PDF ({notes_res.title})",
        })

        if format_output == "docx":
            docx_path = generate_docx_document(
                title=f"Study Notes: {notes_res.title}",
                content_markdown=notes_res.detailed_notes_markdown,
                subtitle=f"Subject: {notes_res.subject}",
            )
            generated_files.append({
                "id": docx_path.name,
                "filename": docx_path.name,
                "fileType": "docx",
                "sizeBytes": docx_path.stat().st_size,
                "downloadUrl": f"/api/files/download/{docx_path.name}",
                "description": f"Comprehensive Study Notes Word Document ({notes_res.title})",
            })

        return {
            "study_notes": notes_res,
            "generated_files": generated_files,
        }


study_agent = StudyAgent()
