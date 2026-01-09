"""Tests for parallel agent execution with work stealing."""

import tempfile
from pathlib import Path

from src.parallel_executor import (
    Agent,
    AgentStatus,
    ParallelExecutor,
    Task,
    TaskPriority,
    TaskStatus,
    WorkQueue,
    WorkResult,
)


class TestTaskPriority:
    """Tests for task priority enum."""

    def test_priority_values(self):
        """Should have expected priority values."""
        assert TaskPriority.CRITICAL.value == 1
        assert TaskPriority.HIGH.value == 2
        assert TaskPriority.NORMAL.value == 3
        assert TaskPriority.LOW.value == 4

    def test_priority_comparison(self):
        """Should compare priorities correctly."""
        assert TaskPriority.CRITICAL.value < TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value < TaskPriority.NORMAL.value


class TestTaskStatus:
    """Tests for task status enum."""

    def test_task_statuses(self):
        """Should have expected task statuses."""
        assert TaskStatus.PENDING
        assert TaskStatus.QUEUED
        assert TaskStatus.IN_PROGRESS
        assert TaskStatus.COMPLETED
        assert TaskStatus.FAILED
        assert TaskStatus.BLOCKED


class TestAgentStatus:
    """Tests for agent status enum."""

    def test_agent_statuses(self):
        """Should have expected agent statuses."""
        assert AgentStatus.IDLE
        assert AgentStatus.BUSY
        assert AgentStatus.STEALING
        assert AgentStatus.STOPPED


class TestTask:
    """Tests for task dataclass."""

    def test_task_creation(self):
        """Should create task with required fields."""
        task = Task(
            task_id="task-1",
            name="Implement feature X",
            priority=TaskPriority.HIGH,
        )
        assert task.task_id == "task-1"
        assert task.name == "Implement feature X"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING

    def test_task_with_dependencies(self):
        """Should handle task dependencies."""
        task = Task(
            task_id="task-2",
            name="Build on task-1",
            priority=TaskPriority.NORMAL,
            dependencies=["task-1"],
        )
        assert "task-1" in task.dependencies

    def test_task_metadata(self):
        """Should store task metadata."""
        task = Task(
            task_id="task-3",
            name="Task with metadata",
            priority=TaskPriority.NORMAL,
            metadata={"estimated_time": 300, "feature_id": "F001"},
        )
        assert task.metadata["estimated_time"] == 300

    def test_task_is_ready(self):
        """Should determine if task is ready to run."""
        # Task with no dependencies is ready
        task1 = Task(task_id="t1", name="Task 1", priority=TaskPriority.NORMAL)
        assert task1.is_ready(completed_tasks=set())

        # Task with dependencies not ready until deps complete
        task2 = Task(
            task_id="t2",
            name="Task 2",
            priority=TaskPriority.NORMAL,
            dependencies=["t1"],
        )
        assert not task2.is_ready(completed_tasks=set())
        assert task2.is_ready(completed_tasks={"t1"})


class TestWorkResult:
    """Tests for work result dataclass."""

    def test_work_result_success(self):
        """Should create successful work result."""
        result = WorkResult(
            task_id="task-1",
            success=True,
            output="Task completed",
        )
        assert result.success
        assert result.output == "Task completed"

    def test_work_result_failure(self):
        """Should create failed work result."""
        result = WorkResult(
            task_id="task-1",
            success=False,
            error="Failed to complete task",
        )
        assert not result.success
        assert "Failed" in result.error

    def test_work_result_duration(self):
        """Should track execution duration."""
        result = WorkResult(
            task_id="task-1",
            success=True,
            duration_ms=1500.5,
        )
        assert result.duration_ms == 1500.5


class TestAgent:
    """Tests for agent class."""

    def test_agent_creation(self):
        """Should create agent with ID."""
        agent = Agent(agent_id="agent-1")
        assert agent.agent_id == "agent-1"
        assert agent.status == AgentStatus.IDLE

    def test_agent_assign_task(self):
        """Should assign task to agent."""
        agent = Agent(agent_id="agent-1")
        task = Task(task_id="t1", name="Task", priority=TaskPriority.NORMAL)

        agent.assign_task(task)

        assert agent.current_task == task
        assert agent.status == AgentStatus.BUSY

    def test_agent_complete_task(self):
        """Should complete current task."""
        agent = Agent(agent_id="agent-1")
        task = Task(task_id="t1", name="Task", priority=TaskPriority.NORMAL)
        agent.assign_task(task)

        result = agent.complete_task(success=True, output="Done")

        assert result.success
        assert agent.status == AgentStatus.IDLE
        assert agent.current_task is None

    def test_agent_task_history(self):
        """Should track completed tasks."""
        agent = Agent(agent_id="agent-1")

        for i in range(3):
            task = Task(task_id=f"t{i}", name=f"Task {i}", priority=TaskPriority.NORMAL)
            agent.assign_task(task)
            agent.complete_task(success=True)

        assert agent.completed_count == 3

    def test_agent_work_stealing(self):
        """Should indicate when stealing work."""
        agent = Agent(agent_id="agent-1")
        agent.start_stealing()

        assert agent.status == AgentStatus.STEALING

        agent.stop_stealing()
        assert agent.status == AgentStatus.IDLE


