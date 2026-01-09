"""Context pressure monitoring and checkpointing.

This module provides intelligent context management for long-running autonomous
development sessions. It includes:

- Context pressure monitoring
- Hierarchical memory (hot/warm/cold tiers)
- Automatic checkpointing
- Context compression
- Checkpoint persistence
"""

import contextlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ContextTier(Enum):
    """Tiers for hierarchical context memory."""

    HOT = ("hot", 180)  # Current task, < 3 minutes
    WARM = ("warm", 1800)  # Recent decisions, < 30 minutes
    COLD = ("cold", 86400)  # Archived, < 24 hours

    def __init__(self, name: str, max_age: int) -> None:
        self._name = name
        self._max_age = max_age

    @property
    def max_age_seconds(self) -> int:
        """Maximum age in seconds before promotion/demotion."""
        return self._max_age


@dataclass
class ContextPressure:
    """Represents current context pressure state."""

    current_tokens: int
    max_tokens: int

    @property
    def percentage(self) -> float:
        """Context usage as percentage."""
        if self.max_tokens == 0:
            return 0
        return (self.current_tokens / self.max_tokens) * 100

    @property
    def level(self) -> str:
        """Pressure level as string."""
        pct = self.percentage
        if pct >= 90:
            return "critical"
        elif pct >= 70:
            return "high"
        elif pct >= 30:
            return "medium"
        return "low"

    @property
    def should_checkpoint(self) -> bool:
        """Whether a checkpoint should be created."""
        return self.percentage >= 70


@dataclass
class ContextEntry:
    """A single context entry with metadata."""

    key: str
    value: Any
    tier: ContextTier
    created_at: float = field(default_factory=time.time)

    @property
    def age_seconds(self) -> float:
        """Age of this entry in seconds."""
        return time.time() - self.created_at

    @property
    def is_stale(self) -> bool:
        """Whether this entry is stale for its tier."""
        return self.age_seconds > self.tier.max_age_seconds


@dataclass
class ContextCheckpoint:
    """A snapshot of context state for persistence."""

    session_id: str
    progress_summary: str
    hot_context: dict[str, Any]
    warm_context: dict[str, Any]
    cold_context: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def save(self, filepath: Path) -> None:
        """Save checkpoint to file.

        Args:
            filepath: Path to save the checkpoint
        """
        data = {
            "session_id": self.session_id,
            "progress_summary": self.progress_summary,
            "hot_context": self.hot_context,
            "warm_context": self.warm_context,
            "cold_context": self.cold_context,
            "created_at": self.created_at,
        }
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

    @classmethod
    def load(cls, filepath: Path) -> "ContextCheckpoint":
        """Load checkpoint from file.

        Args:
            filepath: Path to load the checkpoint from

        Returns:
            Loaded ContextCheckpoint
        """
        with open(filepath) as f:
            data = json.load(f)

        return cls(
            session_id=data["session_id"],
            progress_summary=data["progress_summary"],
            hot_context=data.get("hot_context", {}),
            warm_context=data.get("warm_context", {}),
            cold_context=data.get("cold_context", {}),
            created_at=data.get("created_at", time.time()),
        )


