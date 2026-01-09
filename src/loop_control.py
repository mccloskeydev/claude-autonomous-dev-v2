"""Enhanced loop control with adaptive iteration limits.

This module provides intelligent loop control for long-running autonomous
development sessions. It includes:

- Adaptive iteration limits based on task complexity
- Intelligent backoff when stuck
- Progress tracking and stuck detection
- History tracking for analysis
"""

import random
import time
from dataclasses import dataclass, field
from enum import IntEnum


class TaskComplexity(IntEnum):
    """Task complexity levels affecting iteration limits."""

    TRIVIAL = 1
    SIMPLE = 2
    MODERATE = 3
    COMPLEX = 4
    EPIC = 5

    @classmethod
    def from_metrics(
        cls,
        file_count: int = 1,
        test_count: int = 0,
        dependency_depth: int = 0,
    ) -> "TaskComplexity":
        """Calculate complexity from task metrics.

        Args:
            file_count: Number of files to modify
            test_count: Number of tests to write
            dependency_depth: Depth of dependency chain

        Returns:
            Calculated TaskComplexity level
        """
        score = 0

        # File count contribution (0-6 points)
        # Each metric alone should be able to reach at least MODERATE
        # file_count=5 -> MODERATE, file_count=20 -> COMPLEX
        if file_count <= 1:
            score += 0
        elif file_count <= 2:
            score += 1
        elif file_count <= 4:
            score += 3  # 3-4 files
        elif file_count <= 10:
            score += 4  # 5-10 files -> at least MODERATE
        elif file_count <= 20:
            score += 6  # 11-20 files -> COMPLEX
        else:
            score += 8  # 20+ files -> EPIC

        # Test count contribution (0-6 points)
        # test_count=10 -> should reach at least MODERATE
        if test_count <= 2:
            score += 0
        elif test_count <= 5:
            score += 2
        elif test_count < 10:
            score += 3
        else:
            score += 4  # 10+ tests -> at least MODERATE

        # Dependency depth contribution (0-8 points)
        # dependency_depth=5 -> should reach at least COMPLEX
        if dependency_depth <= 1:
            score += 0
        elif dependency_depth <= 2:
            score += 2
        elif dependency_depth <= 4:
            score += 4
        else:
            score += 6  # depth 5+ -> at least COMPLEX

        # Map score to complexity
        # 0-1 = TRIVIAL, 2-3 = SIMPLE, 4-5 = MODERATE, 6-9 = COMPLEX, 10+ = EPIC
        if score <= 1:
            return cls.TRIVIAL
        elif score <= 3:
            return cls.SIMPLE
        elif score <= 5:
            return cls.MODERATE
        elif score <= 9:
            return cls.COMPLEX
        else:
            return cls.EPIC


@dataclass
class LoopConfig:
    """Configuration for loop iteration limits.

    Attributes:
        base_iterations: Default iteration limit
        min_iterations: Minimum allowed iterations
        max_iterations: Maximum allowed iterations
        complexity_multipliers: Multipliers per complexity level
    """

    base_iterations: int = 50
    min_iterations: int = 10
    max_iterations: int = 200
    complexity_multipliers: dict[TaskComplexity, float] = field(
        default_factory=lambda: {
            TaskComplexity.TRIVIAL: 0.3,
            TaskComplexity.SIMPLE: 0.6,
            TaskComplexity.MODERATE: 1.0,
            TaskComplexity.COMPLEX: 1.5,
            TaskComplexity.EPIC: 4.0,  # 50 * 4 = 200 = max_iterations
        }
    )

    def get_adaptive_limit(self, complexity: TaskComplexity) -> int:
        """Get iteration limit adjusted for task complexity.

        Args:
            complexity: The task complexity level

        Returns:
            Adjusted iteration limit
        """
        multiplier = self.complexity_multipliers.get(complexity, 1.0)
        calculated = int(self.base_iterations * multiplier)
        return max(self.min_iterations, min(calculated, self.max_iterations))


@dataclass
class BackoffStrategy:
    """Intelligent backoff strategy when encountering issues.

    Implements exponential backoff with optional jitter.

    Attributes:
        base_delay: Initial delay in seconds
        multiplier: Exponential multiplier
        max_delay: Maximum delay cap in seconds
        jitter: Whether to add randomness to delays
    """

    base_delay: float = 0.5
    multiplier: float = 2.0
    max_delay: float = 30.0
    jitter: bool = False

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number.

        Args:
            attempt: Attempt number (1-based)

        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (self.multiplier ** (attempt - 1))
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add up to 25% random jitter
            jitter_amount = delay * 0.25 * random.random()
            delay += jitter_amount

        return delay


@dataclass
class IterationRecord:
    """Record of a single iteration for history tracking."""

    iteration: int
    timestamp: float
    files_changed: int = 0
    tests_passed: int = 0
    error: str | None = None


