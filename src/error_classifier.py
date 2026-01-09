"""Error classification and strategy selection.

This module provides intelligent error classification for autonomous development
sessions. It includes:

- Error type classification (syntax, import, type, runtime, etc.)
- Severity assessment
- Recovery strategy selection
- Similar error detection
- Escalation decision making
- Recovery playbooks
"""

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class ErrorType(Enum):
    """Types of errors that can occur during development."""

    SYNTAX = auto()
    IMPORT = auto()
    TYPE = auto()
    RUNTIME = auto()
    TEST_FAILURE = auto()
    ENVIRONMENT = auto()
    TIMEOUT = auto()
    NETWORK = auto()
    LOGIC = auto()
    PERMISSION = auto()
    RESOURCE = auto()
    UNKNOWN = auto()


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    LOW = 1
    WARNING = 2
    HIGH = 3
    CRITICAL = 4


class RecoveryStrategy(Enum):
    """Strategies for recovering from errors."""

    RETRY = auto()
    FIX_CODE = auto()
    FIX_IMPORT = auto()
    FIX_TEST = auto()
    INSTALL_DEPENDENCY = auto()
    CHECK_ENVIRONMENT = auto()
    INCREASE_TIMEOUT = auto()
    OPTIMIZE = auto()
    DEBUG = auto()
    ROLLBACK = auto()
    SKIP = auto()
    ESCALATE = auto()


# Error patterns for classification
ERROR_PATTERNS: dict[ErrorType, list[re.Pattern]] = {
    ErrorType.SYNTAX: [
        re.compile(r"SyntaxError", re.IGNORECASE),
        re.compile(r"IndentationError", re.IGNORECASE),
        re.compile(r"invalid syntax", re.IGNORECASE),
    ],
    ErrorType.IMPORT: [
        re.compile(r"ImportError", re.IGNORECASE),
        re.compile(r"ModuleNotFoundError", re.IGNORECASE),
        re.compile(r"No module named", re.IGNORECASE),
    ],
    ErrorType.TYPE: [
        re.compile(r"TypeError", re.IGNORECASE),
        re.compile(r"unsupported operand type", re.IGNORECASE),
    ],
    ErrorType.RUNTIME: [
        re.compile(r"RuntimeError", re.IGNORECASE),
        re.compile(r"recursion depth", re.IGNORECASE),
        re.compile(r"maximum recursion", re.IGNORECASE),
    ],
    ErrorType.TEST_FAILURE: [
        re.compile(r"FAILED\s+test", re.IGNORECASE),
        re.compile(r"test.*failed", re.IGNORECASE),
        re.compile(r"AssertionError", re.IGNORECASE),
    ],
    ErrorType.ENVIRONMENT: [
        re.compile(r"FileNotFoundError", re.IGNORECASE),
        re.compile(r"No such file or directory", re.IGNORECASE),
        re.compile(r"PermissionError", re.IGNORECASE),
        re.compile(r"Permission denied", re.IGNORECASE),
    ],
    ErrorType.TIMEOUT: [
        re.compile(r"TimeoutError", re.IGNORECASE),
        re.compile(r"timed out", re.IGNORECASE),
        re.compile(r"timeout", re.IGNORECASE),
    ],
    ErrorType.NETWORK: [
        re.compile(r"ConnectionError", re.IGNORECASE),
        re.compile(r"Connection refused", re.IGNORECASE),
        re.compile(r"Connection reset", re.IGNORECASE),
        re.compile(r"NetworkError", re.IGNORECASE),
    ],
    ErrorType.LOGIC: [
        re.compile(r"ValueError", re.IGNORECASE),
        re.compile(r"KeyError", re.IGNORECASE),
        re.compile(r"IndexError", re.IGNORECASE),
    ],
}

