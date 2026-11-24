"""
JARVIS 2.0 — Enterprise Task Graph & Dependency DAG Execution Engine.

Features:
1. DAG Validation & Cycle Detection: Validates graph structure before execution.
2. Strict Dependency Resolution: Never runs a node until all prerequisite nodes are COMPLETED.
3. Cascading Failure Propagation: Automatically marks downstream dependents as SKIPPED/FAILED if a parent fails.
4. Parallel Independent Branching: Executes unblocked nodes concurrently with bounded concurrency.
5. Timeout Management: Per-node timeout enforcement preventing hanging steps.
6. Execution Tracing & Partial Result Preservation: Collects intermediate results safely even under partial failures.
7. Cancellation Support: Ability to cancel in-flight execution.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict, deque
import concurrent.futures
from dataclasses import dataclass, field
from enum import Enum
import logging
import time
from typing import Any, Callable

logger = logging.getLogger("jarvis.task_graph")


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class TaskNode:
    id: str
    title: str
    action_type: str
    handler: Callable[..., Any] | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    timeout_seconds: float = 30.0
    status: NodeStatus = NodeStatus.PENDING
    result: Any = None
    error: str | None = None
    start_time: float | None = None
    end_time: float | None = None


class DAGValidationError(Exception):
    """Raised when a task graph has cycles or unknown dependency references."""
    pass


class TaskGraph:
    """Enterprise DAG orchestration engine with parallel branching and fault containment."""

    def __init__(self, name: str = "ExecutionGraph", max_concurrency: int = 4) -> None:
        self.name = name
        self.max_concurrency = max_concurrency
        self.nodes: dict[str, TaskNode] = {}
        self._cancelled = False

    def add_node(
        self,
        node_id: str,
        title: str,
        action_type: str,
        handler: Callable[..., Any] | None = None,
        parameters: dict[str, Any] | None = None,
        dependencies: list[str] | None = None,
        timeout_seconds: float = 30.0,
    ) -> TaskGraph:
        self.nodes[node_id] = TaskNode(
            id=node_id,
            title=title,
            action_type=action_type,
            handler=handler,
            parameters=parameters or {},
            dependencies=dependencies or [],
            timeout_seconds=timeout_seconds,
        )
        return self

    def validate_dag(self) -> None:
        """Validate that all dependencies exist and there are no cycles in the graph."""
        # 1. Check for unknown dependencies
        for node_id, node in self.nodes.items():
            for dep in node.dependencies:
                if dep not in self.nodes:
                    raise DAGValidationError(f"Node '{node_id}' depends on undefined node '{dep}'.")
                if dep == node_id:
                    raise DAGValidationError(f"Self-dependency detected on node '{node_id}'.")

        # 2. Cycle Detection using Kahn's algorithm (Topological Sort)
        in_degree: dict[str, int] = {nid: 0 for nid in self.nodes}
        adj_list: dict[str, list[str]] = defaultdict(list)

        for nid, node in self.nodes.items():
            for dep in node.dependencies:
                adj_list[dep].append(nid)
                in_degree[nid] += 1

        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        visited_count = 0

        while queue:
            curr = queue.popleft()
            visited_count += 1
            for neighbor in adj_list[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(self.nodes):
            raise DAGValidationError(f"Cycle detected in TaskGraph '{self.name}'. Graph is not a valid DAG.")

    def cancel(self) -> None:
        """Signal cancellation for remaining tasks."""
        self._cancelled = True
        for node in self.nodes.values():
            if node.status == NodeStatus.PENDING:
                node.status = NodeStatus.CANCELLED
                node.error = "Execution cancelled by caller."

    def is_complete(self) -> bool:
        return all(node.status in (NodeStatus.COMPLETED, NodeStatus.FAILED, NodeStatus.SKIPPED, NodeStatus.CANCELLED) for node in self.nodes.values())

    def get_progress_summary(self) -> list[dict[str, Any]]:
        return [
            {
                "id": node.id,
                "title": node.title,
                "actionType": node.action_type,
                "status": node.status.value,
                "error": node.error,
                "dependencies": node.dependencies,
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
        self.validate_dag()
        semaphore = asyncio.Semaphore(self.max_concurrency)

        while not self.is_complete():
            if self._cancelled:
                break

            # Find ready nodes whose dependencies are all COMPLETED
            ready_nodes: list[TaskNode] = []
            for node in self.nodes.values():
                if node.status != NodeStatus.PENDING:
                    continue

                # Check status of dependencies
                deps = [self.nodes[d] for d in node.dependencies]
                if any(d.status in (NodeStatus.FAILED, NodeStatus.SKIPPED, NodeStatus.CANCELLED) for d in deps):
                    # Prerequisite failed -> Fail or Skip this dependent node
                    node.status = NodeStatus.SKIPPED
                    failed_deps = [d.id for d in deps if d.status in (NodeStatus.FAILED, NodeStatus.SKIPPED, NodeStatus.CANCELLED)]
                    node.error = f"Prerequisite task(s) failed or cancelled: {', '.join(failed_deps)}"
                    logger.warning("Cascading skip on node '%s': %s", node.id, node.error)
                    continue

                if all(d.status == NodeStatus.COMPLETED for d in deps):
                    ready_nodes.append(node)

            if not ready_nodes:
                # If there are pending nodes but none are ready and none were just skipped, we are deadlocked
                pending = [n for n in self.nodes.values() if n.status == NodeStatus.PENDING]
                if pending:
                    for n in pending:
                        n.status = NodeStatus.FAILED
                        n.error = "Unresolvable dependency or deadlock during execution"
                break

            # Execute ready nodes concurrently under semaphore bound
            async def _run_with_sem(n: TaskNode) -> None:
                async with semaphore:
                    await self._execute_single_node(n)

            await asyncio.gather(*[_run_with_sem(n) for n in ready_nodes])

        all_completed = all(n.status == NodeStatus.COMPLETED for n in self.nodes.values())
        return {
            "completed": all_completed,
            "progress": self.get_progress_summary(),
            "results": {nid: n.result for nid, n in self.nodes.items() if n.status == NodeStatus.COMPLETED},
            "failures": {nid: n.error for nid, n in self.nodes.items() if n.status in (NodeStatus.FAILED, NodeStatus.SKIPPED)},
        }

    async def _execute_single_node(self, node: TaskNode) -> None:
        node.status = NodeStatus.RUNNING
        node.start_time = time.time()
        logger.info("TaskGraph: Starting task '%s' (%s)", node.title, node.id)

        try:
            if node.handler:
                import inspect
                params = dict(node.parameters)
                dep_results = {dep_id: self.nodes[dep_id].result for dep_id in node.dependencies if self.nodes[dep_id].result is not None}

                # Only inject dependency_results if the handler accepts **kwargs or explicitly declares 'dependency_results'
                sig = inspect.signature(node.handler)
                has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
                if dep_results and ("dependency_results" in sig.parameters or has_var_keyword):
                    params["dependency_results"] = dep_results

                if asyncio.iscoroutinefunction(node.handler):
                    node.result = await asyncio.wait_for(node.handler(**params), timeout=node.timeout_seconds)
                else:
                    node.result = await asyncio.wait_for(
                        asyncio.to_thread(node.handler, **params),
                        timeout=node.timeout_seconds,
                    )
            else:
                node.result = {"ok": True, "message": f"Completed {node.title}"}

            node.status = NodeStatus.COMPLETED
            logger.info("TaskGraph: Completed task '%s' (%s)", node.title, node.id)
        except asyncio.TimeoutError:
            node.status = NodeStatus.FAILED
            node.error = f"Task timed out after {node.timeout_seconds:.1f} seconds."
            logger.warning("TaskGraph: Task '%s' timed out", node.title)
        except Exception as exc:
            node.status = NodeStatus.FAILED
            node.error = str(exc)
            logger.error("TaskGraph: Task '%s' failed: %s", node.title, exc)
        finally:
            node.end_time = time.time()
