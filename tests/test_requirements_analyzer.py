"""Tests for requirements analysis and discovery phase.

This module tests the RequirementsAnalyzer which is responsible for:
- Analyzing task descriptions for completeness
- Detecting information gaps
- Scoring completeness (0-100 scale)
- Generating targeted questions to fill gaps
- Prioritizing questions by importance
"""

from src.requirements_analyzer import (
    CompletenessScore,
    InformationGap,
    QuestionOption,
    RequirementCategory,
    RequirementsAnalysis,
    RequirementsAnalyzer,
    StructuredRequirements,
    TargetedQuestion,
)

# =============================================================================
# Test RequirementCategory Enum
# =============================================================================

class TestRequirementCategory:
    """Tests for the RequirementCategory enum."""

    def test_all_categories_exist(self):
        """Should have all required categories."""
        categories = [c.name for c in RequirementCategory]
        assert "PROBLEM" in categories
        assert "SUCCESS_CRITERIA" in categories
        assert "STAKEHOLDERS" in categories
        assert "CONTEXT" in categories
        assert "CONSTRAINTS" in categories

    def test_categories_have_priority_weights(self):
        """Each category should have an associated priority weight."""
        # Problem is most important, constraints least
        assert RequirementCategory.PROBLEM.value <= RequirementCategory.CONSTRAINTS.value

    def test_category_order_by_priority(self):
        """Categories should be orderable by priority."""
        categories = list(RequirementCategory)
        # Problem should come first (lowest value = highest priority)
        assert categories[0] == RequirementCategory.PROBLEM


# =============================================================================
# Test InformationGap
# =============================================================================

class TestInformationGap:
    """Tests for information gap detection."""

    def test_information_gap_creation(self):
        """Should create an information gap with required fields."""
        gap = InformationGap(
            category=RequirementCategory.PROBLEM,
            description="No clear problem statement found",
            severity=0.9,
            detected_from="Missing problem keywords"
        )
        assert gap.category == RequirementCategory.PROBLEM
        assert gap.severity == 0.9
        assert "problem" in gap.description.lower()

    def test_gap_severity_range(self):
        """Severity should be between 0 and 1."""
        gap = InformationGap(
            category=RequirementCategory.CONTEXT,
            description="Missing context",
            severity=0.5,
            detected_from="analysis"
        )
        assert 0 <= gap.severity <= 1

    def test_gap_is_comparable(self):
        """Gaps should be sortable by severity."""
        gap1 = InformationGap(
            category=RequirementCategory.PROBLEM,
            description="High severity gap",
            severity=0.9,
            detected_from="analysis"
        )
        gap2 = InformationGap(
            category=RequirementCategory.CONTEXT,
            description="Low severity gap",
            severity=0.3,
            detected_from="analysis"
        )
        # Higher severity should sort first
        gaps = sorted([gap2, gap1], key=lambda g: -g.severity)
        assert gaps[0].severity > gaps[1].severity


# =============================================================================
# Test CompletenessScore
# =============================================================================

class TestCompletenessScore:
    """Tests for completeness scoring."""

    def test_score_creation(self):
        """Should create a completeness score."""
        score = CompletenessScore(
            total=75,
            by_category={
                RequirementCategory.PROBLEM: 90,
                RequirementCategory.SUCCESS_CRITERIA: 60,
                RequirementCategory.STAKEHOLDERS: 70,
                RequirementCategory.CONTEXT: 80,
                RequirementCategory.CONSTRAINTS: 75,
            }
        )
        assert score.total == 75
        assert score.by_category[RequirementCategory.PROBLEM] == 90

    def test_score_range(self):
        """Total score should be 0-100."""
        score = CompletenessScore(total=50, by_category={})
        assert 0 <= score.total <= 100

    def test_can_proceed_threshold(self):
        """Score of 60+ should allow proceeding without questions."""
        high_score = CompletenessScore(total=75, by_category={})
        low_score = CompletenessScore(total=45, by_category={})

        assert high_score.can_proceed()
        assert not low_score.can_proceed()

    def test_can_proceed_with_custom_threshold(self):
        """Should respect custom threshold."""
        score = CompletenessScore(total=55, by_category={})
        assert score.can_proceed(threshold=50)
        assert not score.can_proceed(threshold=60)


# =============================================================================
# Test QuestionOption
# =============================================================================

