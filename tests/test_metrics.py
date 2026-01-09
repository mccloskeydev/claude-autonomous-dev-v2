"""Tests for metrics collection and performance tracking."""

import tempfile
import time
from pathlib import Path

from src.metrics import (
    MetricsCollector,
    MetricType,
    MetricValue,
    PerformanceTracker,
    SessionMetrics,
)


class TestMetricType:
    """Tests for metric types."""

    def test_metric_types_exist(self):
        """Should have all expected metric types."""
        assert MetricType.ITERATIONS
        assert MetricType.TOKENS_USED
        assert MetricType.FEATURES_COMPLETED
        assert MetricType.TESTS_WRITTEN
        assert MetricType.BUGS_FIXED
        assert MetricType.ERRORS_ENCOUNTERED
        assert MetricType.TIME_ELAPSED


class TestMetricValue:
    """Tests for metric values."""

    def test_metric_value_creation(self):
        """Should create metric value."""
        value = MetricValue(
            metric_type=MetricType.ITERATIONS,
            value=10,
        )
        assert value.value == 10
        assert value.metric_type == MetricType.ITERATIONS

    def test_metric_value_with_timestamp(self):
        """Should include timestamp."""
        value = MetricValue(
            metric_type=MetricType.TOKENS_USED,
            value=50000,
        )
        assert value.timestamp is not None
        assert value.timestamp > 0


