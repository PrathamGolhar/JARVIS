from datetime import datetime
import json
from pathlib import Path
from threading import RLock
from uuid import uuid4

from app.schemas import ProjectItem, ProjectTaskItem
from app.settings import settings


class ProjectManager:
    """
    Persistent project management engine handling tasks, contextual notes, linked files, and history.
    """

    def __init__(self, storage_dir: Path | None = None) -> None:
        self.storage_dir = storage_dir or settings.projects_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def _project_file(self, project_id: str) -> Path:
        return self.storage_dir / f"proj_{project_id}.json"

    def list_projects(self) -> list[ProjectItem]:
        with self._lock:
            projects = []
            for p in self.storage_dir.glob("proj_*.json"):
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    tasks = [
                        ProjectTaskItem(
                            id=t["id"],
                            title=t["title"],
                            completed=t.get("completed", False),
                            dueDate=t.get("dueDate"),
                        )
                        for t in data.get("tasks", [])
                    ]
                    projects.append(ProjectItem(
                        id=data["id"],
                        name=data["name"],
                        description=data.get("description", ""),
                        createdAt=data.get("createdAt", datetime.now().isoformat()),
                        updatedAt=data.get("updatedAt", datetime.now().isoformat()),
                        tasks=tasks,
                        linkedFiles=data.get("linkedFiles", []),
                        notes=data.get("notes", ""),
                    ))
                except Exception:
                    continue
            projects.sort(key=lambda x: x.updated_at, reverse=True)
            return projects

    def create_project(self, name: str, description: str = "") -> ProjectItem:
        with self._lock:
            pid = uuid4().hex[:8]
            now = datetime.now().isoformat()
            project = ProjectItem(
                id=pid,
                name=name.strip(),
                description=description.strip(),
                createdAt=now,
                updatedAt=now,
                tasks=[],
                linkedFiles=[],
                notes="",
            )
            file_path = self._project_file(pid)
            file_path.write_text(json.dumps(project.model_dump(by_alias=True), indent=2), encoding="utf-8")
            return project

    def get_project(self, project_id: str) -> ProjectItem | None:
        with self._lock:
            file_path = self._project_file(project_id)
            if not file_path.exists():
                return None
            data = json.loads(file_path.read_text(encoding="utf-8"))
            tasks = [
                ProjectTaskItem(
                    id=t["id"],
                    title=t["title"],
                    completed=t.get("completed", False),
                    dueDate=t.get("dueDate"),
                )
                for t in data.get("tasks", [])
            ]
            return ProjectItem(
                id=data["id"],
                name=data["name"],
                description=data.get("description", ""),
                createdAt=data.get("createdAt", ""),
                updatedAt=data.get("updatedAt", ""),
                tasks=tasks,
                linkedFiles=data.get("linkedFiles", []),
                notes=data.get("notes", ""),
            )

    def add_task(self, project_id: str, title: str, due_date: str | None = None) -> ProjectItem | None:
        with self._lock:
            proj = self.get_project(project_id)
            if not proj:
                return None
            task_id = f"task_{uuid4().hex[:6]}"
            new_task = ProjectTaskItem(id=task_id, title=title, completed=False, dueDate=due_date)
            proj.tasks.append(new_task)
            proj.updated_at = datetime.now().isoformat()
            self._project_file(project_id).write_text(
                json.dumps(proj.model_dump(by_alias=True), indent=2), encoding="utf-8"
            )
            return proj

    def toggle_task(self, project_id: str, task_id: str) -> ProjectItem | None:
        with self._lock:
            proj = self.get_project(project_id)
            if not proj:
                return None
            for t in proj.tasks:
                if t.id == task_id:
                    t.completed = not t.completed
                    break
            proj.updated_at = datetime.now().isoformat()
            self._project_file(project_id).write_text(
                json.dumps(proj.model_dump(by_alias=True), indent=2), encoding="utf-8"
            )
            return proj

    def link_file(self, project_id: str, filename: str) -> ProjectItem | None:
        with self._lock:
            proj = self.get_project(project_id)
            if not proj:
                return None
            if filename not in proj.linked_files:
                proj.linked_files.append(filename)
                proj.updated_at = datetime.now().isoformat()
                self._project_file(project_id).write_text(
                    json.dumps(proj.model_dump(by_alias=True), indent=2), encoding="utf-8"
                )
            return proj

    def update_notes(self, project_id: str, notes: str) -> ProjectItem | None:
        with self._lock:
            proj = self.get_project(project_id)
            if not proj:
                return None
            proj.notes = notes
            proj.updated_at = datetime.now().isoformat()
            self._project_file(project_id).write_text(
                json.dumps(proj.model_dump(by_alias=True), indent=2), encoding="utf-8"
            )
            return proj

    def build_project_context(self, project_id: str) -> str:
        proj = self.get_project(project_id)
        if not proj:
            return ""
        pending_tasks = [t.title for t in proj.tasks if not t.completed]
        done_tasks = [t.title for t in proj.tasks if t.completed]
        return (
            f"Active Project Context:\n"
            f"- Project Name: {proj.name}\n"
            f"- Description: {proj.description}\n"
            f"- Linked Files: {', '.join(proj.linked_files) or 'None'}\n"
            f"- Pending Tasks: {', '.join(pending_tasks) or 'None'}\n"
            f"- Completed Tasks: {', '.join(done_tasks) or 'None'}\n"
            f"- Project Notes: {proj.notes[:400] or 'None'}"
        )


project_manager = ProjectManager()
