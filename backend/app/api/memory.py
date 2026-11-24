from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas import MemoryItem, MemorySetRequest
from app.services.auth import require_principal
from app.services.memory import memory_store
from app.settings import settings

router = APIRouter(prefix="/api/memory", tags=["memory"], dependencies=[Depends(require_principal)])


@router.get("", response_model=list[MemoryItem])
async def list_memories(owner_id: str = Depends(require_principal)) -> list[MemoryItem]:
    return memory_store.list_memories(owner_id=owner_id)


@router.post("", response_model=MemoryItem)
async def set_memory(
    request: MemorySetRequest,
    owner_id: str = Depends(require_principal),
) -> MemoryItem:
    if getattr(settings, "permission_mode", "assisted") == "read_only":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Modifying persistent memory is disabled in 'read_only' permission mode.",
        )

    if not request.key.strip() or not request.value.strip():
        raise HTTPException(status_code=422, detail="Memory key and value cannot be blank.")
    item, is_conflict = memory_store.set_memory(
        key=request.key,
        value=request.value,
        category=request.category,
        owner_id=owner_id,
        provenance="user_explicit",
        source="memory center",
    )
    return item.model_copy(update={"conflict": is_conflict})


@router.delete("/{key}")
async def delete_memory(key: str, owner_id: str = Depends(require_principal)):
    if getattr(settings, "permission_mode", "assisted") == "read_only":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Deleting memory items is disabled in 'read_only' permission mode.",
        )

    ok = memory_store.delete_memory(key, owner_id=owner_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Memory key '{key}' not found.")
    return {"ok": True, "message": f"Memory '{key}' deleted."}
