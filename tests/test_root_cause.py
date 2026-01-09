"""Tests for root cause analysis automation."""

import tempfile
from pathlib import Path

from src.root_cause_analyzer import (
    CausalChain,
    Evidence,
    EvidenceType,
    Hypothesis,
    Investigation,
    RootCause,
    RootCauseAnalyzer,
)


class TestEvidence:
    """Tests for evidence collection."""

    def test_evidence_creation(self):
        """Should create evidence with required fields."""
        evidence = Evidence(
            evidence_type=EvidenceType.ERROR_MESSAGE,
            content="TypeError: 'NoneType' object is not subscriptable",
            source="traceback",
        )
        assert evidence.evidence_type == EvidenceType.ERROR_MESSAGE
        assert "NoneType" in evidence.content
        assert evidence.source == "traceback"

    def test_evidence_with_metadata(self):
        """Should store metadata."""
        evidence = Evidence(
            evidence_type=EvidenceType.LOG_ENTRY,
            content="Connection refused",
            source="app.log",
            metadata={"line": 42, "timestamp": "2026-01-09T10:00:00Z"},
        )
        assert evidence.metadata["line"] == 42

    def test_evidence_relevance_score(self):
        """Should calculate relevance score."""
        evidence = Evidence(
            evidence_type=EvidenceType.ERROR_MESSAGE,
            content="KeyError: 'user_id'",
            source="traceback",
            relevance=0.9,
        )
        assert evidence.relevance == 0.9


class TestEvidenceType:
    """Tests for evidence types."""

    def test_evidence_types_exist(self):
        """Should have expected evidence types."""
        assert EvidenceType.ERROR_MESSAGE
        assert EvidenceType.STACK_TRACE
        assert EvidenceType.LOG_ENTRY
        assert EvidenceType.CODE_DIFF
        assert EvidenceType.TEST_OUTPUT
        assert EvidenceType.CONFIGURATION
        assert EvidenceType.SYSTEM_STATE


class TestHypothesis:
    """Tests for hypotheses."""

    def test_hypothesis_creation(self):
        """Should create hypothesis."""
        hypothesis = Hypothesis(
            description="Missing null check in get_user function",
            confidence=0.7,
        )
        assert "null check" in hypothesis.description
        assert hypothesis.confidence == 0.7

    def test_hypothesis_with_evidence(self):
        """Should link evidence to hypothesis."""
        evidence = Evidence(
            evidence_type=EvidenceType.ERROR_MESSAGE,
            content="NoneType error",
            source="traceback",
        )
        hypothesis = Hypothesis(
            description="Null pointer issue",
            confidence=0.8,
            supporting_evidence=[evidence],
        )
        assert len(hypothesis.supporting_evidence) == 1

    def test_hypothesis_confirmation(self):
        """Should track confirmation status."""
        hypothesis = Hypothesis(
            description="Test hypothesis",
            confidence=0.5,
        )
        assert not hypothesis.confirmed
        assert not hypothesis.rejected

        hypothesis.confirm()
        assert hypothesis.confirmed

    def test_hypothesis_rejection(self):
        """Should track rejection status."""
        hypothesis = Hypothesis(
            description="Test hypothesis",
            confidence=0.5,
        )
        hypothesis.reject(reason="Evidence contradicts hypothesis")
        assert hypothesis.rejected
        assert "contradicts" in hypothesis.rejection_reason


class TestCausalChain:
    """Tests for causal chains."""

    def test_causal_chain_creation(self):
        """Should create causal chain."""
        chain = CausalChain()
        assert len(chain.steps) == 0

    def test_add_step(self):
        """Should add steps to chain."""
        chain = CausalChain()
        chain.add_step("User sends request without auth token")
        chain.add_step("Auth middleware receives null token")
        chain.add_step("NoneType error raised")

        assert len(chain.steps) == 3
        assert "auth token" in chain.steps[0]

    def test_get_root(self):
        """Should identify root of chain."""
        chain = CausalChain()
        chain.add_step("Database connection pool exhausted")
        chain.add_step("Connection timeout")
        chain.add_step("Request handler crashes")

        root = chain.get_root()
        assert "pool exhausted" in root

    def test_get_immediate_cause(self):
        """Should identify immediate cause."""
        chain = CausalChain()
        chain.add_step("Root cause")
        chain.add_step("Intermediate")
        chain.add_step("Immediate cause")

        immediate = chain.get_immediate_cause()
        assert immediate == "Immediate cause"

    def test_chain_depth(self):
        """Should calculate chain depth."""
        chain = CausalChain()
        chain.add_step("Step 1")
        chain.add_step("Step 2")
        chain.add_step("Step 3")

        assert chain.depth() == 3