class ContextManager:
    """Manages context pressure and hierarchical memory.

    This class provides:
    - Context pressure monitoring
    - Hierarchical memory (hot/warm/cold)
    - Automatic checkpointing
    - Context compression
    """

    def __init__(
        self,
        max_tokens: int = 100000,
        checkpoint_dir: Path | None = None,
        pressure_callback: Callable[[ContextPressure], None] | None = None,
        pressure_threshold: float = 0.7,
        max_checkpoints: int = 10,
    ) -> None:
        """Initialize context manager.

        Args:
            max_tokens: Maximum tokens before critical pressure
            checkpoint_dir: Directory to store checkpoints
            pressure_callback: Callback when pressure threshold exceeded
            pressure_threshold: Threshold to trigger callback (0-1)
            max_checkpoints: Maximum checkpoints to keep
        """
        self.max_tokens = max_tokens
        self.checkpoint_dir = checkpoint_dir or Path(".claude/checkpoints")
        self.pressure_callback = pressure_callback
        self.pressure_threshold = pressure_threshold
        self.max_checkpoints = max_checkpoints
        self._entries: dict[str, ContextEntry] = {}

    def add(
        self,
        key: str,
        value: Any,
        tier: ContextTier = ContextTier.HOT,
    ) -> None:
        """Add or update a context entry.

        Args:
            key: Unique key for the entry
            value: The value to store
            tier: Context tier (default: HOT)
        """
        self._entries[key] = ContextEntry(
            key=key,
            value=value,
            tier=tier,
        )

        # Check pressure after adding
        self._check_pressure()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a context value by key.

        Args:
            key: The key to look up
            default: Default value if not found

        Returns:
            The stored value or default
        """
        entry = self._entries.get(key)
        if entry is None:
            return default
        return entry.value

    def remove(self, key: str) -> None:
        """Remove a context entry.

        Args:
            key: The key to remove
        """
        self._entries.pop(key, None)

    def clear_tier(self, tier: ContextTier) -> None:
        """Clear all entries in a tier.

        Args:
            tier: The tier to clear
        """
        keys_to_remove = [
            key for key, entry in self._entries.items() if entry.tier == tier
        ]
        for key in keys_to_remove:
            del self._entries[key]

    def get_tier(self, tier: ContextTier) -> list[ContextEntry]:
        """Get all entries in a tier.

        Args:
            tier: The tier to get entries from

        Returns:
            List of entries in the tier
        """
        return [entry for entry in self._entries.values() if entry.tier == tier]

    def promote(self, key: str, target_tier: ContextTier) -> None:
        """Promote an entry to a higher priority tier.

        Args:
            key: The key to promote
            target_tier: The tier to promote to
        """
        if key in self._entries:
            self._entries[key].tier = target_tier
            self._entries[key].created_at = time.time()

    def demote(self, key: str, target_tier: ContextTier) -> None:
        """Demote an entry to a lower priority tier.

        Args:
            key: The key to demote
            target_tier: The tier to demote to
        """
        if key in self._entries:
            self._entries[key].tier = target_tier

    def demote_stale(self) -> None:
        """Auto-demote stale entries to lower tiers."""
        for _key, entry in list(self._entries.items()):
            if entry.is_stale:
                if entry.tier == ContextTier.HOT:
                    entry.tier = ContextTier.WARM
                elif entry.tier == ContextTier.WARM:
                    entry.tier = ContextTier.COLD

    def estimate_tokens(self) -> int:
        """Estimate total tokens used by current context.

        Uses rough approximation of ~4 characters per token.

        Returns:
            Estimated token count
        """
        total_chars = 0
        for entry in self._entries.values():
            value_str = str(entry.value)
            total_chars += len(entry.key) + len(value_str)

        # Rough approximation: 4 chars per token
        return total_chars // 4

    @property
    def pressure(self) -> ContextPressure:
        """Get current context pressure."""
        return ContextPressure(
            current_tokens=self.estimate_tokens(),
            max_tokens=self.max_tokens,
        )

    def _check_pressure(self) -> None:
        """Check pressure and call callback if threshold exceeded."""
        pressure = self.pressure
        if self.pressure_callback and pressure.percentage >= (
            self.pressure_threshold * 100
        ):
            self.pressure_callback(pressure)

    def should_checkpoint(self) -> bool:
        """Whether a checkpoint should be created now.

        Returns:
            True if checkpoint recommended
        """
        return self.pressure.should_checkpoint

    def create_checkpoint(
        self,
        session_id: str,
        progress_summary: str,
    ) -> ContextCheckpoint:
        """Create a checkpoint of current context.

        Args:
            session_id: Identifier for this session
            progress_summary: Summary of progress so far

        Returns:
            Created ContextCheckpoint
        """
        # Gather context by tier
        hot_context = {
            entry.key: entry.value
            for entry in self._entries.values()
            if entry.tier == ContextTier.HOT
        }
        warm_context = {
            entry.key: entry.value
            for entry in self._entries.values()
            if entry.tier == ContextTier.WARM
        }
        cold_context = {
            entry.key: entry.value
            for entry in self._entries.values()
            if entry.tier == ContextTier.COLD
        }

        checkpoint = ContextCheckpoint(
            session_id=session_id,
            progress_summary=progress_summary,
            hot_context=hot_context,
            warm_context=warm_context,
            cold_context=cold_context,
        )

        # Save to file
        filename = f"checkpoint-{session_id}-{int(time.time())}.json"
        filepath = self.checkpoint_dir / filename
        checkpoint.save(filepath)

        # Cleanup old checkpoints
        self._cleanup_old_checkpoints()

        return checkpoint

    def restore_checkpoint(self, filepath: Path) -> None:
        """Restore context from a checkpoint file.

        Args:
            filepath: Path to checkpoint file
        """
        checkpoint = ContextCheckpoint.load(filepath)

        # Clear current context
        self._entries.clear()

        # Restore hot context
        for key, value in checkpoint.hot_context.items():
            self.add(key, value, tier=ContextTier.HOT)

        # Restore warm context
        for key, value in checkpoint.warm_context.items():
            self.add(key, value, tier=ContextTier.WARM)

        # Restore cold context
        for key, value in checkpoint.cold_context.items():
            self.add(key, value, tier=ContextTier.COLD)

    def compress(self) -> None:
        """Compress context to reduce token usage.

        This is a simple implementation that truncates long values.
        A more sophisticated version could use semantic summarization.
        """
        for entry in self._entries.values():
            if isinstance(entry.value, str) and len(entry.value) > 500:
                # Truncate long strings
                entry.value = entry.value[:200] + "... [truncated]"

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of current context state.

        Returns:
            Dictionary with context state summary
        """
        return {
            "hot_count": len(self.get_tier(ContextTier.HOT)),
            "warm_count": len(self.get_tier(ContextTier.WARM)),
            "cold_count": len(self.get_tier(ContextTier.COLD)),
            "total_entries": len(self._entries),
            "estimated_tokens": self.estimate_tokens(),
            "pressure": self.pressure.percentage,
            "pressure_level": self.pressure.level,
        }

    def list_checkpoints(self) -> list[Path]:
        """List available checkpoint files.

        Returns:
            List of checkpoint file paths
        """
        if not self.checkpoint_dir.exists():
            return []

        return sorted(
            self.checkpoint_dir.glob("checkpoint-*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

    def _cleanup_old_checkpoints(self) -> None:
        """Remove old checkpoints beyond max_checkpoints."""
        checkpoints = self.list_checkpoints()

        # Remove oldest checkpoints beyond limit
        for old_checkpoint in checkpoints[self.max_checkpoints :]:
            with contextlib.suppress(OSError):
                old_checkpoint.unlink()
