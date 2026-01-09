"""Tests for test pyramid enforcement and coverage trending."""

import tempfile
from pathlib import Path

from src.test_analyzer import (
    CoverageTrend,
    TestAnalyzer,
    TestPyramid,
    TestResult,
    TestType,
)


class TestTestType:
    """Tests for test type classification."""

    def test_unit_test_identification(self):
        """Should identify unit tests."""
        assert TestType.from_path("tests/unit/test_foo.py") == TestType.UNIT
        assert TestType.from_path("test_foo.py") == TestType.UNIT

    def test_integration_test_identification(self):
        """Should identify integration tests."""
        assert TestType.from_path("tests/integration/test_api.py") == TestType.INTEGRATION
        assert TestType.from_path("test_integration_foo.py") == TestType.INTEGRATION

    def test_e2e_test_identification(self):
        """Should identify E2E tests."""
        assert TestType.from_path("tests/e2e/test_flow.py") == TestType.E2E
        assert TestType.from_path("test_e2e_login.py") == TestType.E2E

    def test_unknown_defaults_to_unit(self):
        """Should default ambiguous tests to unit."""
        assert TestType.from_path("tests/test_something.py") == TestType.UNIT


class TestTestResult:
    """Tests for test result tracking."""

    def test_result_creation(self):
        """Should create test result."""
        result = TestResult(
            name="test_foo",
            test_type=TestType.UNIT,
            passed=True,
            duration_ms=50,
        )
        assert result.name == "test_foo"
        assert result.passed

    def test_result_with_error(self):
        """Should track error message."""
        result = TestResult(
            name="test_bar",
            test_type=TestType.UNIT,
            passed=False,
            duration_ms=100,
            error="AssertionError: expected 1, got 2",
        )
        assert not result.passed
        assert "AssertionError" in result.error


class TestTestPyramid:
    """Tests for test pyramid enforcement."""

    def test_pyramid_ratio(self):
        """Should track test counts by type."""
        pyramid = TestPyramid()
        pyramid.add_test(TestType.UNIT, passed=True)
        pyramid.add_test(TestType.UNIT, passed=True)
        pyramid.add_test(TestType.UNIT, passed=True)
        pyramid.add_test(TestType.INTEGRATION, passed=True)
        pyramid.add_test(TestType.E2E, passed=True)

        ratio = pyramid.get_ratio()
        assert ratio["unit"] == 3
        assert ratio["integration"] == 1
        assert ratio["e2e"] == 1

    def test_ideal_pyramid_shape(self):
        """Should identify ideal pyramid shape."""
        pyramid = TestPyramid()
        # Good pyramid: 70% unit, 20% integration, 10% e2e
        for _ in range(7):
            pyramid.add_test(TestType.UNIT, passed=True)
        for _ in range(2):
            pyramid.add_test(TestType.INTEGRATION, passed=True)
        pyramid.add_test(TestType.E2E, passed=True)

        assert pyramid.is_healthy_shape()

    def test_inverted_pyramid_unhealthy(self):
        """Should identify inverted pyramid as unhealthy."""
        pyramid = TestPyramid()
        # Bad pyramid: more E2E than unit
        pyramid.add_test(TestType.UNIT, passed=True)
        for _ in range(5):
            pyramid.add_test(TestType.E2E, passed=True)

        assert not pyramid.is_healthy_shape()

    def test_pyramid_with_failing_tests(self):
        """Should track pass/fail by type."""
        pyramid = TestPyramid()
        pyramid.add_test(TestType.UNIT, passed=True)
        pyramid.add_test(TestType.UNIT, passed=False)
        pyramid.add_test(TestType.UNIT, passed=True)

        stats = pyramid.get_stats()
        assert stats["unit"]["passed"] == 2
        assert stats["unit"]["failed"] == 1

    def test_pyramid_recommendations(self):
        """Should provide recommendations."""
        pyramid = TestPyramid()
        # Too few unit tests
        pyramid.add_test(TestType.E2E, passed=True)
        pyramid.add_test(TestType.E2E, passed=True)

        recommendations = pyramid.get_recommendations()
        assert any("unit" in r.lower() for r in recommendations)


class TestCoverageTrend:
    """Tests for coverage trending."""

    def test_record_coverage(self):
        """Should record coverage data points."""
        trend = CoverageTrend()
        trend.record(80.0)
        trend.record(82.0)
        trend.record(85.0)

        assert len(trend.history) == 3
        assert trend.latest == 85.0

    def test_coverage_improving(self):
        """Should detect improving coverage."""
        trend = CoverageTrend()
        trend.record(70.0)
        trend.record(75.0)
        trend.record(80.0)

        assert trend.is_improving()

    def test_coverage_declining(self):
        """Should detect declining coverage."""
        trend = CoverageTrend()
        trend.record(80.0)
        trend.record(75.0)
        trend.record(70.0)

        assert trend.is_declining()

    def test_coverage_stable(self):
        """Should detect stable coverage."""
        trend = CoverageTrend()
        trend.record(80.0)
        trend.record(80.5)
        trend.record(79.5)

        assert trend.is_stable()

    def test_coverage_meets_threshold(self):
        """Should check against threshold."""
        trend = CoverageTrend(threshold=80.0)
        trend.record(85.0)

        assert trend.meets_threshold()

    def test_coverage_below_threshold(self):
        """Should detect below threshold."""
        trend = CoverageTrend(threshold=80.0)
        trend.record(75.0)

        assert not trend.meets_threshold()

    def test_coverage_change_percentage(self):
        """Should calculate coverage change."""
        trend = CoverageTrend()
        trend.record(80.0)
        trend.record(84.0)

        assert trend.change_from_start() == 4.0


