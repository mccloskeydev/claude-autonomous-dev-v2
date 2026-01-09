"""Tests for error classification and strategy selection."""

from src.error_classifier import (
    ErrorClassifier,
    ErrorSeverity,
    ErrorType,
    RecoveryPlaybook,
    RecoveryStrategy,
)


class TestErrorType:
    """Tests for error type classification."""

    def test_syntax_error_detection(self):
        """Should classify syntax errors correctly."""
        classifier = ErrorClassifier()
        result = classifier.classify("SyntaxError: invalid syntax at line 10")
        assert result.error_type == ErrorType.SYNTAX

    def test_import_error_detection(self):
        """Should classify import errors correctly."""
        classifier = ErrorClassifier()
        result = classifier.classify("ImportError: No module named 'missing_module'")
        assert result.error_type == ErrorType.IMPORT

    def test_type_error_detection(self):
        """Should classify type errors correctly."""
        classifier = ErrorClassifier()
        result = classifier.classify("TypeError: unsupported operand type(s)")
        assert result.error_type == ErrorType.TYPE

    def test_runtime_error_detection(self):
        """Should classify runtime errors correctly."""
        classifier = ErrorClassifier()
        result = classifier.classify("RuntimeError: maximum recursion depth exceeded")
        assert result.error_type == ErrorType.RUNTIME

    def test_test_failure_detection(self):
        """Should classify test failures correctly."""
        classifier = ErrorClassifier()
        result = classifier.classify("FAILED tests/test_foo.py::test_bar - AssertionError")
        assert result.error_type == ErrorType.TEST_FAILURE

    def test_environment_error_detection(self):
        """Should classify environment errors correctly."""
        classifier = ErrorClassifier()
        result = classifier.classify("FileNotFoundError: [Errno 2] No such file or directory")
        assert result.error_type == ErrorType.ENVIRONMENT

    def test_timeout_error_detection(self):
        """Should classify timeout errors correctly."""
        classifier = ErrorClassifier()
        result = classifier.classify("TimeoutError: operation timed out")
        assert result.error_type == ErrorType.TIMEOUT

    def test_network_error_detection(self):
        """Should classify network errors correctly."""
        classifier = ErrorClassifier()
        result = classifier.classify("ConnectionError: Connection refused")
        assert result.error_type == ErrorType.NETWORK

    def test_unknown_error_fallback(self):
        """Should fall back to UNKNOWN for unrecognized errors."""
        classifier = ErrorClassifier()
        result = classifier.classify("SomeWeirdError: something went wrong")
        assert result.error_type == ErrorType.UNKNOWN


class TestErrorSeverity:
    """Tests for error severity assessment."""

    def test_syntax_error_is_critical(self):
        """Syntax errors should be critical (blocks execution)."""
        classifier = ErrorClassifier()
        result = classifier.classify("SyntaxError: invalid syntax")
        assert result.severity == ErrorSeverity.CRITICAL

    def test_test_failure_is_warning(self):
        """Test failures should be warning level."""
        classifier = ErrorClassifier()
        result = classifier.classify("FAILED test_foo - assertion failed")
        assert result.severity == ErrorSeverity.WARNING

    def test_timeout_is_high(self):
        """Timeout errors should be high severity."""
        classifier = ErrorClassifier()
        result = classifier.classify("TimeoutError: timed out after 30s")
        assert result.severity == ErrorSeverity.HIGH


class TestRecoveryStrategy:
    """Tests for recovery strategy selection."""

    def test_syntax_error_strategy(self):
        """Syntax errors should suggest code fix."""
        classifier = ErrorClassifier()
        result = classifier.classify("SyntaxError: unexpected EOF")
        assert RecoveryStrategy.FIX_CODE in result.strategies

    def test_import_error_strategy(self):
        """Import errors should suggest install or fix import."""
        classifier = ErrorClassifier()
        result = classifier.classify("ModuleNotFoundError: No module named 'foo'")
        strategies = result.strategies
        assert RecoveryStrategy.INSTALL_DEPENDENCY in strategies or RecoveryStrategy.FIX_IMPORT in strategies

    def test_test_failure_strategy(self):
        """Test failures should suggest debug or fix test."""
        classifier = ErrorClassifier()
        result = classifier.classify("FAILED test_x - AssertionError: expected 1, got 2")
        strategies = result.strategies
        assert RecoveryStrategy.DEBUG in strategies or RecoveryStrategy.FIX_TEST in strategies

    def test_environment_error_strategy(self):
        """Environment errors should suggest check environment."""
        classifier = ErrorClassifier()
        result = classifier.classify("PermissionError: Permission denied")
        assert RecoveryStrategy.CHECK_ENVIRONMENT in result.strategies

    def test_flaky_error_strategy(self):
        """Flaky errors should suggest retry."""
        classifier = ErrorClassifier()
        # Simulate a known flaky pattern
        result = classifier.classify("Connection reset by peer", context={"flaky_history": True})
        assert RecoveryStrategy.RETRY in result.strategies

    def test_timeout_strategy(self):
        """Timeout errors should suggest increase timeout or optimize."""
        classifier = ErrorClassifier()
        result = classifier.classify("TimeoutError: test timed out")
        strategies = result.strategies
        assert RecoveryStrategy.INCREASE_TIMEOUT in strategies or RecoveryStrategy.OPTIMIZE in strategies


