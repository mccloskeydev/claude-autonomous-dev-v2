"""Tests for enhanced loop control with adaptive iteration limits."""


from src.loop_control import (
    BackoffStrategy,
    LoopConfig,
    LoopController,
    LoopState,
    TaskComplexity,
)


class TestTaskComplexity:
    """Tests for task complexity assessment."""

    def test_complexity_from_file_count(self):
        """Complexity should scale with number of files affected."""
        assert TaskComplexity.from_metrics(file_count=1).value <= TaskComplexity.SIMPLE.value
        assert TaskComplexity.from_metrics(file_count=5).value >= TaskComplexity.MODERATE.value
        assert TaskComplexity.from_metrics(file_count=20).value >= TaskComplexity.COMPLEX.value

    def test_complexity_from_test_count(self):
        """Complexity should consider number of tests to write."""
        assert TaskComplexity.from_metrics(test_count=2).value <= TaskComplexity.SIMPLE.value
        assert TaskComplexity.from_metrics(test_count=10).value >= TaskComplexity.MODERATE.value

    def test_complexity_from_dependency_depth(self):
        """Complexity increases with dependency chain depth."""
        assert TaskComplexity.from_metrics(dependency_depth=1).value <= TaskComplexity.SIMPLE.value
        assert TaskComplexity.from_metrics(dependency_depth=5).value >= TaskComplexity.COMPLEX.value

    def test_combined_complexity(self):
        """Multiple factors should combine for overall complexity."""
        complexity = TaskComplexity.from_metrics(
            file_count=5,
            test_count=8,
            dependency_depth=3
        )
        assert complexity.value >= TaskComplexity.MODERATE.value