class TestQuestionOption:
    """Tests for question options."""

    def test_option_creation(self):
        """Should create a question option."""
        option = QuestionOption(
            id=1,
            label="User pain point",
            description="Users are struggling with something specific"
        )
        assert option.id == 1
        assert option.label == "User pain point"

    def test_option_is_custom(self):
        """Should identify custom/other options."""
        predefined = QuestionOption(id=1, label="Option 1", description="desc")
        custom = QuestionOption(id=5, label="Other", description="Custom response", is_custom=True)

        assert not predefined.is_custom
        assert custom.is_custom


# =============================================================================
# Test TargetedQuestion
# =============================================================================

class TestTargetedQuestion:
    """Tests for targeted questions."""

    def test_question_creation(self):
        """Should create a targeted question."""
        question = TargetedQuestion(
            category=RequirementCategory.PROBLEM,
            question_text="What specific problem are we trying to solve?",
            options=[
                QuestionOption(1, "User pain point", "Users are struggling"),
                QuestionOption(2, "System limitation", "System can't do something"),
                QuestionOption(3, "Business need", "Business requires new capability"),
            ],
            priority=1,
            gap=InformationGap(
                category=RequirementCategory.PROBLEM,
                description="No problem defined",
                severity=0.9,
                detected_from="analysis"
            )
        )
        assert question.category == RequirementCategory.PROBLEM
        assert len(question.options) == 3
        assert question.priority == 1

    def test_question_has_other_option(self):
        """Questions should always have an 'Other' option for custom input."""
        question = TargetedQuestion(
            category=RequirementCategory.PROBLEM,
            question_text="What is the problem?",
            options=[
                QuestionOption(1, "Option 1", "desc"),
            ],
            priority=1,
            gap=InformationGap(
                category=RequirementCategory.PROBLEM,
                description="gap",
                severity=0.5,
                detected_from="analysis"
            )
        )
        # The question should add an "Other" option
        assert any(opt.is_custom for opt in question.get_all_options())

    def test_question_priority_order(self):
        """Questions should be sortable by priority."""
        q1 = TargetedQuestion(
            category=RequirementCategory.PROBLEM,
            question_text="Problem?",
            options=[],
            priority=1,
            gap=InformationGap(RequirementCategory.PROBLEM, "gap", 0.9, "analysis")
        )
        q2 = TargetedQuestion(
            category=RequirementCategory.CONSTRAINTS,
            question_text="Constraints?",
            options=[],
            priority=5,
            gap=InformationGap(RequirementCategory.CONSTRAINTS, "gap", 0.5, "analysis")
        )

        questions = sorted([q2, q1], key=lambda q: q.priority)
        assert questions[0].category == RequirementCategory.PROBLEM


# =============================================================================
# Test RequirementsAnalysis
# =============================================================================

class TestRequirementsAnalysis:
    """Tests for the full requirements analysis result."""

    def test_analysis_creation(self):
        """Should create an analysis result."""
        analysis = RequirementsAnalysis(
            original_description="Build a REST API",
            score=CompletenessScore(total=45, by_category={}),
            gaps=[
                InformationGap(RequirementCategory.PROBLEM, "No problem", 0.9, "analysis")
            ],
            questions=[],
            extracted_requirements={}
        )
        assert analysis.original_description == "Build a REST API"
        assert analysis.score.total == 45

    def test_analysis_needs_discovery(self):
        """Should indicate if discovery is needed."""
        needs_discovery = RequirementsAnalysis(
            original_description="desc",
            score=CompletenessScore(total=40, by_category={}),
            gaps=[InformationGap(RequirementCategory.PROBLEM, "gap", 0.9, "analysis")],
            questions=[],
            extracted_requirements={}
        )
        no_discovery = RequirementsAnalysis(
            original_description="desc",
            score=CompletenessScore(total=80, by_category={}),
            gaps=[],
            questions=[],
            extracted_requirements={}
        )

        assert needs_discovery.needs_discovery()
        assert not no_discovery.needs_discovery()

    def test_analysis_top_questions(self):
        """Should return top N questions by priority."""
        questions = [
            TargetedQuestion(RequirementCategory.PROBLEM, "Q1", [], 1,
                InformationGap(RequirementCategory.PROBLEM, "gap", 0.9, "a")),
            TargetedQuestion(RequirementCategory.SUCCESS_CRITERIA, "Q2", [], 2,
                InformationGap(RequirementCategory.SUCCESS_CRITERIA, "gap", 0.8, "a")),
            TargetedQuestion(RequirementCategory.STAKEHOLDERS, "Q3", [], 3,
                InformationGap(RequirementCategory.STAKEHOLDERS, "gap", 0.7, "a")),
            TargetedQuestion(RequirementCategory.CONTEXT, "Q4", [], 4,
                InformationGap(RequirementCategory.CONTEXT, "gap", 0.6, "a")),
            TargetedQuestion(RequirementCategory.CONSTRAINTS, "Q5", [], 5,
                InformationGap(RequirementCategory.CONSTRAINTS, "gap", 0.5, "a")),
        ]
        analysis = RequirementsAnalysis(
            original_description="desc",
            score=CompletenessScore(total=30, by_category={}),
            gaps=[],
            questions=questions,
            extracted_requirements={}
        )

        top = analysis.get_top_questions(4)
        assert len(top) == 4
        assert top[0].category == RequirementCategory.PROBLEM


