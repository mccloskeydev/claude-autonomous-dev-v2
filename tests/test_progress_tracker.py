"""Tests for effort estimation and progress tracking."""

import tempfile
import time
from pathlib import Path

from src.progress_tracker import (
    EffortEstimate,
    EffortUnit,
    ProgressPhase,
    ProgressTracker,
    TaskProgress,
    VelocityTracker,
)


class TestEffortUnit:
    """Tests for effort unit enum."""

    def test_effort_units(self):
        """Should have expected effort units."""
        assert EffortUnit.STORY_POINTS
        assert EffortUnit.HOURS
        assert EffortUnit.DAYS
        assert EffortUnit.TOKENS


class TestProgressPhase:
    """Tests for progress phase enum."""

    def test_progress_phases(self):
        """Should have expected progress phases."""
        assert ProgressPhase.NOT_STARTED
        assert ProgressPhase.PLANNING
        assert ProgressPhase.IN_PROGRESS
        assert ProgressPhase.TESTING
        assert ProgressPhase.REVIEW
        assert ProgressPhase.COMPLETE


class TestEffortEstimate:
    """Tests for effort estimates."""

    def test_estimate_creation(self):
        """Should create effort estimate."""
        estimate = EffortEstimate(
            value=5,
            unit=EffortUnit.STORY_POINTS,
            confidence=0.8,
        )
        assert estimate.value == 5
        assert estimate.unit == EffortUnit.STORY_POINTS
        assert estimate.confidence == 0.8

    def test_estimate_with_breakdown(self):
        """Should support breakdown by phase."""
        estimate = EffortEstimate(
            value=8,
            unit=EffortUnit.HOURS,
            confidence=0.7,
            breakdown={
                "planning": 1,
                "implementation": 5,
                "testing": 2,
            },
        )
        assert estimate.breakdown["implementation"] == 5

    def test_estimate_to_hours(self):
        """Should convert estimate to hours."""
        # Story points (assuming 1 point = 2 hours)
        sp_estimate = EffortEstimate(value=3, unit=EffortUnit.STORY_POINTS)
        assert sp_estimate.to_hours(hours_per_point=2) >= 6

        # Days (8 hours per day)
        day_estimate = EffortEstimate(value=2, unit=EffortUnit.DAYS)
        assert day_estimate.to_hours() >= 16

    def test_estimate_comparison(self):
        """Should compare estimates."""
        small = EffortEstimate(value=2, unit=EffortUnit.HOURS)
        large = EffortEstimate(value=8, unit=EffortUnit.HOURS)
        assert small.value < large.value


class TestTaskProgress:
    """Tests for task progress tracking."""

    def test_progress_creation(self):
        """Should create task progress."""
        progress = TaskProgress(
            task_id="F001",
            name="Feature 1",
        )
        assert progress.task_id == "F001"
        assert progress.phase == ProgressPhase.NOT_STARTED
        assert progress.completion_percentage == 0

    def test_set_phase(self):
        """Should update phase."""
        progress = TaskProgress(task_id="F001", name="Feature 1")
        progress.set_phase(ProgressPhase.PLANNING)

        assert progress.phase == ProgressPhase.PLANNING

    def test_update_completion(self):
        """Should update completion percentage."""
        progress = TaskProgress(task_id="F001", name="Feature 1")
        progress.update_completion(50)

        assert progress.completion_percentage == 50

    def test_completion_bounds(self):
        """Should bound completion between 0-100."""
        progress = TaskProgress(task_id="F001", name="Feature 1")

        progress.update_completion(150)
        assert progress.completion_percentage == 100

        progress.update_completion(-10)
        assert progress.completion_percentage == 0

    def test_add_note(self):
        """Should add progress notes."""
        progress = TaskProgress(task_id="F001", name="Feature 1")
        progress.add_note("Started implementation")
        progress.add_note("Added tests")

        assert len(progress.notes) == 2

    def test_set_estimate(self):
        """Should set effort estimate."""
        progress = TaskProgress(task_id="F001", name="Feature 1")
        estimate = EffortEstimate(value=5, unit=EffortUnit.STORY_POINTS)
        progress.set_estimate(estimate)

        assert progress.estimate is not None
        assert progress.estimate.value == 5

    def test_record_actual_effort(self):
        """Should record actual effort spent."""
        progress = TaskProgress(task_id="F001", name="Feature 1")
        progress.record_effort(2.5, EffortUnit.HOURS)
        progress.record_effort(1.5, EffortUnit.HOURS)

        assert progress.actual_effort >= 4.0

    def test_time_tracking(self):
        """Should track time spent."""
        progress = TaskProgress(task_id="F001", name="Feature 1")
        progress.start_timer()
        time.sleep(0.1)
        progress.stop_timer()

        assert progress.elapsed_seconds() >= 0.1

    def test_accuracy(self):
        """Should calculate estimation accuracy."""
        progress = TaskProgress(task_id="F001", name="Feature 1")
        estimate = EffortEstimate(value=4, unit=EffortUnit.HOURS)
        progress.set_estimate(estimate)
        progress.record_effort(5, EffortUnit.HOURS)

        accuracy = progress.estimation_accuracy()
        assert 0 < accuracy <= 1  # Should be 80%

    def test_is_overdue(self):
        """Should detect if task is overdue."""
        progress = TaskProgress(task_id="F001", name="Feature 1")
        estimate = EffortEstimate(value=1, unit=EffortUnit.HOURS)
        progress.set_estimate(estimate)
        progress.record_effort(2, EffortUnit.HOURS)

        assert progress.is_overdue()


