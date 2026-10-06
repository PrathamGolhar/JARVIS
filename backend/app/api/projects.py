from fastapi import APIRouter, HTTPException

from app.schemas import ProjectCreateRequest, ProjectItem
from app.services.projects.manager import project_manager

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectItem])
async def list_projects() -> list[ProjectItem]:
    return project_manager.list_projects()


@router.post("", response_model=ProjectItem)
async def create_project(request: ProjectCreateRequest) -> ProjectItem:
    return project_manager.create_project(name=request.name, description=request.description)


@router.get("/{project_id}", response_model=ProjectItem)
async def get_project(project_id: str) -> ProjectItem:
    proj = project_manager.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found.")
    return proj


@router.post("/{project_id}/tasks")
async def add_project_task(project_id: str, title: str, due_date: str | None = None) -> ProjectItem:
    proj = project_manager.add_task(project_id, title=title, due_date=due_date)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found.")
    return proj


@router.patch("/{project_id}/tasks/{task_id}/toggle")
async def toggle_project_task(project_id: str, task_id: str) -> ProjectItem:
    proj = project_manager.toggle_task(project_id, task_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project or task not found.")
    return proj


@router.post("/{project_id}/link-file")
async def link_project_file(project_id: str, filename: str) -> ProjectItem:
    proj = project_manager.link_file(project_id, filename)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found.")
    return proj


@router.post("/{project_id}/notes")
async def update_project_notes(project_id: str, notes: str) -> ProjectItem:
    proj = project_manager.update_notes(project_id, notes)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found.")
    return proj