# Severity mapping by error type
SEVERITY_MAP: dict[ErrorType, ErrorSeverity] = {
    ErrorType.SYNTAX: ErrorSeverity.CRITICAL,
    ErrorType.IMPORT: ErrorSeverity.HIGH,
    ErrorType.TYPE: ErrorSeverity.HIGH,
    ErrorType.RUNTIME: ErrorSeverity.HIGH,
    ErrorType.TEST_FAILURE: ErrorSeverity.WARNING,
    ErrorType.ENVIRONMENT: ErrorSeverity.HIGH,
    ErrorType.TIMEOUT: ErrorSeverity.HIGH,
    ErrorType.NETWORK: ErrorSeverity.HIGH,
    ErrorType.LOGIC: ErrorSeverity.WARNING,
    ErrorType.PERMISSION: ErrorSeverity.HIGH,
    ErrorType.RESOURCE: ErrorSeverity.HIGH,
    ErrorType.UNKNOWN: ErrorSeverity.WARNING,
}

# Recovery strategies by error type
STRATEGY_MAP: dict[ErrorType, list[RecoveryStrategy]] = {
    ErrorType.SYNTAX: [RecoveryStrategy.FIX_CODE],
    ErrorType.IMPORT: [RecoveryStrategy.FIX_IMPORT, RecoveryStrategy.INSTALL_DEPENDENCY],
    ErrorType.TYPE: [RecoveryStrategy.FIX_CODE, RecoveryStrategy.DEBUG],
    ErrorType.RUNTIME: [RecoveryStrategy.FIX_CODE, RecoveryStrategy.DEBUG],
    ErrorType.TEST_FAILURE: [RecoveryStrategy.DEBUG, RecoveryStrategy.FIX_TEST, RecoveryStrategy.FIX_CODE],
    ErrorType.ENVIRONMENT: [RecoveryStrategy.CHECK_ENVIRONMENT],
    ErrorType.TIMEOUT: [RecoveryStrategy.INCREASE_TIMEOUT, RecoveryStrategy.OPTIMIZE, RecoveryStrategy.RETRY],
    ErrorType.NETWORK: [RecoveryStrategy.RETRY, RecoveryStrategy.CHECK_ENVIRONMENT],
    ErrorType.LOGIC: [RecoveryStrategy.FIX_CODE, RecoveryStrategy.DEBUG],
    ErrorType.PERMISSION: [RecoveryStrategy.CHECK_ENVIRONMENT],
    ErrorType.RESOURCE: [RecoveryStrategy.OPTIMIZE, RecoveryStrategy.RETRY],
    ErrorType.UNKNOWN: [RecoveryStrategy.DEBUG, RecoveryStrategy.ESCALATE],
}

# Escalation thresholds by error type (lower = escalate sooner)
ESCALATION_THRESHOLDS: dict[ErrorType, int] = {
    ErrorType.SYNTAX: 5,
    ErrorType.IMPORT: 5,
    ErrorType.TYPE: 5,
    ErrorType.RUNTIME: 5,
    ErrorType.TEST_FAILURE: 10,
    ErrorType.ENVIRONMENT: 3,
    ErrorType.TIMEOUT: 5,
    ErrorType.NETWORK: 8,
    ErrorType.LOGIC: 5,
    ErrorType.PERMISSION: 3,
    ErrorType.RESOURCE: 5,
    ErrorType.UNKNOWN: 5,
}


@dataclass
class ErrorSignature:
    """A normalized signature for an error."""

    error_type: ErrorType
    message_hash: str

    def __hash__(self) -> int:
        return hash((self.error_type, self.message_hash))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ErrorSignature):
            return False
        return self.error_type == other.error_type and self.message_hash == other.message_hash


