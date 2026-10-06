from datetime import datetime
import mimetypes
import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.schemas import FileUploadResponse, GeneratedFileItem
from app.services.file_processing.extractor import extract_file_text_and_meta
from app.services.memory import memory_store
from app.services.memory.vector_store import rag_store
from app.settings import settings

router = APIRouter(prefix="/api/files", tags=["files"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50MB
ALLOWED_UPLOAD_EXTS = {
    ".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".json",
    ".txt", ".md", ".py", ".js", ".ts", ".html", ".css",
    ".cpp", ".c", ".java", ".sql", ".png", ".jpg", ".jpeg", ".webp",
}


@router.post("/upload", response_model=FileUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    session_id: str | None = None,
) -> FileUploadResponse:
    """
    Universal document upload & extraction. Indexes text chunks for RAG semantic search.
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="File must have a filename.")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_UPLOAD_EXTS))}",
        )

    content_bytes = await file.read()
    if not content_bytes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Uploaded file is empty.")
    if len(content_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds 50MB limit.")

    file_id = uuid4().hex[:8]
    safe_filename = f"{file_id}_{Path(file.filename).name}"
    dest_path = settings.uploads_dir / safe_filename

    with open(dest_path, "wb") as f:
        f.write(content_bytes)

    # Extract text & metadata
    extracted = extract_file_text_and_meta(dest_path)
    text = extracted["text"]
    total_units = extracted["total_units"]
    topics = extracted["topics"]

    # Index into RAG vector store for instant semantic search
    if text.strip():
        rag_store.chunk_and_index(file_id=file_id, filename=file.filename, full_text=text)

    # Inform conversation session memory
    if session_id:
        memory_store.append_message(
            session_id,
            "system",
            f"[Master uploaded '{file.filename}' ({total_units} pages/units)] Extract snippet:\n{text[:1200]}",
        )

    preview = text[:400].strip() + ("..." if len(text) > 400 else "")

    return FileUploadResponse(
        ok=True,
        fileId=file_id,
        filename=file.filename,
        fileType=ext.lstrip("."),
        sizeBytes=len(content_bytes),
        extractedTextPreview=preview,
        totalPagesOrLines=total_units,
        detectedTopics=topics,
        message=f"Document '{file.filename}' analyzed and indexed into RAG memory successfully.",
    )


@router.get("/generated", response_model=list[GeneratedFileItem])
async def list_generated_files() -> list[GeneratedFileItem]:
    """
    Return all generated documents (PDF, PPTX, DOCX, XLSX).
    """
    files = []
    for p in settings.generated_dir.glob("*.*"):
        if p.is_file():
            stat = p.stat()
            dt = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            files.append(GeneratedFileItem(
                id=p.name,
                filename=p.name,
                fileType=p.suffix.lstrip(".").lower(),
                sizeBytes=stat.st_size,
                createdAt=dt,
                downloadUrl=f"/api/files/download/{p.name}",
                description=f"Generated {p.suffix.upper()} file",
            ))
    files.sort(key=lambda x: x.created_at, reverse=True)
    return files


@router.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download a file from either generated/ or uploads/ directory.
    """
    # Check generated files
    target = settings.generated_dir / filename
    if not target.exists():
        target = settings.uploads_dir / filename
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")

    mime_type, _ = mimetypes.guess_type(str(target))
    return FileResponse(
        path=str(target),
        media_type=mime_type or "application/octet-stream",
        filename=filename,
    )


@router.delete("/{filename}")
async def delete_file(filename: str):
    target = settings.generated_dir / filename
    if not target.exists():
        target = settings.uploads_dir / filename
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    target.unlink()
    return {"ok": True, "message": f"File '{filename}' deleted successfully."}