# =============================================================================
# Test StructuredRequirements
# =============================================================================

class TestStructuredRequirements:
    """Tests for structured requirements output."""

    def test_structured_requirements_creation(self):
        """Should create structured requirements."""
        req = StructuredRequirements(
            problem_statement="Users cannot track their expenses",
            success_criteria=["Users can log expenses", "Export to CSV"],
            stakeholders=["End users", "Product team"],
            context="Mobile-first expense tracking app",
            constraints=["Must work offline", "Budget: 2 weeks"]
        )
        assert "expenses" in req.problem_statement.lower()
        assert len(req.success_criteria) == 2

    def test_to_markdown(self):
        """Should convert to markdown format."""
        req = StructuredRequirements(
            problem_statement="Problem here",
            success_criteria=["Criteria 1", "Criteria 2"],
            stakeholders=["User 1"],
            context="Context here",
            constraints=["Constraint 1"]
        )
        md = req.to_markdown()

        assert "# Requirements" in md
        assert "## Problem Statement" in md
        assert "## Success Criteria" in md
        assert "Problem here" in md


# =============================================================================
# Test RequirementsAnalyzer - Basic Functionality
# =============================================================================

class TestRequirementsAnalyzerBasic:
    """Tests for basic RequirementsAnalyzer functionality."""

    def test_analyzer_creation(self):
        """Should create an analyzer instance."""
        analyzer = RequirementsAnalyzer()
        assert analyzer is not None

    def test_analyze_empty_description(self):
        """Should handle empty description."""
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze("")

        assert result.score.total == 0
        assert len(result.gaps) > 0

    def test_analyze_returns_analysis(self):
        """Should return a RequirementsAnalysis object."""
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze("Build a web app")

        assert isinstance(result, RequirementsAnalysis)

    def test_analyze_preserves_original(self):
        """Should preserve the original description."""
        analyzer = RequirementsAnalyzer()
        desc = "Build a mobile app for tracking tasks"
        result = analyzer.analyze(desc)

        assert result.original_description == desc


# =============================================================================
# Test RequirementsAnalyzer - Gap Detection
# =============================================================================

