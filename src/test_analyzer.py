"""Test pyramid enforcement and coverage trending.

This module provides test analysis for autonomous development:

- Test type classification (unit, integration, e2e)
- Test pyramid health assessment
- Coverage trend tracking
- Flaky test detection
- Test impact analysis
"""

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class TestType(Enum):
    """Types of tests in the test pyramid."""

    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"

    @classmethod
    def from_path(cls, path: str) -> "TestType":
        """Determine test type from file path.

        Args:
            path: Path to test file

        Returns:
            TestType enum value
        """
        path_lower = path.lower()

        # Check for E2E indicators
        if "e2e" in path_lower or "end_to_end" in path_lower or "end-to-end" in path_lower:
            return cls.E2E

        # Check for integration indicators
        if "integration" in path_lower or "integ" in path_lower:
            return cls.INTEGRATION

        # Default to unit
        return cls.UNIT


@dataclass
class TestResult:
    """Result of a single test execution."""

    name: str
    test_type: TestType
    passed: bool
    duration_ms: float
    error: str = ""
    file_path: str = ""


@dataclass
class PyramidStats:
    """Statistics for a test type."""

    passed: int = 0
    failed: int = 0

    @property
    def total(self) -> int:
        return self.passed + self.failed


class TestPyramid:
    """Tracks test pyramid shape and health."""

    def __init__(self) -> None:
        """Initialize test pyramid."""
        self._stats: dict[TestType, PyramidStats] = {
            TestType.UNIT: PyramidStats(),
            TestType.INTEGRATION: PyramidStats(),
            TestType.E2E: PyramidStats(),
        }

    def add_test(self, test_type: TestType, passed: bool) -> None:
        """Add a test result to the pyramid.

        Args:
            test_type: Type of test
            passed: Whether test passed
        """
        stats = self._stats[test_type]
        if passed:
            stats.passed += 1
        else:
            stats.failed += 1

    def get_ratio(self) -> dict[str, int]:
        """Get test counts by type.

        Returns:
            Dictionary with test counts
        """
        return {
            "unit": self._stats[TestType.UNIT].total,
            "integration": self._stats[TestType.INTEGRATION].total,
            "e2e": self._stats[TestType.E2E].total,
        }

    def get_stats(self) -> dict[str, dict[str, int]]:
        """Get detailed statistics by type.

        Returns:
            Dictionary with pass/fail counts per type
        """
        return {
            "unit": {
                "passed": self._stats[TestType.UNIT].passed,
                "failed": self._stats[TestType.UNIT].failed,
            },
            "integration": {
                "passed": self._stats[TestType.INTEGRATION].passed,
                "failed": self._stats[TestType.INTEGRATION].failed,
            },
            "e2e": {
                "passed": self._stats[TestType.E2E].passed,
                "failed": self._stats[TestType.E2E].failed,
            },
        }

    def is_healthy_shape(self) -> bool:
        """Check if pyramid has healthy shape.

        Ideal pyramid: unit > integration > e2e

        Returns:
            True if pyramid shape is healthy
        """
        ratio = self.get_ratio()
        total = sum(ratio.values())

        if total == 0:
            return True  # No tests yet

        # Check that unit tests are the majority
        unit_pct = ratio["unit"] / total

        # Unit should be at least 50% and more than E2E
        return unit_pct >= 0.5 and ratio["unit"] > ratio["e2e"]

    def get_recommendations(self) -> list[str]:
        """Get recommendations for improving pyramid.

        Returns:
            List of recommendation strings
        """
        recommendations = []
        ratio = self.get_ratio()
        total = sum(ratio.values())

        if total == 0:
            recommendations.append("Add unit tests first")
            return recommendations

        unit_pct = ratio["unit"] / total

        if unit_pct < 0.5:
            recommendations.append(
                f"Add more unit tests. Currently {unit_pct:.0%}, recommend >= 50%"
            )

        if ratio["e2e"] > ratio["unit"]:
            recommendations.append(
                "Too many E2E tests relative to unit tests. Consider converting some to unit tests."
            )

        stats = self.get_stats()
        for test_type, type_stats in stats.items():
            if type_stats["failed"] > 0:
                recommendations.append(
                    f"Fix {type_stats['failed']} failing {test_type} test(s)"
                )

        return recommendations


