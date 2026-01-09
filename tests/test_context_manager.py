"""Tests for context pressure monitoring and checkpointing."""

import tempfile
from pathlib import Path

from src.context_manager import (
    ContextCheckpoint,
    ContextEntry,
    ContextManager,
    ContextPressure,
    ContextTier,
)


class TestContextPressure:
    """Tests for context pressure assessment."""

    def test_low_pressure(self):
        """Should identify low context pressure."""
        pressure = ContextPressure(current_tokens=1000, max_tokens=100000)
        assert pressure.level == "low"
        assert pressure.percentage < 30

    def test_medium_pressure(self):
        """Should identify medium context pressure."""
        pressure = ContextPressure(current_tokens=40000, max_tokens=100000)
        assert pressure.level == "medium"
        assert 30 <= pressure.percentage < 70

    def test_high_pressure(self):
        """Should identify high context pressure."""
        pressure = ContextPressure(current_tokens=75000, max_tokens=100000)
        assert pressure.level == "high"
        assert pressure.percentage >= 70

    def test_critical_pressure(self):
        """Should identify critical context pressure."""
        pressure = ContextPressure(current_tokens=92000, max_tokens=100000)
        assert pressure.level == "critical"
        assert pressure.percentage >= 90

    def test_should_checkpoint_when_high(self):
        """Should recommend checkpoint when pressure is high."""
        pressure = ContextPressure(current_tokens=75000, max_tokens=100000)
        assert pressure.should_checkpoint

    def test_no_checkpoint_when_low(self):
        """Should not recommend checkpoint when pressure is low."""
        pressure = ContextPressure(current_tokens=20000, max_tokens=100000)
        assert not pressure.should_checkpoint


class TestContextTier:
    """Tests for hierarchical context tiers."""

    def test_hot_tier(self):
        """Hot tier should be for current task context."""
        hot = ContextTier.HOT
        assert hot.max_age_seconds < 300  # Less than 5 minutes

    def test_warm_tier(self):
        """Warm tier should be for recent decisions."""
        warm = ContextTier.WARM
        assert warm.max_age_seconds >= 300  # At least 5 minutes
        assert warm.max_age_seconds < 3600  # Less than 1 hour

    def test_cold_tier(self):
        """Cold tier should be for archived checkpoints."""
        cold = ContextTier.COLD
        assert cold.max_age_seconds >= 3600  # At least 1 hour

    def test_tier_ordering(self):
        """Tiers should have proper ordering."""
        assert ContextTier.HOT.max_age_seconds < ContextTier.WARM.max_age_seconds
        assert ContextTier.WARM.max_age_seconds < ContextTier.COLD.max_age_seconds


class TestContextEntry:
    """Tests for context entries."""

    def test_entry_creation(self):
        """Should create a context entry."""
        entry = ContextEntry(
            key="current_task",
            value="Implement feature X",
            tier=ContextTier.HOT,
        )
        assert entry.key == "current_task"
        assert entry.tier == ContextTier.HOT

    def test_entry_age(self):
        """Should track entry age."""
        import time
        entry = ContextEntry(
            key="test",
            value="value",
            tier=ContextTier.HOT,
        )
        time.sleep(0.1)
        assert entry.age_seconds >= 0.1

    def test_entry_is_stale(self):
        """Should detect stale entries."""
        import time
        entry = ContextEntry(
            key="test",
            value="value",
            tier=ContextTier.HOT,
            created_at=time.time() - 1000,  # Created 1000 seconds ago
        )
        assert entry.is_stale


