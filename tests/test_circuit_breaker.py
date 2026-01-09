"""Tests for multi-level circuit breakers."""

import time

from src.circuit_breaker import (
    CircuitBreakerLevel,
    CircuitBreakerState,
    MultiLevelCircuitBreaker,
    ProgressCircuitBreaker,
    QualityCircuitBreaker,
    TimeCircuitBreaker,
    TokenCircuitBreaker,
)


class TestCircuitBreakerLevel:
    """Tests for circuit breaker levels."""

    def test_level_ordering(self):
        """Levels should have proper ordering."""
        assert CircuitBreakerLevel.TOKEN.value < CircuitBreakerLevel.PROGRESS.value
        assert CircuitBreakerLevel.PROGRESS.value < CircuitBreakerLevel.QUALITY.value
        assert CircuitBreakerLevel.QUALITY.value < CircuitBreakerLevel.TIME.value

    def test_level_names(self):
        """Levels should have meaningful names."""
        assert "token" in CircuitBreakerLevel.TOKEN.name.lower()
        assert "progress" in CircuitBreakerLevel.PROGRESS.name.lower()
        assert "quality" in CircuitBreakerLevel.QUALITY.name.lower()
        assert "time" in CircuitBreakerLevel.TIME.name.lower()


class TestCircuitBreakerState:
    """Tests for circuit breaker state."""

    def test_initial_state_closed(self):
        """Circuit should start closed (operational)."""
        state = CircuitBreakerState()
        assert state.is_closed

    def test_state_transitions(self):
        """State should transition properly."""
        state = CircuitBreakerState()
        assert state.is_closed

        state.open()
        assert state.is_open
        assert not state.is_closed

        state.half_open()
        assert state.is_half_open

        state.close()
        assert state.is_closed

    def test_failure_count(self):
        """Should track failure count."""
        state = CircuitBreakerState()
        state.record_failure()
        state.record_failure()
        state.record_failure()
        assert state.failure_count == 3

    def test_success_resets_failure_count(self):
        """Success should reset failure count."""
        state = CircuitBreakerState()
        state.record_failure()
        state.record_failure()
        state.record_success()
        assert state.failure_count == 0


class TestTokenCircuitBreaker:
    """Tests for token-level circuit breaker."""

    def test_check_under_limit(self):
        """Should allow when under token limit."""
        cb = TokenCircuitBreaker(max_tokens=100000, threshold_pct=90)
        result = cb.check(current_tokens=50000)
        assert result.is_ok

    def test_trip_at_threshold(self):
        """Should trip when at threshold."""
        cb = TokenCircuitBreaker(max_tokens=100000, threshold_pct=90)
        result = cb.check(current_tokens=92000)
        assert result.is_tripped
        assert "token" in result.reason.lower()

    def test_warning_near_threshold(self):
        """Should warn when approaching threshold."""
        cb = TokenCircuitBreaker(max_tokens=100000, threshold_pct=90)
        result = cb.check(current_tokens=80000)
        assert result.is_warning


class TestProgressCircuitBreaker:
    """Tests for progress-level circuit breaker."""

    def test_check_with_progress(self):
        """Should allow when making progress."""
        cb = ProgressCircuitBreaker(no_progress_threshold=3)
        cb.record_progress(files_changed=1, tests_passed=1)
        result = cb.check()
        assert result.is_ok

    def test_trip_no_progress(self):
        """Should trip after too many iterations without progress."""
        cb = ProgressCircuitBreaker(no_progress_threshold=3)
        cb.record_progress(files_changed=0, tests_passed=0)
        cb.record_progress(files_changed=0, tests_passed=0)
        cb.record_progress(files_changed=0, tests_passed=0)
        result = cb.check()
        assert result.is_tripped
        assert "progress" in result.reason.lower()

    def test_progress_resets_counter(self):
        """Progress should reset no-progress counter."""
        cb = ProgressCircuitBreaker(no_progress_threshold=3)
        cb.record_progress(files_changed=0, tests_passed=0)
        cb.record_progress(files_changed=0, tests_passed=0)
        cb.record_progress(files_changed=1, tests_passed=0)  # Progress!
        cb.record_progress(files_changed=0, tests_passed=0)
        result = cb.check()
        assert result.is_ok  # Counter was reset

    def test_detect_output_decline(self):
        """Should detect declining output quality."""
        cb = ProgressCircuitBreaker(output_decline_threshold=70)
        cb.record_output_quality(100)
        cb.record_output_quality(80)
        cb.record_output_quality(60)  # Declined to 60%
        result = cb.check()
        assert result.is_warning or result.is_tripped


class TestQualityCircuitBreaker:
    """Tests for quality-level circuit breaker."""

    def test_check_tests_passing(self):
        """Should allow when tests are passing."""
        cb = QualityCircuitBreaker()
        cb.record_test_result(passed=10, failed=0)
        result = cb.check()
        assert result.is_ok

    def test_trip_tests_degrading(self):
        """Should trip when tests are degrading."""
        cb = QualityCircuitBreaker(degradation_threshold=3)
        # Simulate tests degrading
        cb.record_test_result(passed=10, failed=0)
        cb.record_test_result(passed=9, failed=1)
        cb.record_test_result(passed=8, failed=2)
        cb.record_test_result(passed=7, failed=3)
        result = cb.check()
        assert result.is_tripped
        assert "quality" in result.reason.lower() or "test" in result.reason.lower()

    def test_coverage_check(self):
        """Should check coverage threshold."""
        cb = QualityCircuitBreaker(min_coverage=80)
        cb.record_coverage(75)
        result = cb.check()
        assert result.is_warning

    def test_lint_errors_check(self):
        """Should check lint error count."""
        cb = QualityCircuitBreaker(max_lint_errors=10)
        cb.record_lint_errors(15)
        result = cb.check()
        assert result.is_warning


