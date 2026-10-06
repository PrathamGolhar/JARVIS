from fastapi import APIRouter, HTTPException

from app.schemas import (
    GenerateDocxRequest,
    GeneratePdfRequest,
    GeneratePptxRequest,
    GenerateXlsxRequest,
    GeneratedFileItem,
)
from app.services.document_generation.docx_generator import generate_docx_document
from app.services.document_generation.excel_generator import generate_excel_spreadsheet
from app.services.document_generation.pdf_generator import generate_pdf_document
from app.services.document_generation.pptx_generator import generate_pptx_presentation

router = APIRouter(prefix="/api/generate", tags=["generation"])


@router.post("/pdf")
async def generate_pdf(request: GeneratePdfRequest):
    try:
        pdf_path = generate_pdf_document(
            title=request.title,
            content_markdown=request.content_markdown,
            subtitle=request.subtitle,
            subject=request.subject,
        )
        return {
            "ok": True,
            "filename": pdf_path.name,
            "downloadUrl": f"/api/files/download/{pdf_path.name}",
            "sizeBytes": pdf_path.stat().st_size,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}") from exc


@router.post("/pptx")
async def generate_pptx(request: GeneratePptxRequest):
    try:
        from app.services.agents.document_agent import document_agent
        if not request.slides:
            res = document_agent.create_presentation_from_prompt(
                topic=request.topic,
                num_slides=request.num_slides,
                theme_color=request.theme_color,
            )
            return {"ok": True, "file": res["file"]}

        pptx_path = generate_pptx_presentation(
            topic=request.topic,
            slides=request.slides,
            theme_color=request.theme_color,
        )
        return {
            "ok": True,
            "filename": pptx_path.name,
            "downloadUrl": f"/api/files/download/{pptx_path.name}",
            "sizeBytes": pptx_path.stat().st_size,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PowerPoint generation failed: {exc}") from exc


@router.post("/docx")
async def generate_docx(request: GenerateDocxRequest):
    try:
        docx_path = generate_docx_document(
            title=request.title,
            content_markdown=request.content_markdown,
            subtitle=request.subtitle,
            author=request.author,
        )
        return {
            "ok": True,
            "filename": docx_path.name,
            "downloadUrl": f"/api/files/download/{docx_path.name}",
            "sizeBytes": docx_path.stat().st_size,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Word document generation failed: {exc}") from exc


@router.post("/xlsx")
async def generate_xlsx(request: GenerateXlsxRequest):
    try:
        xlsx_path = generate_excel_spreadsheet(
            filename=request.filename,
            headers=request.headers,
            rows=request.rows,
            sheet_name=request.sheet_name,
            include_summary_row=request.include_summary_row,
        )
        return {
            "ok": True,
            "filename": xlsx_path.name,
            "downloadUrl": f"/api/files/download/{xlsx_path.name}",
            "sizeBytes": xlsx_path.stat().st_size,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Excel generation failed: {exc}") from exc