class TestRootCause:
    """Tests for root cause results."""

    def test_root_cause_creation(self):
        """Should create root cause with required fields."""
        root_cause = RootCause(
            description="Missing input validation in user registration",
            category="validation",
            confidence=0.85,
        )
        assert "input validation" in root_cause.description
        assert root_cause.category == "validation"
        assert root_cause.confidence == 0.85

    def test_root_cause_with_fix_suggestions(self):
        """Should include fix suggestions."""
        root_cause = RootCause(
            description="SQL injection vulnerability",
            category="security",
            confidence=0.95,
            fix_suggestions=[
                "Use parameterized queries",
                "Sanitize user input",
            ],
        )
        assert len(root_cause.fix_suggestions) == 2

    def test_root_cause_with_causal_chain(self):
        """Should include causal chain."""
        chain = CausalChain()
        chain.add_step("Cause 1")
        chain.add_step("Cause 2")

        root_cause = RootCause(
            description="Test root cause",
            category="test",
            confidence=0.8,
            causal_chain=chain,
        )
        assert root_cause.causal_chain.depth() == 2

    def test_root_cause_affected_files(self):
        """Should track affected files."""
        root_cause = RootCause(
            description="Bug in auth module",
            category="logic",
            confidence=0.9,
            affected_files=["src/auth.py", "src/middleware.py"],
        )
        assert "src/auth.py" in root_cause.affected_files


class TestInvestigation:
    """Tests for investigations."""

    def test_investigation_creation(self):
        """Should create investigation from error."""
        investigation = Investigation(
            error_message="ImportError: No module named 'foo'",
            error_type="ImportError",
        )
        assert "ImportError" in investigation.error_message
        assert investigation.status == "open"

    def test_add_evidence(self):
        """Should add evidence to investigation."""
        investigation = Investigation(
            error_message="Test error",
            error_type="TestError",
        )
        evidence = Evidence(
            evidence_type=EvidenceType.ERROR_MESSAGE,
            content="Test content",
            source="test",
        )
        investigation.add_evidence(evidence)
        assert len(investigation.evidence) == 1

    def test_add_hypothesis(self):
        """Should add hypothesis to investigation."""
        investigation = Investigation(
            error_message="Test error",
            error_type="TestError",
        )
        hypothesis = Hypothesis(
            description="Test hypothesis",
            confidence=0.5,
        )
        investigation.add_hypothesis(hypothesis)
        assert len(investigation.hypotheses) == 1

    def test_investigation_status(self):
        """Should track investigation status."""
        investigation = Investigation(
            error_message="Test error",
            error_type="TestError",
        )
        assert investigation.status == "open"

        investigation.start()
        assert investigation.status == "in_progress"

        investigation.conclude(
            RootCause(description="Found", category="test", confidence=0.9)
        )
        assert investigation.status == "concluded"

    def test_get_top_hypotheses(self):
        """Should return hypotheses sorted by confidence."""
        investigation = Investigation(
            error_message="Test error",
            error_type="TestError",
        )
        investigation.add_hypothesis(Hypothesis(description="Low", confidence=0.3))
        investigation.add_hypothesis(Hypothesis(description="High", confidence=0.9))
        investigation.add_hypothesis(Hypothesis(description="Medium", confidence=0.6))

        top = investigation.get_top_hypotheses(limit=2)
        assert len(top) == 2
        assert top[0].confidence >= top[1].confidence