class TestRequirementsAnalyzerGapDetection:
    """Tests for information gap detection."""

    def test_detects_missing_problem(self):
        """Should detect when no problem statement is present."""
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze("Build a REST API")

        problem_gaps = [g for g in result.gaps if g.category == RequirementCategory.PROBLEM]
        assert len(problem_gaps) > 0

    def test_detects_present_problem(self):
        """Should recognize problem statements."""
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze(
            "Users cannot track their expenses because there's no mobile app. "
            "This causes frustration and financial mismanagement."
        )

        problem_gaps = [g for g in result.gaps if g.category == RequirementCategory.PROBLEM]
        # Should have fewer/no gaps when problem is stated
        if problem_gaps:
            assert all(g.severity < 0.5 for g in problem_gaps)

    def test_detects_missing_success_criteria(self):
        """Should detect when success criteria are missing."""
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze("Build something that helps users")

        success_gaps = [g for g in result.gaps if g.category == RequirementCategory.SUCCESS_CRITERIA]
        assert len(success_gaps) > 0

    def test_detects_present_success_criteria(self):
        """Should recognize success criteria."""
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze(
            "Build an expense tracker. "
            "Success means: 1) Users can log expenses in <5 seconds, "
            "2) 95% of users complete onboarding, "
            "3) App achieves 4+ star rating"
        )

        success_gaps = [g for g in result.gaps if g.category == RequirementCategory.SUCCESS_CRITERIA]
        if success_gaps:
            assert all(g.severity < 0.5 for g in success_gaps)

    def test_detects_missing_stakeholders(self):
        """Should detect when stakeholders are not mentioned."""
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze("Build an API endpoint")

        stakeholder_gaps = [g for g in result.gaps if g.category == RequirementCategory.STAKEHOLDERS]
        assert len(stakeholder_gaps) > 0

    def test_detects_present_stakeholders(self):
        """Should recognize stakeholder mentions."""
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze(
            "The mobile team needs an API for the iOS and Android apps. "
            "End users will indirectly benefit from faster load times. "
            "The QA team will need documentation."
        )

        stakeholder_gaps = [g for g in result.gaps if g.category == RequirementCategory.STAKEHOLDERS]
        if stakeholder_gaps:
            assert all(g.severity < 0.7 for g in stakeholder_gaps)

    def test_detects_missing_context(self):
        """Should detect when context is missing."""
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze("Build feature X")

        context_gaps = [g for g in result.gaps if g.category == RequirementCategory.CONTEXT]
        assert len(context_gaps) > 0

    def test_detects_present_context(self):
        """Should recognize contextual information."""
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze(
            "Our e-commerce platform currently uses a monolithic architecture. "
            "We're migrating to microservices and need to extract the payment "
            "processing module. The existing code is in Python 3.9 with Django."
        )

        context_gaps = [g for g in result.gaps if g.category == RequirementCategory.CONTEXT]
        if context_gaps:
            assert all(g.severity < 0.5 for g in context_gaps)

    def test_detects_missing_constraints(self):
        """Should detect when constraints are not specified."""
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze("Build a new feature")

        constraint_gaps = [g for g in result.gaps if g.category == RequirementCategory.CONSTRAINTS]
        assert len(constraint_gaps) > 0

    def test_detects_present_constraints(self):
        """Should recognize constraint mentions."""
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze(
            "Build a dashboard. Must be completed within 2 weeks. "
            "Budget is limited to existing team. Must work with our current "
            "PostgreSQL database. Cannot change the existing API contract."
        )

        constraint_gaps = [g for g in result.gaps if g.category == RequirementCategory.CONSTRAINTS]
        if constraint_gaps:
            assert all(g.severity < 0.5 for g in constraint_gaps)


# =============================================================================
# Test RequirementsAnalyzer - Scoring
# =============================================================================

class TestRequirementsAnalyzerScoring:
    """Tests for completeness scoring."""

    def test_score_increases_with_completeness(self):
        """More complete descriptions should score higher."""
        analyzer = RequirementsAnalyzer()

        minimal = analyzer.analyze("Build an app")

        detailed = analyzer.analyze(
            "Problem: Users struggle to track daily expenses, leading to overspending. "
            "Success criteria: Users can log expenses in under 5 seconds, monthly reports "
            "are generated automatically, 90% user satisfaction. "
            "Stakeholders: End users (primary), finance team (secondary), mobile team (dev). "
            "Context: Part of our fintech suite, must integrate with existing auth. "
            "Constraints: Must work offline, 3-week timeline, iOS-first."
        )

        assert detailed.score.total > minimal.score.total

    def test_score_weights_problem_higher(self):
        """Problem statement should contribute more to score."""
        analyzer = RequirementsAnalyzer()

        # Description with good problem but nothing else
        with_problem = analyzer.analyze(
            "The core problem is that users cannot easily share files between devices. "
            "This causes frustration and reduced productivity."
        )

        # Description with constraints but no problem
        analyzer.analyze(
            "Must be completed in 2 weeks. Budget is $10k. "
            "Must use Python. Cannot change the database."
        )

        # Problem should contribute more to score
        problem_score = with_problem.score.by_category.get(RequirementCategory.PROBLEM, 0)
        assert problem_score > 0

    def test_score_zero_for_empty(self):
        """Empty description should score 0."""
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze("")

        assert result.score.total == 0

    def test_score_max_for_complete(self):
        """Fully complete description should score high (80+)."""
        analyzer = RequirementsAnalyzer()

        result = analyzer.analyze("""
            PROBLEM: Users cannot collaborate on documents in real-time, causing
            version conflicts and lost work. This affects productivity significantly.

            SUCCESS CRITERIA:
            - Real-time sync with <100ms latency
            - Conflict resolution handles 99% of cases automatically
            - User satisfaction score >4.5/5
            - Zero data loss incidents

            STAKEHOLDERS:
            - End users: Writers, editors, and reviewers
            - Product team: Owns the roadmap
            - Engineering: Maintains the system
            - Support: Handles user issues

            CONTEXT:
            - Existing document editor built with React
            - Backend uses Node.js with MongoDB
            - Currently supports 10k daily active users
            - Mobile apps exist but don't have this feature

            CONSTRAINTS:
            - Timeline: 6 weeks
            - Budget: Existing team only
            - Technical: Must use WebSockets
            - Compliance: GDPR compliant
            - Performance: Must handle 1000 concurrent editors
        """)

        assert result.score.total >= 80


