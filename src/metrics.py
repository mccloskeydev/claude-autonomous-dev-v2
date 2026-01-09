"""Metrics collection and performance tracking.

This module provides metrics collection for autonomous development:

- Metric types and values
- Metrics collector
- Session metrics
- Performance tracking
- Efficiency calculations
"""

import contextlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class MetricType(Enum):
    """Types of metrics to track."""

    ITERATIONS = "iterations"
    TOKENS_USED = "tokens_used"
    FEATURES_COMPLETED = "features_completed"
    FEATURES_STARTED = "features_started"
    TESTS_WRITTEN = "tests_written"
    TESTS_PASSED = "tests_passed"
    TESTS_FAILED = "tests_failed"
    BUGS_FIXED = "bugs_fixed"
    ERRORS_ENCOUNTERED = "errors_encountered"
    TIME_ELAPSED = "time_elapsed"
    COVERAGE = "coverage"
    FILES_CHANGED = "files_changed"


@dataclass
class MetricValue:
    """A single metric measurement."""

    metric_type: MetricType
    value: float
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects and aggregates metrics."""

    def __init__(self) -> None:
        """Initialize metrics collector."""
        self._metrics: dict[MetricType, list[MetricValue]] = {}
        self._counters: dict[MetricType, int] = {}

    def record(self, metric_type: MetricType, value: float, **metadata: Any) -> None:
        """Record a metric value.

        Args:
            metric_type: Type of metric
            value: Metric value
            **metadata: Additional metadata
        """
        if metric_type not in self._metrics:
            self._metrics[metric_type] = []

        metric_value = MetricValue(
            metric_type=metric_type,
            value=value,
            metadata=metadata,
        )
        self._metrics[metric_type].append(metric_value)

    def increment(self, metric_type: MetricType, amount: int = 1) -> None:
        """Increment a counter metric.

        Args:
            metric_type: Type of metric
            amount: Amount to increment
        """
        if metric_type not in self._counters:
            self._counters[metric_type] = 0
        self._counters[metric_type] += amount

    def get_values(self, metric_type: MetricType) -> list[MetricValue]:
        """Get all values for a metric type.

        Args:
            metric_type: Type of metric

        Returns:
            List of metric values
        """
        return self._metrics.get(metric_type, [])

    def get_latest(self, metric_type: MetricType) -> MetricValue | None:
        """Get latest value for a metric.

        Args:
            metric_type: Type of metric

        Returns:
            Latest MetricValue or None
        """
        values = self.get_values(metric_type)
        return values[-1] if values else None

    def get_sum(self, metric_type: MetricType) -> float:
        """Get sum of metric values.

        Args:
            metric_type: Type of metric

        Returns:
            Sum of values
        """
        values = self.get_values(metric_type)
        return sum(v.value for v in values)

    def get_average(self, metric_type: MetricType) -> float:
        """Get average of metric values.

        Args:
            metric_type: Type of metric

        Returns:
            Average value
        """
        values = self.get_values(metric_type)
        if not values:
            return 0.0
        return sum(v.value for v in values) / len(values)

    def get_count(self, metric_type: MetricType) -> int:
        """Get counter value for a metric.

        Args:
            metric_type: Type of metric

        Returns:
            Counter value
        """
        return self._counters.get(metric_type, 0)

    def export_json(self) -> str:
        """Export metrics to JSON string.

        Returns:
            JSON string
        """
        data = {
            "metrics": {
                mt.value: [
                    {"value": v.value, "timestamp": v.timestamp, "metadata": v.metadata}
                    for v in values
                ]
                for mt, values in self._metrics.items()
            },
            "counters": {mt.value: count for mt, count in self._counters.items()},
        }
        return json.dumps(data, indent=2)

    def save(self, filepath: Path) -> None:
        """Save metrics to file.

        Args:
            filepath: Path to save to
        """
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            f.write(self.export_json())

    @classmethod
    def load(cls, filepath: Path) -> "MetricsCollector":
        """Load metrics from file.

        Args:
            filepath: Path to load from

        Returns:
            MetricsCollector instance
        """
        collector = cls()

        with open(filepath) as f:
            data = json.load(f)

        # Restore metrics
        for metric_name, values in data.get("metrics", {}).items():
            try:
                metric_type = MetricType(metric_name)
                for v in values:
                    collector._metrics.setdefault(metric_type, []).append(
                        MetricValue(
                            metric_type=metric_type,
                            value=v["value"],
                            timestamp=v.get("timestamp", time.time()),
                            metadata=v.get("metadata", {}),
                        )
                    )
            except ValueError:
                pass  # Unknown metric type, skip

        # Restore counters
        for counter_name, count in data.get("counters", {}).items():
            try:
                metric_type = MetricType(counter_name)
                collector._counters[metric_type] = count
            except ValueError:
                pass

        return collector


class SessionMetrics:
    """Session-level metrics tracking."""

    def __init__(self, session_id: str) -> None:
        """Initialize session metrics.

        Args:
            session_id: Unique session identifier
        """
        self.session_id = session_id
        self.start_time = time.time()
        self.collector = MetricsCollector()
        self._features_started: set[str] = set()
        self._features_completed: set[str] = set()
        self._errors_by_type: dict[str, int] = {}

    def duration_seconds(self) -> float:
        """Get session duration in seconds.

        Returns:
            Duration in seconds
        """
        return time.time() - self.start_time

    @property
    def features_started(self) -> int:
        """Number of features started."""
        return len(self._features_started)

    @property
    def features_completed(self) -> int:
        """Number of features completed."""
        return len(self._features_completed)

    @property
    def errors_by_type(self) -> dict[str, int]:
        """Errors grouped by type."""
        return self._errors_by_type.copy()

    def record_feature_started(self, feature_id: str) -> None:
        """Record a feature being started.

        Args:
            feature_id: Feature identifier
        """
        self._features_started.add(feature_id)
        self.collector.increment(MetricType.FEATURES_STARTED)

    def record_feature_completed(self, feature_id: str) -> None:
        """Record a feature being completed.

        Args:
            feature_id: Feature identifier
        """
        self._features_completed.add(feature_id)
        self.collector.increment(MetricType.FEATURES_COMPLETED)

    def record_error(self, error_type: str) -> None:
        """Record an error occurrence.

        Args:
            error_type: Type of error
        """
        if error_type not in self._errors_by_type:
            self._errors_by_type[error_type] = 0
        self._errors_by_type[error_type] += 1
        self.collector.increment(MetricType.ERRORS_ENCOUNTERED)

    def get_summary(self) -> dict[str, Any]:
        """Get session summary.

        Returns:
            Summary dictionary
        """
        return {
            "session_id": self.session_id,
            "duration": self.duration_seconds(),
            "features_started": self.features_started,
            "features_completed": self.features_completed,
            "iterations": self.collector.get_count(MetricType.ITERATIONS)
            or len(self.collector.get_values(MetricType.ITERATIONS)),
            "tokens_used": self.collector.get_sum(MetricType.TOKENS_USED),
            "tests_written": self.collector.get_count(MetricType.TESTS_WRITTEN),
            "bugs_fixed": self.collector.get_count(MetricType.BUGS_FIXED),
            "errors_encountered": sum(self._errors_by_type.values()),
            "errors_by_type": self._errors_by_type,
        }

    def save(self, filepath: Path) -> None:
        """Save session metrics to file.

        Args:
            filepath: Path to save to
        """
        data = {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "features_started": list(self._features_started),
            "features_completed": list(self._features_completed),
            "errors_by_type": self._errors_by_type,
            "collector": json.loads(self.collector.export_json()),
        }
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, filepath: Path) -> "SessionMetrics":
        """Load session metrics from file.

        Args:
            filepath: Path to load from

        Returns:
            SessionMetrics instance
        """
        with open(filepath) as f:
            data = json.load(f)

        session = cls(session_id=data.get("session_id", "unknown"))
        session.start_time = data.get("start_time", time.time())
        session._features_started = set(data.get("features_started", []))
        session._features_completed = set(data.get("features_completed", []))
        session._errors_by_type = data.get("errors_by_type", {})

        # Restore collector
        collector_data = data.get("collector", {})
        for metric_name, values in collector_data.get("metrics", {}).items():
            try:
                metric_type = MetricType(metric_name)
                for v in values:
                    session.collector._metrics.setdefault(metric_type, []).append(
                        MetricValue(
                            metric_type=metric_type,
                            value=v["value"],
                            timestamp=v.get("timestamp", time.time()),
                            metadata=v.get("metadata", {}),
                        )
                    )
            except ValueError:
                pass

        for counter_name, count in collector_data.get("counters", {}).items():
            try:
                metric_type = MetricType(counter_name)
                session.collector._counters[metric_type] = count
            except ValueError:
                pass

        return session


class PerformanceTracker:
    """Tracks performance metrics for operations."""

    def __init__(self) -> None:
        """Initialize performance tracker."""
        self._timings: dict[str, list[float]] = {}
        self._tokens_by_feature: dict[str, int] = {}
        self._time_by_feature: dict[str, float] = {}

    @contextlib.contextmanager
    def track(self, operation: str):
        """Context manager to track operation time.

        Args:
            operation: Name of operation

        Yields:
            None
        """
        start = time.time()
        try:
            yield
        finally:
            elapsed_ms = (time.time() - start) * 1000
            if operation not in self._timings:
                self._timings[operation] = []
            self._timings[operation].append(elapsed_ms)

    def get_timing(self, operation: str) -> float | None:
        """Get latest timing for operation.

        Args:
            operation: Name of operation

        Returns:
            Timing in milliseconds or None
        """
        timings = self._timings.get(operation, [])
        return timings[-1] if timings else None

    def get_average_timing(self, operation: str) -> float:
        """Get average timing for operation.

        Args:
            operation: Name of operation

        Returns:
            Average timing in milliseconds
        """
        timings = self._timings.get(operation, [])
        if not timings:
            return 0.0
        return sum(timings) / len(timings)

    def get_stats(self, operation: str) -> dict[str, float]:
        """Get timing statistics for operation.

        Args:
            operation: Name of operation

        Returns:
            Statistics dictionary
        """
        timings = self._timings.get(operation, [])
        if not timings:
            return {"min": 0, "max": 0, "avg": 0, "count": 0}

        return {
            "min": min(timings),
            "max": max(timings),
            "avg": sum(timings) / len(timings),
            "count": len(timings),
        }

    def record_tokens_for_feature(self, feature_id: str, tokens: int) -> None:
        """Record tokens used for a feature.

        Args:
            feature_id: Feature identifier
            tokens: Number of tokens used
        """
        self._tokens_by_feature[feature_id] = tokens

    def record_feature_time(self, feature_id: str, seconds: float) -> None:
        """Record time spent on a feature.

        Args:
            feature_id: Feature identifier
            seconds: Time in seconds
        """
        self._time_by_feature[feature_id] = seconds

    def average_tokens_per_feature(self) -> float:
        """Calculate average tokens per feature.

        Returns:
            Average tokens
        """
        if not self._tokens_by_feature:
            return 0.0
        return sum(self._tokens_by_feature.values()) / len(self._tokens_by_feature)

    def get_efficiency_metrics(self) -> dict[str, float]:
        """Get efficiency metrics.

        Returns:
            Efficiency metrics dictionary
        """
        total_tokens = sum(self._tokens_by_feature.values())
        total_time = sum(self._time_by_feature.values())
        num_features = len(self._tokens_by_feature)

        metrics: dict[str, float] = {}

        if total_time > 0:
            metrics["tokens_per_minute"] = (total_tokens / total_time) * 60
            metrics["features_per_hour"] = (num_features / total_time) * 3600
        else:
            metrics["tokens_per_minute"] = 0
            metrics["features_per_hour"] = 0

        return metrics
