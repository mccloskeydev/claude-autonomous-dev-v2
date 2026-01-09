"""Tests for flaky test detection and quarantine."""

import tempfile
import time
from pathlib import Path

from src.flaky_detector import (
    FlakyDetector,
    FlakyTestCandidate,
    QuarantineStatus,
    TestHistory,
    TestRun,
)


class TestTestRun:
    """Tests for TestRun dataclass."""

    def test_test_run_creation(self):
        """Should create test run with required fields."""
        run = TestRun(
            test_name="test_foo",
            passed=True,
        )
        assert run.test_name == "test_foo"
        assert run.passed is True
        assert run.timestamp is not None

    def test_test_run_with_duration(self):
        """Should store test duration."""
        run = TestRun(
            test_name="test_bar",
            passed=False,
            duration_ms=150.5,
        )
        assert run.duration_ms == 150.5

    def test_test_run_with_error(self):
        """Should store error message."""
        run = TestRun(
            test_name="test_baz",
            passed=False,
            error_message="AssertionError: expected 1, got 2",
        )
        assert "AssertionError" in run.error_message


class TestTestHistory:
    """Tests for test history tracking."""

    def test_history_creation(self):
        """Should create test history."""
        history = TestHistory(test_name="test_foo")
        assert history.test_name == "test_foo"
        assert len(history.runs) == 0

    def test_add_run(self):
        """Should add runs to history."""
        history = TestHistory(test_name="test_foo")
        history.add_run(TestRun(test_name="test_foo", passed=True))
        history.add_run(TestRun(test_name="test_foo", passed=False))
        assert len(history.runs) == 2

    def test_pass_rate(self):
        """Should calculate pass rate."""
        history = TestHistory(test_name="test_foo")
        history.add_run(TestRun(test_name="test_foo", passed=True))
        history.add_run(TestRun(test_name="test_foo", passed=True))
        history.add_run(TestRun(test_name="test_foo", passed=False))
        history.add_run(TestRun(test_name="test_foo", passed=True))
        assert history.pass_rate() == 0.75

    def test_pass_rate_empty(self):
        """Should return 1.0 for empty history."""
        history = TestHistory(test_name="test_foo")
        assert history.pass_rate() == 1.0

    def test_failure_rate(self):
        """Should calculate failure rate."""
        history = TestHistory(test_name="test_foo")
        history.add_run(TestRun(test_name="test_foo", passed=True))
        history.add_run(TestRun(test_name="test_foo", passed=False))
        assert history.failure_rate() == 0.5

    def test_flakiness_score(self):
        """Should calculate flakiness score based on pass/fail transitions."""
        history = TestHistory(test_name="test_foo")
        # Alternating pattern is highly flaky
        history.add_run(TestRun(test_name="test_foo", passed=True))
        history.add_run(TestRun(test_name="test_foo", passed=False))
        history.add_run(TestRun(test_name="test_foo", passed=True))
        history.add_run(TestRun(test_name="test_foo", passed=False))

        score = history.flakiness_score()
        assert score > 0.5  # High flakiness

    def test_consistent_test_has_low_flakiness(self):
        """Consistently passing or failing tests should have low flakiness."""
        history = TestHistory(test_name="test_foo")
        for _ in range(10):
            history.add_run(TestRun(test_name="test_foo", passed=True))

        score = history.flakiness_score()
        assert score < 0.2  # Low flakiness

    def test_recent_runs(self):
        """Should get recent runs."""
        history = TestHistory(test_name="test_foo")
        for i in range(10):
            history.add_run(TestRun(test_name="test_foo", passed=i % 2 == 0))

        recent = history.recent_runs(5)
        assert len(recent) == 5


class TestFlakyTestCandidate:
    """Tests for flaky test candidates."""

    def test_candidate_creation(self):
        """Should create flaky test candidate."""
        candidate = FlakyTestCandidate(
            test_name="test_foo",
            flakiness_score=0.6,
            pass_rate=0.7,
            run_count=20,
        )
        assert candidate.test_name == "test_foo"
        assert candidate.flakiness_score == 0.6
        assert candidate.pass_rate == 0.7
        assert candidate.run_count == 20

    def test_candidate_recommendation(self):
        """Should provide recommendation based on flakiness."""
        high_flaky = FlakyTestCandidate(
            test_name="test_foo",
            flakiness_score=0.8,
            pass_rate=0.5,
            run_count=20,
        )
        assert "quarantine" in high_flaky.recommendation.lower()

        low_flaky = FlakyTestCandidate(
            test_name="test_bar",
            flakiness_score=0.2,
            pass_rate=0.9,
            run_count=20,
        )
        assert "monitor" in low_flaky.recommendation.lower()