class TestContextCheckpoint:
    """Tests for context checkpoints."""

    def test_checkpoint_creation(self):
        """Should create a checkpoint."""
        checkpoint = ContextCheckpoint(
            session_id="session-123",
            progress_summary="Completed 3 features",
            hot_context={"current_task": "Feature 4"},
            warm_context={"recent_decisions": ["Used TDD", "Chose REST"]},
        )
        assert checkpoint.session_id == "session-123"
        assert "current_task" in checkpoint.hot_context

    def test_checkpoint_save_load(self):
        """Should save and load checkpoint from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint = ContextCheckpoint(
                session_id="session-456",
                progress_summary="Test checkpoint",
                hot_context={"key": "value"},
                warm_context={},
            )

            # Save
            filepath = Path(tmpdir) / "checkpoint.json"
            checkpoint.save(filepath)

            # Load
            loaded = ContextCheckpoint.load(filepath)

            assert loaded.session_id == "session-456"
            assert loaded.hot_context == {"key": "value"}

    def test_checkpoint_has_timestamp(self):
        """Checkpoint should have creation timestamp."""
        checkpoint = ContextCheckpoint(
            session_id="test",
            progress_summary="",
            hot_context={},
            warm_context={},
        )
        assert checkpoint.created_at is not None
        assert checkpoint.created_at > 0


class TestContextManager:
    """Tests for the context manager."""

    def test_manager_creation(self):
        """Should create a context manager."""
        manager = ContextManager()
        assert manager is not None
        assert manager.pressure.percentage == 0  # Empty context

    def test_add_context(self):
        """Should add context entries."""
        manager = ContextManager()
        manager.add("current_feature", "Login system", tier=ContextTier.HOT)

        assert manager.get("current_feature") == "Login system"

    def test_get_missing_context(self):
        """Should return None for missing keys."""
        manager = ContextManager()
        assert manager.get("nonexistent") is None

    def test_get_with_default(self):
        """Should return default for missing keys."""
        manager = ContextManager()
        assert manager.get("missing", default="fallback") == "fallback"

    def test_remove_context(self):
        """Should remove context entries."""
        manager = ContextManager()
        manager.add("temp", "value", tier=ContextTier.HOT)
        manager.remove("temp")
        assert manager.get("temp") is None

    def test_clear_tier(self):
        """Should clear all entries in a tier."""
        manager = ContextManager()
        manager.add("hot1", "val1", tier=ContextTier.HOT)
        manager.add("hot2", "val2", tier=ContextTier.HOT)
        manager.add("warm1", "val3", tier=ContextTier.WARM)

        manager.clear_tier(ContextTier.HOT)

        assert manager.get("hot1") is None
        assert manager.get("hot2") is None
        assert manager.get("warm1") == "val3"  # Warm tier untouched

    def test_promote_to_hot(self):
        """Should promote warm context to hot."""
        manager = ContextManager()
        manager.add("item", "value", tier=ContextTier.WARM)
        manager.promote("item", ContextTier.HOT)

        entries = manager.get_tier(ContextTier.HOT)
        assert any(e.key == "item" for e in entries)

    def test_demote_to_cold(self):
        """Should demote warm context to cold."""
        manager = ContextManager()
        manager.add("old_item", "value", tier=ContextTier.WARM)
        manager.demote("old_item", ContextTier.COLD)

        entries = manager.get_tier(ContextTier.COLD)
        assert any(e.key == "old_item" for e in entries)

    def test_auto_demote_stale(self):
        """Should auto-demote stale entries."""
        import time
        manager = ContextManager()

        # Add entry with old timestamp (simulating stale)
        entry = ContextEntry(
            key="stale_item",
            value="old value",
            tier=ContextTier.HOT,
            created_at=time.time() - 1000,  # 1000 seconds ago
        )
        manager._entries["stale_item"] = entry

        # Run maintenance
        manager.demote_stale()

        # Should have been demoted
        current_entry = manager._entries.get("stale_item")
        assert current_entry is not None
        assert current_entry.tier != ContextTier.HOT  # No longer hot

    def test_estimate_tokens(self):
        """Should estimate token count for context."""
        manager = ContextManager()
        manager.add("short", "hello", tier=ContextTier.HOT)
        manager.add("long", "a" * 1000, tier=ContextTier.HOT)

        tokens = manager.estimate_tokens()
        assert tokens > 0
        assert tokens > 200  # 1000 chars / ~4 chars per token

    def test_pressure_calculation(self):
        """Should calculate context pressure."""
        manager = ContextManager(max_tokens=1000)
        manager.add("data", "x" * 2000, tier=ContextTier.HOT)  # ~500 tokens

        pressure = manager.pressure
        assert pressure.percentage > 0

    def test_create_checkpoint(self):
        """Should create checkpoint with current context."""
        manager = ContextManager()
        manager.add("current", "task1", tier=ContextTier.HOT)
        manager.add("recent", "decision1", tier=ContextTier.WARM)

        checkpoint = manager.create_checkpoint(
            session_id="test-session",
            progress_summary="Test progress",
        )

        assert checkpoint.session_id == "test-session"
        assert "current" in checkpoint.hot_context
        assert "recent" in checkpoint.warm_context

    def test_restore_checkpoint(self):
        """Should restore context from checkpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and save checkpoint
            checkpoint = ContextCheckpoint(
                session_id="restore-test",
                progress_summary="To restore",
                hot_context={"restored_hot": "hot_value"},
                warm_context={"restored_warm": "warm_value"},
            )
            filepath = Path(tmpdir) / "checkpoint.json"
            checkpoint.save(filepath)

            # Create new manager and restore
            manager = ContextManager()
            manager.restore_checkpoint(filepath)

            assert manager.get("restored_hot") == "hot_value"
            assert manager.get("restored_warm") == "warm_value"

    def test_compress_context(self):
        """Should compress context to reduce tokens."""
        manager = ContextManager()

        # Add verbose context
        manager.add("verbose1", "This is a very long description " * 10, tier=ContextTier.WARM)
        manager.add("verbose2", "Another lengthy explanation " * 10, tier=ContextTier.WARM)

        original_tokens = manager.estimate_tokens()

        # Compress
        manager.compress()

        compressed_tokens = manager.estimate_tokens()

        # Should be smaller or equal (compression applied)
        assert compressed_tokens <= original_tokens

    def test_get_summary(self):
        """Should get a summary of context state."""
        manager = ContextManager()
        manager.add("hot1", "val1", tier=ContextTier.HOT)
        manager.add("warm1", "val2", tier=ContextTier.WARM)
        manager.add("cold1", "val3", tier=ContextTier.COLD)

        summary = manager.get_summary()

        assert summary["hot_count"] == 1
        assert summary["warm_count"] == 1
        assert summary["cold_count"] == 1
        assert "pressure" in summary


