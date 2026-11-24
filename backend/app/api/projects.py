from fastapi import APIRouter, Depends, HTTPException, status
import re

from app.schemas import ProjectCreateRequest, ProjectItem
from app.services.auth import require_principal
from app.services.memory.vector_store import rag_store
from app.services.projects.manager import project_manager
from app.settings import settings

router = APIRouter(prefix="/api/projects", tags=["projects"], dependencies=[Depends(require_principal)])


def check_write_permission() -> None:
    if getattr(settings, "permission_mode", "assisted") == "read_only":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project modifications are disabled in 'read_only' permission mode.",
        )


@router.get("", response_model=list[ProjectItem])
async def list_projects(owner_id: str = Depends(require_principal)) -> list[ProjectItem]:
    return project_manager.list_projects(owner_id=owner_id)


@router.post("", response_model=ProjectItem)
async def create_project(
    request: ProjectCreateRequest,
    owner_id: str = Depends(require_principal),
) -> ProjectItem:
    check_write_permission()
    return project_manager.create_project(name=request.name, description=request.description, owner_id=owner_id)


@router.get("/{project_id}", response_model=ProjectItem)
async def get_project(project_id: str, owner_id: str = Depends(require_principal)) -> ProjectItem:
    proj = project_manager.get_project(project_id, owner_id=owner_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found.")
    return proj


@router.post("/{project_id}/tasks")
async def add_project_task(
    project_id: str,
    title: str,
    due_date: str | None = None,
    owner_id: str = Depends(require_principal),
) -> ProjectItem:
    check_write_permission()
    proj = project_manager.add_task(project_id, title=title, due_date=due_date, owner_id=owner_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found.")
    return proj


@router.patch("/{project_id}/tasks/{task_id}/toggle")
async def toggle_project_task(
    project_id: str,
    task_id: str,
    owner_id: str = Depends(require_principal),
) -> ProjectItem:
    check_write_permission()
    proj = project_manager.toggle_task(project_id, task_id, owner_id=owner_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project or task not found.")
    return proj


@router.post("/{project_id}/link-file")
async def link_project_file(
    project_id: str,
    filename: str,
    owner_id: str = Depends(require_principal),
) -> ProjectItem:
    check_write_permission()
    match = re.match(r"^([0-9a-f]{8}|[0-9a-f]{32})(?:_|$)", filename, flags=re.IGNORECASE)
    if match and not rag_store.get_document(match.group(1).lower(), owner_id=owner_id):
        raise HTTPException(status_code=404, detail="Document not found.")
    proj = project_manager.link_file(project_id, filename, owner_id=owner_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found.")
    if match and not rag_store.attach_document_to_project(match.group(1).lower(), project_id, owner_id):
        raise HTTPException(status_code=404, detail="Document not found.")
    return proj


@router.post("/{project_id}/notes")
async def update_project_notes(
    project_id: str,
    notes: str,
    owner_id: str = Depends(require_principal),
) -> ProjectItem:
    check_write_permission()
    proj = project_manager.update_notes(project_id, notes, owner_id=owner_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found.")
    return proj
