"""Effort estimation and progress tracking.

This module provides effort estimation and progress tracking for autonomous development:

- Effort estimation with multiple units
- Task progress tracking by phase
- Velocity tracking for predictions
- Time tracking integration
- Progress persistence
"""

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class EffortUnit(Enum):
    """Units for effort estimation."""

    STORY_POINTS = "story_points"
    HOURS = "hours"
    DAYS = "days"
    TOKENS = "tokens"


class ProgressPhase(Enum):
    """Phases of task progress."""

    NOT_STARTED = "not_started"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    REVIEW = "review"
    COMPLETE = "complete"


@dataclass
class EffortEstimate:
    """An effort estimate for a task."""

    value: float
    unit: EffortUnit
    confidence: float = 0.5
    breakdown: dict[str, float] = field(default_factory=dict)

    def to_hours(self, hours_per_point: float = 2, hours_per_day: float = 8) -> float:
        """Convert estimate to hours.

        Args:
            hours_per_point: Hours per story point
            hours_per_day: Hours per day

        Returns:
            Estimated hours
        """
        if self.unit == EffortUnit.HOURS:
            return self.value
        elif self.unit == EffortUnit.DAYS:
            return self.value * hours_per_day
        elif self.unit == EffortUnit.STORY_POINTS:
            return self.value * hours_per_point
        else:
            # Tokens - rough estimate (10k tokens ~ 1 hour)
            return self.value / 10000


@dataclass
class TaskProgress:
    """Progress tracking for a single task."""

    task_id: str
    name: str
    phase: ProgressPhase = ProgressPhase.NOT_STARTED
    completion_percentage: int = 0
    estimate: EffortEstimate | None = None
    actual_effort: float = 0
    effort_unit: EffortUnit = EffortUnit.HOURS
    notes: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    _timer_start: float | None = field(default=None, repr=False)

    def set_phase(self, phase: ProgressPhase) -> None:
        """Set the current phase.

        Args:
            phase: New phase
        """
        self.phase = phase
        if phase == ProgressPhase.COMPLETE:
            self.completion_percentage = 100
            self.completed_at = time.time()

    def update_completion(self, percentage: int) -> None:
        """Update completion percentage.

        Args:
            percentage: Completion percentage (0-100)
        """
        self.completion_percentage = max(0, min(100, percentage))

    def add_note(self, note: str) -> None:
        """Add a progress note.

        Args:
            note: Note text
        """
        self.notes.append(note)

    def set_estimate(self, estimate: EffortEstimate) -> None:
        """Set effort estimate.

        Args:
            estimate: Effort estimate
        """
        self.estimate = estimate

    def record_effort(self, amount: float, unit: EffortUnit = EffortUnit.HOURS) -> None:
        """Record actual effort spent.

        Args:
            amount: Amount of effort
            unit: Unit of effort
        """
        # Convert to hours for accumulation
        if unit == EffortUnit.HOURS:
            self.actual_effort += amount
        elif unit == EffortUnit.DAYS:
            self.actual_effort += amount * 8
        else:
            self.actual_effort += amount
        self.effort_unit = unit

    def start_timer(self) -> None:
        """Start timing this task."""
        self._timer_start = time.time()
        if self.started_at is None:
            self.started_at = time.time()

    def stop_timer(self) -> None:
        """Stop timing and record effort."""
        if self._timer_start:
            elapsed = time.time() - self._timer_start
            self.actual_effort += elapsed / 3600  # Convert to hours
            self._timer_start = None

    def elapsed_seconds(self) -> float:
        """Get total elapsed time in seconds.

        Returns:
            Elapsed seconds
        """
        return self.actual_effort * 3600  # Convert hours to seconds

    def estimation_accuracy(self) -> float:
        """Calculate estimation accuracy.

        Returns:
            Accuracy as ratio (1.0 = perfect)
        """
        if not self.estimate or self.actual_effort == 0:
            return 1.0

        estimated_hours = self.estimate.to_hours()
        if estimated_hours == 0:
            return 1.0

        # Accuracy is how close actual is to estimate
        ratio = min(estimated_hours, self.actual_effort) / max(estimated_hours, self.actual_effort)
        return ratio

    def is_overdue(self) -> bool:
        """Check if task is over estimate.

        Returns:
            True if actual effort exceeds estimate
        """
        if not self.estimate:
            return False
        return self.actual_effort > self.estimate.to_hours()


@dataclass
class VelocityRecord:
    """Record of a completed task for velocity tracking."""

    task_id: str
    story_points: float
    hours_spent: float
    timestamp: float = field(default_factory=time.time)


