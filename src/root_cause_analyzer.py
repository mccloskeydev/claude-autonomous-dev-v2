"""Root cause analysis automation.

This module provides root cause analysis for autonomous development:

- Evidence collection and typing
- Hypothesis generation and validation
- Causal chain construction
- Root cause determination with confidence scoring
- Integration with error classifier
"""

import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class EvidenceType(Enum):
    """Types of evidence for root cause analysis."""

    ERROR_MESSAGE = "error_message"
    STACK_TRACE = "stack_trace"
    LOG_ENTRY = "log_entry"
    CODE_DIFF = "code_diff"
    TEST_OUTPUT = "test_output"
    CONFIGURATION = "configuration"
    SYSTEM_STATE = "system_state"


@dataclass
class Evidence:
    """A piece of evidence for root cause analysis."""

    evidence_type: EvidenceType
    content: str
    source: str
    relevance: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class Hypothesis:
    """A hypothesis about the root cause."""

    description: str
    confidence: float
    supporting_evidence: list[Evidence] = field(default_factory=list)
    confirmed: bool = False
    rejected: bool = False
    rejection_reason: str | None = None

    def confirm(self) -> None:
        """Mark hypothesis as confirmed."""
        self.confirmed = True
        self.rejected = False

    def reject(self, reason: str) -> None:
        """Mark hypothesis as rejected.

        Args:
            reason: Reason for rejection
        """
        self.rejected = True
        self.confirmed = False
        self.rejection_reason = reason


@dataclass
class CausalChain:
    """A chain of events leading to an error."""

    steps: list[str] = field(default_factory=list)

    def add_step(self, step: str) -> None:
        """Add a step to the causal chain.

        Args:
            step: Description of the step
        """
        self.steps.append(step)

    def get_root(self) -> str | None:
        """Get the root cause (first step).

        Returns:
            Root cause or None
        """
        return self.steps[0] if self.steps else None

    def get_immediate_cause(self) -> str | None:
        """Get the immediate cause (last step).

        Returns:
            Immediate cause or None
        """
        return self.steps[-1] if self.steps else None

    def depth(self) -> int:
        """Get the depth of the causal chain.

        Returns:
            Number of steps
        """
        return len(self.steps)


@dataclass
class RootCause:
    """The determined root cause of an error."""

    description: str
    category: str
    confidence: float
    causal_chain: CausalChain | None = None
    fix_suggestions: list[str] = field(default_factory=list)
    affected_files: list[str] = field(default_factory=list)
    related_errors: list[str] = field(default_factory=list)


@dataclass
class Investigation:
    """An investigation into an error."""

    error_message: str
    error_type: str
    evidence: list[Evidence] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    status: str = "open"
    root_cause: RootCause | None = None
    _affected_files: list[str] = field(default_factory=list)

    def add_evidence(self, evidence: Evidence) -> None:
        """Add evidence to investigation.

        Args:
            evidence: Evidence to add
        """
        self.evidence.append(evidence)

    def add_hypothesis(self, hypothesis: Hypothesis) -> None:
        """Add hypothesis to investigation.

        Args:
            hypothesis: Hypothesis to add
        """
        self.hypotheses.append(hypothesis)

    def start(self) -> None:
        """Start the investigation."""
        self.status = "in_progress"

    def conclude(self, root_cause: RootCause) -> None:
        """Conclude the investigation with a root cause.

        Args:
            root_cause: The determined root cause
        """
        self.root_cause = root_cause
        self.status = "concluded"

    def get_top_hypotheses(self, limit: int = 5) -> list[Hypothesis]:
        """Get top hypotheses sorted by confidence.

        Args:
            limit: Maximum number to return

        Returns:
            List of hypotheses
        """
        sorted_hypotheses = sorted(
            self.hypotheses, key=lambda h: h.confidence, reverse=True
        )
        return sorted_hypotheses[:limit]

    def get_affected_files(self) -> list[str]:
        """Get list of affected files.

        Returns:
            List of file paths
        """
        return self._affected_files

    def set_affected_files(self, files: list[str]) -> None:
        """Set affected files.

        Args:
            files: List of file paths
        """
        self._affected_files = files


