"""Tests for agent communication protocol."""

import tempfile
from pathlib import Path

from src.agent_protocol import (
    AgentProtocol,
    Message,
    MessageBus,
    MessagePriority,
    MessageType,
)


class TestMessageType:
    """Tests for message types."""

    def test_message_types(self):
        """Should have expected message types."""
        assert MessageType.TASK_ASSIGNMENT
        assert MessageType.TASK_COMPLETION
        assert MessageType.STATUS_UPDATE
        assert MessageType.ERROR_REPORT
        assert MessageType.WORK_STEAL_REQUEST
        assert MessageType.WORK_STEAL_RESPONSE
        assert MessageType.HEARTBEAT
        assert MessageType.SHUTDOWN


class TestMessagePriority:
    """Tests for message priority."""

    def test_priority_values(self):
        """Should have expected priority values."""
        assert MessagePriority.CRITICAL.value < MessagePriority.HIGH.value
        assert MessagePriority.HIGH.value < MessagePriority.NORMAL.value
        assert MessagePriority.NORMAL.value < MessagePriority.LOW.value


class TestMessage:
    """Tests for message dataclass."""

    def test_message_creation(self):
        """Should create message with required fields."""
        msg = Message(
            msg_type=MessageType.TASK_ASSIGNMENT,
            sender="orchestrator",
            recipient="agent-1",
            payload={"task_id": "t1", "name": "Task 1"},
        )
        assert msg.msg_type == MessageType.TASK_ASSIGNMENT
        assert msg.sender == "orchestrator"
        assert msg.recipient == "agent-1"
        assert msg.payload["task_id"] == "t1"

    def test_message_id_generated(self):
        """Should auto-generate message ID."""
        msg = Message(
            msg_type=MessageType.HEARTBEAT,
            sender="agent-1",
            recipient="orchestrator",
        )
        assert msg.msg_id is not None
        assert len(msg.msg_id) > 0

    def test_message_timestamp(self):
        """Should auto-generate timestamp."""
        msg = Message(
            msg_type=MessageType.HEARTBEAT,
            sender="agent-1",
            recipient="orchestrator",
        )
        assert msg.timestamp is not None
        assert msg.timestamp > 0

    def test_message_priority_default(self):
        """Should default to NORMAL priority."""
        msg = Message(
            msg_type=MessageType.STATUS_UPDATE,
            sender="agent-1",
            recipient="orchestrator",
        )
        assert msg.priority == MessagePriority.NORMAL

    def test_message_with_priority(self):
        """Should allow custom priority."""
        msg = Message(
            msg_type=MessageType.ERROR_REPORT,
            sender="agent-1",
            recipient="orchestrator",
            priority=MessagePriority.CRITICAL,
        )
        assert msg.priority == MessagePriority.CRITICAL

    def test_message_reply_to(self):
        """Should support reply_to for request-response."""
        original = Message(
            msg_type=MessageType.WORK_STEAL_REQUEST,
            sender="agent-1",
            recipient="orchestrator",
        )
        reply = Message(
            msg_type=MessageType.WORK_STEAL_RESPONSE,
            sender="orchestrator",
            recipient="agent-1",
            reply_to=original.msg_id,
        )
        assert reply.reply_to == original.msg_id