class TestQuarantineStatus:
    """Tests for quarantine status enum."""

    def test_quarantine_statuses(self):
        """Should have expected quarantine statuses."""
        assert QuarantineStatus.ACTIVE
        assert QuarantineStatus.QUARANTINED
        assert QuarantineStatus.PROBATION
        assert QuarantineStatus.RETIRED


class TestFlakyDetector:
    """Tests for flaky test detector."""

    def test_detector_creation(self):
        """Should create detector with default thresholds."""
        detector = FlakyDetector()
        assert detector is not None
        assert detector.flakiness_threshold == 0.3
        assert detector.min_runs == 5

    def test_detector_custom_thresholds(self):
        """Should accept custom thresholds."""
        detector = FlakyDetector(flakiness_threshold=0.5, min_runs=10)
        assert detector.flakiness_threshold == 0.5
        assert detector.min_runs == 10

    def test_record_test_run(self):
        """Should record test runs."""
        detector = FlakyDetector()
        detector.record_run("test_foo", passed=True)
        detector.record_run("test_foo", passed=False)

        history = detector.get_history("test_foo")
        assert len(history.runs) == 2

    def test_record_run_with_details(self):
        """Should record run with duration and error."""
        detector = FlakyDetector()
        detector.record_run(
            "test_foo",
            passed=False,
            duration_ms=250.0,
            error_message="Connection timeout",
        )

        history = detector.get_history("test_foo")
        assert history.runs[0].duration_ms == 250.0
        assert "timeout" in history.runs[0].error_message.lower()

    def test_detect_flaky_tests(self):
        """Should detect flaky tests."""
        detector = FlakyDetector(flakiness_threshold=0.3, min_runs=5)

        # Record alternating passes/fails (very flaky)
        for i in range(10):
            detector.record_run("test_flaky", passed=i % 2 == 0)

        # Record consistent passes (not flaky)
        for _ in range(10):
            detector.record_run("test_stable", passed=True)

        flaky = detector.detect_flaky_tests()
        flaky_names = [f.test_name for f in flaky]

        assert "test_flaky" in flaky_names
        assert "test_stable" not in flaky_names

    def test_quarantine_test(self):
        """Should quarantine a test."""
        detector = FlakyDetector()
        detector.quarantine_test("test_flaky", reason="Fails intermittently in CI")

        assert detector.is_quarantined("test_flaky")
        assert not detector.is_quarantined("test_other")

    def test_unquarantine_test(self):
        """Should unquarantine a test."""
        detector = FlakyDetector()
        detector.quarantine_test("test_flaky", reason="Flaky")
        assert detector.is_quarantined("test_flaky")

        detector.unquarantine_test("test_flaky")
        assert not detector.is_quarantined("test_flaky")

    def test_get_quarantined_tests(self):
        """Should list quarantined tests."""
        detector = FlakyDetector()
        detector.quarantine_test("test_a", reason="Reason A")
        detector.quarantine_test("test_b", reason="Reason B")
        detector.quarantine_test("test_c", reason="Reason C")
        detector.unquarantine_test("test_b")

        quarantined = detector.get_quarantined_tests()
        assert "test_a" in quarantined
        assert "test_b" not in quarantined
        assert "test_c" in quarantined

    def test_probation_tracking(self):
        """Should track tests on probation."""
        detector = FlakyDetector()
        detector.quarantine_test("test_foo", reason="Flaky")

        # Put on probation (being tested before full release)
        detector.set_probation("test_foo")

        assert detector.get_status("test_foo") == QuarantineStatus.PROBATION

    def test_auto_quarantine_threshold(self):
        """Should auto-quarantine when threshold exceeded."""
        detector = FlakyDetector(
            flakiness_threshold=0.3,
            min_runs=5,
            auto_quarantine=True,
        )

        # Record highly flaky pattern
        for i in range(6):
            detector.record_run("test_auto", passed=i % 2 == 0)

        # Should be auto-quarantined
        assert detector.is_quarantined("test_auto")

    def test_no_auto_quarantine_below_min_runs(self):
        """Should not auto-quarantine before min_runs reached."""
        detector = FlakyDetector(
            flakiness_threshold=0.3,
            min_runs=10,
            auto_quarantine=True,
        )

        # Record flaky pattern but not enough runs
        for i in range(5):
            detector.record_run("test_few", passed=i % 2 == 0)

        # Should not be quarantined yet
        assert not detector.is_quarantined("test_few")

    def test_persistence(self):
        """Should save and load detector state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "flaky.json"

            # Create and save
            detector = FlakyDetector()
            detector.record_run("test_foo", passed=True)
            detector.record_run("test_foo", passed=False)
            detector.quarantine_test("test_bar", reason="Flaky in CI")
            detector.save(filepath)

            # Load and verify
            loaded = FlakyDetector.load(filepath)
            assert len(loaded.get_history("test_foo").runs) == 2
            assert loaded.is_quarantined("test_bar")

    def test_get_summary(self):
        """Should provide summary of flaky tests."""
        detector = FlakyDetector(min_runs=3)

        # Add various test histories
        for i in range(5):
            detector.record_run("test_flaky", passed=i % 2 == 0)
        for _ in range(5):
            detector.record_run("test_stable", passed=True)
        detector.quarantine_test("test_known", reason="Known issue")

        summary = detector.get_summary()
        assert "total_tests" in summary
        assert "quarantined_count" in summary
        assert "flaky_candidates" in summary

    def test_cleanup_old_runs(self):
        """Should clean up old runs beyond retention period."""
        detector = FlakyDetector(retention_days=7)

        # Add an old run (simulate)
        history = detector.get_history("test_foo")
        old_run = TestRun(
            test_name="test_foo",
            passed=True,
            timestamp=time.time() - (10 * 24 * 60 * 60),  # 10 days ago
        )
        history.add_run(old_run)

        # Add a recent run
        detector.record_run("test_foo", passed=True)

        # Cleanup
        detector.cleanup_old_runs()

        # Should only have recent run
        assert len(detector.get_history("test_foo").runs) == 1

    def test_get_most_flaky(self):
        """Should get most flaky tests sorted by score."""
        detector = FlakyDetector(min_runs=3)

        # Very flaky test
        for i in range(10):
            detector.record_run("test_very_flaky", passed=i % 2 == 0)

        # Somewhat flaky test (mostly passes)
        for i in range(10):
            detector.record_run("test_somewhat_flaky", passed=i % 3 != 0)

        # Stable test
        for _ in range(10):
            detector.record_run("test_stable", passed=True)

        most_flaky = detector.get_most_flaky(limit=2)
        assert len(most_flaky) <= 2
        if len(most_flaky) >= 2:
            assert most_flaky[0].flakiness_score >= most_flaky[1].flakiness_score

    def test_parse_pytest_output(self):
        """Should parse pytest output to record runs."""
        detector = FlakyDetector()

        output = """
