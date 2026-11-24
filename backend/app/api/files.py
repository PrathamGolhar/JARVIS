from datetime import datetime
import mimetypes
from pathlib import Path
import re
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.schemas import FileUploadResponse, GeneratedFileItem
from app.services.auth import require_principal
from app.services.file_processing.extractor import extract_file_text_and_meta
from app.services.memory import memory_store
from app.services.memory.vector_store import rag_store
from app.services.projects.manager import project_manager
from app.settings import settings

router = APIRouter(prefix="/api/files", tags=["files"], dependencies=[Depends(require_principal)])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50MB
ALLOWED_UPLOAD_EXTS = {
    ".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".json",
    ".txt", ".md", ".py", ".js", ".ts", ".html", ".css",
    ".cpp", ".c", ".java", ".sql", ".png", ".jpg", ".jpeg", ".webp",
}
FORBIDDEN_PATTERNS = {".env", ".git", ".db", ".sqlite", ".pem", ".key"}


@router.post("/upload", response_model=FileUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    session_id: str | None = None,
    project_id: str | None = None,
    owner_id: str = Depends(require_principal),
) -> FileUploadResponse:
    """
    Universal document upload & extraction with RAG semantic indexing.
    Enforces server-side permission checks, extension allowlists, size limits, and filename sanitization.
    """
    if getattr(settings, "permission_mode", "assisted") == "read_only":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="File upload is strictly disabled in 'read_only' permission mode.",
        )

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="File must have a filename.")

    if "\0" in file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename contains invalid characters.")

    safe_base = Path(file.filename).name
    if not safe_base or safe_base in (".", ".."):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename format.")

    ext = Path(safe_base).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_UPLOAD_EXTS))}",
        )

    if project_id and not project_manager.get_project(project_id, owner_id=owner_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    if session_id and not memory_store.ensure_session_owner(session_id, owner_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found.")

    content_bytes = await file.read()
    if not content_bytes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Uploaded file is empty.")
    if len(content_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds 50MB limit.")

    file_id = uuid4().hex
    safe_filename = f"{file_id}_{safe_base}"
    dest_path = (settings.uploads_dir / safe_filename).resolve()

    if not dest_path.is_relative_to(settings.uploads_dir.resolve()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path traversal attempt detected.")

    with open(dest_path, "wb") as f:
        f.write(content_bytes)

    # Extract text & metadata
    try:
        extracted = extract_file_text_and_meta(dest_path)
    except Exception as exc:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unable to extract uploaded file '{safe_base}'.",
        ) from exc
    text = extracted["text"]
    total_units = extracted["total_units"]
    topics = extracted["topics"]

    # Index into persistent RAG store for instant semantic search with session isolation
    indexed_chunks = rag_store.chunk_and_index(
        file_id=file_id,
        filename=safe_base,
        full_text=text,
        session_id=session_id,
        owner_id=owner_id,
        project_id=project_id,
    )

    preview = text[:400].strip() + ("..." if len(text) > 400 else "")
    if indexed_chunks:
        message = f"Document '{safe_base}' was extracted and indexed into searchable memory."
    elif ext in {".png", ".jpg", ".jpeg", ".webp"}:
        message = (
            f"Image '{safe_base}' was uploaded, but OCR and searchable text indexing were not performed. "
            "Visual understanding requires an image-capable chat provider."
        )
    else:
        message = f"File '{safe_base}' was uploaded, but no searchable text was extracted."

    return FileUploadResponse(
        ok=True,
        fileId=file_id,
        filename=safe_base,
        fileType=ext.lstrip("."),
        sizeBytes=len(content_bytes),
        extractedTextPreview=preview,
        totalPagesOrLines=total_units,
        detectedTopics=topics,
        message=message,
    )


@router.get("/generated", response_model=list[GeneratedFileItem])
async def list_generated_files(owner_id: str = Depends(require_principal)) -> list[GeneratedFileItem]:
    """Return all generated documents (PDF, PPTX, DOCX, XLSX)."""
    files = []
    for p in settings.generated_dir.glob("*.*"):
        if p.is_file():
            if not memory_store.artifact_belongs_to(p.name, owner_id):
                if owner_id != memory_store.legacy_owner_id or not memory_store.register_artifact(p.name, owner_id):
                    continue
            stat = p.stat()
            dt = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            files.append(
                GeneratedFileItem(
                    id=p.name,
                    filename=p.name,
                    fileType=p.suffix.lstrip(".").lower(),
                    sizeBytes=stat.st_size,
                    createdAt=dt,
                    downloadUrl=f"/api/files/download/{p.name}",
                    description=f"Generated {p.suffix.upper()} file",
                )
            )
    files.sort(key=lambda x: x.created_at, reverse=True)
    return files


@router.get("/download/{filename}")
async def download_file(filename: str, owner_id: str = Depends(require_principal)):
    """
    Download a file from generated/ or uploads/ directory with strict path traversal & symlink protection.
    """
    if "\0" in filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename.")

    safe_name = Path(filename).name
    if not safe_name or safe_name in (".", ".."):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename.")

    lower = safe_name.lower()
    if any(lower.startswith(p) or lower.endswith(p) for p in FORBIDDEN_PATTERNS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access to protected file is restricted.")

    gen_root = settings.generated_dir.resolve()
    up_root = settings.uploads_dir.resolve()

    target_gen = (gen_root / safe_name).resolve()
    target_up = (up_root / safe_name).resolve()

    target: Path | None = None
    if target_gen.exists() and target_gen.is_relative_to(gen_root) and target_gen.is_file():
        target = target_gen
    elif target_up.exists() and target_up.is_relative_to(up_root) and target_up.is_file():
        target = target_up

    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File '{safe_name}' not found.")

    if target.parent == gen_root and not _ensure_generated_file_owner(safe_name, owner_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    if target.parent == up_root:
        file_id = _uploaded_file_id(safe_name)
        if not file_id or not rag_store.get_document(file_id, owner_id=owner_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")

    mime_type, _ = mimetypes.guess_type(str(target))
    return FileResponse(
        path=str(target),
        media_type=mime_type or "application/octet-stream",
        filename=safe_name,
    )


@router.delete("/{filename}")
async def delete_file(filename: str, owner_id: str = Depends(require_principal)):
    """
    Delete a file from generated/ or uploads/ with permission enforcement and path traversal protection.
    """
    if getattr(settings, "permission_mode", "assisted") == "read_only":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="File deletion is strictly disabled in 'read_only' permission mode.",
        )

    if "\0" in filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename.")

    safe_name = Path(filename).name
    if not safe_name or safe_name in (".", ".."):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename.")

    lower = safe_name.lower()
    if any(lower.startswith(p) or lower.endswith(p) for p in FORBIDDEN_PATTERNS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Deletion of protected files is prohibited.")

    gen_root = settings.generated_dir.resolve()
    up_root = settings.uploads_dir.resolve()

    target_gen = (gen_root / safe_name).resolve()
    target_up = (up_root / safe_name).resolve()

    target: Path | None = None
    if target_gen.exists() and target_gen.is_relative_to(gen_root) and target_gen.is_file():
        target = target_gen
    elif target_up.exists() and target_up.is_relative_to(up_root) and target_up.is_file():
        target = target_up

    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File '{safe_name}' not found.")

    if target.parent == gen_root and not _ensure_generated_file_owner(safe_name, owner_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    if target.parent == up_root:
        file_id = _uploaded_file_id(safe_name)
        if not file_id or not rag_store.get_document(file_id, owner_id=owner_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
        if not rag_store.delete_document(file_id, owner_id=owner_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")

    target.unlink()
    if target.parent == gen_root:
        memory_store.delete_artifact(safe_name, owner_id)
    return {"ok": True, "message": f"File '{safe_name}' deleted successfully."}


def _uploaded_file_id(filename: str) -> str | None:
    match = re.match(r"^([0-9a-f]{8}|[0-9a-f]{32})(?:_|$)", filename, flags=re.IGNORECASE)
    return match.group(1).lower() if match else None


def _ensure_generated_file_owner(filename: str, owner_id: str) -> bool:
    if memory_store.artifact_belongs_to(filename, owner_id):
        return True
    return owner_id == memory_store.legacy_owner_id and memory_store.register_artifact(filename, owner_id)