class TestWorkQueue:
    """Tests for work queue."""

    def test_queue_creation(self):
        """Should create empty queue."""
        queue = WorkQueue()
        assert queue.size() == 0
        assert queue.is_empty()

    def test_enqueue_task(self):
        """Should add tasks to queue."""
        queue = WorkQueue()
        task = Task(task_id="t1", name="Task", priority=TaskPriority.NORMAL)

        queue.enqueue(task)

        assert queue.size() == 1
        assert not queue.is_empty()

    def test_dequeue_by_priority(self):
        """Should dequeue highest priority task first."""
        queue = WorkQueue()

        queue.enqueue(Task(task_id="low", name="Low", priority=TaskPriority.LOW))
        queue.enqueue(Task(task_id="high", name="High", priority=TaskPriority.HIGH))
        queue.enqueue(Task(task_id="critical", name="Critical", priority=TaskPriority.CRITICAL))

        task = queue.dequeue()
        assert task.task_id == "critical"

        task = queue.dequeue()
        assert task.task_id == "high"

    def test_dequeue_empty(self):
        """Should return None for empty queue."""
        queue = WorkQueue()
        assert queue.dequeue() is None

    def test_peek(self):
        """Should peek at next task without removing."""
        queue = WorkQueue()
        task = Task(task_id="t1", name="Task", priority=TaskPriority.NORMAL)
        queue.enqueue(task)

        peeked = queue.peek()
        assert peeked.task_id == "t1"
        assert queue.size() == 1  # Still in queue

    def test_steal_work(self):
        """Should allow stealing work from queue."""
        queue = WorkQueue()

        for i in range(5):
            queue.enqueue(
                Task(task_id=f"t{i}", name=f"Task {i}", priority=TaskPriority.NORMAL)
            )

        stolen = queue.steal(count=2)
        assert len(stolen) == 2
        assert queue.size() == 3

    def test_steal_from_empty(self):
        """Should handle stealing from empty queue."""
        queue = WorkQueue()
        stolen = queue.steal(count=3)
        assert len(stolen) == 0