tests/test_foo.py::test_one PASSED
tests/test_foo.py::test_two FAILED
tests/test_bar.py::test_three PASSED
tests/test_bar.py::test_four PASSED
"""
        detector.parse_pytest_output(output)

        assert detector.get_history("tests/test_foo.py::test_one").runs[-1].passed
        assert not detector.get_history("tests/test_foo.py::test_two").runs[-1].passed
        assert detector.get_history("tests/test_bar.py::test_three").runs[-1].passed


class TestFlakyDetectorIntegration:
    """Integration tests for flaky detector."""

    def test_full_workflow(self):
        """Should support full flaky test workflow."""
        detector = FlakyDetector(
            flakiness_threshold=0.3,
            min_runs=5,
            auto_quarantine=True,
        )

        # Simulate multiple test runs over time
        run_results = [
            ("test_stable", True),
            ("test_stable", True),
            ("test_stable", True),
            ("test_flaky", True),
            ("test_flaky", False),
            ("test_flaky", True),
            ("test_flaky", False),
            ("test_flaky", True),
            ("test_broken", False),
            ("test_broken", False),
            ("test_broken", False),
        ]

        for test_name, passed in run_results:
            detector.record_run(test_name, passed=passed)

        # Check detection
        flaky_tests = detector.detect_flaky_tests()
        flaky_names = [f.test_name for f in flaky_tests]

        # test_flaky should be detected
        assert "test_flaky" in flaky_names

        # test_stable should not be flaky
        assert "test_stable" not in flaky_names

        # test_broken is consistently failing, not flaky
        assert "test_broken" not in flaky_names

    def test_integration_with_test_analyzer(self):
        """Should integrate with test analyzer for test runs."""
        # This tests the compatibility with F007's test_analyzer
        from src.test_analyzer import TestResult, TestType

        detector = FlakyDetector()

        # Create test results as would come from test_analyzer
        results = [
            TestResult(name="test_unit_one", test_type=TestType.UNIT, passed=True, duration_ms=50),
            TestResult(name="test_unit_one", test_type=TestType.UNIT, passed=False, duration_ms=55),
            TestResult(name="test_unit_two", test_type=TestType.UNIT, passed=True, duration_ms=30),
        ]

        # Record from TestResult objects
        for result in results:
            detector.record_run(
                result.name,
                passed=result.passed,
                duration_ms=result.duration_ms,
            )

        history = detector.get_history("test_unit_one")
        assert len(history.runs) == 2
        assert history.pass_rate() == 0.5