class TestErrorSignature:
    """Tests for error signature extraction."""

    def test_signature_extraction(self):
        """Should extract a normalized signature from error."""
        classifier = ErrorClassifier()
        error1 = "TypeError: cannot add 'int' and 'str' at line 42"
        error2 = "TypeError: cannot add 'int' and 'str' at line 100"

        sig1 = classifier.get_signature(error1)
        sig2 = classifier.get_signature(error2)

        # Same error type and message should have same signature
        assert sig1 == sig2

    def test_different_errors_different_signatures(self):
        """Different errors should have different signatures."""
        classifier = ErrorClassifier()
        error1 = "TypeError: cannot add types"
        error2 = "ValueError: invalid literal"

        sig1 = classifier.get_signature(error1)
        sig2 = classifier.get_signature(error2)

        assert sig1 != sig2

    def test_signature_is_hashable(self):
        """Signatures should be hashable for use in dicts/sets."""
        classifier = ErrorClassifier()
        sig = classifier.get_signature("SomeError: message")

        # Should be usable as dict key
        error_counts = {sig: 1}
        assert sig in error_counts


class TestSimilarErrorDetection:
    """Tests for detecting similar previously seen errors."""

    def test_detect_similar_error(self):
        """Should detect when we've seen a similar error before."""
        classifier = ErrorClassifier()

        # Record first occurrence
        classifier.record_error("TypeError: unsupported operand types")

        # Check if similar
        is_similar = classifier.is_similar_to_previous("TypeError: unsupported operand types")
        assert is_similar

    def test_count_similar_errors(self):
        """Should count occurrences of similar errors."""
        classifier = ErrorClassifier()

        classifier.record_error("ImportError: no module 'x'")
        classifier.record_error("ImportError: no module 'x'")
        classifier.record_error("ImportError: no module 'x'")

        count = classifier.get_error_count("ImportError: no module 'x'")
        assert count == 3

    def test_clear_error_history(self):
        """Should be able to clear error history."""
        classifier = ErrorClassifier()

        classifier.record_error("Error1")
        classifier.record_error("Error2")
        classifier.clear_history()

        assert classifier.get_error_count("Error1") == 0


class TestRecoveryPlaybook:
    """Tests for recovery playbooks."""

    def test_playbook_for_syntax_error(self):
        """Should have a playbook for syntax errors."""
        playbook = RecoveryPlaybook.for_error_type(ErrorType.SYNTAX)
        assert playbook is not None
        assert len(playbook.steps) > 0

    def test_playbook_for_import_error(self):
        """Should have a playbook for import errors."""
        playbook = RecoveryPlaybook.for_error_type(ErrorType.IMPORT)
        assert playbook is not None
        assert len(playbook.steps) > 0

    def test_playbook_for_test_failure(self):
        """Should have a playbook for test failures."""
        playbook = RecoveryPlaybook.for_error_type(ErrorType.TEST_FAILURE)
        assert playbook is not None
        assert len(playbook.steps) > 0

    def test_playbook_steps_are_ordered(self):
        """Playbook steps should be in recommended order."""
        playbook = RecoveryPlaybook.for_error_type(ErrorType.SYNTAX)
        # First step should be something like "identify location"
        assert "identify" in playbook.steps[0].lower() or "locate" in playbook.steps[0].lower() or "find" in playbook.steps[0].lower()

    def test_playbook_has_escalation(self):
        """Playbook should define when to escalate."""
        playbook = RecoveryPlaybook.for_error_type(ErrorType.SYNTAX)
        assert playbook.escalation_threshold > 0


class TestEscalationDecision:
    """Tests for deciding when to escalate to human."""

    def test_escalate_after_many_attempts(self):
        """Should recommend escalation after many failed attempts."""
        classifier = ErrorClassifier()

        # Record same error many times
        error = "SomeError: persistent issue"
        for _ in range(10):
            classifier.record_error(error)

        result = classifier.classify(error)
        assert result.should_escalate

    def test_no_escalate_on_first_occurrence(self):
        """Should not escalate on first occurrence."""
        classifier = ErrorClassifier()

        result = classifier.classify("NewError: first time seeing this")
        assert not result.should_escalate

    def test_escalate_critical_error_sooner(self):
        """Critical errors should escalate sooner."""
        classifier = ErrorClassifier()

        # Critical errors escalate after fewer attempts
        error = "SyntaxError: complete nonsense"
        for _ in range(3):
            classifier.record_error(error)

        result = classifier.classify(error)
        # May or may not escalate depending on threshold, but should have lower threshold
        assert result.escalation_threshold <= 5


class TestFullClassification:
    """Integration tests for full error classification."""

    def test_full_classification_result(self):
        """Should return a complete classification result."""
        classifier = ErrorClassifier()

        result = classifier.classify(
            "ModuleNotFoundError: No module named 'requests'",
            context={"file": "app.py", "line": 5}
        )

        assert result.error_type == ErrorType.IMPORT
        assert result.severity is not None
        assert len(result.strategies) > 0
        assert result.signature is not None

    def test_classification_with_context(self):
        """Should use context to improve classification."""
        classifier = ErrorClassifier()

        # Same error but different contexts
        result1 = classifier.classify(
            "AssertionError: 1 != 2",
            context={"source": "test"}
        )
        result2 = classifier.classify(
            "AssertionError: 1 != 2",
            context={"source": "production"}
        )

        # Test context should classify as test failure
        assert result1.error_type == ErrorType.TEST_FAILURE
        # Production context might be different
        assert result2.error_type in [ErrorType.LOGIC, ErrorType.RUNTIME, ErrorType.TEST_FAILURE]