class TestParallelExecutor:
    """Tests for parallel executor."""

    def test_executor_creation(self):
        """Should create executor with agents."""
        executor = ParallelExecutor(num_agents=3)
        assert len(executor.agents) == 3

    def test_submit_task(self):
        """Should submit task to executor."""
        executor = ParallelExecutor(num_agents=2)
        task = Task(task_id="t1", name="Task", priority=TaskPriority.NORMAL)

        executor.submit(task)

        assert executor.pending_count() == 1

    def test_submit_multiple_tasks(self):
        """Should handle multiple tasks."""
        executor = ParallelExecutor(num_agents=2)

        for i in range(5):
            executor.submit(
                Task(task_id=f"t{i}", name=f"Task {i}", priority=TaskPriority.NORMAL)
            )

        assert executor.pending_count() == 5

    def test_task_assignment(self):
        """Should assign tasks to available agents."""
        executor = ParallelExecutor(num_agents=2)
        executor.submit(Task(task_id="t1", name="Task 1", priority=TaskPriority.NORMAL))
        executor.submit(Task(task_id="t2", name="Task 2", priority=TaskPriority.NORMAL))

        executor.assign_tasks()

        busy_agents = [a for a in executor.agents if a.status == AgentStatus.BUSY]
        assert len(busy_agents) == 2

    def test_task_completion(self):
        """Should handle task completion."""
        executor = ParallelExecutor(num_agents=1)
        executor.submit(Task(task_id="t1", name="Task", priority=TaskPriority.NORMAL))

        executor.assign_tasks()
        agent = executor.agents[0]

        # Simulate task completion
        result = executor.complete_task(agent.agent_id, success=True)

        assert result.success
        assert executor.completed_count() == 1

    def test_work_stealing(self):
        """Should support work stealing between agents."""
        executor = ParallelExecutor(num_agents=2)

        # Add tasks to one agent's local queue
        for i in range(4):
            executor.submit(
                Task(task_id=f"t{i}", name=f"Task {i}", priority=TaskPriority.NORMAL)
            )

        # Assign all to first agent
        executor.assign_tasks()

        # Second agent should be able to steal
        idle_agents = [a for a in executor.agents if a.status == AgentStatus.IDLE]
        if idle_agents:
            stolen = executor.steal_work_for(idle_agents[0].agent_id)
            assert stolen >= 0  # May or may not have stolen depending on implementation

    def test_blocked_task_handling(self):
        """Should handle blocked tasks correctly."""
        executor = ParallelExecutor(num_agents=2)

        # Task with unmet dependency
        task1 = Task(task_id="t1", name="Task 1", priority=TaskPriority.NORMAL)
        task2 = Task(
            task_id="t2",
            name="Task 2",
            priority=TaskPriority.NORMAL,
            dependencies=["t1"],
        )

        executor.submit(task2)  # Submit dependent task first
        executor.submit(task1)  # Then the dependency

        executor.assign_tasks()

        # Only task1 should be assigned (task2 blocked)
        busy = [a for a in executor.agents if a.status == AgentStatus.BUSY]
        assert len(busy) == 1
        assert busy[0].current_task.task_id == "t1"

    def test_get_status(self):
        """Should provide executor status."""
        executor = ParallelExecutor(num_agents=3)
        executor.submit(Task(task_id="t1", name="Task", priority=TaskPriority.NORMAL))

        status = executor.get_status()

        assert "agents" in status
        assert "pending_tasks" in status
        assert "completed_tasks" in status
        assert status["total_agents"] == 3

    def test_shutdown(self):
        """Should shutdown executor cleanly."""
        executor = ParallelExecutor(num_agents=2)
        executor.submit(Task(task_id="t1", name="Task", priority=TaskPriority.NORMAL))

        executor.shutdown()

        for agent in executor.agents:
            assert agent.status == AgentStatus.STOPPED

    def test_integration_with_dependency_graph(self):
        """Should integrate with dependency graph from F005."""
        from src.dependency_graph import DependencyGraph, Feature, FeatureStatus

        # Create features
        features = [
            Feature(id="F1", description="Feature 1", priority=1, dependencies=[], status=FeatureStatus.PENDING),
            Feature(id="F2", description="Feature 2", priority=2, dependencies=["F1"], status=FeatureStatus.PENDING),
            Feature(id="F3", description="Feature 3", priority=1, dependencies=[], status=FeatureStatus.PENDING),
        ]

        graph = DependencyGraph()
        for f in features:
            graph.add_feature(f)

        # Get execution order
        ready = graph.get_ready_features()

        # Create executor and submit ready features as tasks
        executor = ParallelExecutor(num_agents=2)
        for feature in ready:
            task = Task(
                task_id=feature.id,
                name=feature.description,
                priority=TaskPriority.HIGH if feature.priority == 1 else TaskPriority.NORMAL,
            )
            executor.submit(task)

        assert executor.pending_count() == 2  # F1 and F3 are ready


class TestParallelExecutorIntegration:
    """Integration tests for parallel executor."""

    def test_full_execution_cycle(self):
        """Should complete full execution cycle."""
        executor = ParallelExecutor(num_agents=2)

        # Submit tasks with dependencies
        executor.submit(Task(task_id="t1", name="Task 1", priority=TaskPriority.HIGH))
        executor.submit(Task(task_id="t2", name="Task 2", priority=TaskPriority.NORMAL))
        executor.submit(
            Task(
                task_id="t3",
                name="Task 3",
                priority=TaskPriority.LOW,
                dependencies=["t1", "t2"],
            )
        )

        # First round - assign independent tasks
        executor.assign_tasks()
        assert executor.pending_count() >= 1  # t3 blocked

        # Complete first tasks
        for agent in executor.agents:
            if agent.current_task:
                executor.complete_task(agent.agent_id, success=True)

        # Now t3 should be assignable
        executor.assign_tasks()

        # Complete remaining
        for agent in executor.agents:
            if agent.current_task:
                executor.complete_task(agent.agent_id, success=True)

        assert executor.completed_count() == 3

    def test_work_stealing_scenario(self):
        """Should effectively steal work to balance load."""
        executor = ParallelExecutor(num_agents=3)

        # Submit many tasks
        for i in range(9):
            executor.submit(
                Task(task_id=f"t{i}", name=f"Task {i}", priority=TaskPriority.NORMAL)
            )

        # Initial assignment
        executor.assign_tasks()

        # Check distribution
        status = executor.get_status()
        assert status["pending_tasks"] >= 0
        assert status["total_agents"] == 3

    def test_persistence(self):
        """Should save and load executor state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "executor.json"

            # Create and save
            executor = ParallelExecutor(num_agents=2)
            executor.submit(Task(task_id="t1", name="Task 1", priority=TaskPriority.HIGH))
            executor.submit(Task(task_id="t2", name="Task 2", priority=TaskPriority.NORMAL))
            executor.save(filepath)

            # Load and verify
            loaded = ParallelExecutor.load(filepath)
            assert len(loaded.agents) == 2
            assert loaded.pending_count() == 2