class TestRootCauseAnalyzer:
    """Tests for root cause analyzer."""

    def test_analyzer_creation(self):
        """Should create analyzer."""
        analyzer = RootCauseAnalyzer()
        assert analyzer is not None

    def test_analyze_error_message(self):
        """Should analyze error message and extract evidence."""
        analyzer = RootCauseAnalyzer()

        error = """
Traceback (most recent call last):
  File "src/app.py", line 42, in process_request
    result = user.get_profile()
  File "src/user.py", line 15, in get_profile
    return self.data['profile']
TypeError: 'NoneType' object is not subscriptable
"""
        investigation = analyzer.analyze(error)

        assert investigation is not None
        assert len(investigation.evidence) > 0
        assert investigation.error_type == "TypeError"

    def test_analyze_identifies_affected_files(self):
        """Should identify affected files from traceback."""
        analyzer = RootCauseAnalyzer()

        error = """
Traceback (most recent call last):
  File "src/main.py", line 10
  File "src/utils.py", line 25
  File "src/core.py", line 42
ValueError: invalid literal
"""
        investigation = analyzer.analyze(error)
        files = investigation.get_affected_files()

        assert "src/main.py" in files
        assert "src/utils.py" in files
        assert "src/core.py" in files

    def test_generate_hypotheses(self):
        """Should generate hypotheses from evidence."""
        analyzer = RootCauseAnalyzer()

        error = "TypeError: 'NoneType' object is not subscriptable"
        investigation = analyzer.analyze(error)

        assert len(investigation.hypotheses) > 0

    def test_analyze_import_error(self):
        """Should analyze import errors."""
        analyzer = RootCauseAnalyzer()

        error = """
Traceback (most recent call last):
  File "src/main.py", line 1
ImportError: No module named 'nonexistent_module'
"""
        investigation = analyzer.analyze(error)

        assert investigation.error_type == "ImportError"
        # Should suggest checking dependencies
        hypotheses = [h.description.lower() for h in investigation.hypotheses]
        assert any("module" in h or "install" in h or "import" in h for h in hypotheses)

    def test_analyze_attribute_error(self):
        """Should analyze attribute errors."""
        analyzer = RootCauseAnalyzer()

        error = "AttributeError: 'User' object has no attribute 'email_address'"
        investigation = analyzer.analyze(error)

        assert investigation.error_type == "AttributeError"

    def test_analyze_key_error(self):
        """Should analyze key errors."""
        analyzer = RootCauseAnalyzer()

        error = "KeyError: 'user_id'"
        investigation = analyzer.analyze(error)

        assert investigation.error_type == "KeyError"

    def test_build_causal_chain(self):
        """Should build causal chain from evidence."""
        analyzer = RootCauseAnalyzer()

        error = """
Traceback (most recent call last):
  File "src/api.py", line 50, in handle_request
    data = self.fetch_data()
  File "src/data.py", line 20, in fetch_data
    return self.cache.get(key)
  File "src/cache.py", line 10, in get
    return self.storage[key]
KeyError: 'session_123'
"""
        investigation = analyzer.analyze(error)
        chain = analyzer.build_causal_chain(investigation)

        assert chain is not None
        assert chain.depth() > 0

    def test_suggest_fixes(self):
        """Should suggest fixes based on root cause."""
        analyzer = RootCauseAnalyzer()

        error = "TypeError: 'NoneType' object is not subscriptable"
        investigation = analyzer.analyze(error)
        root_cause = analyzer.determine_root_cause(investigation)

        assert root_cause is not None
        assert len(root_cause.fix_suggestions) > 0

    def test_integration_with_error_classifier(self):
        """Should integrate with error classifier from F009."""
        from src.error_classifier import ErrorClassifier

        analyzer = RootCauseAnalyzer()
        classifier = ErrorClassifier()

        error = "SyntaxError: invalid syntax"

        # Classify the error
        classification = classifier.classify(error)

        # Analyze for root cause
        investigation = analyzer.analyze(error, classification=classification)

        assert investigation.error_type == "SyntaxError"

    def test_confidence_scoring(self):
        """Should calculate confidence in root cause."""
        analyzer = RootCauseAnalyzer()

        error = """
TypeError: 'NoneType' object is not subscriptable
"""
        investigation = analyzer.analyze(error)
        root_cause = analyzer.determine_root_cause(investigation)

        assert 0 <= root_cause.confidence <= 1

    def test_persistence(self):
        """Should save and load investigations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "investigations.json"

            analyzer = RootCauseAnalyzer()
            investigation = analyzer.analyze("KeyError: 'test_key'")
            analyzer.save_investigation(investigation, filepath)

            # Load and verify
            loaded = analyzer.load_investigation(filepath)
            assert loaded.error_type == "KeyError"


class TestRootCauseAnalyzerIntegration:
    """Integration tests for root cause analyzer."""

    def test_full_analysis_workflow(self):
        """Should complete full analysis workflow."""
        analyzer = RootCauseAnalyzer()

        # Complex error with traceback
        error = """
Traceback (most recent call last):
  File "src/handlers/user_handler.py", line 45, in create_user
    user = User(email=data['email'], name=data['name'])
  File "src/models/user.py", line 20, in __init__
    self.validate_email(email)
  File "src/models/user.py", line 35, in validate_email
    if not re.match(EMAIL_PATTERN, email):
TypeError: expected string or bytes-like object
"""

        # Analyze
        investigation = analyzer.analyze(error)
        assert investigation.status == "open"

        # Start investigation
        investigation.start()
        assert investigation.status == "in_progress"

        # Get hypotheses
        hypotheses = investigation.get_top_hypotheses(limit=3)
        assert len(hypotheses) > 0

        # Determine root cause
        root_cause = analyzer.determine_root_cause(investigation)
        assert root_cause is not None
        assert root_cause.confidence > 0

        # Get fix suggestions
        assert len(root_cause.fix_suggestions) > 0

        # Complete investigation
        investigation.conclude(root_cause)
        assert investigation.status == "concluded"
        assert investigation.root_cause is not None

    def test_analyze_multiple_errors(self):
        """Should handle multiple error analyses."""
        analyzer = RootCauseAnalyzer()

        errors = [
            "KeyError: 'user_id'",
            "TypeError: cannot unpack non-iterable NoneType object",
            "ImportError: No module named 'missing'",
        ]

        investigations = []
        for error in errors:
            investigation = analyzer.analyze(error)
            investigations.append(investigation)

        assert len(investigations) == 3
        error_types = [inv.error_type for inv in investigations]
        assert "KeyError" in error_types
        assert "TypeError" in error_types
        assert "ImportError" in error_types
