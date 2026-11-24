from fastapi import APIRouter, Depends, HTTPException

from app.services.auth import require_principal
from app.schemas import (
    GenerateDocxRequest,
    GeneratePdfRequest,
    GeneratePptxRequest,
    GenerateXlsxRequest,
)
from app.services.document_generation.docx_generator import generate_docx_document
from app.services.document_generation.excel_generator import generate_excel_spreadsheet
from app.services.document_generation.pdf_generator import generate_pdf_document
from app.services.document_generation.pptx_generator import generate_pptx_presentation
from app.services.agents.verifier import output_verifier
from app.services.memory import memory_store

router = APIRouter(prefix="/api/generate", tags=["generation"], dependencies=[Depends(require_principal)])


def _verify_generated_artifact(path, expected_extension: str) -> None:
    verification = output_verifier.verify_generated_file(path, expected_extension=expected_extension)
    if not verification.get("verified"):
        raise RuntimeError(f"Generated file verification failed: {verification.get('reason')}")


@router.post("/pdf")
async def generate_pdf(
    request: GeneratePdfRequest,
    owner_id: str = Depends(require_principal),
):
    try:
        pdf_path = generate_pdf_document(
            title=request.title,
            content_markdown=request.content_markdown,
            subtitle=request.subtitle,
            subject=request.subject,
        )
        _verify_generated_artifact(pdf_path, ".pdf")
        memory_store.register_artifact(pdf_path.name, owner_id)
        return {
            "ok": True,
            "filename": pdf_path.name,
            "downloadUrl": f"/api/files/download/{pdf_path.name}",
            "sizeBytes": pdf_path.stat().st_size,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}") from exc


@router.post("/pptx")
async def generate_pptx(
    request: GeneratePptxRequest,
    owner_id: str = Depends(require_principal),
):
    try:
        from app.services.agents.document_agent import document_agent
        if not request.slides:
            res = document_agent.create_presentation_from_prompt(
                topic=request.topic,
                num_slides=request.num_slides,
                theme_color=request.theme_color,
            )
            filename = res["file"]["filename"]
            memory_store.register_artifact(filename, owner_id)
            return {"ok": True, "file": res["file"]}

        pptx_path = generate_pptx_presentation(
            topic=request.topic,
            slides=request.slides,
            theme_color=request.theme_color,
        )
        _verify_generated_artifact(pptx_path, ".pptx")
        memory_store.register_artifact(pptx_path.name, owner_id)
        return {
            "ok": True,
            "filename": pptx_path.name,
            "downloadUrl": f"/api/files/download/{pptx_path.name}",
            "sizeBytes": pptx_path.stat().st_size,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PowerPoint generation failed: {exc}") from exc


@router.post("/docx")
async def generate_docx(
    request: GenerateDocxRequest,
    owner_id: str = Depends(require_principal),
):
    try:
        docx_path = generate_docx_document(
            title=request.title,
            content_markdown=request.content_markdown,
            subtitle=request.subtitle,
            author=request.author,
        )
        _verify_generated_artifact(docx_path, ".docx")
        memory_store.register_artifact(docx_path.name, owner_id)
        return {
            "ok": True,
            "filename": docx_path.name,
            "downloadUrl": f"/api/files/download/{docx_path.name}",
            "sizeBytes": docx_path.stat().st_size,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Word document generation failed: {exc}") from exc


@router.post("/xlsx")
async def generate_xlsx(
    request: GenerateXlsxRequest,
    owner_id: str = Depends(require_principal),
):
    try:
        xlsx_path = generate_excel_spreadsheet(
            filename=request.filename,
            headers=request.headers,
            rows=request.rows,
            sheet_name=request.sheet_name,
            include_summary_row=request.include_summary_row,
        )
        _verify_generated_artifact(xlsx_path, ".xlsx")
        memory_store.register_artifact(xlsx_path.name, owner_id)
        return {
            "ok": True,
            "filename": xlsx_path.name,
            "downloadUrl": f"/api/files/download/{xlsx_path.name}",
            "sizeBytes": xlsx_path.stat().st_size,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Excel generation failed: {exc}") from exc
