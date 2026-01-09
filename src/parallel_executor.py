"""Parallel agent execution with work stealing.

This module provides parallel task execution for autonomous development:

- Task priority and status management
- Agent pool with status tracking
- Work queue with priority ordering
- Work stealing for load balancing
- Integration with dependency graph
"""

import heapq
import json
import time
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any


class TaskPriority(IntEnum):
    """Task priority levels."""

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class TaskStatus(Enum):
    """Task status."""

    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class AgentStatus(Enum):
    """Agent status."""

    IDLE = "idle"
    BUSY = "busy"
    STEALING = "stealing"
    STOPPED = "stopped"


@dataclass
class Task:
    """A task to be executed."""

    task_id: str
    name: str
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def is_ready(self, completed_tasks: set[str]) -> bool:
        """Check if task is ready to run (all dependencies met).

        Args:
            completed_tasks: Set of completed task IDs

        Returns:
            True if ready to run
        """
        if not self.dependencies:
            return True
        return all(dep in completed_tasks for dep in self.dependencies)

    def __lt__(self, other: "Task") -> bool:
        """Compare tasks by priority and creation time."""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


@dataclass
class WorkResult:
    """Result of task execution."""

    task_id: str
    success: bool
    output: str | None = None
    error: str | None = None
    duration_ms: float | None = None
    timestamp: float = field(default_factory=time.time)


class Agent:
    """An agent that executes tasks."""

    def __init__(self, agent_id: str) -> None:
        """Initialize agent.

        Args:
            agent_id: Unique agent identifier
        """
        self.agent_id = agent_id
        self.status = AgentStatus.IDLE
        self.current_task: Task | None = None
        self._completed_count = 0
        self._task_start_time: float | None = None

    @property
    def completed_count(self) -> int:
        """Number of completed tasks."""
        return self._completed_count

    def assign_task(self, task: Task) -> None:
        """Assign a task to this agent.

        Args:
            task: Task to assign
        """
        self.current_task = task
        self.current_task.status = TaskStatus.IN_PROGRESS
        self.status = AgentStatus.BUSY
        self._task_start_time = time.time()

    def complete_task(self, success: bool = True, output: str | None = None, error: str | None = None) -> WorkResult:
        """Complete the current task.

        Args:
            success: Whether task succeeded
            output: Task output
            error: Error message if failed

        Returns:
            WorkResult
        """
        task_id = self.current_task.task_id if self.current_task else "unknown"

        duration_ms = None
        if self._task_start_time:
            duration_ms = (time.time() - self._task_start_time) * 1000

        if self.current_task:
            self.current_task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED

        result = WorkResult(
            task_id=task_id,
            success=success,
            output=output,
            error=error,
            duration_ms=duration_ms,
        )

        self._completed_count += 1
        self.current_task = None
        self.status = AgentStatus.IDLE
        self._task_start_time = None

        return result

    def start_stealing(self) -> None:
        """Mark agent as stealing work."""
        self.status = AgentStatus.STEALING

    def stop_stealing(self) -> None:
        """Stop stealing work."""
        if self.status == AgentStatus.STEALING:
            self.status = AgentStatus.IDLE

    def stop(self) -> None:
        """Stop the agent."""
        self.status = AgentStatus.STOPPED


class WorkQueue:
    """Priority queue for tasks."""

    def __init__(self) -> None:
        """Initialize work queue."""
        self._heap: list[Task] = []
        self._task_map: dict[str, Task] = {}

    def size(self) -> int:
        """Get queue size.

        Returns:
            Number of tasks in queue
        """
        return len(self._heap)

    def is_empty(self) -> bool:
        """Check if queue is empty.

        Returns:
            True if empty
        """
        return len(self._heap) == 0

    def enqueue(self, task: Task) -> None:
        """Add task to queue.

        Args:
            task: Task to add
        """
        task.status = TaskStatus.QUEUED
        heapq.heappush(self._heap, task)
        self._task_map[task.task_id] = task

    def dequeue(self) -> Task | None:
        """Remove and return highest priority task.

        Returns:
            Task or None if empty
        """
        if self._heap:
            task = heapq.heappop(self._heap)
            del self._task_map[task.task_id]
            return task
        return None

    def peek(self) -> Task | None:
        """View highest priority task without removing.

        Returns:
            Task or None if empty
        """
        return self._heap[0] if self._heap else None

    def steal(self, count: int) -> list[Task]:
        """Steal tasks from queue (for work stealing).

        Steals from the back (lowest priority) tasks.

        Args:
            count: Number of tasks to steal

        Returns:
            List of stolen tasks
        """
        if not self._heap:
            return []

        # Steal lowest priority tasks
        count = min(count, len(self._heap))
        stolen = []

        # Re-heapify after stealing
        tasks = list(self._heap)
        self._heap = []
        self._task_map = {}

        # Sort and steal from end (lowest priority)
        tasks.sort()
        for task in tasks[-count:]:
            stolen.append(task)

        # Re-add remaining tasks
        for task in tasks[:-count] if count > 0 else tasks:
            self.enqueue(task)

        return stolen