class TestMetricsCollector:
    """Tests for metrics collector."""

    def test_collector_creation(self):
        """Should create collector."""
        collector = MetricsCollector()
        assert collector is not None

    def test_record_metric(self):
        """Should record metrics."""
        collector = MetricsCollector()
        collector.record(MetricType.ITERATIONS, 1)
        collector.record(MetricType.ITERATIONS, 2)
        collector.record(MetricType.ITERATIONS, 3)

        values = collector.get_values(MetricType.ITERATIONS)
        assert len(values) == 3
        assert values[-1].value == 3

    def test_get_latest(self):
        """Should get latest value for metric."""
        collector = MetricsCollector()
        collector.record(MetricType.TOKENS_USED, 1000)
        collector.record(MetricType.TOKENS_USED, 2000)

        latest = collector.get_latest(MetricType.TOKENS_USED)
        assert latest.value == 2000

    def test_get_sum(self):
        """Should sum metric values."""
        collector = MetricsCollector()
        collector.record(MetricType.BUGS_FIXED, 1)
        collector.record(MetricType.BUGS_FIXED, 2)
        collector.record(MetricType.BUGS_FIXED, 1)

        total = collector.get_sum(MetricType.BUGS_FIXED)
        assert total == 4

    def test_get_average(self):
        """Should calculate average."""
        collector = MetricsCollector()
        collector.record(MetricType.TIME_ELAPSED, 100)
        collector.record(MetricType.TIME_ELAPSED, 200)
        collector.record(MetricType.TIME_ELAPSED, 300)

        avg = collector.get_average(MetricType.TIME_ELAPSED)
        assert avg == 200

    def test_increment(self):
        """Should increment counter metrics."""
        collector = MetricsCollector()
        collector.increment(MetricType.TESTS_WRITTEN)
        collector.increment(MetricType.TESTS_WRITTEN)
        collector.increment(MetricType.TESTS_WRITTEN)

        count = collector.get_count(MetricType.TESTS_WRITTEN)
        assert count == 3

    def test_export_json(self):
        """Should export to JSON."""
        collector = MetricsCollector()
        collector.record(MetricType.ITERATIONS, 10)
        collector.record(MetricType.FEATURES_COMPLETED, 3)

        data = collector.export_json()
        assert "ITERATIONS" in data or "iterations" in data.lower()

    def test_save_and_load(self):
        """Should save and load from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "metrics.json"

            collector = MetricsCollector()
            collector.record(MetricType.ITERATIONS, 10)
            collector.record(MetricType.BUGS_FIXED, 2)
            collector.save(filepath)

            # Load into new collector
            loaded = MetricsCollector.load(filepath)
            assert loaded.get_latest(MetricType.ITERATIONS).value == 10


class TestSessionMetrics:
    """Tests for session-level metrics."""

    def test_session_creation(self):
        """Should create session metrics."""
        session = SessionMetrics(session_id="test-session")
        assert session.session_id == "test-session"
        assert session.start_time is not None

    def test_session_duration(self):
        """Should track session duration."""
        session = SessionMetrics(session_id="test")
        time.sleep(0.1)
        duration = session.duration_seconds()
        assert duration >= 0.1

    def test_session_summary(self):
        """Should provide session summary."""
        session = SessionMetrics(session_id="test")
        session.collector.record(MetricType.ITERATIONS, 10)
        session.collector.record(MetricType.FEATURES_COMPLETED, 3)

        summary = session.get_summary()
        assert "session_id" in summary
        assert "duration" in summary

    def test_feature_tracking(self):
        """Should track feature completion."""
        session = SessionMetrics(session_id="test")
        session.record_feature_started("F001")
        session.record_feature_completed("F001")

        assert session.features_started == 1
        assert session.features_completed == 1

    def test_error_tracking(self):
        """Should track errors by type."""
        session = SessionMetrics(session_id="test")
        session.record_error("SyntaxError")
        session.record_error("SyntaxError")
        session.record_error("ImportError")

        errors = session.errors_by_type
        assert errors["SyntaxError"] == 2
        assert errors["ImportError"] == 1


class TestPerformanceTracker:
    """Tests for performance tracking."""

    def test_tracker_creation(self):
        """Should create performance tracker."""
        tracker = PerformanceTracker()
        assert tracker is not None

    def test_track_operation_time(self):
        """Should track operation time."""
        tracker = PerformanceTracker()

        with tracker.track("test_operation"):
            time.sleep(0.1)

        timing = tracker.get_timing("test_operation")
        assert timing is not None
        assert timing >= 100  # At least 100ms

    def test_track_multiple_operations(self):
        """Should track multiple operations."""
        tracker = PerformanceTracker()

        with tracker.track("op1"):
            time.sleep(0.05)

        with tracker.track("op2"):
            time.sleep(0.05)

        assert tracker.get_timing("op1") is not None
        assert tracker.get_timing("op2") is not None

    def test_average_timing(self):
        """Should calculate average timing."""
        tracker = PerformanceTracker()

        for _ in range(3):
            with tracker.track("repeated_op"):
                time.sleep(0.01)

        avg = tracker.get_average_timing("repeated_op")
        assert avg >= 10  # At least 10ms

    def test_timing_stats(self):
        """Should provide timing statistics."""
        tracker = PerformanceTracker()

        with tracker.track("stats_op"):
            time.sleep(0.05)
        with tracker.track("stats_op"):
            time.sleep(0.10)

        stats = tracker.get_stats("stats_op")
        assert "min" in stats
        assert "max" in stats
        assert "avg" in stats
        assert "count" in stats

    def test_tokens_per_feature(self):
        """Should track tokens per feature."""
        tracker = PerformanceTracker()
        tracker.record_tokens_for_feature("F001", 5000)
        tracker.record_tokens_for_feature("F002", 3000)
        tracker.record_tokens_for_feature("F003", 4000)

        avg = tracker.average_tokens_per_feature()
        assert avg == 4000

    def test_efficiency_metrics(self):
        """Should calculate efficiency metrics."""
        tracker = PerformanceTracker()
        tracker.record_tokens_for_feature("F001", 5000)
        tracker.record_feature_time("F001", 300)  # 5 minutes

        metrics = tracker.get_efficiency_metrics()
        assert "tokens_per_minute" in metrics
        assert "features_per_hour" in metrics


class TestMetricsIntegration:
    """Integration tests for metrics."""

    def test_integrate_with_session(self):
        """Should integrate collector with session."""
        session = SessionMetrics(session_id="integration-test")

        # Simulate work
        session.collector.increment(MetricType.ITERATIONS)
        session.record_feature_started("F001")
        session.collector.record(MetricType.TOKENS_USED, 1000)
        session.record_feature_completed("F001")
        session.collector.increment(MetricType.TESTS_WRITTEN)

        summary = session.get_summary()
        assert summary["features_completed"] == 1
        assert summary["iterations"] >= 1

    def test_persist_metrics(self):
        """Should persist and restore metrics across sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "session_metrics.json"

            # First session
            session1 = SessionMetrics(session_id="session-1")
            session1.collector.record(MetricType.ITERATIONS, 10)
            session1.collector.record(MetricType.FEATURES_COMPLETED, 2)
            session1.save(filepath)

            # Load and continue
            session2 = SessionMetrics.load(filepath)
            session2.collector.record(MetricType.ITERATIONS, 5)

            # Should have accumulated data
            total_iterations = session2.collector.get_sum(MetricType.ITERATIONS)
            assert total_iterations == 15