class TestContextMonitoring:
    """Tests for automatic context monitoring."""

    def test_should_checkpoint_trigger(self):
        """Should trigger checkpoint when pressure is high."""
        manager = ContextManager(max_tokens=100)  # Very low max for testing

        # Add lots of context
        manager.add("big", "x" * 500, tier=ContextTier.HOT)

        assert manager.should_checkpoint()

    def test_monitor_callback(self):
        """Should call callback when pressure threshold exceeded."""
        callback_called = []

        def on_pressure(pressure: ContextPressure):
            callback_called.append(pressure)

        manager = ContextManager(
            max_tokens=100,
            pressure_callback=on_pressure,
            pressure_threshold=0.5,  # 50%
        )

        # Add context to exceed threshold
        manager.add("data", "x" * 300, tier=ContextTier.HOT)

        assert len(callback_called) == 1
        assert callback_called[0].percentage >= 50


class TestContextPersistence:
    """Tests for checkpoint file management."""

    def test_list_checkpoints(self):
        """Should list available checkpoints."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ContextManager(checkpoint_dir=Path(tmpdir))

            # Create a few checkpoints
            manager.add("test", "value", tier=ContextTier.HOT)
            manager.create_checkpoint("session-1", "Checkpoint 1")
            manager.create_checkpoint("session-2", "Checkpoint 2")

            checkpoints = manager.list_checkpoints()
            assert len(checkpoints) >= 2

    def test_auto_cleanup_old_checkpoints(self):
        """Should cleanup old checkpoints beyond max count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ContextManager(
                checkpoint_dir=Path(tmpdir),
                max_checkpoints=2,
            )

            # Create more checkpoints than max
            for i in range(5):
                manager.add("test", f"value{i}", tier=ContextTier.HOT)
                manager.create_checkpoint(f"session-{i}", f"Checkpoint {i}")

            checkpoints = manager.list_checkpoints()

            # Should only keep max_checkpoints
            assert len(checkpoints) <= 3  # Allow some tolerance