class TestMessageBus:
    """Tests for message bus."""

    def test_bus_creation(self):
        """Should create message bus."""
        bus = MessageBus()
        assert bus is not None

    def test_publish_message(self):
        """Should publish messages."""
        bus = MessageBus()
        msg = Message(
            msg_type=MessageType.TASK_ASSIGNMENT,
            sender="orchestrator",
            recipient="agent-1",
            payload={"task": "test"},
        )
        bus.publish(msg)
        assert bus.pending_count() == 1

    def test_subscribe_to_messages(self):
        """Should allow subscribing to message types."""
        bus = MessageBus()
        received = []

        def handler(msg):
            received.append(msg)

        bus.subscribe("agent-1", handler)

        msg = Message(
            msg_type=MessageType.TASK_ASSIGNMENT,
            sender="orchestrator",
            recipient="agent-1",
        )
        bus.publish(msg)
        bus.deliver()

        assert len(received) == 1

    def test_broadcast_message(self):
        """Should support broadcast to all agents."""
        bus = MessageBus()
        received_1 = []
        received_2 = []

        bus.subscribe("agent-1", lambda m: received_1.append(m))
        bus.subscribe("agent-2", lambda m: received_2.append(m))

        msg = Message(
            msg_type=MessageType.SHUTDOWN,
            sender="orchestrator",
            recipient="*",  # Broadcast
        )
        bus.publish(msg)
        bus.deliver()

        assert len(received_1) == 1
        assert len(received_2) == 1

    def test_priority_ordering(self):
        """Should deliver higher priority messages first."""
        bus = MessageBus()
        delivered = []

        bus.subscribe("agent-1", lambda m: delivered.append(m))

        bus.publish(Message(
            msg_type=MessageType.STATUS_UPDATE,
            sender="orchestrator",
            recipient="agent-1",
            priority=MessagePriority.LOW,
            payload={"order": "low"},
        ))
        bus.publish(Message(
            msg_type=MessageType.ERROR_REPORT,
            sender="orchestrator",
            recipient="agent-1",
            priority=MessagePriority.CRITICAL,
            payload={"order": "critical"},
        ))
        bus.publish(Message(
            msg_type=MessageType.TASK_ASSIGNMENT,
            sender="orchestrator",
            recipient="agent-1",
            priority=MessagePriority.NORMAL,
            payload={"order": "normal"},
        ))

        bus.deliver()

        # Critical should be first
        assert delivered[0].payload["order"] == "critical"

    def test_unsubscribe(self):
        """Should allow unsubscribing."""
        bus = MessageBus()
        received = []

        def handler(m):
            received.append(m)

        bus.subscribe("agent-1", handler)
        bus.unsubscribe("agent-1")

        bus.publish(Message(
            msg_type=MessageType.HEARTBEAT,
            sender="orchestrator",
            recipient="agent-1",
        ))
        bus.deliver()

        assert len(received) == 0

    def test_message_history(self):
        """Should keep message history."""
        bus = MessageBus()
        bus.subscribe("agent-1", lambda m: None)

        for i in range(5):
            bus.publish(Message(
                msg_type=MessageType.STATUS_UPDATE,
                sender=f"agent-{i}",
                recipient="agent-1",
            ))
        bus.deliver()

        history = bus.get_history(limit=3)
        assert len(history) == 3