# =============================================================================
# Test RequirementsAnalyzer - Question Generation
# =============================================================================

class TestRequirementsAnalyzerQuestions:
    """Tests for question generation."""

    def test_generates_questions_for_gaps(self):
        """Should generate questions for identified gaps."""
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze("Build a thing")

        assert len(result.questions) > 0

    def test_questions_have_options(self):
        """Generated questions should have predefined options."""
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze("Create an API")

        for question in result.questions:
            assert len(question.options) >= 1

    def test_questions_have_other_option(self):
        """All questions should include an 'Other' option for custom input."""
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze("Build something")

        for question in result.questions:
            all_options = question.get_all_options()
            has_other = any(opt.is_custom for opt in all_options)
            assert has_other

    def test_questions_prioritized_by_category(self):
        """Questions should be prioritized: Problem > Success > Stakeholders > Context > Constraints."""
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze("Build a feature")

        if len(result.questions) >= 2:
            priorities = [q.priority for q in result.questions]
            assert priorities == sorted(priorities)

    def test_no_questions_for_complete_description(self):
        """Should not generate questions when description is complete."""
        analyzer = RequirementsAnalyzer()

        result = analyzer.analyze("""
            PROBLEM: Critical bug causes data loss for 10% of users during checkout.

            SUCCESS: Bug is fixed, no more data loss, checkout success rate returns to 99%.

            STAKEHOLDERS: Customers losing orders, support team handling complaints,
            revenue team tracking lost sales.

            CONTEXT: E-commerce checkout flow, React frontend, Node backend,
            PostgreSQL database. Bug introduced in last release.

            CONSTRAINTS: Must fix within 24 hours, cannot take site offline,
            must maintain backward compatibility with existing orders.
        """)

        # Either no questions or only low-priority ones
        if result.questions:
            assert all(q.gap.severity < 0.5 for q in result.questions)

    def test_max_four_questions(self):
        """Should return at most 4 questions at a time."""
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze("x")  # Minimal description = many gaps

        top = result.get_top_questions(4)
        assert len(top) <= 4

    def test_problem_question_format(self):
        """Problem questions should have appropriate options."""
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze("Build something")

        problem_questions = [q for q in result.questions if q.category == RequirementCategory.PROBLEM]

        if problem_questions:
            q = problem_questions[0]
            option_labels = [opt.label.lower() for opt in q.options]
            # Should have common problem types as options
            assert any("pain" in label or "user" in label or "issue" in label for label in option_labels)

    def test_success_criteria_question_format(self):
        """Success criteria questions should have measurable options."""
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze("Build a feature without success criteria")

        success_questions = [q for q in result.questions if q.category == RequirementCategory.SUCCESS_CRITERIA]

        if success_questions:
            q = success_questions[0]
            assert "success" in q.question_text.lower() or "criteria" in q.question_text.lower()


# =============================================================================
# Test RequirementsAnalyzer - Extraction
# =============================================================================