@dataclass
class LoopState:
    """Tracks the current state of the control loop.

    Attributes:
        iteration: Current iteration number
        errors_count: Total errors encountered
        last_error: Most recent error message
        consecutive_same_error: Count of consecutive same errors
        consecutive_no_progress: Count of iterations without progress
        stuck_threshold: Threshold for stuck detection
        no_progress_threshold: Threshold for no-progress detection
    """

    iteration: int = 0
    errors_count: int = 0
    last_error: str | None = None
    consecutive_same_error: int = 0
    consecutive_no_progress: int = 0
    stuck_threshold: int = 5
    no_progress_threshold: int = 3
    _last_error_hash: str | None = field(default=None, repr=False)
    _history: list[IterationRecord] = field(default_factory=list, repr=False)

    def increment(self) -> None:
        """Increment the iteration counter."""
        self.iteration += 1

    def record_error(self, error: str) -> None:
        """Record an error occurrence.

        Args:
            error: The error message
        """
        self.errors_count += 1
        self.last_error = error

        # Check if same error as before (using simple hash)
        error_hash = str(hash(error))
        if error_hash == self._last_error_hash:
            self.consecutive_same_error += 1
        else:
            self.consecutive_same_error = 1
            self._last_error_hash = error_hash

        # Update history
        if self._history and self._history[-1].iteration == self.iteration:
            self._history[-1].error = error

    def record_progress(self, files_changed: int, tests_passed: int) -> None:
        """Record progress made in an iteration.

        Args:
            files_changed: Number of files modified
            tests_passed: Number of tests now passing
        """
        if files_changed > 0 or tests_passed > 0:
            # Reset stuck counters on progress
            self.consecutive_same_error = 0
            self.consecutive_no_progress = 0
            self._last_error_hash = None
        else:
            self.consecutive_no_progress += 1

        # Update or add history record
        record = IterationRecord(
            iteration=self.iteration,
            timestamp=time.time(),
            files_changed=files_changed,
            tests_passed=tests_passed,
        )

        # If we already have a record for this iteration (from error), update it
        if self._history and self._history[-1].iteration == self.iteration:
            self._history[-1].files_changed = files_changed
            self._history[-1].tests_passed = tests_passed
        else:
            self._history.append(record)

    @property
    def is_stuck(self) -> bool:
        """Check if we're stuck on the same error."""
        return self.consecutive_same_error >= self.stuck_threshold

    @property
    def has_no_progress(self) -> bool:
        """Check if we've had no progress for too long."""
        return self.consecutive_no_progress >= self.no_progress_threshold

    def get_history(self) -> list[dict]:
        """Get iteration history as list of dicts.

        Returns:
            List of iteration records as dictionaries
        """
        return [
            {
                "iteration": r.iteration,
                "timestamp": r.timestamp,
                "files_changed": r.files_changed,
                "tests_passed": r.tests_passed,
                "error": r.error,
            }
            for r in self._history
        ]


class LoopController:
    """Main controller for adaptive iteration loops.

    Combines configuration, state tracking, and backoff strategy
    to provide intelligent loop control.
    """

    def __init__(
        self,
        config: LoopConfig | None = None,
        complexity: TaskComplexity = TaskComplexity.MODERATE,
        backoff: BackoffStrategy | None = None,
    ):
        """Initialize the loop controller.

        Args:
            config: Loop configuration (uses defaults if None)
            complexity: Task complexity level
            backoff: Backoff strategy (uses defaults if None)
        """
        self.config = config or LoopConfig()
        self.complexity = complexity
        self.backoff = backoff or BackoffStrategy(jitter=True)
        self.state = LoopState()
        self._stop_reason: str | None = None

    @property
    def iteration_limit(self) -> int:
        """Get the current iteration limit based on complexity."""
        return self.config.get_adaptive_limit(self.complexity)

    @property
    def stop_reason(self) -> str:
        """Get the reason for stopping."""
        return self._stop_reason or ""

    def tick(self) -> None:
        """Advance the iteration counter."""
        self.state.increment()

        # Add a placeholder history record
        self.state._history.append(
            IterationRecord(
                iteration=self.state.iteration,
                timestamp=time.time(),
            )
        )

    def record_error(self, error: str) -> None:
        """Record an error in the current iteration.

        Args:
            error: The error message
        """
        self.state.record_error(error)

    def record_progress(self, files_changed: int, tests_passed: int) -> None:
        """Record progress in the current iteration.

        Args:
            files_changed: Number of files modified
            tests_passed: Number of tests now passing
        """
        self.state.record_progress(files_changed, tests_passed)

    def should_stop(self) -> bool:
        """Check if the loop should stop.

        Returns:
            True if the loop should stop
        """
        # Check max iterations
        if self.state.iteration >= self.iteration_limit:
            self._stop_reason = f"Max iterations ({self.iteration_limit}) reached"
            return True

        # Check if stuck on same error
        if self.state.is_stuck:
            self._stop_reason = "Stuck on same error repeatedly"
            return True

        # Check for no progress
        if self.state.has_no_progress:
            self._stop_reason = "No progress for too many iterations"
            return True

        return False

    def get_recommended_delay(self) -> float:
        """Get recommended delay before next iteration.

        Returns:
            Delay in seconds (0 if no delay needed)
        """
        # Calculate based on error count
        error_attempts = self.state.consecutive_same_error
        if error_attempts > 0:
            return self.backoff.get_delay(error_attempts)
        return 0.0

    def get_history(self) -> list[dict]:
        """Get iteration history.

        Returns:
            List of iteration records
        """
        return self.state.get_history()
