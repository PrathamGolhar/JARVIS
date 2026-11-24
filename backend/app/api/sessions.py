from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.auth import require_principal
from app.services.memory import memory_store
from app.services.memory.vector_store import rag_store
from app.settings import settings

router = APIRouter(prefix="/api/sessions", tags=["sessions"], dependencies=[Depends(require_principal)])


class SessionCreateRequest(BaseModel):
    session_id: UUID = Field(alias="sessionId")


@router.post("")
async def register_session(
    request: SessionCreateRequest,
    owner_id: str = Depends(require_principal),
) -> dict[str, str]:
    if not memory_store.ensure_session_owner(request.session_id, owner_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found.")
    return {"sessionId": str(request.session_id)}


@router.get("")
async def list_sessions(owner_id: str = Depends(require_principal)) -> list[dict[str, str]]:
    return memory_store.list_sessions(owner_id)


@router.get("/{session_id}/history")
async def get_session_history(
    session_id: UUID,
    owner_id: str = Depends(require_principal),
) -> list[dict[str, str]]:
    if not memory_store.session_belongs_to(session_id, owner_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found.")
    return memory_store.get_history(session_id, limit=200, owner_id=owner_id)


@router.post("/{session_id}/reset")
async def reset_session(
    session_id: UUID,
    owner_id: str = Depends(require_principal),
) -> dict[str, bool]:
    if not memory_store.reset_session_history(session_id, owner_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found.")
    return {"ok": True}


@router.delete("/{session_id}")
async def delete_session(
    session_id: UUID,
    owner_id: str = Depends(require_principal),
) -> dict[str, bool]:
    if not memory_store.session_belongs_to(session_id, owner_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found.")

    documents = rag_store.list_session_documents(str(session_id), owner_id)
    artifacts = memory_store.list_session_artifacts(session_id, owner_id)
    uploads_root = settings.uploads_dir.resolve()
    generated_root = settings.generated_dir.resolve()
    for document in documents:
        filename = f"{document['file_id']}_{Path(document['filename']).name}"
        target = (uploads_root / filename).resolve()
        if target.is_relative_to(uploads_root) and target.is_file():
            target.unlink()
    for filename in artifacts:
        target = (generated_root / Path(filename).name).resolve()
        if target.is_relative_to(generated_root) and target.is_file():
            target.unlink()
    for filename in artifacts:
        memory_store.delete_artifact(filename, owner_id)
    for document in documents:
        if not rag_store.delete_document(document["file_id"], owner_id=owner_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Session document index changed during deletion; retry the request.",
            )
    if not memory_store.delete_session(session_id, owner_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found.")
    return {"ok": True}
