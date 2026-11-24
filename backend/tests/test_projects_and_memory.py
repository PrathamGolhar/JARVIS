from pathlib import Path

from app.services.memory import memory_store
from app.services.projects.manager import project_manager
from app.services.projects.manager import ProjectManager


def test_memory_store_set_get_list_delete() -> None:
    key = "test_pref_robotics"
    val = "Arduino and ROS2 platform"
    memory_store.set_memory(key, val, category="project")

    retrieved = memory_store.get_memory(key)
    assert retrieved == val

    all_memories = memory_store.list_memories()
    assert any(m.key == key and m.value == val for m in all_memories)

    ok = memory_store.delete_memory(key)
    assert ok is True
    assert memory_store.get_memory(key) is None


def test_project_manager_crud_and_tasks() -> None:
    proj = project_manager.create_project(name="Mars Rover Simulation", description="Autonomous rover navigation")
    assert proj.id
    assert proj.name == "Mars Rover Simulation"

    updated = project_manager.add_task(proj.id, "Implement LiDAR SLAM filter")
    assert updated is not None
    assert len(updated.tasks) == 1
    task_id = updated.tasks[0].id
    assert updated.tasks[0].completed is False

    toggled = project_manager.toggle_task(proj.id, task_id)
    assert toggled is not None
    assert toggled.tasks[0].completed is True

    context_str = project_manager.build_project_context(proj.id)
    assert "Mars Rover Simulation" in context_str
    assert "LiDAR SLAM filter" in context_str


def test_project_manager_scopes_projects_by_owner(tmp_path: Path) -> None:
    manager = ProjectManager(storage_dir=tmp_path)
    project = manager.create_project("Alice's project", owner_id="owner_alice")

    assert manager.get_project(project.id, owner_id="owner_alice") is not None
    assert manager.get_project(project.id, owner_id="owner_bob") is None
    assert manager.list_projects(owner_id="owner_bob") == []
    assert manager.add_task(project.id, "private task", owner_id="owner_bob") is None
