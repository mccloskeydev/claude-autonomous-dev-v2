"""Multi-level circuit breakers for autonomous development.

This module provides circuit breakers at multiple levels:

- Token level: Approaching context limit
- Progress level: No meaningful changes
- Quality level: Tests degrading
- Time level: Wall clock limits
"""

import time
from dataclasses import dataclass, field
from enum import IntEnum


class CircuitBreakerLevel(IntEnum):
    """Levels of circuit breakers."""

    TOKEN = 1
    PROGRESS = 2
    QUALITY = 3
    TIME = 4


class CircuitState(IntEnum):
    """State of a circuit breaker."""

    CLOSED = 1  # Normal operation
    OPEN = 2  # Tripped, blocking
    HALF_OPEN = 3  # Testing recovery


@dataclass
class CircuitBreakerResult:
    """Result of a circuit breaker check."""

    level: CircuitBreakerLevel | None = None
    state: CircuitState = CircuitState.CLOSED
    reason: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def is_ok(self) -> bool:
        """Check if circuit is OK (closed)."""
        return self.state == CircuitState.CLOSED and not self.warnings

    @property
    def is_tripped(self) -> bool:
        """Check if circuit is tripped (open)."""
        return self.state == CircuitState.OPEN

    @property
    def is_warning(self) -> bool:
        """Check if there are warnings."""
        return len(self.warnings) > 0 and self.state != CircuitState.OPEN


@dataclass
class CircuitBreakerState:
    """State tracking for a circuit breaker."""

    _state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (operational)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (tripped)."""
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing)."""
        return self._state == CircuitState.HALF_OPEN

    def open(self) -> None:
        """Open the circuit (trip it)."""
        self._state = CircuitState.OPEN
        self.last_failure_time = time.time()

    def close(self) -> None:
        """Close the circuit (restore normal operation)."""
        self._state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_success_time = time.time()

    def half_open(self) -> None:
        """Set circuit to half-open (testing recovery)."""
        self._state = CircuitState.HALF_OPEN

    def record_failure(self) -> None:
        """Record a failure."""
        self.failure_count += 1
        self.last_failure_time = time.time()

    def record_success(self) -> None:
        """Record a success, resetting failure count."""
        self.failure_count = 0
        self.last_success_time = time.time()


class TokenCircuitBreaker:
    """Circuit breaker for token/context limits."""

    def __init__(
        self,
        max_tokens: int = 100000,
        threshold_pct: int = 90,
        warning_pct: int = 70,
    ) -> None:
        """Initialize token circuit breaker.

        Args:
            max_tokens: Maximum allowed tokens
            threshold_pct: Percentage at which to trip
            warning_pct: Percentage at which to warn
        """
        self.max_tokens = max_tokens
        self.threshold_pct = threshold_pct
        self.warning_pct = warning_pct
        self.state = CircuitBreakerState()

    def check(self, current_tokens: int) -> CircuitBreakerResult:
        """Check token usage against limits.

        Args:
            current_tokens: Current token count

        Returns:
            CircuitBreakerResult
        """
        pct = (current_tokens / self.max_tokens) * 100

        if self.state.is_half_open:
            if pct < self.threshold_pct:
                self.state.close()
                return CircuitBreakerResult(
                    level=CircuitBreakerLevel.TOKEN,
                    state=CircuitState.CLOSED,
                )
            else:
                self.state.open()
                return CircuitBreakerResult(
                    level=CircuitBreakerLevel.TOKEN,
                    state=CircuitState.OPEN,
                    reason=f"Token usage at {pct:.1f}% (probe failed)",
                )

        if pct >= self.threshold_pct:
            self.state.open()
            return CircuitBreakerResult(
                level=CircuitBreakerLevel.TOKEN,
                state=CircuitState.OPEN,
                reason=f"Token usage at {pct:.1f}% exceeds threshold ({self.threshold_pct}%)",
            )

        if pct >= self.warning_pct:
            return CircuitBreakerResult(
                level=CircuitBreakerLevel.TOKEN,
                state=CircuitState.CLOSED,
                warnings=[f"Token usage at {pct:.1f}% approaching threshold"],
            )

        return CircuitBreakerResult(
            level=CircuitBreakerLevel.TOKEN,
            state=CircuitState.CLOSED,
        )