class VelocityTracker:
    """Tracks velocity (points per hour) over time."""

    def __init__(self) -> None:
        """Initialize velocity tracker."""
        self._records: list[VelocityRecord] = []

    def record_completion(
        self,
        task_id: str,
        story_points: float,
        hours_spent: float,
    ) -> None:
        """Record a task completion.

        Args:
            task_id: Task identifier
            story_points: Points completed
            hours_spent: Hours spent
        """
        self._records.append(
            VelocityRecord(
                task_id=task_id,
                story_points=story_points,
                hours_spent=hours_spent,
            )
        )

    def completed_count(self) -> int:
        """Get number of completed tasks.

        Returns:
            Task count
        """
        return len(self._records)

    def total_points(self) -> float:
        """Get total story points completed.

        Returns:
            Total points
        """
        return sum(r.story_points for r in self._records)

    def total_hours(self) -> float:
        """Get total hours spent.

        Returns:
            Total hours
        """
        return sum(r.hours_spent for r in self._records)

    def velocity(self) -> float:
        """Calculate overall velocity (points per hour).

        Returns:
            Velocity
        """
        total_hours = self.total_hours()
        if total_hours == 0:
            return 0
        return self.total_points() / total_hours

    def rolling_velocity(self, n: int = 3) -> float:
        """Calculate rolling velocity over last N tasks.

        Args:
            n: Number of recent tasks

        Returns:
            Rolling velocity
        """
        recent = self._records[-n:] if self._records else []
        if not recent:
            return 0

        total_points = sum(r.story_points for r in recent)
        total_hours = sum(r.hours_spent for r in recent)
        if total_hours == 0:
            return 0
        return total_points / total_hours

    def estimate_hours(self, remaining_points: float) -> float:
        """Estimate hours for remaining work.

        Args:
            remaining_points: Story points remaining

        Returns:
            Estimated hours
        """
        v = self.velocity()
        if v == 0:
            return 0
        return remaining_points / v

    def trend(self) -> str:
        """Determine velocity trend.

        Returns:
            "improving", "declining", or "stable"
        """
        if len(self._records) < 3:
            return "stable"

        # Compare first half to second half
        mid = len(self._records) // 2
        first_half = self._records[:mid]
        second_half = self._records[mid:]

        first_velocity = sum(r.story_points for r in first_half) / max(sum(r.hours_spent for r in first_half), 0.01)
        second_velocity = sum(r.story_points for r in second_half) / max(sum(r.hours_spent for r in second_half), 0.01)

        diff = second_velocity - first_velocity
        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "declining"
        return "stable"


