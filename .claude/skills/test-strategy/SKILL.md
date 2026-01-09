---
name: test-strategy
description: |
  Test pyramid enforcement and coverage trending. Classifies tests by type (unit, integration, e2e),
  tracks test pyramid health, monitors coverage trends, identifies flaky tests, and provides
  recommendations for improving test suite.
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
---

# Test Strategy - Pyramid Enforcement and Coverage

You are the test strategy manager for autonomous development. Your role is to ensure a healthy test pyramid and good coverage.

## Test Pyramid

The ideal test pyramid has:
- **70%+ Unit tests** - Fast, isolated, test single units
- **20% Integration tests** - Test component interactions
- **10% E2E tests** - Test full user flows

## Test Classification

Tests are classified by path patterns:
- **Unit**: `test_*.py`, `tests/unit/*`
- **Integration**: `tests/integration/*`, `*_integration_*`
- **E2E**: `tests/e2e/*`, `*_e2e_*`

## Using the Python Module

```python
from src.test_analyzer import (
    TestAnalyzer,
    TestType,
    TestResult,
    TestPyramid,
    CoverageTrend,
)

analyzer = TestAnalyzer(min_unit_ratio=0.7, min_coverage=80)

# Analyze pytest output
output = """
tests/test_foo.py::test_one PASSED
tests/test_foo.py::test_two FAILED
"""
analyzer.analyze_output(output)

# Check pyramid health
if not analyzer.pyramid.is_healthy_shape():
    recommendations = analyzer.pyramid.get_recommendations()
    for rec in recommendations:
        print(f"Recommendation: {rec}")

# Track coverage
coverage_output = """
TOTAL    100    20    80%
"""
coverage = analyzer.extract_coverage(coverage_output)
print(f"Coverage: {coverage}%")

if analyzer.coverage_trend.is_declining():
    print("Warning: Coverage is declining!")

# Get summary
summary = analyzer.get_summary()
print(f"Total tests: {summary['total_tests']}")
print(f"Pyramid health: {summary['pyramid_health']}")

# Find flaky tests
flaky = analyzer.get_flaky_candidates()
if flaky:
    print(f"Potentially flaky: {flaky}")

# Check enforcement
violations = analyzer.check_pyramid_enforcement()
if violations:
    for v in violations:
        print(f"Violation: {v}")
```

## Coverage Trending

Track coverage over time:
- **Improving**: Last 3 measurements increasing
- **Stable**: Last 3 measurements within 2%
- **Declining**: Last 3 measurements decreasing

## Pyramid Health Indicators

| Indicator | Healthy | Warning | Critical |
|-----------|---------|---------|----------|
| Unit ratio | >= 50% | 30-50% | < 30% |
| E2E ratio | <= 20% | 20-40% | > 40% |
| Coverage | >= 80% | 60-80% | < 60% |
| Failures | 0 | 1-5 | > 5 |

## Recommendations

The analyzer provides actionable recommendations:
- "Add more unit tests"
- "Fix N failing tests"
- "Too many E2E tests relative to unit tests"
- "Coverage below threshold"

## Test Impact Analysis

Map source files to relevant tests:

```python
analyzer.register_test_mapping("src/auth.py", ["tests/test_auth.py"])

# When auth.py changes
affected = analyzer.get_affected_tests(["src/auth.py"])
# Returns ["tests/test_auth.py"]
```

## Workflow

1. **Discover** - Find all test files
2. **Categorize** - Classify by type
3. **Run** - Execute tests with pytest
4. **Analyze** - Parse output and coverage
5. **Evaluate** - Check pyramid health
6. **Recommend** - Suggest improvements

## Integration with Other Modules

### With Loop Controller
```python
from src.loop_control import LoopController

controller = LoopController()
analyzer = TestAnalyzer()

# After each iteration
if summary["failed"] > 0:
    controller.record_error(f"{summary['failed']} tests failing")
else:
    controller.record_progress(files_changed=1, tests_passed=summary["passed"])
```

### With Circuit Breaker
```python
from src.circuit_breaker import MultiLevelCircuitBreaker

cb = MultiLevelCircuitBreaker()
cb.record_test_result(passed=summary["passed"], failed=summary["failed"])
```

## Best Practices

1. **Write unit tests first** - They're fastest and catch most bugs
2. **Keep E2E tests minimal** - Only for critical user flows
3. **Track coverage trends** - Not just current value
4. **Fix flaky tests immediately** - They erode trust in the suite
5. **Review pyramid regularly** - Prevent inversion
