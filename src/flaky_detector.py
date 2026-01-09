"""Flaky test detection and quarantine.

This module provides flaky test detection for autonomous development:

- Test run recording and history tracking
- Flakiness score calculation based on pass/fail transitions
- Automatic quarantine for highly flaky tests
- Persistence for tracking across sessions
- Integration with test analyzer
"""

import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class QuarantineStatus(Enum):
    """Status of a test in the quarantine system."""

    ACTIVE = "active"  # Normal test, not quarantined
    QUARANTINED = "quarantined"  # Quarantined, skipped in CI
    PROBATION = "probation"  # Being tested for stability
    RETIRED = "retired"  # Permanently disabled


@dataclass
class TestRun:
    """A single test run result."""

    test_name: str
    passed: bool
    timestamp: float = field(default_factory=time.time)
    duration_ms: float | None = None
    error_message: str | None = None


@dataclass
class TestHistory:
    """History of runs for a single test."""

    test_name: str
    runs: list[TestRun] = field(default_factory=list)

    def add_run(self, run: TestRun) -> None:
        """Add a run to history.

        Args:
            run: Test run to add
        """
        self.runs.append(run)

    def pass_rate(self) -> float:
        """Calculate pass rate.

        Returns:
            Pass rate between 0.0 and 1.0
        """
        if not self.runs:
            return 1.0
        passed = sum(1 for r in self.runs if r.passed)
        return passed / len(self.runs)

    def failure_rate(self) -> float:
        """Calculate failure rate.

        Returns:
            Failure rate between 0.0 and 1.0
        """
        return 1.0 - self.pass_rate()

    def flakiness_score(self) -> float:
        """Calculate flakiness score based on pass/fail transitions.

        A test that alternates between pass/fail is flaky.
        A test that consistently passes or fails is not flaky.

        Returns:
            Flakiness score between 0.0 and 1.0
        """
        if len(self.runs) < 2:
            return 0.0

        # Count transitions between pass and fail
        transitions = 0
        for i in range(1, len(self.runs)):
            if self.runs[i].passed != self.runs[i - 1].passed:
                transitions += 1

        # Max possible transitions is len(runs) - 1
        max_transitions = len(self.runs) - 1
        return transitions / max_transitions if max_transitions > 0 else 0.0

    def recent_runs(self, count: int) -> list[TestRun]:
        """Get most recent runs.

        Args:
            count: Number of runs to get

        Returns:
            List of recent runs
        """
        return self.runs[-count:] if self.runs else []


@dataclass
class FlakyTestCandidate:
    """A test identified as potentially flaky."""

    test_name: str
    flakiness_score: float
    pass_rate: float
    run_count: int
    recent_failures: int = 0

    @property
    def recommendation(self) -> str:
        """Get recommendation based on flakiness.

        Returns:
            Recommendation string
        """
        if self.flakiness_score >= 0.6:
            return "Quarantine: Highly flaky test should be isolated and fixed"
        elif self.flakiness_score >= 0.4:
            return "Investigate: Moderate flakiness, needs attention"
        else:
            return "Monitor: Low flakiness, continue tracking"


@dataclass
class QuarantineEntry:
    """Entry for a quarantined test."""

    test_name: str
    status: QuarantineStatus
    reason: str
    quarantined_at: float = field(default_factory=time.time)
    probation_started: float | None = None


