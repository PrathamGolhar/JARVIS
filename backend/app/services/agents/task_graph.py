"""
JARVIS 2.0 — Task Graph & Dependency DAG Orchestrator.
Supports breaking complex user instructions into a directed acyclic graph (DAG) of executable subtasks,
executing independent branches in parallel, monitoring progress, and recovering from failures.
"""
import asyncio
from dataclasses import dataclass, field
from enum import Enum
import logging
import time
from typing import Any, Callable, Coroutine

logger = logging.getLogger("jarvis.task_graph")


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskNode:
    id: str
    title: str
    action_type: str  # "research", "file_extract", "generate_pdf", "generate_pptx", "verify", "math_eval"
    handler: Callable[..., Any] | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    result: Any = None
    error: str | None = None
    start_time: float | None = None
    end_time: float | None = None


class TaskGraph:
    """Manages a DAG of tasks with dependency resolution and status reporting."""

    def __init__(self, name: str = "ExecutionGraph") -> None:
        self.name = name
        self.nodes: dict[str, TaskNode] = {}

    def add_node(
        self,
        node_id: str,
        title: str,
        action_type: str,
        handler: Callable[..., Any] | None = None,
        parameters: dict[str, Any] | None = None,
        dependencies: list[str] | None = None,
    ) -> "TaskGraph":
        self.nodes[node_id] = TaskNode(
            id=node_id,
            title=title,
            action_type=action_type,
            handler=handler,
            parameters=parameters or {},
            dependencies=dependencies or [],
        )
        return self

    def is_executable(self, node: TaskNode) -> bool:
        if node.status != NodeStatus.PENDING:
            return False
        for dep_id in node.dependencies:
            dep_node = self.nodes.get(dep_id)
            if not dep_node or dep_node.status != NodeStatus.COMPLETED:
                return False
        return True

    def is_complete(self) -> bool:
        return all(node.status in (NodeStatus.COMPLETED, NodeStatus.FAILED, NodeStatus.SKIPPED) for node in self.nodes.values())

    def get_progress_summary(self) -> list[dict[str, Any]]:
        return [
            {
                "id": node.id,
                "title": node.title,
                "actionType": node.action_type,
                "status": node.status.value,
                "error": node.error,
                "durationMs": (
                    round((node.end_time - node.start_time) * 1000, 1)
                    if node.start_time and node.end_time
                    else None
                ),
            }
            for node in self.nodes.values()
        ]

    async def execute_all(self) -> dict[str, Any]:
        """Execute all nodes in dependency order, running independent parallel branches."""
        while not self.is_complete():
            executable_nodes = [node for node in self.nodes.values() if self.is_executable(node)]

            if not executable_nodes:
                # Check for deadlock or remaining unfulfilled dependencies
                for node in self.nodes.values():
                    if node.status == NodeStatus.PENDING:
                        node.status = NodeStatus.FAILED
                        node.error = "Unresolvable dependency or previous stage failure"
                break

            tasks = [self._execute_single_node(node) for node in executable_nodes]
            await asyncio.gather(*tasks)

        return {
            "completed": all(n.status == NodeStatus.COMPLETED for n in self.nodes.values()),
            "progress": self.get_progress_summary(),
            "results": {nid: n.result for nid, n in self.nodes.items() if n.status == NodeStatus.COMPLETED},
        }

    async def _execute_single_node(self, node: TaskNode) -> None:
        node.status = NodeStatus.RUNNING
        node.start_time = time.time()
        logger.info("TaskGraph: Starting task '%s' (%s)", node.title, node.id)

        try:
            if node.handler:
                # Support both async and synchronous handlers
                if asyncio.iscoroutinefunction(node.handler):
                    node.result = await node.handler(**node.parameters)
                else:
                    node.result = node.handler(**node.parameters)
            else:
                node.result = {"ok": True, "message": f"Simulated execution of {node.title}"}

            node.status = NodeStatus.COMPLETED
            logger.info("TaskGraph: Completed task '%s' (%s)", node.title, node.id)
        except Exception as exc:
            node.status = NodeStatus.FAILED
            node.error = str(exc)
            logger.error("TaskGraph: Task '%s' failed: %s", node.title, exc)
        finally:
            node.end_time = time.time()