class TestTestAnalyzer:
    """Tests for the main test analyzer."""

    def test_analyzer_creation(self):
        """Should create analyzer."""
        analyzer = TestAnalyzer()
        assert analyzer is not None

    def test_analyze_test_output(self):
        """Should analyze pytest output."""
        analyzer = TestAnalyzer()
        output = """
        tests/test_foo.py::test_one PASSED
        tests/test_foo.py::test_two PASSED
        tests/test_foo.py::test_three FAILED
        tests/integration/test_api.py::test_endpoint PASSED
        """
        analyzer.analyze_output(output)

        stats = analyzer.pyramid.get_stats()
        assert stats["unit"]["passed"] == 2
        assert stats["unit"]["failed"] == 1
        assert stats["integration"]["passed"] == 1

    def test_analyze_coverage_output(self):
        """Should extract coverage from output."""
        analyzer = TestAnalyzer()
        output = """
        Name                 Stmts   Miss  Cover
        ----------------------------------------
        src/module.py           50     10    80%
        TOTAL                  100     20    80%
        """
        coverage = analyzer.extract_coverage(output)
        assert coverage == 80.0

    def test_get_summary(self):
        """Should provide test summary."""
        analyzer = TestAnalyzer()
        analyzer.pyramid.add_test(TestType.UNIT, passed=True)
        analyzer.pyramid.add_test(TestType.UNIT, passed=True)
        analyzer.coverage_trend.record(80.0)

        summary = analyzer.get_summary()
        assert "total_tests" in summary
        assert "coverage" in summary
        assert "pyramid_health" in summary

    def test_identify_flaky_candidates(self):
        """Should identify potentially flaky tests."""
        analyzer = TestAnalyzer()
        # Same test passes and fails
        analyzer.record_result(TestResult(
            name="test_flaky", test_type=TestType.UNIT, passed=True, duration_ms=100
        ))
        analyzer.record_result(TestResult(
            name="test_flaky", test_type=TestType.UNIT, passed=False, duration_ms=150
        ))
        analyzer.record_result(TestResult(
            name="test_flaky", test_type=TestType.UNIT, passed=True, duration_ms=120
        ))

        flaky = analyzer.get_flaky_candidates()
        assert "test_flaky" in flaky

    def test_enforce_pyramid(self):
        """Should enforce pyramid requirements."""
        analyzer = TestAnalyzer(
            min_unit_ratio=0.7,  # 70% unit tests
            min_coverage=80,
        )
        # Add tests with poor ratio
        analyzer.pyramid.add_test(TestType.UNIT, passed=True)
        analyzer.pyramid.add_test(TestType.E2E, passed=True)
        analyzer.pyramid.add_test(TestType.E2E, passed=True)

        violations = analyzer.check_pyramid_enforcement()
        assert len(violations) > 0
        assert any("unit" in v.lower() for v in violations)


class TestTestDiscovery:
    """Tests for test file discovery."""

    def test_discover_tests(self):
        """Should discover test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test structure
            test_dir = Path(tmpdir) / "tests"
            test_dir.mkdir()
            (test_dir / "test_unit.py").write_text("def test_foo(): pass")
            (test_dir / "integration").mkdir()
            (test_dir / "integration" / "test_api.py").write_text("def test_api(): pass")

            analyzer = TestAnalyzer()
            tests = analyzer.discover_tests(Path(tmpdir))

            assert len(tests) == 2
            assert any("test_unit.py" in str(t) for t in tests)

    def test_categorize_discovered_tests(self):
        """Should categorize discovered tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "tests"
            test_dir.mkdir()
            (test_dir / "unit").mkdir()
            (test_dir / "unit" / "test_foo.py").write_text("def test_foo(): pass")
            (test_dir / "e2e").mkdir()
            (test_dir / "e2e" / "test_flow.py").write_text("def test_flow(): pass")

            analyzer = TestAnalyzer()
            categorized = analyzer.categorize_tests(Path(tmpdir))

            assert TestType.UNIT in categorized
            assert TestType.E2E in categorized


class TestTestImpact:
    """Tests for test impact analysis."""

    def test_map_file_to_tests(self):
        """Should map source files to relevant tests."""
        analyzer = TestAnalyzer()
        # Register mapping
        analyzer.register_test_mapping("src/auth.py", ["tests/test_auth.py"])
        analyzer.register_test_mapping("src/api.py", ["tests/integration/test_api.py"])

        tests = analyzer.get_affected_tests(["src/auth.py"])
        assert "tests/test_auth.py" in tests

    def test_no_mapping_returns_all(self):
        """Should return all tests if no mapping exists."""
        analyzer = TestAnalyzer()
        tests = analyzer.get_affected_tests(["src/unknown.py"])
        # Should indicate to run all tests
        assert tests == [] or tests is None  # Convention for "run all"
