"""Agent communication protocol.

This module provides inter-agent communication for autonomous development:

- Message types and priorities
- Message bus for pub/sub communication
- Agent protocol for standardized messaging
- Request-response patterns
- Message history and persistence
"""

import heapq
import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any


class MessageType(Enum):
    """Types of messages between agents."""

    TASK_ASSIGNMENT = "task_assignment"
    TASK_COMPLETION = "task_completion"
    STATUS_UPDATE = "status_update"
    ERROR_REPORT = "error_report"
    WORK_STEAL_REQUEST = "work_steal_request"
    WORK_STEAL_RESPONSE = "work_steal_response"
    HEARTBEAT = "heartbeat"
    SHUTDOWN = "shutdown"


class MessagePriority(IntEnum):
    """Message priority levels."""

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


@dataclass
class Message:
    """A message between agents."""

    msg_type: MessageType
    sender: str
    recipient: str
    payload: dict[str, Any] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    reply_to: str | None = None

    def __lt__(self, other: "Message") -> bool:
        """Compare by priority then timestamp."""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.timestamp < other.timestamp


class MessageBus:
    """Central message bus for agent communication."""

    def __init__(self) -> None:
        """Initialize message bus."""
        self._queue: list[Message] = []
        self._subscribers: dict[str, Callable[[Message], None]] = {}
        self._history: list[Message] = []
        self._max_history = 1000

    def publish(self, message: Message) -> None:
        """Publish a message to the bus.

        Args:
            message: Message to publish
        """
        heapq.heappush(self._queue, message)

    def subscribe(self, agent_id: str, handler: Callable[[Message], None]) -> None:
        """Subscribe to messages.

        Args:
            agent_id: Agent identifier
            handler: Message handler function
        """
        self._subscribers[agent_id] = handler

    def unsubscribe(self, agent_id: str) -> None:
        """Unsubscribe from messages.

        Args:
            agent_id: Agent identifier
        """
        if agent_id in self._subscribers:
            del self._subscribers[agent_id]

    def deliver(self) -> int:
        """Deliver all pending messages.

        Returns:
            Number of messages delivered
        """
        delivered = 0

        while self._queue:
            message = heapq.heappop(self._queue)

            # Record in history
            self._history.append(message)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

            # Broadcast messages go to all subscribers
            if message.recipient == "*":
                for handler in self._subscribers.values():
                    handler(message)
                    delivered += 1
            elif message.recipient in self._subscribers:
                self._subscribers[message.recipient](message)
                delivered += 1

        return delivered

    def pending_count(self) -> int:
        """Get count of pending messages.

        Returns:
            Number of pending messages
        """
        return len(self._queue)

    def get_history(self, limit: int = 100) -> list[Message]:
        """Get message history.

        Args:
            limit: Maximum number of messages

        Returns:
            List of recent messages
        """
        return self._history[-limit:]

    def save_history(self, filepath: Path) -> None:
        """Save message history to file.

        Args:
            filepath: Path to save to
        """
        data = [
            {
                "msg_type": m.msg_type.value,
                "sender": m.sender,
                "recipient": m.recipient,
                "payload": m.payload,
                "priority": m.priority.value,
                "msg_id": m.msg_id,
                "timestamp": m.timestamp,
                "reply_to": m.reply_to,
            }
            for m in self._history
        ]

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_history(cls, filepath: Path) -> list[Message]:
        """Load message history from file.

        Args:
            filepath: Path to load from

        Returns:
            List of messages
        """
        with open(filepath) as f:
            data = json.load(f)

        messages = []
        for m_data in data:
            msg = Message(
                msg_type=MessageType(m_data["msg_type"]),
                sender=m_data["sender"],
                recipient=m_data["recipient"],
                payload=m_data.get("payload", {}),
                priority=MessagePriority(m_data.get("priority", 3)),
                msg_id=m_data.get("msg_id", str(uuid.uuid4())),
                timestamp=m_data.get("timestamp", time.time()),
                reply_to=m_data.get("reply_to"),
            )
            messages.append(msg)

        return messages


class AgentProtocol:
    """Protocol for agent communication."""

    def __init__(self, agent_id: str, bus: MessageBus | None = None) -> None:
        """Initialize agent protocol.

        Args:
            agent_id: Agent identifier
            bus: Message bus to use
        """
        self.agent_id = agent_id
        self._bus = bus or MessageBus()
        self._handlers: list[Callable[[Message], None]] = []

        # Subscribe to the bus
        self._bus.subscribe(agent_id, self._handle_message)

    def _handle_message(self, message: Message) -> None:
        """Internal message handler.

        Args:
            message: Received message
        """
        for handler in self._handlers:
            handler(message)

    def on_message(self, handler: Callable[[Message], None]) -> None:
        """Register message handler.

        Args:
            handler: Handler function
        """
        self._handlers.append(handler)

    def send(self, message: Message) -> None:
        """Send a message.

        Args:
            message: Message to send
        """
        self._bus.publish(message)

    def send_task_completion(
        self,
        task_id: str,
        success: bool,
        output: str | None = None,
        error: str | None = None,
    ) -> None:
        """Send task completion message.

        Args:
            task_id: Task identifier
            success: Whether task succeeded
            output: Task output
            error: Error message if failed
        """
        self.send(Message(
            msg_type=MessageType.TASK_COMPLETION,
            sender=self.agent_id,
            recipient="orchestrator",
            payload={
                "task_id": task_id,
                "success": success,
                "output": output,
                "error": error,
            },
        ))

    def send_status_update(
        self,
        status: str,
        progress: int = 0,
        current_task: str | None = None,
    ) -> None:
        """Send status update message.

        Args:
            status: Current status
            progress: Progress percentage
            current_task: Current task ID
        """
        self.send(Message(
            msg_type=MessageType.STATUS_UPDATE,
            sender=self.agent_id,
            recipient="orchestrator",
            payload={
                "status": status,
                "progress": progress,
                "current_task": current_task,
            },
        ))

    def send_error_report(
        self,
        error_type: str,
        error_message: str,
        task_id: str | None = None,
    ) -> None:
        """Send error report message.

        Args:
            error_type: Type of error
            error_message: Error message
            task_id: Related task ID
        """
        self.send(Message(
            msg_type=MessageType.ERROR_REPORT,
            sender=self.agent_id,
            recipient="orchestrator",
            priority=MessagePriority.HIGH,
            payload={
                "error_type": error_type,
                "error_message": error_message,
                "task_id": task_id,
            },
        ))

    def request_work_steal(self, target: str = "orchestrator") -> None:
        """Request work to steal.

        Args:
            target: Agent to request from
        """
        self.send(Message(
            msg_type=MessageType.WORK_STEAL_REQUEST,
            sender=self.agent_id,
            recipient=target,
        ))

    def send_heartbeat(self) -> None:
        """Send heartbeat message."""
        self.send(Message(
            msg_type=MessageType.HEARTBEAT,
            sender=self.agent_id,
            recipient="orchestrator",
            priority=MessagePriority.LOW,
            payload={
                "timestamp": time.time(),
            },
        ))
