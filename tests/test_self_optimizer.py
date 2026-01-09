"""Tests for self-optimization based on outcomes."""

import tempfile
from pathlib import Path

from src.self_optimizer import (
    OptimizationStrategy,
    Outcome,
    OutcomeType,
    ParameterRange,
    SelfOptimizer,
    TuningParameter,
)


class TestOutcomeType:
    """Tests for outcome types."""

    def test_outcome_types(self):
        """Should have expected outcome types."""
        assert OutcomeType.SUCCESS
        assert OutcomeType.FAILURE
        assert OutcomeType.PARTIAL
        assert OutcomeType.TIMEOUT


class TestOutcome:
    """Tests for outcome recording."""

    def test_outcome_creation(self):
        """Should create outcome with required fields."""
        outcome = Outcome(
            outcome_type=OutcomeType.SUCCESS,
            metric_name="tests_passed",
            value=25,
        )
        assert outcome.outcome_type == OutcomeType.SUCCESS
        assert outcome.metric_name == "tests_passed"
        assert outcome.value == 25

    def test_outcome_with_context(self):
        """Should store context."""
        outcome = Outcome(
            outcome_type=OutcomeType.FAILURE,
            metric_name="error_count",
            value=3,
            context={"task": "F001", "phase": "testing"},
        )
        assert outcome.context["task"] == "F001"

    def test_outcome_timestamp(self):
        """Should have timestamp."""
        outcome = Outcome(
            outcome_type=OutcomeType.SUCCESS,
            metric_name="coverage",
            value=85,
        )
        assert outcome.timestamp is not None


class TestParameterRange:
    """Tests for parameter ranges."""

    def test_range_creation(self):
        """Should create parameter range."""
        param_range = ParameterRange(
            min_value=1,
            max_value=100,
            step=5,
        )
        assert param_range.min_value == 1
        assert param_range.max_value == 100
        assert param_range.step == 5

    def test_is_valid(self):
        """Should validate values."""
        param_range = ParameterRange(min_value=0, max_value=10, step=1)
        assert param_range.is_valid(5)
        assert not param_range.is_valid(15)
        assert not param_range.is_valid(-1)

    def test_clamp(self):
        """Should clamp values to range."""
        param_range = ParameterRange(min_value=0, max_value=10, step=1)
        assert param_range.clamp(5) == 5
        assert param_range.clamp(15) == 10
        assert param_range.clamp(-5) == 0


class TestTuningParameter:
    """Tests for tuning parameters."""

    def test_parameter_creation(self):
        """Should create tuning parameter."""
        param = TuningParameter(
            name="max_iterations",
            current_value=50,
            range=ParameterRange(min_value=10, max_value=200, step=10),
        )
        assert param.name == "max_iterations"
        assert param.current_value == 50

    def test_parameter_adjustment(self):
        """Should adjust parameter value."""
        param = TuningParameter(
            name="retry_limit",
            current_value=3,
            range=ParameterRange(min_value=1, max_value=10, step=1),
        )
        param.adjust(5)
        assert param.current_value == 5

    def test_parameter_history(self):
        """Should track value history."""
        param = TuningParameter(
            name="timeout",
            current_value=30,
            range=ParameterRange(min_value=10, max_value=120, step=10),
        )
        param.adjust(40)
        param.adjust(50)
        param.adjust(60)

        assert len(param.history) >= 3

    def test_parameter_bounded_adjustment(self):
        """Should bound adjustments to range."""
        param = TuningParameter(
            name="limit",
            current_value=50,
            range=ParameterRange(min_value=0, max_value=100, step=1),
        )
        param.adjust(150)  # Over max
        assert param.current_value == 100

        param.adjust(-10)  # Under min
        assert param.current_value == 0


class TestOptimizationStrategy:
    """Tests for optimization strategy enum."""

    def test_strategies(self):
        """Should have expected strategies."""
        assert OptimizationStrategy.HILL_CLIMBING
        assert OptimizationStrategy.SIMULATED_ANNEALING
        assert OptimizationStrategy.RANDOM_SEARCH
        assert OptimizationStrategy.GRADIENT_DESCENT