class ProgressCircuitBreaker:
    """Circuit breaker for progress monitoring."""

    def __init__(
        self,
        no_progress_threshold: int = 3,
        output_decline_threshold: int = 70,
    ) -> None:
        """Initialize progress circuit breaker.

        Args:
            no_progress_threshold: Iterations without progress before trip
            output_decline_threshold: Output quality decline percentage before warning
        """
        self.no_progress_threshold = no_progress_threshold
        self.output_decline_threshold = output_decline_threshold
        self.state = CircuitBreakerState()
        self.no_progress_count = 0
        self.output_quality_history: list[float] = []

    def record_progress(self, files_changed: int, tests_passed: int) -> None:
        """Record progress for an iteration.

        Args:
            files_changed: Number of files modified
            tests_passed: Number of tests now passing
        """
        if files_changed > 0 or tests_passed > 0:
            self.no_progress_count = 0
            self.state.record_success()
        else:
            self.no_progress_count += 1
            self.state.record_failure()

    def record_output_quality(self, quality: float) -> None:
        """Record output quality metric.

        Args:
            quality: Quality score (0-100)
        """
        self.output_quality_history.append(quality)

    def check(self) -> CircuitBreakerResult:
        """Check progress metrics.

        Returns:
            CircuitBreakerResult
        """
        warnings = []

        # Check no progress
        if self.no_progress_count >= self.no_progress_threshold:
            self.state.open()
            return CircuitBreakerResult(
                level=CircuitBreakerLevel.PROGRESS,
                state=CircuitState.OPEN,
                reason=f"No progress for {self.no_progress_count} iterations",
            )

        # Check output quality decline
        if len(self.output_quality_history) >= 3:
            recent = self.output_quality_history[-3:]
            if recent[-1] < self.output_decline_threshold:
                warnings.append(f"Output quality declined to {recent[-1]:.1f}%")

        return CircuitBreakerResult(
            level=CircuitBreakerLevel.PROGRESS,
            state=CircuitState.CLOSED,
            warnings=warnings,
        )


class QualityCircuitBreaker:
    """Circuit breaker for code quality metrics."""

    def __init__(
        self,
        degradation_threshold: int = 3,
        min_coverage: int = 80,
        max_lint_errors: int = 10,
    ) -> None:
        """Initialize quality circuit breaker.

        Args:
            degradation_threshold: Test result degradation threshold
            min_coverage: Minimum acceptable coverage percentage
            max_lint_errors: Maximum acceptable lint errors
        """
        self.degradation_threshold = degradation_threshold
        self.min_coverage = min_coverage
        self.max_lint_errors = max_lint_errors
        self.state = CircuitBreakerState()
        self.test_history: list[tuple[int, int]] = []  # (passed, failed)
        self.coverage: float | None = None
        self.lint_errors: int = 0

    def record_test_result(self, passed: int, failed: int) -> None:
        """Record test results.

        Args:
            passed: Number of tests passed
            failed: Number of tests failed
        """
        self.test_history.append((passed, failed))

    def record_coverage(self, coverage: float) -> None:
        """Record coverage percentage.

        Args:
            coverage: Coverage percentage (0-100)
        """
        self.coverage = coverage

    def record_lint_errors(self, count: int) -> None:
        """Record lint error count.

        Args:
            count: Number of lint errors
        """
        self.lint_errors = count

    def check(self) -> CircuitBreakerResult:
        """Check quality metrics.

        Returns:
            CircuitBreakerResult
        """
        warnings = []

        # Check test degradation
        if len(self.test_history) >= self.degradation_threshold:
            recent = self.test_history[-self.degradation_threshold :]
            # Check if failed tests are increasing
            failed_trend = [r[1] for r in recent]
            is_monotonic = all(
                failed_trend[i] <= failed_trend[i + 1] for i in range(len(failed_trend) - 1)
            )
            if is_monotonic and failed_trend[-1] > failed_trend[0]:
                self.state.open()
                return CircuitBreakerResult(
                    level=CircuitBreakerLevel.QUALITY,
                    state=CircuitState.OPEN,
                    reason=f"Tests degrading: failures increased from {failed_trend[0]} to {failed_trend[-1]}",
                )

        # Check coverage
        if self.coverage is not None and self.coverage < self.min_coverage:
            warnings.append(f"Coverage {self.coverage:.1f}% below minimum {self.min_coverage}%")

        # Check lint errors
        if self.lint_errors > self.max_lint_errors:
            warnings.append(f"Lint errors ({self.lint_errors}) exceed maximum ({self.max_lint_errors})")

        return CircuitBreakerResult(
            level=CircuitBreakerLevel.QUALITY,
            state=CircuitState.CLOSED,
            warnings=warnings,
        )