class ProgressTracker:
    """Main progress tracking for all tasks."""

    def __init__(self) -> None:
        """Initialize progress tracker."""
        self._tasks: dict[str, TaskProgress] = {}
        self.velocity_tracker = VelocityTracker()

    def track(self, task_id: str, name: str) -> TaskProgress:
        """Start tracking a new task.

        Args:
            task_id: Task identifier
            name: Task name

        Returns:
            TaskProgress object
        """
        progress = TaskProgress(task_id=task_id, name=name)
        self._tasks[task_id] = progress
        return progress

    def get_progress(self, task_id: str) -> TaskProgress | None:
        """Get progress for a task.

        Args:
            task_id: Task identifier

        Returns:
            TaskProgress or None
        """
        return self._tasks.get(task_id)

    def update(
        self,
        task_id: str,
        phase: ProgressPhase | None = None,
        completion: int | None = None,
    ) -> None:
        """Update task progress.

        Args:
            task_id: Task identifier
            phase: Optional new phase
            completion: Optional completion percentage
        """
        progress = self._tasks.get(task_id)
        if not progress:
            return

        if phase is not None:
            progress.set_phase(phase)
        if completion is not None:
            progress.update_completion(completion)

    def complete(self, task_id: str) -> None:
        """Mark a task as complete.

        Args:
            task_id: Task identifier
        """
        progress = self._tasks.get(task_id)
        if not progress:
            return

        progress.set_phase(ProgressPhase.COMPLETE)

        # Record velocity
        story_points = 0
        if progress.estimate:
            if progress.estimate.unit == EffortUnit.STORY_POINTS:
                story_points = progress.estimate.value
            else:
                # Convert to approximate story points
                story_points = progress.estimate.to_hours() / 2

        hours_spent = progress.actual_effort
        if hours_spent > 0 or story_points > 0:
            self.velocity_tracker.record_completion(
                task_id=task_id,
                story_points=story_points,
                hours_spent=max(hours_spent, 0.1),  # Min 0.1 hours
            )

    def is_complete(self, task_id: str) -> bool:
        """Check if task is complete.

        Args:
            task_id: Task identifier

        Returns:
            True if complete
        """
        progress = self._tasks.get(task_id)
        return progress is not None and progress.phase == ProgressPhase.COMPLETE

    def get_all(self) -> list[TaskProgress]:
        """Get all task progress.

        Returns:
            List of all TaskProgress
        """
        return list(self._tasks.values())

    def get_by_phase(self, phase: ProgressPhase) -> list[TaskProgress]:
        """Get tasks in a specific phase.

        Args:
            phase: Phase to filter by

        Returns:
            List of TaskProgress in phase
        """
        return [p for p in self._tasks.values() if p.phase == phase]

    def overall_completion(self) -> float:
        """Calculate overall completion percentage.

        Returns:
            Average completion percentage
        """
        if not self._tasks:
            return 0
        return sum(p.completion_percentage for p in self._tasks.values()) / len(self._tasks)

    def remaining_points(self) -> float:
        """Calculate remaining story points.

        Returns:
            Total remaining points
        """
        total = 0
        for progress in self._tasks.values():
            if (
                progress.phase != ProgressPhase.COMPLETE
                and progress.estimate
                and progress.estimate.unit == EffortUnit.STORY_POINTS
            ):
                total += progress.estimate.value
        return total

    def get_summary(self) -> dict[str, Any]:
        """Get progress summary.

        Returns:
            Summary dictionary
        """
        phases = dict.fromkeys(ProgressPhase, 0)
        for progress in self._tasks.values():
            phases[progress.phase] += 1

        return {
            "total_tasks": len(self._tasks),
            "not_started": phases[ProgressPhase.NOT_STARTED],
            "planning": phases[ProgressPhase.PLANNING],
            "in_progress": phases[ProgressPhase.IN_PROGRESS],
            "testing": phases[ProgressPhase.TESTING],
            "review": phases[ProgressPhase.REVIEW],
            "complete": phases[ProgressPhase.COMPLETE],
            "overall_completion": self.overall_completion(),
            "velocity": self.velocity_tracker.velocity(),
            "velocity_trend": self.velocity_tracker.trend(),
        }

    def save(self, filepath: Path) -> None:
        """Save progress to file.

        Args:
            filepath: Path to save to
        """
        data = {
            "tasks": {
                task_id: {
                    "task_id": p.task_id,
                    "name": p.name,
                    "phase": p.phase.value,
                    "completion_percentage": p.completion_percentage,
                    "actual_effort": p.actual_effort,
                    "notes": p.notes,
                    "estimate": {
                        "value": p.estimate.value,
                        "unit": p.estimate.unit.value,
                        "confidence": p.estimate.confidence,
                    }
                    if p.estimate
                    else None,
                }
                for task_id, p in self._tasks.items()
            },
            "velocity": {
                "records": [
                    {
                        "task_id": r.task_id,
                        "story_points": r.story_points,
                        "hours_spent": r.hours_spent,
                        "timestamp": r.timestamp,
                    }
                    for r in self.velocity_tracker._records
                ]
            },
        }

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, filepath: Path) -> "ProgressTracker":
        """Load progress from file.

        Args:
            filepath: Path to load from

        Returns:
            ProgressTracker instance
        """
        with open(filepath) as f:
            data = json.load(f)

        tracker = cls()

        # Restore tasks
        for task_data in data.get("tasks", {}).values():
            progress = TaskProgress(
                task_id=task_data["task_id"],
                name=task_data["name"],
            )
            progress.phase = ProgressPhase(task_data["phase"])
            progress.completion_percentage = task_data["completion_percentage"]
            progress.actual_effort = task_data.get("actual_effort", 0)
            progress.notes = task_data.get("notes", [])

            if task_data.get("estimate"):
                estimate = EffortEstimate(
                    value=task_data["estimate"]["value"],
                    unit=EffortUnit(task_data["estimate"]["unit"]),
                    confidence=task_data["estimate"].get("confidence", 0.5),
                )
                progress.estimate = estimate

            tracker._tasks[progress.task_id] = progress

        # Restore velocity records
        for record_data in data.get("velocity", {}).get("records", []):
            record = VelocityRecord(
                task_id=record_data["task_id"],
                story_points=record_data["story_points"],
                hours_spent=record_data["hours_spent"],
                timestamp=record_data.get("timestamp", time.time()),
            )
            tracker.velocity_tracker._records.append(record)

        return tracker