class ParallelExecutor:
    """Executes tasks in parallel with work stealing."""

    def __init__(self, num_agents: int = 2) -> None:
        """Initialize parallel executor.

        Args:
            num_agents: Number of agents to create
        """
        self.agents = [Agent(f"agent-{i}") for i in range(num_agents)]
        self._queue = WorkQueue()
        self._completed: list[Task] = []
        self._completed_ids: set[str] = set()
        self._blocked_tasks: list[Task] = []

    def submit(self, task: Task) -> None:
        """Submit a task for execution.

        Args:
            task: Task to submit
        """
        if task.is_ready(self._completed_ids):
            self._queue.enqueue(task)
        else:
            task.status = TaskStatus.BLOCKED
            self._blocked_tasks.append(task)

    def pending_count(self) -> int:
        """Get count of pending tasks.

        Returns:
            Number of pending tasks
        """
        return self._queue.size() + len(self._blocked_tasks)

    def completed_count(self) -> int:
        """Get count of completed tasks.

        Returns:
            Number of completed tasks
        """
        return len(self._completed)

    def assign_tasks(self) -> int:
        """Assign tasks to idle agents.

        Returns:
            Number of tasks assigned
        """
        assigned = 0

        for agent in self.agents:
            if agent.status == AgentStatus.IDLE and not self._queue.is_empty():
                task = self._queue.dequeue()
                if task:
                    agent.assign_task(task)
                    assigned += 1

        return assigned

    def complete_task(
        self,
        agent_id: str,
        success: bool = True,
        output: str | None = None,
        error: str | None = None,
    ) -> WorkResult | None:
        """Complete a task for an agent.

        Args:
            agent_id: Agent that completed task
            success: Whether task succeeded
            output: Task output
            error: Error message if failed

        Returns:
            WorkResult or None if agent not found
        """
        agent = self._find_agent(agent_id)
        if not agent or not agent.current_task:
            return None

        task = agent.current_task
        result = agent.complete_task(success=success, output=output, error=error)

        if success:
            self._completed.append(task)
            self._completed_ids.add(task.task_id)

            # Check if any blocked tasks can now run
            self._unblock_tasks()

        return result

    def _unblock_tasks(self) -> None:
        """Check and unblock tasks whose dependencies are met."""
        still_blocked = []

        for task in self._blocked_tasks:
            if task.is_ready(self._completed_ids):
                task.status = TaskStatus.PENDING
                self._queue.enqueue(task)
            else:
                still_blocked.append(task)

        self._blocked_tasks = still_blocked

    def _find_agent(self, agent_id: str) -> Agent | None:
        """Find agent by ID.

        Args:
            agent_id: Agent ID

        Returns:
            Agent or None
        """
        for agent in self.agents:
            if agent.agent_id == agent_id:
                return agent
        return None

    def steal_work_for(self, agent_id: str) -> int:
        """Steal work for an idle agent.

        Args:
            agent_id: Agent to steal for

        Returns:
            Number of tasks stolen
        """
        agent = self._find_agent(agent_id)
        if not agent or agent.status != AgentStatus.IDLE:
            return 0

        agent.start_stealing()

        # Steal from main queue
        stolen = self._queue.steal(count=1)
        if stolen and agent.status == AgentStatus.STEALING:
            agent.stop_stealing()
            agent.assign_task(stolen[0])
            return 1

        agent.stop_stealing()
        return 0

    def get_status(self) -> dict[str, Any]:
        """Get executor status.

        Returns:
            Status dictionary
        """
        agent_status = {}
        for agent in self.agents:
            agent_status[agent.agent_id] = {
                "status": agent.status.value,
                "current_task": agent.current_task.task_id if agent.current_task else None,
                "completed_count": agent.completed_count,
            }

        return {
            "total_agents": len(self.agents),
            "agents": agent_status,
            "pending_tasks": self.pending_count(),
            "completed_tasks": self.completed_count(),
            "blocked_tasks": len(self._blocked_tasks),
        }

    def shutdown(self) -> None:
        """Shutdown all agents."""
        for agent in self.agents:
            agent.stop()

    def save(self, filepath: Path) -> None:
        """Save executor state to file.

        Args:
            filepath: Path to save to
        """
        data = {
            "num_agents": len(self.agents),
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "status": a.status.value,
                    "completed_count": a.completed_count,
                }
                for a in self.agents
            ],
            "queue": [
                {
                    "task_id": t.task_id,
                    "name": t.name,
                    "priority": t.priority.value,
                    "status": t.status.value,
                    "dependencies": t.dependencies,
                    "metadata": t.metadata,
                }
                for t in self._queue._heap
            ],
            "blocked": [
                {
                    "task_id": t.task_id,
                    "name": t.name,
                    "priority": t.priority.value,
                    "status": t.status.value,
                    "dependencies": t.dependencies,
                    "metadata": t.metadata,
                }
                for t in self._blocked_tasks
            ],
            "completed_ids": list(self._completed_ids),
        }

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, filepath: Path) -> "ParallelExecutor":
        """Load executor state from file.

        Args:
            filepath: Path to load from

        Returns:
            ParallelExecutor instance
        """
        with open(filepath) as f:
            data = json.load(f)

        executor = cls(num_agents=data["num_agents"])

        # Restore completed IDs first
        executor._completed_ids = set(data.get("completed_ids", []))

        # Restore queue
        for task_data in data.get("queue", []):
            task = Task(
                task_id=task_data["task_id"],
                name=task_data["name"],
                priority=TaskPriority(task_data["priority"]),
                status=TaskStatus(task_data["status"]),
                dependencies=task_data.get("dependencies", []),
                metadata=task_data.get("metadata", {}),
            )
            executor._queue.enqueue(task)

        # Restore blocked tasks
        for task_data in data.get("blocked", []):
            task = Task(
                task_id=task_data["task_id"],
                name=task_data["name"],
                priority=TaskPriority(task_data["priority"]),
                status=TaskStatus(task_data["status"]),
                dependencies=task_data.get("dependencies", []),
                metadata=task_data.get("metadata", {}),
            )
            executor._blocked_tasks.append(task)

        return executor