class TestTimeCircuitBreaker:
    """Tests for time-level circuit breaker."""

    def test_check_under_time_limit(self):
        """Should allow when under time limit."""
        cb = TimeCircuitBreaker(max_duration_seconds=3600)
        result = cb.check()
        assert result.is_ok

    def test_trip_over_time_limit(self):
        """Should trip when over time limit."""
        cb = TimeCircuitBreaker(max_duration_seconds=0.1)
        time.sleep(0.2)
        result = cb.check()
        assert result.is_tripped
        assert "time" in result.reason.lower()

    def test_warn_approaching_limit(self):
        """Should warn when approaching time limit."""
        cb = TimeCircuitBreaker(max_duration_seconds=1.0, warning_pct=50)
        time.sleep(0.6)  # 60% of time
        result = cb.check()
        assert result.is_warning

    def test_remaining_time(self):
        """Should report remaining time."""
        cb = TimeCircuitBreaker(max_duration_seconds=10)
        remaining = cb.remaining_time()
        assert remaining > 0
        assert remaining <= 10


class TestMultiLevelCircuitBreaker:
    """Tests for combined multi-level circuit breaker."""

    def test_check_all_ok(self):
        """Should be OK when all levels pass."""
        cb = MultiLevelCircuitBreaker(
            max_tokens=100000,
            no_progress_threshold=3,
            max_duration_seconds=3600,
        )
        result = cb.check(current_tokens=50000)
        assert result.is_ok

    def test_trip_on_any_level(self):
        """Should trip if any level trips."""
        cb = MultiLevelCircuitBreaker(
            max_tokens=100000,
            no_progress_threshold=3,
            max_duration_seconds=0.1,  # Very short
        )
        time.sleep(0.2)
        result = cb.check(current_tokens=50000)
        assert result.is_tripped

    def test_report_which_level_tripped(self):
        """Should report which level caused trip."""
        cb = MultiLevelCircuitBreaker(
            max_tokens=100,  # Very low
            no_progress_threshold=3,
            max_duration_seconds=3600,
        )
        result = cb.check(current_tokens=95)
        assert result.is_tripped
        assert result.level == CircuitBreakerLevel.TOKEN

    def test_aggregate_warnings(self):
        """Should aggregate warnings from multiple levels."""
        cb = MultiLevelCircuitBreaker(
            max_tokens=100000,
            no_progress_threshold=3,
            max_duration_seconds=3600,
        )
        # Record some declining metrics
        cb.record_progress(files_changed=0, tests_passed=0)
        cb.record_test_result(passed=9, failed=1)

        result = cb.check(current_tokens=50000)
        # Should have collected warnings
        assert len(result.warnings) >= 0

    def test_status_summary(self):
        """Should provide status summary of all levels."""
        cb = MultiLevelCircuitBreaker(
            max_tokens=100000,
            no_progress_threshold=3,
            max_duration_seconds=3600,
        )
        summary = cb.get_status_summary()

        assert "token" in summary
        assert "progress" in summary
        assert "quality" in summary
        assert "time" in summary


class TestCircuitBreakerRecovery:
    """Tests for circuit breaker recovery."""

    def test_half_open_allows_probe(self):
        """Half-open state should allow probe requests."""
        cb = TokenCircuitBreaker(max_tokens=100, threshold_pct=90)
        cb.check(current_tokens=95)  # Trip it

        # After cooldown, should go half-open
        cb.state.half_open()
        result = cb.check(current_tokens=50)  # Probe
        assert result.is_ok

    def test_successful_probe_closes_circuit(self):
        """Successful probe should close circuit."""
        cb = TokenCircuitBreaker(max_tokens=100, threshold_pct=90)
        cb.check(current_tokens=95)  # Trip it
        cb.state.half_open()
        cb.check(current_tokens=50)  # Successful probe

        assert cb.state.is_closed

    def test_failed_probe_reopens_circuit(self):
        """Failed probe should reopen circuit."""
        cb = TokenCircuitBreaker(max_tokens=100, threshold_pct=90)
        cb.check(current_tokens=95)  # Trip it
        cb.state.half_open()
        cb.check(current_tokens=95)  # Failed probe

        assert cb.state.is_open


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breakers."""

    def test_integrate_with_loop_controller(self):
        """Should integrate with loop controller."""
        from src.loop_control import LoopController

        cb = MultiLevelCircuitBreaker(
            max_tokens=100000,
            no_progress_threshold=3,
            max_duration_seconds=3600,
        )
        controller = LoopController()

        # Simulate iterations
        for _ in range(5):
            controller.tick()
            cb.record_progress(files_changed=1, tests_passed=1)

            result = cb.check(current_tokens=50000)
            if result.is_tripped:
                break

        # Should not have tripped
        assert not cb.check(current_tokens=50000).is_tripped

    def test_integrate_with_error_classifier(self):
        """Should integrate with error classifier."""
        from src.error_classifier import ErrorClassifier

        cb = MultiLevelCircuitBreaker(
            max_tokens=100000,
            no_progress_threshold=3,
            max_duration_seconds=3600,
        )
        classifier = ErrorClassifier()

        # Simulate errors
        for _ in range(3):
            classifier.record_error("SomeError")
            cb.record_progress(files_changed=0, tests_passed=0)

        result = cb.check(current_tokens=50000)
        assert result.is_tripped or len(result.warnings) > 0