@dataclass
class ClassificationResult:
    """Result of error classification."""

    error_type: ErrorType
    severity: ErrorSeverity
    strategies: list[RecoveryStrategy]
    signature: ErrorSignature
    escalation_threshold: int
    should_escalate: bool = False
    raw_error: str = ""
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryPlaybook:
    """A playbook of steps to recover from an error type."""

    error_type: ErrorType
    steps: list[str]
    escalation_threshold: int

    @classmethod
    def for_error_type(cls, error_type: ErrorType) -> "RecoveryPlaybook":
        """Get the playbook for a specific error type."""
        playbooks = {
            ErrorType.SYNTAX: cls(
                error_type=ErrorType.SYNTAX,
                steps=[
                    "Identify the exact location of the syntax error",
                    "Check for common issues: missing colons, brackets, parentheses",
                    "Verify proper indentation",
                    "Fix the syntax error",
                    "Run linter to catch additional issues",
                ],
                escalation_threshold=5,
            ),
            ErrorType.IMPORT: cls(
                error_type=ErrorType.IMPORT,
                steps=[
                    "Identify the missing module",
                    "Check if module is installed (pip list / pip show)",
                    "If not installed, add to dependencies and install",
                    "If installed, check import path and spelling",
                    "Verify __init__.py files exist for packages",
                ],
                escalation_threshold=5,
            ),
            ErrorType.TYPE: cls(
                error_type=ErrorType.TYPE,
                steps=[
                    "Identify the types involved in the error",
                    "Check function signatures and return types",
                    "Add type annotations if missing",
                    "Fix type mismatches",
                    "Run type checker to verify",
                ],
                escalation_threshold=5,
            ),
            ErrorType.RUNTIME: cls(
                error_type=ErrorType.RUNTIME,
                steps=[
                    "Identify the runtime condition causing the error",
                    "Add debugging output to trace execution",
                    "Check for infinite loops or recursion",
                    "Add guards for edge cases",
                    "Fix the root cause",
                ],
                escalation_threshold=5,
            ),
            ErrorType.TEST_FAILURE: cls(
                error_type=ErrorType.TEST_FAILURE,
                steps=[
                    "Identify which test is failing",
                    "Check the assertion that failed",
                    "Determine if the test is correct or the code",
                    "Fix either the test or the implementation",
                    "Run the test again to verify",
                ],
                escalation_threshold=10,
            ),
            ErrorType.ENVIRONMENT: cls(
                error_type=ErrorType.ENVIRONMENT,
                steps=[
                    "Identify the missing resource or permission issue",
                    "Check file paths and permissions",
                    "Verify environment variables",
                    "Create missing files/directories if needed",
                    "Adjust permissions or paths",
                ],
                escalation_threshold=3,
            ),
            ErrorType.TIMEOUT: cls(
                error_type=ErrorType.TIMEOUT,
                steps=[
                    "Identify what operation is timing out",
                    "Check if timeout value is reasonable",
                    "Look for performance bottlenecks",
                    "Optimize slow operations",
                    "Increase timeout if operation is legitimately slow",
                ],
                escalation_threshold=5,
            ),
            ErrorType.NETWORK: cls(
                error_type=ErrorType.NETWORK,
                steps=[
                    "Check network connectivity",
                    "Verify the target host/port is correct",
                    "Check for firewall or proxy issues",
                    "Retry with exponential backoff",
                    "Add error handling for network failures",
                ],
                escalation_threshold=8,
            ),
            ErrorType.LOGIC: cls(
                error_type=ErrorType.LOGIC,
                steps=[
                    "Identify the logical error",
                    "Trace the data flow",
                    "Check boundary conditions",
                    "Fix the logic",
                    "Add tests for edge cases",
                ],
                escalation_threshold=5,
            ),
            ErrorType.UNKNOWN: cls(
                error_type=ErrorType.UNKNOWN,
                steps=[
                    "Locate the exact error message and stack trace",
                    "Search for similar errors online",
                    "Add debugging output",
                    "Try to reproduce consistently",
                    "Escalate if unable to diagnose",
                ],
                escalation_threshold=5,
            ),
        }

        return playbooks.get(error_type, playbooks[ErrorType.UNKNOWN])