@dataclass
class CoverageDataPoint:
    """A single coverage measurement."""

    value: float
    timestamp: float = 0


class CoverageTrend:
    """Tracks coverage over time."""

    def __init__(self, threshold: float = 80.0) -> None:
        """Initialize coverage trend.

        Args:
            threshold: Minimum acceptable coverage
        """
        self.threshold = threshold
        self.history: list[float] = []

    def record(self, coverage: float) -> None:
        """Record a coverage measurement.

        Args:
            coverage: Coverage percentage (0-100)
        """
        self.history.append(coverage)

    @property
    def latest(self) -> float | None:
        """Get latest coverage value."""
        return self.history[-1] if self.history else None

    def is_improving(self) -> bool:
        """Check if coverage is improving.

        Returns:
            True if coverage is trending up
        """
        if len(self.history) < 2:
            return False

        # Check last 3 values (or all if < 3)
        recent = self.history[-3:]
        return all(recent[i] < recent[i + 1] for i in range(len(recent) - 1))

    def is_declining(self) -> bool:
        """Check if coverage is declining.

        Returns:
            True if coverage is trending down
        """
        if len(self.history) < 2:
            return False

        recent = self.history[-3:]
        return all(recent[i] > recent[i + 1] for i in range(len(recent) - 1))

    def is_stable(self) -> bool:
        """Check if coverage is stable (within 2%).

        Returns:
            True if coverage is stable
        """
        if len(self.history) < 2:
            return True

        recent = self.history[-3:]
        return max(recent) - min(recent) < 2.0

    def meets_threshold(self) -> bool:
        """Check if latest coverage meets threshold.

        Returns:
            True if coverage >= threshold
        """
        return self.latest is not None and self.latest >= self.threshold

    def change_from_start(self) -> float:
        """Calculate coverage change from start.

        Returns:
            Coverage change in percentage points
        """
        if len(self.history) < 2:
            return 0.0
        return self.history[-1] - self.history[0]


