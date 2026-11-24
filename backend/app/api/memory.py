from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas import MemoryItem, MemorySetRequest
from app.services.auth import require_auth
from app.services.memory import memory_store
from app.settings import settings

router = APIRouter(prefix="/api/memory", tags=["memory"], dependencies=[Depends(require_auth)])


@router.get("", response_model=list[MemoryItem])
async def list_memories() -> list[MemoryItem]:
    return memory_store.list_memories()


@router.post("", response_model=MemoryItem)
async def set_memory(request: MemorySetRequest) -> MemoryItem:
    if getattr(settings, "permission_mode", "assisted") == "read_only":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Modifying persistent memory is disabled in 'read_only' permission mode.",
        )

    if not request.key.strip():
        raise HTTPException(status_code=422, detail="Memory key cannot be blank.")
    return memory_store.set_memory(
        key=request.key,
        value=request.value,
        category=request.category,
    )


@router.delete("/{key}")
async def delete_memory(key: str):
    if getattr(settings, "permission_mode", "assisted") == "read_only":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Deleting memory items is disabled in 'read_only' permission mode.",
        )

    ok = memory_store.delete_memory(key)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Memory key '{key}' not found.")
    return {"ok": True, "message": f"Memory '{key}' deleted."}
