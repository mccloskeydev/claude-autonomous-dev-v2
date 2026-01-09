"""Self-optimization based on outcomes.

This module provides self-optimization for autonomous development:

- Outcome recording and tracking
- Tuning parameters with ranges
- Optimization strategies
- Parameter adjustment based on outcomes
- Integration with metrics
"""

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class OutcomeType(Enum):
    """Types of outcomes."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMEOUT = "timeout"


class OptimizationStrategy(Enum):
    """Optimization strategies."""

    HILL_CLIMBING = "hill_climbing"
    SIMULATED_ANNEALING = "simulated_annealing"
    RANDOM_SEARCH = "random_search"
    GRADIENT_DESCENT = "gradient_descent"


@dataclass
class Outcome:
    """A recorded outcome."""

    outcome_type: OutcomeType
    metric_name: str
    value: float
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class ParameterRange:
    """Valid range for a parameter."""

    min_value: float
    max_value: float
    step: float = 1

    def is_valid(self, value: float) -> bool:
        """Check if value is in range.

        Args:
            value: Value to check

        Returns:
            True if valid
        """
        return self.min_value <= value <= self.max_value

    def clamp(self, value: float) -> float:
        """Clamp value to range.

        Args:
            value: Value to clamp

        Returns:
            Clamped value
        """
        return max(self.min_value, min(self.max_value, value))


@dataclass
class ParameterHistoryEntry:
    """Entry in parameter history."""

    value: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class TuningParameter:
    """A parameter that can be tuned."""

    name: str
    current_value: float
    range: ParameterRange
    history: list[ParameterHistoryEntry] = field(default_factory=list)

    def __post_init__(self):
        """Record initial value in history."""
        self.history.append(ParameterHistoryEntry(value=self.current_value))

    def adjust(self, new_value: float) -> None:
        """Adjust parameter value.

        Args:
            new_value: New value (will be clamped to range)
        """
        self.current_value = self.range.clamp(new_value)
        self.history.append(ParameterHistoryEntry(value=self.current_value))


class SelfOptimizer:
    """Optimizes parameters based on outcomes."""

    def __init__(
        self,
        learning_rate: float = 0.1,
        strategy: OptimizationStrategy = OptimizationStrategy.HILL_CLIMBING,
    ) -> None:
        """Initialize self optimizer.

        Args:
            learning_rate: Rate of parameter adjustment
            strategy: Optimization strategy to use
        """
        self.learning_rate = learning_rate
        self.strategy = strategy
        self._parameters: dict[str, TuningParameter] = {}
        self.outcomes: list[Outcome] = []
        self._optimization_steps = 0

    def register_parameter(
        self,
        name: str,
        initial_value: float,
        min_value: float,
        max_value: float,
        step: float = 1,
    ) -> None:
        """Register a tuning parameter.

        Args:
            name: Parameter name
            initial_value: Starting value
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            step: Step size for adjustments
        """
        param = TuningParameter(
            name=name,
            current_value=initial_value,
            range=ParameterRange(min_value=min_value, max_value=max_value, step=step),
        )
        self._parameters[name] = param

    def get_parameter(self, name: str) -> TuningParameter | None:
        """Get a parameter by name.

        Args:
            name: Parameter name

        Returns:
            TuningParameter or None
        """
        return self._parameters.get(name)

    def record_outcome(
        self,
        outcome_type: OutcomeType,
        metric_name: str,
        value: float,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Record an outcome.

        Args:
            outcome_type: Type of outcome
            metric_name: Name of metric
            value: Metric value
            context: Optional context
        """
        outcome = Outcome(
            outcome_type=outcome_type,
            metric_name=metric_name,
            value=value,
            context=context or {},
        )
        self.outcomes.append(outcome)

    def success_rate(self) -> float:
        """Calculate success rate.

        Returns:
            Success rate between 0 and 1
        """
        if not self.outcomes:
            return 1.0
        successes = sum(1 for o in self.outcomes if o.outcome_type == OutcomeType.SUCCESS)
        return successes / len(self.outcomes)

    def get_recommendations(self) -> dict[str, Any]:
        """Get parameter adjustment recommendations.

        Returns:
            Dictionary of recommendations
        """
        recommendations = {}

        # Analyze recent outcomes
        recent = self.outcomes[-20:] if len(self.outcomes) > 20 else self.outcomes
        recent_success_rate = (
            sum(1 for o in recent if o.outcome_type == OutcomeType.SUCCESS) / len(recent)
            if recent
            else 1.0
        )

        # Count outcome types
        timeout_count = sum(1 for o in recent if o.outcome_type == OutcomeType.TIMEOUT)
        failure_count = sum(1 for o in recent if o.outcome_type == OutcomeType.FAILURE)

        # Generate recommendations based on patterns
        for name, param in self._parameters.items():
            if "timeout" in name.lower() and timeout_count > len(recent) * 0.3:
                recommendations[name] = {
                    "action": "increase",
                    "reason": "High timeout rate",
                    "suggested_value": min(param.current_value * 1.5, param.range.max_value),
                }
            elif "retry" in name.lower() and failure_count > len(recent) * 0.3:
                recommendations[name] = {
                    "action": "increase",
                    "reason": "High failure rate",
                    "suggested_value": min(param.current_value + param.range.step, param.range.max_value),
                }
            elif recent_success_rate > 0.9 and "iteration" in name.lower():
                # Things are going well, could be more aggressive
                recommendations[name] = {
                    "action": "decrease",
                    "reason": "High success rate, can be more efficient",
                    "suggested_value": max(param.current_value * 0.9, param.range.min_value),
                }

        return recommendations

    def optimize_step(self) -> None:
        """Perform one optimization step."""
        self._optimization_steps += 1
        recommendations = self.get_recommendations()

        # Apply recommendations based on strategy
        if self.strategy == OptimizationStrategy.HILL_CLIMBING:
            for name, rec in recommendations.items():
                param = self._parameters.get(name)
                if param and "suggested_value" in rec:
                    # Apply with learning rate
                    diff = rec["suggested_value"] - param.current_value
                    new_value = param.current_value + (diff * self.learning_rate)
                    param.adjust(new_value)

        elif self.strategy == OptimizationStrategy.RANDOM_SEARCH:
            import random
            for _name, param in self._parameters.items():
                if random.random() < 0.2:  # 20% chance to adjust
                    # Random step in either direction
                    adjustment = random.choice([-1, 1]) * param.range.step
                    param.adjust(param.current_value + adjustment)

        elif self.strategy == OptimizationStrategy.SIMULATED_ANNEALING:
            import random
            # Temperature decreases with more outcomes (more certainty)
            temperature = max(0.1, 1.0 - len(self.outcomes) / 100)
            for name, rec in recommendations.items():
                param = self._parameters.get(name)
                if param and "suggested_value" in rec:
                    diff = rec["suggested_value"] - param.current_value
                    # Accept change based on temperature
                    if random.random() < temperature or diff > 0:
                        new_value = param.current_value + (diff * self.learning_rate)
                        param.adjust(new_value)

    def get_correlations(self) -> dict[str, float]:
        """Get correlations between parameters and outcomes.

        Returns:
            Dictionary of correlations
        """
        correlations = {}

        # Simple correlation: track if parameter changes align with outcome changes
        for name, param in self._parameters.items():
            if len(param.history) >= 2 and len(self.outcomes) >= 2:
                # Check if parameter increases correlate with success
                param_trend = param.history[-1].value - param.history[0].value
                recent_successes = sum(
                    1 for o in self.outcomes[-5:]
                    if o.outcome_type == OutcomeType.SUCCESS
                )
                if param_trend != 0:
                    correlations[name] = recent_successes / 5 if param_trend > 0 else -recent_successes / 5

        return correlations

    def set_learning_rate(self, rate: float) -> None:
        """Set learning rate.

        Args:
            rate: New learning rate
        """
        self.learning_rate = rate

    def set_strategy(self, strategy: OptimizationStrategy) -> None:
        """Set optimization strategy.

        Args:
            strategy: New strategy
        """
        self.strategy = strategy

    def get_summary(self) -> dict[str, Any]:
        """Get optimization summary.

        Returns:
            Summary dictionary
        """
        return {
            "total_outcomes": len(self.outcomes),
            "success_rate": self.success_rate(),
            "learning_rate": self.learning_rate,
            "strategy": self.strategy.value,
            "optimization_steps": self._optimization_steps,
            "parameters": {
                name: {
                    "current_value": param.current_value,
                    "min": param.range.min_value,
                    "max": param.range.max_value,
                    "history_length": len(param.history),
                }
                for name, param in self._parameters.items()
            },
        }

    def save(self, filepath: Path) -> None:
        """Save optimizer state to file.

        Args:
            filepath: Path to save to
        """
        data = {
            "learning_rate": self.learning_rate,
            "strategy": self.strategy.value,
            "optimization_steps": self._optimization_steps,
            "parameters": {
                name: {
                    "name": param.name,
                    "current_value": param.current_value,
                    "min_value": param.range.min_value,
                    "max_value": param.range.max_value,
                    "step": param.range.step,
                    "history": [
                        {"value": h.value, "timestamp": h.timestamp}
                        for h in param.history
                    ],
                }
                for name, param in self._parameters.items()
            },
            "outcomes": [
                {
                    "outcome_type": o.outcome_type.value,
                    "metric_name": o.metric_name,
                    "value": o.value,
                    "context": o.context,
                    "timestamp": o.timestamp,
                }
                for o in self.outcomes
            ],
        }

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, filepath: Path) -> "SelfOptimizer":
        """Load optimizer state from file.

        Args:
            filepath: Path to load from

        Returns:
            SelfOptimizer instance
        """
        with open(filepath) as f:
            data = json.load(f)

        optimizer = cls(
            learning_rate=data.get("learning_rate", 0.1),
            strategy=OptimizationStrategy(data.get("strategy", "hill_climbing")),
        )
        optimizer._optimization_steps = data.get("optimization_steps", 0)

        # Restore parameters
        for name, param_data in data.get("parameters", {}).items():
            param = TuningParameter(
                name=param_data["name"],
                current_value=param_data["current_value"],
                range=ParameterRange(
                    min_value=param_data["min_value"],
                    max_value=param_data["max_value"],
                    step=param_data.get("step", 1),
                ),
            )
            # Clear auto-created history and restore actual history
            param.history = [
                ParameterHistoryEntry(
                    value=h["value"],
                    timestamp=h.get("timestamp", time.time()),
                )
                for h in param_data.get("history", [])
            ]
            optimizer._parameters[name] = param

        # Restore outcomes
        for outcome_data in data.get("outcomes", []):
            outcome = Outcome(
                outcome_type=OutcomeType(outcome_data["outcome_type"]),
                metric_name=outcome_data["metric_name"],
                value=outcome_data["value"],
                context=outcome_data.get("context", {}),
                timestamp=outcome_data.get("timestamp", time.time()),
            )
            optimizer.outcomes.append(outcome)

        return optimizer