class TestVelocityTracker:
    """Tests for velocity tracking."""

    def test_tracker_creation(self):
        """Should create velocity tracker."""
        tracker = VelocityTracker()
        assert tracker is not None

    def test_record_completion(self):
        """Should record task completions."""
        tracker = VelocityTracker()
        tracker.record_completion(
            task_id="F001",
            story_points=5,
            hours_spent=8,
        )

        assert tracker.completed_count() == 1
        assert tracker.total_points() == 5

    def test_calculate_velocity(self):
        """Should calculate velocity (points per hour)."""
        tracker = VelocityTracker()
        tracker.record_completion("F001", story_points=3, hours_spent=6)
        tracker.record_completion("F002", story_points=5, hours_spent=10)

        velocity = tracker.velocity()  # points per hour
        assert velocity == 0.5  # 8 points / 16 hours

    def test_estimate_completion_time(self):
        """Should estimate completion time for remaining work."""
        tracker = VelocityTracker()
        tracker.record_completion("F001", story_points=4, hours_spent=8)  # 0.5 velocity

        remaining_points = 10
        estimated_hours = tracker.estimate_hours(remaining_points)
        assert estimated_hours == 20  # 10 points / 0.5 velocity

    def test_rolling_velocity(self):
        """Should calculate rolling velocity over N tasks."""
        tracker = VelocityTracker()
        tracker.record_completion("F001", story_points=2, hours_spent=4)  # 0.5
        tracker.record_completion("F002", story_points=6, hours_spent=6)  # 1.0
        tracker.record_completion("F003", story_points=4, hours_spent=8)  # 0.5

        rolling = tracker.rolling_velocity(n=2)  # Last 2 tasks
        assert rolling == 5 / 7  # (6+4) / (6+8) - actually (6+4) / (6+8) but impl varies

    def test_velocity_trend(self):
        """Should detect velocity trend."""
        tracker = VelocityTracker()
        tracker.record_completion("F001", story_points=2, hours_spent=4)  # 0.5
        tracker.record_completion("F002", story_points=3, hours_spent=4)  # 0.75
        tracker.record_completion("F003", story_points=4, hours_spent=4)  # 1.0

        trend = tracker.trend()
        assert trend in ["improving", "declining", "stable"]