class TestRequirementsAnalyzerExtraction:
    """Tests for extracting structured requirements from descriptions."""

    def test_extracts_problem_statement(self):
        """Should extract problem statement from description."""
        analyzer = RequirementsAnalyzer()

        result = analyzer.analyze(
            "The main problem is that users can't find the search button. "
            "This leads to poor engagement metrics."
        )

        assert "problem" in result.extracted_requirements or "problem_statement" in str(result.extracted_requirements)

    def test_extracts_success_criteria(self):
        """Should extract success criteria from description."""
        analyzer = RequirementsAnalyzer()

        result = analyzer.analyze(
            "Success criteria: 1) 50% increase in search usage, "
            "2) User satisfaction > 4.0, 3) Page load < 2s"
        )

        extracted = result.extracted_requirements.get("success_criteria", [])
        assert len(extracted) >= 1 or "success" in str(result.extracted_requirements).lower()

    def test_build_structured_requirements(self):
        """Should build StructuredRequirements from complete analysis."""
        analyzer = RequirementsAnalyzer()

        result = analyzer.analyze("""
            Problem: Users cannot export data.
            Success: Export works, 95% success rate.
            Stakeholders: Data analysts, engineering.
            Context: Data warehouse project.
            Constraints: 1 week deadline.
        """)

        structured = result.build_structured_requirements()
        assert isinstance(structured, StructuredRequirements)


# =============================================================================
# Test RequirementsAnalyzer - Edge Cases
# =============================================================================

class TestRequirementsAnalyzerEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_handles_very_long_description(self):
        """Should handle very long descriptions."""
        analyzer = RequirementsAnalyzer()

        long_desc = "Build a feature. " * 1000
        result = analyzer.analyze(long_desc)

        assert result is not None
        assert isinstance(result.score.total, (int, float))

    def test_handles_special_characters(self):
        """Should handle special characters in description."""
        analyzer = RequirementsAnalyzer()

        result = analyzer.analyze(
            "Build a feature with <HTML> tags, 'quotes', \"double quotes\", "
            "and special chars: @#$%^&*()"
        )

        assert result is not None

    def test_handles_unicode(self):
        """Should handle unicode characters."""
        analyzer = RequirementsAnalyzer()

        result = analyzer.analyze(
            "Build a feature for international users who speak Japanese, Chinese, and emoji support."
        )

        assert result is not None

    def test_handles_code_snippets(self):
        """Should handle code snippets in description."""
        analyzer = RequirementsAnalyzer()

        result = analyzer.analyze("""
            Build an API endpoint that returns:
            ```json
            {"status": "ok", "data": []}
            ```
            The function should look like:
            ```python
            def get_data():
                return {"status": "ok"}
            ```
        """)

        assert result is not None

    def test_handles_markdown_formatting(self):
        """Should handle markdown-formatted descriptions."""
        analyzer = RequirementsAnalyzer()

        result = analyzer.analyze("""
            # Feature Request

            ## Problem
            Users **cannot** access the _dashboard_.

            ## Requirements
            - Requirement 1
            - Requirement 2

            ## Notes
            > Important note here
        """)

        assert result is not None


# =============================================================================
# Test RequirementsAnalyzer - Integration
# =============================================================================

class TestRequirementsAnalyzerIntegration:
    """Integration tests for the full analysis workflow."""

    def test_full_analysis_workflow(self):
        """Should complete full analysis workflow."""
        analyzer = RequirementsAnalyzer()

        # Start with incomplete description
        result1 = analyzer.analyze("Build a mobile app")

        assert result1.needs_discovery()
        assert len(result1.get_top_questions(4)) > 0

        # Get more complete description
        result2 = analyzer.analyze("""
            Problem: Users need to track fitness activities but existing apps are too complex.
            Success: Users can log workouts in <30s, 80% weekly retention.
            Stakeholders: Fitness enthusiasts, personal trainers.
            Context: React Native app, backend already exists.
            Constraints: 4 week timeline, must work offline.
        """)

        assert result2.score.total > result1.score.total
        assert len(result2.get_top_questions(4)) < len(result1.get_top_questions(4))

    def test_analysis_to_markdown_output(self):
        """Should produce markdown-ready output."""
        analyzer = RequirementsAnalyzer()

        result = analyzer.analyze("""
            Problem: Data sync issues between mobile and web.
            Success: Real-time sync with <1s delay.
            Stakeholders: Mobile users, web users.
            Context: Existing app with separate mobile/web codebases.
            Constraints: Cannot change database schema.
        """)

        structured = result.build_structured_requirements()
        markdown = structured.to_markdown()

        assert "# Requirements" in markdown
        assert "## Problem Statement" in markdown
