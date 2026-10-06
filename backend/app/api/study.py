from fastapi import APIRouter, HTTPException

from app.schemas import MCQItem, StudyNotesRequest, StudyNotesResponse
from app.services.agents.study_agent import study_agent
from app.services.study_mode.exam_prep import generate_exam_mcqs
from app.services.study_mode.notes_generator import generate_structured_study_notes

router = APIRouter(prefix="/api/study", tags=["study"])


@router.post("/notes", response_model=StudyNotesResponse)
async def get_study_notes(request: StudyNotesRequest) -> StudyNotesResponse:
    try:
        res = study_agent.process_study_request(
            text_or_topic=request.topic_or_text,
            subject=request.subject,
            format_output=request.format_output,
        )
        notes: StudyNotesResponse = res["study_notes"]
        if res.get("generated_files"):
            notes.generated_file_url = res["generated_files"][0].get("downloadUrl")
        return notes
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Study notes generation failed: {exc}") from exc


@router.post("/mcqs", response_model=list[MCQItem])
async def get_exam_mcqs(
    topic_or_text: str,
    count: int = 10,
    difficulty: str = "Medium",
) -> list[MCQItem]:
    try:
        return generate_exam_mcqs(topic_or_text=topic_or_text, count=count, difficulty=difficulty)  # type: ignore[arg-type]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"MCQ generation failed: {exc}") from exc