class ErrorClassifier:
    """Classifies errors and selects recovery strategies.

    This class provides intelligent error classification for autonomous
    development sessions, including:
    - Error type detection from error messages
    - Severity assessment
    - Recovery strategy selection
    - Similar error detection
    - Escalation decision making
    """

    def __init__(self) -> None:
        """Initialize the error classifier."""
        self._error_history: dict[ErrorSignature, int] = {}

    def classify(
        self,
        error: str,
        context: dict[str, Any] | None = None,
    ) -> ClassificationResult:
        """Classify an error and return recovery strategies.

        Args:
            error: The error message or traceback
            context: Optional context about where the error occurred

        Returns:
            ClassificationResult with type, severity, and strategies
        """
        context = context or {}

        # Determine error type
        error_type = self._detect_error_type(error, context)

        # Get severity
        severity = SEVERITY_MAP.get(error_type, ErrorSeverity.WARNING)

        # Get strategies
        strategies = list(STRATEGY_MAP.get(error_type, [RecoveryStrategy.DEBUG]))

        # Add retry strategy for flaky errors
        if context.get("flaky_history") and RecoveryStrategy.RETRY not in strategies:
            strategies.insert(0, RecoveryStrategy.RETRY)

        # Get signature
        signature = self.get_signature(error)

        # Get escalation threshold
        escalation_threshold = ESCALATION_THRESHOLDS.get(error_type, 5)

        # Check if should escalate
        error_count = self._error_history.get(signature, 0)
        should_escalate = error_count >= escalation_threshold

        return ClassificationResult(
            error_type=error_type,
            severity=severity,
            strategies=strategies,
            signature=signature,
            escalation_threshold=escalation_threshold,
            should_escalate=should_escalate,
            raw_error=error,
            context=context,
        )

    def _detect_error_type(self, error: str, context: dict[str, Any]) -> ErrorType:
        """Detect the error type from the error message.

        Args:
            error: The error message
            context: Context about where the error occurred

        Returns:
            The detected ErrorType
        """
        # Check context first for hints
        # Assertion errors in tests are test failures
        if context.get("source") == "test" and "AssertionError" in error:
            return ErrorType.TEST_FAILURE

        # Check each pattern
        for error_type, patterns in ERROR_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(error):
                    return error_type

        return ErrorType.UNKNOWN

    def get_signature(self, error: str) -> ErrorSignature:
        """Extract a normalized signature from an error.

        The signature ignores line numbers and specific values to
        group similar errors together.

        Args:
            error: The error message

        Returns:
            An ErrorSignature object
        """
        # Detect error type
        error_type = self._detect_error_type(error, {})

        # Normalize the error message
        normalized = self._normalize_error(error)

        # Create hash of normalized message
        message_hash = hashlib.md5(normalized.encode()).hexdigest()[:12]

        return ErrorSignature(error_type=error_type, message_hash=message_hash)

    def _normalize_error(self, error: str) -> str:
        """Normalize an error message for signature comparison.

        Removes variable parts like line numbers, file paths, and specific values.

        Args:
            error: The error message

        Returns:
            Normalized error string
        """
        normalized = error

        # Remove line numbers
        normalized = re.sub(r"line \d+", "line N", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r":\d+:", ":N:", normalized)

        # Remove file paths
        normalized = re.sub(r"['\"]?/[^'\":\s]+['\"]?", "PATH", normalized)
        normalized = re.sub(r"['\"]?\w:[\\\/][^'\":\s]+['\"]?", "PATH", normalized)

        # Remove specific numbers
        normalized = re.sub(r"\b\d+\b", "N", normalized)

        # Remove quotes around variable content
        normalized = re.sub(r"'[^']*'", "'X'", normalized)
        normalized = re.sub(r'"[^"]*"', '"X"', normalized)

        return normalized.strip()

    def record_error(self, error: str) -> None:
        """Record an error occurrence for tracking.

        Args:
            error: The error message
        """
        signature = self.get_signature(error)
        self._error_history[signature] = self._error_history.get(signature, 0) + 1

    def is_similar_to_previous(self, error: str) -> bool:
        """Check if this error is similar to a previously seen error.

        Args:
            error: The error message

        Returns:
            True if a similar error was seen before
        """
        signature = self.get_signature(error)
        return signature in self._error_history

    def get_error_count(self, error: str) -> int:
        """Get the number of times a similar error has occurred.

        Args:
            error: The error message

        Returns:
            Number of occurrences
        """
        signature = self.get_signature(error)
        return self._error_history.get(signature, 0)

    def clear_history(self) -> None:
        """Clear the error history."""
        self._error_history.clear()