class TestLoopConfig:
    """Tests for adaptive loop configuration."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = LoopConfig()
        assert config.base_iterations == 50
        assert config.min_iterations == 10
        assert config.max_iterations == 200

    def test_iterations_for_simple_task(self):
        """Simple tasks should have fewer allowed iterations."""
        config = LoopConfig()
        iterations = config.get_adaptive_limit(TaskComplexity.SIMPLE)
        assert iterations >= config.min_iterations
        assert iterations <= config.base_iterations

    def test_iterations_for_complex_task(self):
        """Complex tasks should allow more iterations."""
        config = LoopConfig()
        iterations = config.get_adaptive_limit(TaskComplexity.COMPLEX)
        assert iterations >= config.base_iterations
        assert iterations <= config.max_iterations

    def test_iterations_for_epic_task(self):
        """Epic tasks should get maximum iterations."""
        config = LoopConfig()
        iterations = config.get_adaptive_limit(TaskComplexity.EPIC)
        assert iterations == config.max_iterations


class TestBackoffStrategy:
    """Tests for intelligent backoff when stuck."""

    def test_initial_backoff(self):
        """First backoff should be minimal."""
        strategy = BackoffStrategy()
        delay = strategy.get_delay(attempt=1)
        assert delay <= 1.0  # seconds

    def test_exponential_backoff(self):
        """Backoff should increase exponentially."""
        strategy = BackoffStrategy()
        delay1 = strategy.get_delay(attempt=1)
        delay2 = strategy.get_delay(attempt=2)
        delay3 = strategy.get_delay(attempt=3)
        assert delay2 > delay1
        assert delay3 > delay2

    def test_max_backoff_cap(self):
        """Backoff should not exceed maximum."""
        strategy = BackoffStrategy(max_delay=30.0)
        delay = strategy.get_delay(attempt=100)
        assert delay <= 30.0

    def test_jitter(self):
        """Backoff should include jitter to avoid thundering herd."""
        strategy = BackoffStrategy(jitter=True)
        delays = [strategy.get_delay(attempt=5) for _ in range(10)]
        # With jitter, not all delays should be exactly the same
        assert len(set(delays)) > 1


class TestLoopState:
    """Tests for loop state tracking."""

    def test_initial_state(self):
        """State should start clean."""
        state = LoopState()
        assert state.iteration == 0
        assert state.errors_count == 0
        assert not state.is_stuck

    def test_increment_iteration(self):
        """Should track iteration count."""
        state = LoopState()
        state.increment()
        assert state.iteration == 1
        state.increment()
        assert state.iteration == 2

    def test_record_error(self):
        """Should track errors."""
        state = LoopState()
        state.record_error("SyntaxError: invalid syntax")
        assert state.errors_count == 1
        assert "SyntaxError" in state.last_error

    def test_stuck_detection_same_error(self):
        """Should detect when stuck on same error."""
        state = LoopState(stuck_threshold=3)
        error = "ImportError: module not found"
        for _ in range(3):
            state.record_error(error)
        assert state.is_stuck

    def test_progress_resets_stuck(self):
        """Progress should reset stuck state."""
        state = LoopState(stuck_threshold=3)
        state.record_error("error")
        state.record_error("error")
        state.record_progress(files_changed=2, tests_passed=1)
        state.record_error("error")
        assert not state.is_stuck  # Progress reset the counter

    def test_no_progress_detection(self):
        """Should detect lack of progress."""
        state = LoopState(no_progress_threshold=3)
        for _ in range(3):
            state.record_progress(files_changed=0, tests_passed=0)
        assert state.has_no_progress


class TestLoopController:
    """Tests for the main loop controller."""

    def test_controller_creation(self):
        """Controller should initialize properly."""
        controller = LoopController()
        assert controller.state.iteration == 0
        assert not controller.should_stop()

    def test_simple_task_loop(self):
        """Controller should handle simple task iteration."""
        controller = LoopController(complexity=TaskComplexity.SIMPLE)
        limit = controller.iteration_limit
        assert limit < 50  # Less than base for simple tasks

    def test_stop_on_max_iterations(self):
        """Should stop when max iterations reached."""
        controller = LoopController(complexity=TaskComplexity.SIMPLE)
        limit = controller.iteration_limit
        for _ in range(limit):
            controller.tick()
        assert controller.should_stop()
        assert "max iterations" in controller.stop_reason.lower()

    def test_stop_when_stuck(self):
        """Should stop when stuck on same error."""
        controller = LoopController()
        same_error = "TypeError: something wrong"
        for _ in range(5):
            controller.tick()
            controller.record_error(same_error)
        assert controller.should_stop()
        assert "stuck" in controller.stop_reason.lower()

    def test_stop_on_no_progress(self):
        """Should stop when no progress for too long."""
        controller = LoopController()
        for _ in range(5):
            controller.tick()
            controller.record_progress(files_changed=0, tests_passed=0)
        assert controller.should_stop()
        assert "progress" in controller.stop_reason.lower()

    def test_continue_with_progress(self):
        """Should continue when making progress."""
        controller = LoopController()
        for _ in range(10):
            controller.tick()
            controller.record_progress(files_changed=1, tests_passed=1)
        assert not controller.should_stop()

    def test_get_backoff_when_stuck(self):
        """Should recommend backoff delay when having issues."""
        controller = LoopController()
        controller.record_error("error1")
        controller.record_error("error2")
        delay = controller.get_recommended_delay()
        assert delay > 0

    def test_reset_on_major_progress(self):
        """Major progress should reset error counters."""
        controller = LoopController()
        for _ in range(3):
            controller.record_error("same error")
        controller.record_progress(files_changed=5, tests_passed=10)
        assert not controller.state.is_stuck

    def test_iteration_history(self):
        """Should track iteration history for analysis."""
        controller = LoopController()
        controller.tick()
        controller.record_progress(files_changed=1, tests_passed=0)
        controller.tick()
        controller.record_progress(files_changed=2, tests_passed=1)

        history = controller.get_history()
        assert len(history) == 2
        assert history[0]["files_changed"] == 1
        assert history[1]["tests_passed"] == 1