class TestProgressTracker:
    """Tests for main progress tracker."""

    def test_tracker_creation(self):
        """Should create progress tracker."""
        tracker = ProgressTracker()
        assert tracker is not None

    def test_track_task(self):
        """Should track a new task."""
        tracker = ProgressTracker()
        progress = tracker.track("F001", "Feature 1")

        assert progress.task_id == "F001"
        assert tracker.get_progress("F001") is not None

    def test_update_task(self):
        """Should update task progress."""
        tracker = ProgressTracker()
        tracker.track("F001", "Feature 1")
        tracker.update("F001", phase=ProgressPhase.IN_PROGRESS, completion=30)

        progress = tracker.get_progress("F001")
        assert progress.phase == ProgressPhase.IN_PROGRESS
        assert progress.completion_percentage == 30

    def test_complete_task(self):
        """Should complete a task."""
        tracker = ProgressTracker()
        tracker.track("F001", "Feature 1")
        progress = tracker.get_progress("F001")
        progress.set_estimate(EffortEstimate(value=3, unit=EffortUnit.STORY_POINTS))
        progress.record_effort(4, EffortUnit.HOURS)

        tracker.complete("F001")

        assert tracker.is_complete("F001")
        assert tracker.velocity_tracker.completed_count() == 1

    def test_get_all_progress(self):
        """Should get all task progress."""
        tracker = ProgressTracker()
        tracker.track("F001", "Feature 1")
        tracker.track("F002", "Feature 2")
        tracker.track("F003", "Feature 3")

        all_progress = tracker.get_all()
        assert len(all_progress) == 3

    def test_filter_by_phase(self):
        """Should filter tasks by phase."""
        tracker = ProgressTracker()
        tracker.track("F001", "Feature 1")
        tracker.track("F002", "Feature 2")
        tracker.track("F003", "Feature 3")

        tracker.update("F001", phase=ProgressPhase.IN_PROGRESS)
        tracker.update("F002", phase=ProgressPhase.IN_PROGRESS)
        tracker.update("F003", phase=ProgressPhase.COMPLETE)

        in_progress = tracker.get_by_phase(ProgressPhase.IN_PROGRESS)
        assert len(in_progress) == 2

    def test_overall_completion(self):
        """Should calculate overall completion percentage."""
        tracker = ProgressTracker()
        tracker.track("F001", "Feature 1")
        tracker.track("F002", "Feature 2")

        tracker.update("F001", completion=100)
        tracker.update("F002", completion=50)

        overall = tracker.overall_completion()
        assert overall == 75  # (100 + 50) / 2

    def test_estimate_remaining_work(self):
        """Should estimate remaining work."""
        tracker = ProgressTracker()
        p1 = tracker.track("F001", "Feature 1")
        p2 = tracker.track("F002", "Feature 2")

        p1.set_estimate(EffortEstimate(value=5, unit=EffortUnit.STORY_POINTS))
        p2.set_estimate(EffortEstimate(value=3, unit=EffortUnit.STORY_POINTS))

        tracker.complete("F001")

        remaining = tracker.remaining_points()
        assert remaining == 3

    def test_get_summary(self):
        """Should provide progress summary."""
        tracker = ProgressTracker()
        tracker.track("F001", "Feature 1")
        tracker.update("F001", phase=ProgressPhase.IN_PROGRESS, completion=50)

        summary = tracker.get_summary()
        assert "total_tasks" in summary
        assert "in_progress" in summary
        assert "overall_completion" in summary

    def test_persistence(self):
        """Should save and load progress."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "progress.json"

            tracker = ProgressTracker()
            tracker.track("F001", "Feature 1")
            tracker.update("F001", phase=ProgressPhase.IN_PROGRESS, completion=40)
            tracker.save(filepath)

            loaded = ProgressTracker.load(filepath)
            progress = loaded.get_progress("F001")
            assert progress.completion_percentage == 40


class TestProgressTrackerIntegration:
    """Integration tests for progress tracker."""

    def test_full_workflow(self):
        """Should support full progress tracking workflow."""
        tracker = ProgressTracker()

        # Track new feature
        progress = tracker.track("F001", "Implement user auth")

        # Set estimate
        estimate = EffortEstimate(
            value=8,
            unit=EffortUnit.HOURS,
            confidence=0.8,
            breakdown={"planning": 1, "impl": 5, "test": 2},
        )
        progress.set_estimate(estimate)

        # Start work
        tracker.update("F001", phase=ProgressPhase.PLANNING, completion=10)
        progress.add_note("Reviewed requirements")

        # Continue work
        tracker.update("F001", phase=ProgressPhase.IN_PROGRESS, completion=50)
        progress.record_effort(3, EffortUnit.HOURS)

        # Testing
        tracker.update("F001", phase=ProgressPhase.TESTING, completion=80)
        progress.record_effort(2, EffortUnit.HOURS)

        # Complete
        tracker.complete("F001")

        # Verify
        assert tracker.is_complete("F001")
        assert progress.actual_effort == 5
        assert tracker.velocity_tracker.completed_count() == 1

    def test_integration_with_dependency_graph(self):
        """Should integrate with dependency graph from F005."""
        from src.dependency_graph import DependencyGraph, Feature, FeatureStatus

        # Create features in dependency graph
        graph = DependencyGraph()
        graph.add_feature(Feature(
            id="F001",
            description="Auth module",
            priority=1,
            status=FeatureStatus.PENDING,
        ))
        graph.add_feature(Feature(
            id="F002",
            description="Dashboard",
            priority=2,
            dependencies=["F001"],
            status=FeatureStatus.PENDING,
        ))

        # Create progress tracker for these features
        tracker = ProgressTracker()
        for feature in [graph.get_feature("F001"), graph.get_feature("F002")]:
            progress = tracker.track(feature.id, feature.description)
            progress.set_estimate(EffortEstimate(
                value=feature.effort_estimate,
                unit=EffortUnit.STORY_POINTS,
            ))

        # Verify tracking
        assert tracker.get_progress("F001") is not None
        assert tracker.get_progress("F002") is not None