class TestAgentProtocol:
    """Tests for agent protocol."""

    def test_protocol_creation(self):
        """Should create protocol for agent."""
        protocol = AgentProtocol(agent_id="agent-1")
        assert protocol.agent_id == "agent-1"

    def test_send_task_completion(self):
        """Should send task completion message."""
        bus = MessageBus()
        protocol = AgentProtocol(agent_id="agent-1", bus=bus)

        protocol.send_task_completion(
            task_id="t1",
            success=True,
            output="Task completed",
        )

        assert bus.pending_count() == 1

    def test_send_status_update(self):
        """Should send status update."""
        bus = MessageBus()
        protocol = AgentProtocol(agent_id="agent-1", bus=bus)

        protocol.send_status_update(
            status="idle",
            progress=50,
        )

        assert bus.pending_count() == 1

    def test_send_error_report(self):
        """Should send error report."""
        bus = MessageBus()
        protocol = AgentProtocol(agent_id="agent-1", bus=bus)

        protocol.send_error_report(
            error_type="TestError",
            error_message="Test failed",
            task_id="t1",
        )

        assert bus.pending_count() == 1

    def test_request_work_steal(self):
        """Should request work to steal."""
        bus = MessageBus()
        protocol = AgentProtocol(agent_id="agent-1", bus=bus)

        protocol.request_work_steal()

        assert bus.pending_count() == 1
        msg = bus._queue[0]
        assert msg.msg_type == MessageType.WORK_STEAL_REQUEST

    def test_send_heartbeat(self):
        """Should send heartbeat."""
        bus = MessageBus()
        protocol = AgentProtocol(agent_id="agent-1", bus=bus)

        protocol.send_heartbeat()

        assert bus.pending_count() == 1
        msg = bus._queue[0]
        assert msg.msg_type == MessageType.HEARTBEAT

    def test_receive_message(self):
        """Should receive messages."""
        bus = MessageBus()
        protocol = AgentProtocol(agent_id="agent-1", bus=bus)
        received = []

        protocol.on_message(lambda m: received.append(m))

        bus.publish(Message(
            msg_type=MessageType.TASK_ASSIGNMENT,
            sender="orchestrator",
            recipient="agent-1",
            payload={"task_id": "t1"},
        ))
        bus.deliver()

        assert len(received) == 1
        assert received[0].payload["task_id"] == "t1"

    def test_request_response(self):
        """Should support request-response pattern."""
        bus = MessageBus()
        agent1 = AgentProtocol(agent_id="agent-1", bus=bus)
        agent2 = AgentProtocol(agent_id="agent-2", bus=bus)

        responses = []

        # Agent 2 responds to work steal requests
        def handle_request(msg):
            if msg.msg_type == MessageType.WORK_STEAL_REQUEST:
                agent2.send(Message(
                    msg_type=MessageType.WORK_STEAL_RESPONSE,
                    sender="agent-2",
                    recipient="agent-1",
                    reply_to=msg.msg_id,
                    payload={"tasks": ["t1", "t2"]},
                ))

        agent2.on_message(handle_request)

        # Agent 1 collects responses
        agent1.on_message(lambda m: responses.append(m) if m.msg_type == MessageType.WORK_STEAL_RESPONSE else None)

        # Agent 1 requests work
        agent1.send(Message(
            msg_type=MessageType.WORK_STEAL_REQUEST,
            sender="agent-1",
            recipient="agent-2",
        ))

        # Deliver messages
        bus.deliver()
        bus.deliver()

        assert len(responses) == 1
        assert "tasks" in responses[0].payload


class TestAgentProtocolIntegration:
    """Integration tests for agent protocol."""

    def test_multi_agent_communication(self):
        """Should support multi-agent communication."""
        bus = MessageBus()

        # Create multiple agents
        orchestrator = AgentProtocol(agent_id="orchestrator", bus=bus)
        agents = [AgentProtocol(agent_id=f"agent-{i}", bus=bus) for i in range(3)]

        completions = []

        # Orchestrator receives completions
        orchestrator.on_message(lambda m: completions.append(m) if m.msg_type == MessageType.TASK_COMPLETION else None)

        # Each agent completes a task
        for i, agent in enumerate(agents):
            agent.send_task_completion(
                task_id=f"task-{i}",
                success=True,
            )

        bus.deliver()

        assert len(completions) == 3

    def test_integration_with_parallel_executor(self):
        """Should integrate with parallel executor from F011."""
        from src.parallel_executor import ParallelExecutor, Task, TaskPriority

        bus = MessageBus()

        # Create executor
        executor = ParallelExecutor(num_agents=2)

        # Create protocols for each agent
        protocols = {
            agent.agent_id: AgentProtocol(agent_id=agent.agent_id, bus=bus)
            for agent in executor.agents
        }

        # Submit task
        task = Task(task_id="t1", name="Test Task", priority=TaskPriority.NORMAL)
        executor.submit(task)
        executor.assign_tasks()

        # Find assigned agent and send completion
        for agent in executor.agents:
            if agent.current_task:
                protocol = protocols[agent.agent_id]
                protocol.send_task_completion(
                    task_id=agent.current_task.task_id,
                    success=True,
                )
                executor.complete_task(agent.agent_id, success=True)

        assert executor.completed_count() == 1
        assert bus.pending_count() == 1

    def test_persistence(self):
        """Should save and load message history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "messages.json"

            bus = MessageBus()
            protocol = AgentProtocol(agent_id="agent-1", bus=bus)

            protocol.send_heartbeat()
            protocol.send_status_update(status="working", progress=50)
            bus.deliver()

            bus.save_history(filepath)

            # Load and verify
            loaded_history = MessageBus.load_history(filepath)
            assert len(loaded_history) >= 2