class TimeCircuitBreaker:
    """Circuit breaker for wall clock time limits."""

    def __init__(
        self,
        max_duration_seconds: float = 7200,  # 2 hours default
        warning_pct: int = 80,
    ) -> None:
        """Initialize time circuit breaker.

        Args:
            max_duration_seconds: Maximum allowed duration
            warning_pct: Percentage of time at which to warn
        """
        self.max_duration_seconds = max_duration_seconds
        self.warning_pct = warning_pct
        self.start_time = time.time()
        self.state = CircuitBreakerState()

    def remaining_time(self) -> float:
        """Get remaining time in seconds.

        Returns:
            Remaining time in seconds
        """
        elapsed = time.time() - self.start_time
        return max(0, self.max_duration_seconds - elapsed)

    def check(self) -> CircuitBreakerResult:
        """Check time against limit.

        Returns:
            CircuitBreakerResult
        """
        elapsed = time.time() - self.start_time
        pct = (elapsed / self.max_duration_seconds) * 100

        if elapsed >= self.max_duration_seconds:
            self.state.open()
            return CircuitBreakerResult(
                level=CircuitBreakerLevel.TIME,
                state=CircuitState.OPEN,
                reason=f"Time limit exceeded: {elapsed:.1f}s >= {self.max_duration_seconds}s",
            )

        if pct >= self.warning_pct:
            remaining = self.max_duration_seconds - elapsed
            return CircuitBreakerResult(
                level=CircuitBreakerLevel.TIME,
                state=CircuitState.CLOSED,
                warnings=[f"Time {pct:.1f}% used, {remaining:.1f}s remaining"],
            )

        return CircuitBreakerResult(
            level=CircuitBreakerLevel.TIME,
            state=CircuitState.CLOSED,
        )


class MultiLevelCircuitBreaker:
    """Combined multi-level circuit breaker."""

    def __init__(
        self,
        max_tokens: int = 100000,
        no_progress_threshold: int = 3,
        max_duration_seconds: float = 7200,
        min_coverage: int = 80,
    ) -> None:
        """Initialize multi-level circuit breaker.

        Args:
            max_tokens: Maximum allowed tokens
            no_progress_threshold: Iterations without progress before trip
            max_duration_seconds: Maximum allowed duration
            min_coverage: Minimum acceptable coverage
        """
        self.token_cb = TokenCircuitBreaker(max_tokens=max_tokens)
        self.progress_cb = ProgressCircuitBreaker(no_progress_threshold=no_progress_threshold)
        self.quality_cb = QualityCircuitBreaker(min_coverage=min_coverage)
        self.time_cb = TimeCircuitBreaker(max_duration_seconds=max_duration_seconds)

    def record_progress(self, files_changed: int, tests_passed: int) -> None:
        """Record progress metrics.

        Args:
            files_changed: Number of files modified
            tests_passed: Number of tests passing
        """
        self.progress_cb.record_progress(files_changed, tests_passed)

    def record_test_result(self, passed: int, failed: int) -> None:
        """Record test results.

        Args:
            passed: Number of tests passed
            failed: Number of tests failed
        """
        self.quality_cb.record_test_result(passed, failed)

    def check(self, current_tokens: int = 0) -> CircuitBreakerResult:
        """Check all circuit breaker levels.

        Args:
            current_tokens: Current token count

        Returns:
            Combined CircuitBreakerResult
        """
        all_warnings: list[str] = []

        # Check token level
        token_result = self.token_cb.check(current_tokens)
        if token_result.is_tripped:
            return token_result
        all_warnings.extend(token_result.warnings)

        # Check progress level
        progress_result = self.progress_cb.check()
        if progress_result.is_tripped:
            return progress_result
        all_warnings.extend(progress_result.warnings)

        # Check quality level
        quality_result = self.quality_cb.check()
        if quality_result.is_tripped:
            return quality_result
        all_warnings.extend(quality_result.warnings)

        # Check time level
        time_result = self.time_cb.check()
        if time_result.is_tripped:
            return time_result
        all_warnings.extend(time_result.warnings)

        return CircuitBreakerResult(
            level=None,
            state=CircuitState.CLOSED,
            warnings=all_warnings,
        )

    def get_status_summary(self) -> dict[str, dict]:
        """Get status summary of all circuit breakers.

        Returns:
            Dictionary with status of each level
        """
        return {
            "token": {
                "state": "open" if self.token_cb.state.is_open else "closed",
                "failures": self.token_cb.state.failure_count,
            },
            "progress": {
                "state": "open" if self.progress_cb.state.is_open else "closed",
                "no_progress_count": self.progress_cb.no_progress_count,
            },
            "quality": {
                "state": "open" if self.quality_cb.state.is_open else "closed",
                "test_history_count": len(self.quality_cb.test_history),
            },
            "time": {
                "state": "open" if self.time_cb.state.is_open else "closed",
                "remaining": self.time_cb.remaining_time(),
            },
        }