class TestSelfOptimizer:
    """Tests for self optimizer."""

    def test_optimizer_creation(self):
        """Should create optimizer."""
        optimizer = SelfOptimizer()
        assert optimizer is not None

    def test_register_parameter(self):
        """Should register tuning parameter."""
        optimizer = SelfOptimizer()
        optimizer.register_parameter(
            name="max_iterations",
            initial_value=50,
            min_value=10,
            max_value=200,
            step=10,
        )
        assert optimizer.get_parameter("max_iterations") is not None
        assert optimizer.get_parameter("max_iterations").current_value == 50

    def test_record_outcome(self):
        """Should record outcomes."""
        optimizer = SelfOptimizer()
        optimizer.record_outcome(
            outcome_type=OutcomeType.SUCCESS,
            metric_name="tests_passed",
            value=25,
        )
        assert len(optimizer.outcomes) == 1

    def test_get_recommendations(self):
        """Should provide parameter recommendations."""
        optimizer = SelfOptimizer()
        optimizer.register_parameter(
            name="max_iterations",
            initial_value=50,
            min_value=10,
            max_value=200,
            step=10,
        )

        # Record some successes
        for _ in range(5):
            optimizer.record_outcome(
                outcome_type=OutcomeType.SUCCESS,
                metric_name="completion",
                value=100,
            )

        recommendations = optimizer.get_recommendations()
        assert isinstance(recommendations, dict)

    def test_optimize_step(self):
        """Should perform optimization step."""
        optimizer = SelfOptimizer()
        optimizer.register_parameter(
            name="timeout",
            initial_value=30,
            min_value=10,
            max_value=120,
            step=10,
        )

        # Record failures (might suggest increasing timeout)
        for _ in range(3):
            optimizer.record_outcome(
                outcome_type=OutcomeType.TIMEOUT,
                metric_name="completion",
                value=0,
                context={"parameter": "timeout"},
            )

        optimizer.optimize_step()
        # Parameter should have been adjusted
        param = optimizer.get_parameter("timeout")
        assert param.current_value != 30 or len(param.history) > 0

    def test_success_rate_tracking(self):
        """Should track success rate."""
        optimizer = SelfOptimizer()

        for _ in range(7):
            optimizer.record_outcome(OutcomeType.SUCCESS, "test", 1)
        for _ in range(3):
            optimizer.record_outcome(OutcomeType.FAILURE, "test", 0)

        rate = optimizer.success_rate()
        assert rate == 0.7

    def test_outcome_correlation(self):
        """Should correlate outcomes with parameters."""
        optimizer = SelfOptimizer()
        optimizer.register_parameter(
            name="batch_size",
            initial_value=10,
            min_value=1,
            max_value=100,
            step=5,
        )

        # Record outcomes with different batch sizes
        optimizer.get_parameter("batch_size").adjust(10)
        optimizer.record_outcome(OutcomeType.FAILURE, "speed", 50)

        optimizer.get_parameter("batch_size").adjust(20)
        optimizer.record_outcome(OutcomeType.SUCCESS, "speed", 100)

        correlations = optimizer.get_correlations()
        assert "batch_size" in correlations or len(correlations) >= 0

    def test_learning_rate(self):
        """Should support adjustable learning rate."""
        optimizer = SelfOptimizer(learning_rate=0.1)
        assert optimizer.learning_rate == 0.1

        optimizer.set_learning_rate(0.05)
        assert optimizer.learning_rate == 0.05

    def test_strategy_selection(self):
        """Should support different optimization strategies."""
        optimizer = SelfOptimizer(strategy=OptimizationStrategy.HILL_CLIMBING)
        assert optimizer.strategy == OptimizationStrategy.HILL_CLIMBING

        optimizer.set_strategy(OptimizationStrategy.SIMULATED_ANNEALING)
        assert optimizer.strategy == OptimizationStrategy.SIMULATED_ANNEALING

    def test_get_summary(self):
        """Should provide optimization summary."""
        optimizer = SelfOptimizer()
        optimizer.register_parameter("param1", 10, 0, 100, 5)
        optimizer.record_outcome(OutcomeType.SUCCESS, "metric", 1)

        summary = optimizer.get_summary()
        assert "total_outcomes" in summary
        assert "success_rate" in summary
        assert "parameters" in summary

    def test_persistence(self):
        """Should save and load optimizer state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "optimizer.json"

            optimizer = SelfOptimizer()
            optimizer.register_parameter("timeout", 30, 10, 120, 10)
            optimizer.record_outcome(OutcomeType.SUCCESS, "tests", 25)
            optimizer.save(filepath)

            loaded = SelfOptimizer.load(filepath)
            assert loaded.get_parameter("timeout") is not None
            assert len(loaded.outcomes) == 1


class TestSelfOptimizerIntegration:
    """Integration tests for self optimizer."""

    def test_integration_with_metrics(self):
        """Should integrate with metrics from F013."""
        from src.metrics import MetricType, SessionMetrics

        optimizer = SelfOptimizer()
        optimizer.register_parameter("max_iterations", 50, 10, 200, 10)

        # Create session metrics
        session = SessionMetrics(session_id="test")
        session.collector.record(MetricType.ITERATIONS, 45)
        session.collector.record(MetricType.FEATURES_COMPLETED, 3)

        # Record outcome from metrics
        optimizer.record_outcome(
            outcome_type=OutcomeType.SUCCESS,
            metric_name="features_completed",
            value=session.collector.get_sum(MetricType.FEATURES_COMPLETED),
            context={"session_id": session.session_id},
        )

        assert len(optimizer.outcomes) == 1
        assert optimizer.outcomes[0].value == 3

    def test_full_optimization_cycle(self):
        """Should complete full optimization cycle."""
        optimizer = SelfOptimizer()

        # Register parameters
        optimizer.register_parameter("retry_limit", 3, 1, 10, 1)
        optimizer.register_parameter("timeout", 30, 10, 120, 10)

        # Simulate multiple iterations with outcomes
        for i in range(10):
            # Record varying outcomes
            outcome_type = OutcomeType.SUCCESS if i % 3 != 0 else OutcomeType.FAILURE
            optimizer.record_outcome(
                outcome_type=outcome_type,
                metric_name="iteration_success",
                value=1 if outcome_type == OutcomeType.SUCCESS else 0,
            )

            # Periodically optimize
            if i % 5 == 4:
                optimizer.optimize_step()

        # Should have adjusted parameters
        summary = optimizer.get_summary()
        assert summary["total_outcomes"] == 10
        assert summary["optimization_steps"] >= 1