class FlakyDetector:
    """Detects and manages flaky tests."""

    def __init__(
        self,
        flakiness_threshold: float = 0.3,
        min_runs: int = 5,
        auto_quarantine: bool = False,
        retention_days: int = 30,
    ) -> None:
        """Initialize flaky detector.

        Args:
            flakiness_threshold: Score above which test is considered flaky
            min_runs: Minimum runs before evaluating flakiness
            auto_quarantine: Whether to auto-quarantine flaky tests
            retention_days: Days to retain test run history
        """
        self.flakiness_threshold = flakiness_threshold
        self.min_runs = min_runs
        self.auto_quarantine = auto_quarantine
        self.retention_days = retention_days

        self._histories: dict[str, TestHistory] = {}
        self._quarantine: dict[str, QuarantineEntry] = {}

    def get_history(self, test_name: str) -> TestHistory:
        """Get or create history for a test.

        Args:
            test_name: Name of test

        Returns:
            TestHistory for the test
        """
        if test_name not in self._histories:
            self._histories[test_name] = TestHistory(test_name=test_name)
        return self._histories[test_name]

    def record_run(
        self,
        test_name: str,
        passed: bool,
        duration_ms: float | None = None,
        error_message: str | None = None,
    ) -> None:
        """Record a test run.

        Args:
            test_name: Name of test
            passed: Whether test passed
            duration_ms: Test duration in milliseconds
            error_message: Error message if failed
        """
        run = TestRun(
            test_name=test_name,
            passed=passed,
            duration_ms=duration_ms,
            error_message=error_message,
        )

        history = self.get_history(test_name)
        history.add_run(run)

        # Check for auto-quarantine
        if self.auto_quarantine:
            self._check_auto_quarantine(test_name)

    def _check_auto_quarantine(self, test_name: str) -> None:
        """Check if test should be auto-quarantined.

        Args:
            test_name: Name of test to check
        """
        history = self.get_history(test_name)

        if len(history.runs) < self.min_runs:
            return

        score = history.flakiness_score()
        if score >= self.flakiness_threshold and not self.is_quarantined(test_name):
            self.quarantine_test(test_name, reason="Auto-quarantined: flakiness score exceeded threshold")

    def detect_flaky_tests(self) -> list[FlakyTestCandidate]:
        """Detect all flaky tests.

        Returns:
            List of flaky test candidates
        """
        candidates = []

        for test_name, history in self._histories.items():
            if len(history.runs) < self.min_runs:
                continue

            score = history.flakiness_score()
            if score >= self.flakiness_threshold:
                recent = history.recent_runs(5)
                recent_failures = sum(1 for r in recent if not r.passed)

                candidates.append(
                    FlakyTestCandidate(
                        test_name=test_name,
                        flakiness_score=score,
                        pass_rate=history.pass_rate(),
                        run_count=len(history.runs),
                        recent_failures=recent_failures,
                    )
                )

        return candidates

    def quarantine_test(self, test_name: str, reason: str) -> None:
        """Quarantine a test.

        Args:
            test_name: Name of test to quarantine
            reason: Reason for quarantine
        """
        self._quarantine[test_name] = QuarantineEntry(
            test_name=test_name,
            status=QuarantineStatus.QUARANTINED,
            reason=reason,
        )

    def unquarantine_test(self, test_name: str) -> None:
        """Remove a test from quarantine.

        Args:
            test_name: Name of test to unquarantine
        """
        if test_name in self._quarantine:
            del self._quarantine[test_name]

    def is_quarantined(self, test_name: str) -> bool:
        """Check if a test is quarantined.

        Args:
            test_name: Name of test to check

        Returns:
            True if test is quarantined
        """
        if test_name not in self._quarantine:
            return False
        return self._quarantine[test_name].status == QuarantineStatus.QUARANTINED

    def get_quarantined_tests(self) -> list[str]:
        """Get all quarantined test names.

        Returns:
            List of quarantined test names
        """
        return [
            name
            for name, entry in self._quarantine.items()
            if entry.status == QuarantineStatus.QUARANTINED
        ]

    def set_probation(self, test_name: str) -> None:
        """Put a quarantined test on probation.

        Args:
            test_name: Name of test
        """
        if test_name in self._quarantine:
            self._quarantine[test_name].status = QuarantineStatus.PROBATION
            self._quarantine[test_name].probation_started = time.time()
        else:
            self._quarantine[test_name] = QuarantineEntry(
                test_name=test_name,
                status=QuarantineStatus.PROBATION,
                reason="Placed on probation",
                probation_started=time.time(),
            )

    def get_status(self, test_name: str) -> QuarantineStatus:
        """Get quarantine status for a test.

        Args:
            test_name: Name of test

        Returns:
            QuarantineStatus
        """
        if test_name not in self._quarantine:
            return QuarantineStatus.ACTIVE
        return self._quarantine[test_name].status

    def get_summary(self) -> dict[str, Any]:
        """Get summary of flaky tests.

        Returns:
            Summary dictionary
        """
        flaky = self.detect_flaky_tests()
        quarantined = self.get_quarantined_tests()

        return {
            "total_tests": len(self._histories),
            "quarantined_count": len(quarantined),
            "quarantined_tests": quarantined,
            "flaky_candidates": len(flaky),
            "flaky_test_names": [f.test_name for f in flaky],
        }

    def cleanup_old_runs(self) -> None:
        """Remove runs older than retention period."""
        cutoff = time.time() - (self.retention_days * 24 * 60 * 60)

        for history in self._histories.values():
            history.runs = [r for r in history.runs if r.timestamp >= cutoff]

    def get_most_flaky(self, limit: int = 10) -> list[FlakyTestCandidate]:
        """Get the most flaky tests, sorted by flakiness score.

        Args:
            limit: Maximum number to return

        Returns:
            List of flaky test candidates sorted by score
        """
        candidates = []

        for test_name, history in self._histories.items():
            if len(history.runs) < self.min_runs:
                continue

            score = history.flakiness_score()
            if score > 0:
                recent = history.recent_runs(5)
                recent_failures = sum(1 for r in recent if not r.passed)

                candidates.append(
                    FlakyTestCandidate(
                        test_name=test_name,
                        flakiness_score=score,
                        pass_rate=history.pass_rate(),
                        run_count=len(history.runs),
                        recent_failures=recent_failures,
                    )
                )

        # Sort by flakiness score descending
        candidates.sort(key=lambda c: c.flakiness_score, reverse=True)
        return candidates[:limit]

    def parse_pytest_output(self, output: str) -> None:
        """Parse pytest output to record test runs.

        Args:
            output: Raw pytest output
        """
        # Match patterns like: tests/test_foo.py::test_one PASSED
        pattern = r"^([\w/.:-]+::[\w_]+)\s+(PASSED|FAILED|ERROR|SKIPPED)"

        for line in output.split("\n"):
            match = re.match(pattern, line.strip())
            if match:
                test_name = match.group(1)
                result = match.group(2)
                passed = result == "PASSED"
                self.record_run(test_name, passed=passed)

    def save(self, filepath: Path) -> None:
        """Save detector state to file.

        Args:
            filepath: Path to save to
        """
        data = {
            "settings": {
                "flakiness_threshold": self.flakiness_threshold,
                "min_runs": self.min_runs,
                "auto_quarantine": self.auto_quarantine,
                "retention_days": self.retention_days,
            },
            "histories": {
                name: {
                    "test_name": history.test_name,
                    "runs": [
                        {
                            "test_name": r.test_name,
                            "passed": r.passed,
                            "timestamp": r.timestamp,
                            "duration_ms": r.duration_ms,
                            "error_message": r.error_message,
                        }
                        for r in history.runs
                    ],
                }
                for name, history in self._histories.items()
            },
            "quarantine": {
                name: {
                    "test_name": entry.test_name,
                    "status": entry.status.value,
                    "reason": entry.reason,
                    "quarantined_at": entry.quarantined_at,
                    "probation_started": entry.probation_started,
                }
                for name, entry in self._quarantine.items()
            },
        }

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, filepath: Path) -> "FlakyDetector":
        """Load detector state from file.

        Args:
            filepath: Path to load from

        Returns:
            FlakyDetector instance
        """
        with open(filepath) as f:
            data = json.load(f)

        settings = data.get("settings", {})
        detector = cls(
            flakiness_threshold=settings.get("flakiness_threshold", 0.3),
            min_runs=settings.get("min_runs", 5),
            auto_quarantine=settings.get("auto_quarantine", False),
            retention_days=settings.get("retention_days", 30),
        )

        # Restore histories
        for name, hist_data in data.get("histories", {}).items():
            history = TestHistory(test_name=hist_data["test_name"])
            for run_data in hist_data.get("runs", []):
                run = TestRun(
                    test_name=run_data["test_name"],
                    passed=run_data["passed"],
                    timestamp=run_data.get("timestamp", time.time()),
                    duration_ms=run_data.get("duration_ms"),
                    error_message=run_data.get("error_message"),
                )
                history.add_run(run)
            detector._histories[name] = history

        # Restore quarantine
        for name, entry_data in data.get("quarantine", {}).items():
            entry = QuarantineEntry(
                test_name=entry_data["test_name"],
                status=QuarantineStatus(entry_data["status"]),
                reason=entry_data["reason"],
                quarantined_at=entry_data.get("quarantined_at", time.time()),
                probation_started=entry_data.get("probation_started"),
            )
            detector._quarantine[name] = entry

        return detector