class TestAnalyzer:
    """Main test analyzer for pyramid enforcement."""

    def __init__(
        self,
        min_unit_ratio: float = 0.5,
        min_coverage: float = 80.0,
    ) -> None:
        """Initialize test analyzer.

        Args:
            min_unit_ratio: Minimum ratio of unit tests
            min_coverage: Minimum coverage threshold
        """
        self.min_unit_ratio = min_unit_ratio
        self.min_coverage = min_coverage
        self.pyramid = TestPyramid()
        self.coverage_trend = CoverageTrend(threshold=min_coverage)
        self._results: list[TestResult] = []
        self._test_mappings: dict[str, list[str]] = {}

    def record_result(self, result: TestResult) -> None:
        """Record a test result.

        Args:
            result: TestResult to record
        """
        self._results.append(result)
        self.pyramid.add_test(result.test_type, result.passed)

    def analyze_output(self, output: str) -> None:
        """Analyze pytest output.

        Args:
            output: Raw pytest output
        """
        # Pattern for pytest output: path::test_name STATUS
        pattern = r"([\w/\.]+)::([\w_]+)\s+(PASSED|FAILED)"

        for match in re.finditer(pattern, output):
            file_path = match.group(1)
            test_name = match.group(2)
            status = match.group(3)

            test_type = TestType.from_path(file_path)
            passed = status == "PASSED"

            result = TestResult(
                name=test_name,
                test_type=test_type,
                passed=passed,
                duration_ms=0,
                file_path=file_path,
            )
            self.record_result(result)

    def extract_coverage(self, output: str) -> float | None:
        """Extract coverage percentage from output.

        Args:
            output: Coverage report output

        Returns:
            Coverage percentage or None
        """
        # Look for TOTAL line with percentage
        pattern = r"TOTAL\s+\d+\s+\d+\s+(\d+)%"
        match = re.search(pattern, output)

        if match:
            coverage = float(match.group(1))
            self.coverage_trend.record(coverage)
            return coverage

        return None

    def get_summary(self) -> dict:
        """Get test analysis summary.

        Returns:
            Summary dictionary
        """
        ratio = self.pyramid.get_ratio()
        stats = self.pyramid.get_stats()

        total_tests = sum(ratio.values())
        total_passed = sum(s["passed"] for s in stats.values())
        total_failed = sum(s["failed"] for s in stats.values())

        return {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "coverage": self.coverage_trend.latest,
            "coverage_trend": "improving"
            if self.coverage_trend.is_improving()
            else "declining"
            if self.coverage_trend.is_declining()
            else "stable",
            "pyramid_health": "healthy"
            if self.pyramid.is_healthy_shape()
            else "unhealthy",
            "ratio": ratio,
        }

    def get_flaky_candidates(self) -> list[str]:
        """Identify potentially flaky tests.

        A test is flaky if it has both passed and failed.

        Returns:
            List of potentially flaky test names
        """
        test_outcomes: dict[str, set[bool]] = {}

        for result in self._results:
            if result.name not in test_outcomes:
                test_outcomes[result.name] = set()
            test_outcomes[result.name].add(result.passed)

        # Tests with both True and False outcomes are flaky
        return [name for name, outcomes in test_outcomes.items() if len(outcomes) > 1]

    def check_pyramid_enforcement(self) -> list[str]:
        """Check if test pyramid requirements are met.

        Returns:
            List of violations
        """
        violations = []
        ratio = self.pyramid.get_ratio()
        total = sum(ratio.values())

        if total > 0:
            unit_ratio = ratio["unit"] / total
            if unit_ratio < self.min_unit_ratio:
                violations.append(
                    f"Unit test ratio {unit_ratio:.0%} below minimum {self.min_unit_ratio:.0%}"
                )

        if (
            self.coverage_trend.latest is not None
            and self.coverage_trend.latest < self.min_coverage
        ):
            violations.append(
                f"Coverage {self.coverage_trend.latest:.1f}% below minimum {self.min_coverage}%"
            )

        return violations

    def discover_tests(self, root: Path) -> list[Path]:
        """Discover test files in a directory.

        Args:
            root: Root directory to search

        Returns:
            List of test file paths
        """
        tests = []
        for pattern in ["**/test_*.py", "**/*_test.py"]:
            tests.extend(root.glob(pattern))
        return tests

    def categorize_tests(self, root: Path) -> dict[TestType, list[Path]]:
        """Categorize discovered tests by type.

        Args:
            root: Root directory

        Returns:
            Dictionary of test type to file paths
        """
        categorized: dict[TestType, list[Path]] = {
            TestType.UNIT: [],
            TestType.INTEGRATION: [],
            TestType.E2E: [],
        }

        for test_file in self.discover_tests(root):
            test_type = TestType.from_path(str(test_file))
            categorized[test_type].append(test_file)

        return categorized

    def register_test_mapping(self, source_file: str, test_files: list[str]) -> None:
        """Register a mapping from source to test files.

        Args:
            source_file: Source file path
            test_files: Related test files
        """
        self._test_mappings[source_file] = test_files

    def get_affected_tests(self, changed_files: list[str]) -> list[str] | None:
        """Get tests affected by file changes.

        Args:
            changed_files: List of changed source files

        Returns:
            List of test files to run, or None to run all
        """
        affected = set()

        for source_file in changed_files:
            if source_file in self._test_mappings:
                affected.update(self._test_mappings[source_file])

        if not affected:
            return None  # No mapping found, run all tests

        return list(affected)