class RootCauseAnalyzer:
    """Analyzes errors to determine root cause."""

    # Error patterns for hypothesis generation
    ERROR_PATTERNS = {
        "NoneType": [
            ("Variable is None when it should have a value", 0.8),
            ("Missing null check before accessing attribute", 0.7),
            ("Function returned None unexpectedly", 0.6),
        ],
        "KeyError": [
            ("Dictionary key does not exist", 0.9),
            ("Missing key in data structure", 0.8),
            ("Unexpected data format", 0.6),
        ],
        "TypeError": [
            ("Wrong type passed to function", 0.7),
            ("Incompatible operation between types", 0.6),
            ("Missing type conversion", 0.5),
        ],
        "AttributeError": [
            ("Object does not have expected attribute", 0.8),
            ("Wrong object type being used", 0.7),
            ("Attribute name is misspelled", 0.5),
        ],
        "ImportError": [
            ("Module is not installed", 0.8),
            ("Module name is incorrect", 0.7),
            ("Circular import detected", 0.5),
        ],
        "ValueError": [
            ("Invalid value passed to function", 0.7),
            ("Data validation failed", 0.6),
            ("Conversion error", 0.5),
        ],
        "IndexError": [
            ("List index out of range", 0.9),
            ("Empty list being accessed", 0.7),
            ("Off-by-one error", 0.5),
        ],
        "SyntaxError": [
            ("Invalid Python syntax", 0.9),
            ("Missing closing bracket or quote", 0.7),
            ("Incorrect indentation", 0.5),
        ],
    }

    # Fix suggestions by error type
    FIX_SUGGESTIONS = {
        "NoneType": [
            "Add null check before accessing the variable",
            "Ensure function returns a value in all code paths",
            "Use default value with dict.get() or getattr()",
        ],
        "KeyError": [
            "Check if key exists using 'in' operator",
            "Use dict.get() with default value",
            "Validate data structure before accessing",
        ],
        "TypeError": [
            "Verify variable types before operations",
            "Add type conversion where needed",
            "Use isinstance() to check types",
        ],
        "AttributeError": [
            "Check object type before accessing attribute",
            "Use hasattr() to verify attribute exists",
            "Verify correct object is being used",
        ],
        "ImportError": [
            "Install the missing module with pip",
            "Check module name spelling",
            "Look for circular import issues",
        ],
        "ValueError": [
            "Validate input before processing",
            "Add try/except for conversion errors",
            "Check data format matches expectations",
        ],
        "IndexError": [
            "Check list length before accessing index",
            "Handle empty list case",
            "Verify loop bounds",
        ],
        "SyntaxError": [
            "Check for missing brackets or quotes",
            "Verify indentation is consistent",
            "Look for typos in keywords",
        ],
    }

    def __init__(self) -> None:
        """Initialize root cause analyzer."""
        self._investigations: list[Investigation] = []

    def analyze(
        self,
        error: str,
        classification: Any = None,
    ) -> Investigation:
        """Analyze an error and create an investigation.

        Args:
            error: Error message or traceback
            classification: Optional error classification from F009

        Returns:
            Investigation object
        """
        # Extract error type
        error_type = self._extract_error_type(error)

        # Create investigation
        investigation = Investigation(
            error_message=error,
            error_type=error_type,
        )

        # Collect evidence
        self._collect_evidence(investigation, error)

        # Extract affected files
        files = self._extract_files(error)
        investigation.set_affected_files(files)

        # Generate hypotheses
        self._generate_hypotheses(investigation)

        # Store investigation
        self._investigations.append(investigation)

        return investigation

    def _extract_error_type(self, error: str) -> str:
        """Extract error type from error message.

        Args:
            error: Error string

        Returns:
            Error type name
        """
        # Match patterns like "TypeError:", "KeyError:", etc.
        match = re.search(r"(\w+Error|\w+Exception):", error)
        if match:
            return match.group(1)

        # Check for error type at start of line
        match = re.search(r"^(\w+Error|\w+Exception)", error, re.MULTILINE)
        if match:
            return match.group(1)

        return "UnknownError"

    def _collect_evidence(self, investigation: Investigation, error: str) -> None:
        """Collect evidence from error.

        Args:
            investigation: Investigation to add evidence to
            error: Error string
        """
        # Add error message as evidence
        investigation.add_evidence(
            Evidence(
                evidence_type=EvidenceType.ERROR_MESSAGE,
                content=error,
                source="error_output",
                relevance=1.0,
            )
        )

        # Check for stack trace
        if "Traceback" in error or "File" in error:
            investigation.add_evidence(
                Evidence(
                    evidence_type=EvidenceType.STACK_TRACE,
                    content=error,
                    source="traceback",
                    relevance=0.9,
                )
            )

    def _extract_files(self, error: str) -> list[str]:
        """Extract file paths from error.

        Args:
            error: Error string

        Returns:
            List of file paths
        """
        files = []
        # Match File "path", line N patterns
        for match in re.finditer(r'File ["\']([^"\']+)["\']', error):
            filepath = match.group(1)
            if not filepath.startswith("<"):  # Ignore <stdin>, etc.
                files.append(filepath)

        return files

    def _generate_hypotheses(self, investigation: Investigation) -> None:
        """Generate hypotheses based on evidence.

        Args:
            investigation: Investigation to add hypotheses to
        """
        error_type = investigation.error_type
        error_message = investigation.error_message

        # Get patterns for this error type
        base_type = error_type.replace("Error", "").replace("Exception", "")

        # Check for NoneType specific patterns
        if "NoneType" in error_message:
            patterns = self.ERROR_PATTERNS.get("NoneType", [])
        else:
            patterns = self.ERROR_PATTERNS.get(error_type, [])
            if not patterns:
                patterns = self.ERROR_PATTERNS.get(base_type, [])

        for description, confidence in patterns:
            investigation.add_hypothesis(
                Hypothesis(
                    description=description,
                    confidence=confidence,
                )
            )

        # Add generic hypothesis if no specific patterns
        if not investigation.hypotheses:
            investigation.add_hypothesis(
                Hypothesis(
                    description=f"Unknown issue causing {error_type}",
                    confidence=0.3,
                )
            )

    def build_causal_chain(self, investigation: Investigation) -> CausalChain:
        """Build causal chain from investigation evidence.

        Args:
            investigation: Investigation to analyze

        Returns:
            CausalChain object
        """
        chain = CausalChain()

        # Extract file/line info from traceback
        files = investigation.get_affected_files()

        # Build chain from traceback (root to immediate)
        for file_path in files:
            chain.add_step(f"Execution in {file_path}")

        # Add the error itself as final step
        if investigation.error_type:
            chain.add_step(f"{investigation.error_type} raised")

        return chain

    def determine_root_cause(self, investigation: Investigation) -> RootCause:
        """Determine root cause from investigation.

        Args:
            investigation: Investigation to analyze

        Returns:
            RootCause object
        """
        # Get top hypothesis
        top_hypotheses = investigation.get_top_hypotheses(limit=1)
        if top_hypotheses:
            description = top_hypotheses[0].description
            confidence = top_hypotheses[0].confidence
        else:
            description = f"Unknown cause of {investigation.error_type}"
            confidence = 0.3

        # Determine category
        category = self._categorize_error(investigation.error_type)

        # Build causal chain
        causal_chain = self.build_causal_chain(investigation)

        # Get fix suggestions
        fix_suggestions = self._get_fix_suggestions(investigation.error_type, investigation.error_message)

        # Get affected files
        affected_files = investigation.get_affected_files()

        return RootCause(
            description=description,
            category=category,
            confidence=confidence,
            causal_chain=causal_chain,
            fix_suggestions=fix_suggestions,
            affected_files=affected_files,
        )

    def _categorize_error(self, error_type: str) -> str:
        """Categorize error type.

        Args:
            error_type: Type of error

        Returns:
            Category name
        """
        categories = {
            "SyntaxError": "syntax",
            "IndentationError": "syntax",
            "ImportError": "import",
            "ModuleNotFoundError": "import",
            "TypeError": "type",
            "ValueError": "validation",
            "KeyError": "data",
            "IndexError": "data",
            "AttributeError": "attribute",
            "NameError": "reference",
            "RuntimeError": "runtime",
            "OSError": "system",
            "IOError": "io",
            "FileNotFoundError": "io",
        }
        return categories.get(error_type, "unknown")

    def _get_fix_suggestions(self, error_type: str, error_message: str) -> list[str]:
        """Get fix suggestions for error.

        Args:
            error_type: Type of error
            error_message: Full error message

        Returns:
            List of fix suggestions
        """
        suggestions = []

        # Check for NoneType specific
        if "NoneType" in error_message:
            suggestions.extend(self.FIX_SUGGESTIONS.get("NoneType", []))
        else:
            suggestions.extend(self.FIX_SUGGESTIONS.get(error_type, []))

        # Add generic suggestions if none found
        if not suggestions:
            suggestions = [
                f"Review code for {error_type}",
                "Check variable values at error location",
                "Add logging to trace execution",
            ]

        return suggestions

    def save_investigation(self, investigation: Investigation, filepath: Path) -> None:
        """Save investigation to file.

        Args:
            investigation: Investigation to save
            filepath: Path to save to
        """
        data = {
            "error_message": investigation.error_message,
            "error_type": investigation.error_type,
            "status": investigation.status,
            "evidence": [
                {
                    "type": e.evidence_type.value,
                    "content": e.content,
                    "source": e.source,
                    "relevance": e.relevance,
                }
                for e in investigation.evidence
            ],
            "hypotheses": [
                {
                    "description": h.description,
                    "confidence": h.confidence,
                    "confirmed": h.confirmed,
                    "rejected": h.rejected,
                }
                for h in investigation.hypotheses
            ],
            "affected_files": investigation.get_affected_files(),
        }

        if investigation.root_cause:
            data["root_cause"] = {
                "description": investigation.root_cause.description,
                "category": investigation.root_cause.category,
                "confidence": investigation.root_cause.confidence,
                "fix_suggestions": investigation.root_cause.fix_suggestions,
            }

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def load_investigation(self, filepath: Path) -> Investigation:
        """Load investigation from file.

        Args:
            filepath: Path to load from

        Returns:
            Investigation object
        """
        with open(filepath) as f:
            data = json.load(f)

        investigation = Investigation(
            error_message=data["error_message"],
            error_type=data["error_type"],
        )
        investigation.status = data.get("status", "open")
        investigation.set_affected_files(data.get("affected_files", []))

        # Restore evidence
        for e_data in data.get("evidence", []):
            evidence = Evidence(
                evidence_type=EvidenceType(e_data["type"]),
                content=e_data["content"],
                source=e_data["source"],
                relevance=e_data.get("relevance", 0.5),
            )
            investigation.add_evidence(evidence)

        # Restore hypotheses
        for h_data in data.get("hypotheses", []):
            hypothesis = Hypothesis(
                description=h_data["description"],
                confidence=h_data["confidence"],
            )
            hypothesis.confirmed = h_data.get("confirmed", False)
            hypothesis.rejected = h_data.get("rejected", False)
            investigation.add_hypothesis(hypothesis)

        # Restore root cause if present
        if "root_cause" in data:
            rc_data = data["root_cause"]
            investigation.root_cause = RootCause(
                description=rc_data["description"],
                category=rc_data["category"],
                confidence=rc_data["confidence"],
                fix_suggestions=rc_data.get("fix_suggestions", []),
            )

        return investigation
