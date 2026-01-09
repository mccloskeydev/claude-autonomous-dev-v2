"""Requirements analysis and discovery phase.

This module provides intelligent requirements analysis for autonomous development
sessions. It includes:

- Task description analysis for completeness
- Information gap detection
- Completeness scoring (0-100 scale)
- Targeted question generation to fill gaps
- Question prioritization by importance
- Structured requirements output
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RequirementCategory(Enum):
    """Categories of requirements information.

    Values represent priority (lower = higher priority).
    Order: Problem > Success Criteria > Stakeholders > Context > Constraints
    """

    PROBLEM = 1
    SUCCESS_CRITERIA = 2
    STAKEHOLDERS = 3
    CONTEXT = 4
    CONSTRAINTS = 5


@dataclass
class InformationGap:
    """Represents a gap in requirements information.

    Attributes:
        category: The category of the missing information
        description: Human-readable description of what's missing
        severity: How critical this gap is (0.0-1.0, higher = more severe)
        detected_from: What triggered the gap detection
    """

    category: RequirementCategory
    description: str
    severity: float
    detected_from: str

    def __post_init__(self) -> None:
        """Validate severity is in range."""
        self.severity = max(0.0, min(1.0, self.severity))


@dataclass
class CompletenessScore:
    """Score indicating how complete a requirements description is.

    Attributes:
        total: Overall completeness score (0-100)
        by_category: Breakdown of scores by category
    """

    total: int
    by_category: dict[RequirementCategory, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate total is in range."""
        self.total = max(0, min(100, self.total))

    def can_proceed(self, threshold: int = 60) -> bool:
        """Check if the score is high enough to proceed without questions.

        Args:
            threshold: Minimum score to proceed (default 60)

        Returns:
            True if total score >= threshold
        """
        return self.total >= threshold


@dataclass
class QuestionOption:
    """A predefined option for answering a question.

    Attributes:
        id: Unique identifier for the option (1-based)
        label: Short label for the option
        description: Longer description shown to user
        is_custom: Whether this is the "Other" option for custom input
    """

    id: int
    label: str
    description: str
    is_custom: bool = False


@dataclass
class TargetedQuestion:
    """A question designed to fill an information gap.

    Attributes:
        category: The requirement category this addresses
        question_text: The main question text
        options: Predefined answer options
        priority: Lower number = higher priority
        gap: The information gap this question addresses
    """

    category: RequirementCategory
    question_text: str
    options: list[QuestionOption]
    priority: int
    gap: InformationGap

    def get_all_options(self) -> list[QuestionOption]:
        """Get all options including the 'Other' option.

        Returns:
            List of options, with 'Other' appended if not present
        """
        if any(opt.is_custom for opt in self.options):
            return self.options

        # Add "Other" option
        other_id = max((opt.id for opt in self.options), default=0) + 1
        other_option = QuestionOption(
            id=other_id,
            label="Other",
            description="Provide a custom response",
            is_custom=True
        )
        return self.options + [other_option]


@dataclass
class StructuredRequirements:
    """Structured output of requirements analysis.

    Attributes:
        problem_statement: The core problem being solved
        success_criteria: List of measurable success criteria
        stakeholders: List of affected stakeholders
        context: Background and contextual information
        constraints: List of constraints and limitations
    """

    problem_statement: str = ""
    success_criteria: list[str] = field(default_factory=list)
    stakeholders: list[str] = field(default_factory=list)
    context: str = ""
    constraints: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Convert to markdown format for specs/requirements.md.

        Returns:
            Markdown-formatted requirements document
        """
        lines = ["# Requirements", ""]

        lines.append("## Problem Statement")
        lines.append(self.problem_statement or "*Not specified*")
        lines.append("")

        lines.append("## Success Criteria")
        if self.success_criteria:
            for criterion in self.success_criteria:
                lines.append(f"- {criterion}")
        else:
            lines.append("*Not specified*")
        lines.append("")

        lines.append("## Stakeholders")
        if self.stakeholders:
            for stakeholder in self.stakeholders:
                lines.append(f"- {stakeholder}")
        else:
            lines.append("*Not specified*")
        lines.append("")

        lines.append("## Context")
        lines.append(self.context or "*Not specified*")
        lines.append("")

        lines.append("## Constraints")
        if self.constraints:
            for constraint in self.constraints:
                lines.append(f"- {constraint}")
        else:
            lines.append("*Not specified*")
        lines.append("")

        return "\n".join(lines)


@dataclass
class RequirementsAnalysis:
    """Result of analyzing a task description for requirements completeness.

    Attributes:
        original_description: The input description that was analyzed
        score: Completeness score
        gaps: List of identified information gaps
        questions: Generated questions to fill gaps
        extracted_requirements: Requirements extracted from the description
    """

    original_description: str
    score: CompletenessScore
    gaps: list[InformationGap]
    questions: list[TargetedQuestion]
    extracted_requirements: dict[str, Any]

    def needs_discovery(self) -> bool:
        """Check if discovery phase is needed (questions should be asked).

        Returns:
            True if score is below threshold and gaps exist
        """
        return not self.score.can_proceed() and len(self.gaps) > 0

    def get_top_questions(self, n: int = 4) -> list[TargetedQuestion]:
        """Get the top N highest-priority questions.

        Args:
            n: Maximum number of questions to return

        Returns:
            List of questions sorted by priority
        """
        sorted_questions = sorted(self.questions, key=lambda q: q.priority)
        return sorted_questions[:n]

    def build_structured_requirements(self) -> StructuredRequirements:
        """Build structured requirements from extracted data.

        Returns:
            StructuredRequirements object
        """
        return StructuredRequirements(
            problem_statement=self.extracted_requirements.get("problem_statement", ""),
            success_criteria=self.extracted_requirements.get("success_criteria", []),
            stakeholders=self.extracted_requirements.get("stakeholders", []),
            context=self.extracted_requirements.get("context", ""),
            constraints=self.extracted_requirements.get("constraints", [])
        )


# Pattern definitions for detecting requirements elements
PROBLEM_PATTERNS = [
    re.compile(r"problem[:\s]", re.IGNORECASE),
    re.compile(r"^PROBLEM:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"issue[:\s]", re.IGNORECASE),
    re.compile(r"challenge[:\s]", re.IGNORECASE),
    re.compile(r"users?\s+(cannot|can't|struggle|have trouble|are unable)", re.IGNORECASE),
    re.compile(r"(causes?|leads?\s+to|results?\s+in)\s+(frustration|problems?|issues?)", re.IGNORECASE),
    re.compile(r"pain\s+point", re.IGNORECASE),
    re.compile(r"the\s+(main|core|primary)\s+(problem|issue)", re.IGNORECASE),
    re.compile(r"(critical|major|significant)\s+(bug|issue|problem)", re.IGNORECASE),
    re.compile(r"(conflicts?|lost\s+work|productivity)", re.IGNORECASE),
    re.compile(r"affects?\s+(productivity|performance|users?)", re.IGNORECASE),
]

SUCCESS_PATTERNS = [
    re.compile(r"success(\s+criteria)?[:\s]", re.IGNORECASE),
    re.compile(r"^SUCCESS(\s+CRITERIA)?:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"success\s+means?", re.IGNORECASE),
    re.compile(r"(goal|objective)[:\s]", re.IGNORECASE),
    re.compile(r"(measure|metric|kpi)[:\s]", re.IGNORECASE),
    re.compile(r"\d+%\s+(of\s+users?|success|increase|decrease|improvement)", re.IGNORECASE),
    re.compile(r"(>|<|>=|<=)\s*\d+", re.IGNORECASE),
    re.compile(r"(rating|score)\s*(>|of)\s*[\d.]+", re.IGNORECASE),
    re.compile(r"(achieve|reach|hit)\s+\d+", re.IGNORECASE),
    re.compile(r"\d+%\s+of\s+cases?", re.IGNORECASE),
    re.compile(r"zero\s+(data\s+loss|downtime|errors?)", re.IGNORECASE),
    re.compile(r"latency", re.IGNORECASE),
    re.compile(r"satisfaction", re.IGNORECASE),
]

STAKEHOLDER_PATTERNS = [
    re.compile(r"stakeholder[s]?[:\s]", re.IGNORECASE),
    re.compile(r"^STAKEHOLDERS?:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"(end\s+)?user[s]?[:\s]", re.IGNORECASE),
    re.compile(r"(customer|client)[s]?", re.IGNORECASE),
    re.compile(r"team[:\s]", re.IGNORECASE),
    re.compile(r"(developer|engineer|designer|product|qa|support)[s]?[:\s]", re.IGNORECASE),
    re.compile(r"(primary|secondary)\s+(user|audience|stakeholder)", re.IGNORECASE),
    re.compile(r"(mobile|web|ios|android|frontend|backend)\s+team", re.IGNORECASE),
    re.compile(r"(affect|impact)[s]?\s+(users?|customers?|team)", re.IGNORECASE),
    re.compile(r"(writer|editor|reviewer)[s]?", re.IGNORECASE),
    re.compile(r"(engineering|support)[:\s]", re.IGNORECASE),
    re.compile(r"owns?\s+(the\s+)?roadmap", re.IGNORECASE),
]

CONTEXT_PATTERNS = [
    re.compile(r"context[:\s]", re.IGNORECASE),
    re.compile(r"^CONTEXT:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"background[:\s]", re.IGNORECASE),
    re.compile(r"(currently|existing|current)\s+(use|system|architecture|code|document|editor)", re.IGNORECASE),
    re.compile(r"(built\s+with|using|based\s+on|uses?)\s+(react|vue|angular|python|node|django|mongodb)", re.IGNORECASE),
    re.compile(r"(migrate|migrating|migration)", re.IGNORECASE),
    re.compile(r"(monolith|microservice|api|database)", re.IGNORECASE),
    re.compile(r"(introduced|added|changed)\s+in\s+(last|recent|previous)", re.IGNORECASE),
    re.compile(r"(part\s+of|integrated?\s+with)", re.IGNORECASE),
    re.compile(r"daily\s+active\s+users?", re.IGNORECASE),
    re.compile(r"mobile\s+apps?\s+exist", re.IGNORECASE),
    re.compile(r"backend\s+uses?", re.IGNORECASE),
]

CONSTRAINT_PATTERNS = [
    re.compile(r"constraint[s]?[:\s]", re.IGNORECASE),
    re.compile(r"^CONSTRAINTS?:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"limitation[s]?[:\s]", re.IGNORECASE),
    re.compile(r"(must|cannot|can't|should\s+not|won't|will\s+not)", re.IGNORECASE),
    re.compile(r"(timeline|deadline|due\s+date)[:\s]", re.IGNORECASE),
    re.compile(r"\d+\s*(week|day|hour|month)[s]?(\s+timeline)?", re.IGNORECASE),
    re.compile(r"budget[:\s]", re.IGNORECASE),
    re.compile(r"(limited|restrict|within)\s+(time|budget|scope|team)", re.IGNORECASE),
    re.compile(r"(compliance|gdpr|hipaa|security)", re.IGNORECASE),
    re.compile(r"(backward\s+)?compat", re.IGNORECASE),
]

# Question templates for each category
QUESTION_TEMPLATES: dict[RequirementCategory, dict[str, Any]] = {
    RequirementCategory.PROBLEM: {
        "text": "What specific problem are we trying to solve?",
        "options": [
            QuestionOption(1, "User pain point", "Users are struggling with something specific"),
            QuestionOption(2, "System limitation", "The system can't do something it needs to"),
            QuestionOption(3, "Business need", "Business requires new capability"),
            QuestionOption(4, "Technical issue", "Performance, security, or reliability problem"),
        ]
    },
    RequirementCategory.SUCCESS_CRITERIA: {
        "text": "What does success look like for this task?",
        "options": [
            QuestionOption(1, "Measurable metric", "Specific number to achieve (e.g., 95% uptime)"),
            QuestionOption(2, "User outcome", "Users can do something they couldn't before"),
            QuestionOption(3, "Business outcome", "Revenue, conversion, or engagement target"),
            QuestionOption(4, "Technical outcome", "Performance, reliability, or quality target"),
        ]
    },
    RequirementCategory.STAKEHOLDERS: {
        "text": "Who is affected by this change?",
        "options": [
            QuestionOption(1, "End users", "People using the product directly"),
            QuestionOption(2, "Internal teams", "Engineering, product, support, etc."),
            QuestionOption(3, "Business stakeholders", "Leadership, sales, marketing"),
            QuestionOption(4, "External partners", "API consumers, integrators"),
        ]
    },
    RequirementCategory.CONTEXT: {
        "text": "What is the context for this task?",
        "options": [
            QuestionOption(1, "New feature", "Building something from scratch"),
            QuestionOption(2, "Enhancement", "Improving existing functionality"),
            QuestionOption(3, "Bug fix", "Fixing broken functionality"),
            QuestionOption(4, "Refactor", "Improving code without changing behavior"),
        ]
    },
    RequirementCategory.CONSTRAINTS: {
        "text": "What constraints should we be aware of?",
        "options": [
            QuestionOption(1, "Time constraint", "Specific deadline or timeline"),
            QuestionOption(2, "Technical constraint", "Must use specific technology or approach"),
            QuestionOption(3, "Resource constraint", "Limited budget or team size"),
            QuestionOption(4, "Compatibility constraint", "Must work with existing systems"),
        ]
    },
}

# Category weights for scoring (must sum to 100)
CATEGORY_WEIGHTS: dict[RequirementCategory, int] = {
    RequirementCategory.PROBLEM: 30,
    RequirementCategory.SUCCESS_CRITERIA: 25,
    RequirementCategory.STAKEHOLDERS: 15,
    RequirementCategory.CONTEXT: 15,
    RequirementCategory.CONSTRAINTS: 15,
}


class RequirementsAnalyzer:
    """Analyzes task descriptions for requirements completeness.

    This class provides intelligent analysis of task descriptions to:
    - Detect information gaps
    - Score completeness (0-100)
    - Generate targeted questions to fill gaps
    - Extract structured requirements

    Example:
        analyzer = RequirementsAnalyzer()
        result = analyzer.analyze("Build a mobile app")

        if result.needs_discovery():
            questions = result.get_top_questions(4)
            # Ask questions to fill gaps

        structured = result.build_structured_requirements()
        print(structured.to_markdown())
    """

    def __init__(self) -> None:
        """Initialize the requirements analyzer."""
        self._patterns: dict[RequirementCategory, list[re.Pattern]] = {
            RequirementCategory.PROBLEM: PROBLEM_PATTERNS,
            RequirementCategory.SUCCESS_CRITERIA: SUCCESS_PATTERNS,
            RequirementCategory.STAKEHOLDERS: STAKEHOLDER_PATTERNS,
            RequirementCategory.CONTEXT: CONTEXT_PATTERNS,
            RequirementCategory.CONSTRAINTS: CONSTRAINT_PATTERNS,
        }

    def analyze(self, description: str) -> RequirementsAnalysis:
        """Analyze a task description for requirements completeness.

        Args:
            description: The task description to analyze

        Returns:
            RequirementsAnalysis with score, gaps, questions, and extracted requirements
        """
        if not description or not description.strip():
            return self._empty_analysis(description)

        # Detect presence of each category
        category_presence = self._detect_category_presence(description)

        # Calculate scores
        score = self._calculate_score(category_presence)

        # Detect gaps
        gaps = self._detect_gaps(category_presence, description)

        # Generate questions for gaps
        questions = self._generate_questions(gaps)

        # Extract requirements
        extracted = self._extract_requirements(description, category_presence)

        return RequirementsAnalysis(
            original_description=description,
            score=score,
            gaps=gaps,
            questions=questions,
            extracted_requirements=extracted
        )

    def _empty_analysis(self, description: str) -> RequirementsAnalysis:
        """Create analysis result for empty description.

        Args:
            description: The (empty) description

        Returns:
            RequirementsAnalysis with zero score and all gaps
        """
        gaps = [
            InformationGap(
                category=cat,
                description=f"No {cat.name.lower().replace('_', ' ')} information provided",
                severity=1.0,
                detected_from="Empty description"
            )
            for cat in RequirementCategory
        ]

        questions = self._generate_questions(gaps)

        return RequirementsAnalysis(
            original_description=description,
            score=CompletenessScore(total=0, by_category={}),
            gaps=gaps,
            questions=questions,
            extracted_requirements={}
        )

    def _detect_category_presence(self, description: str) -> dict[RequirementCategory, float]:
        """Detect how well each category is represented in the description.

        Args:
            description: The task description

        Returns:
            Dict mapping each category to a presence score (0.0-1.0)
        """
        presence: dict[RequirementCategory, float] = {}

        for category, patterns in self._patterns.items():
            matches = 0
            for pattern in patterns:
                if pattern.search(description):
                    matches += 1

            # Calculate presence score based on pattern matches
            # 2 matches = 50%, 3+ matches = 75-100%
            # This scales better with varying pattern counts
            if matches == 0:
                presence[category] = 0.0
            elif matches == 1:
                presence[category] = 0.33
            elif matches == 2:
                presence[category] = 0.66
            else:
                # 3+ matches = 85% or higher, capped at 100%
                presence[category] = min(1.0, 0.85 + (matches - 3) * 0.05)

        return presence

    def _calculate_score(self, category_presence: dict[RequirementCategory, float]) -> CompletenessScore:
        """Calculate completeness score from category presence.

        Args:
            category_presence: Presence scores for each category

        Returns:
            CompletenessScore with total and breakdown
        """
        by_category: dict[RequirementCategory, int] = {}
        total = 0.0

        for category, presence in category_presence.items():
            weight = CATEGORY_WEIGHTS.get(category, 0)
            category_score = int(presence * 100)
            by_category[category] = category_score
            total += presence * weight

        return CompletenessScore(
            total=int(total),
            by_category=by_category
        )

    def _detect_gaps(
        self,
        category_presence: dict[RequirementCategory, float],
        description: str
    ) -> list[InformationGap]:
        """Detect information gaps based on category presence.

        Args:
            category_presence: Presence scores for each category
            description: Original description for context

        Returns:
            List of InformationGap objects
        """
        gaps: list[InformationGap] = []

        gap_descriptions: dict[RequirementCategory, str] = {
            RequirementCategory.PROBLEM: "No clear problem statement found",
            RequirementCategory.SUCCESS_CRITERIA: "No success criteria or metrics defined",
            RequirementCategory.STAKEHOLDERS: "No stakeholders or affected parties identified",
            RequirementCategory.CONTEXT: "Missing background or contextual information",
            RequirementCategory.CONSTRAINTS: "No constraints or limitations specified",
        }

        for category, presence in category_presence.items():
            # Create gap if presence is below threshold
            if presence < 0.5:
                severity = 1.0 - presence  # Lower presence = higher severity
                gaps.append(InformationGap(
                    category=category,
                    description=gap_descriptions.get(
                        category,
                        f"Missing {category.name.lower()} information"
                    ),
                    severity=severity,
                    detected_from=f"Pattern match score: {presence:.2f}"
                ))

        return gaps

    def _generate_questions(self, gaps: list[InformationGap]) -> list[TargetedQuestion]:
        """Generate targeted questions to fill identified gaps.

        Args:
            gaps: List of information gaps

        Returns:
            List of TargetedQuestion objects
        """
        questions: list[TargetedQuestion] = []

        for gap in gaps:
            template = QUESTION_TEMPLATES.get(gap.category)
            if not template:
                continue

            question = TargetedQuestion(
                category=gap.category,
                question_text=template["text"],
                options=list(template["options"]),  # Copy to avoid mutation
                priority=gap.category.value,  # Priority matches category order
                gap=gap
            )
            questions.append(question)

        # Sort by priority (category value)
        questions.sort(key=lambda q: q.priority)

        return questions

    def _extract_requirements(
        self,
        description: str,
        category_presence: dict[RequirementCategory, float]
    ) -> dict[str, Any]:
        """Extract structured requirements from description.

        Args:
            description: The task description
            category_presence: Presence scores for context

        Returns:
            Dict with extracted requirements by category
        """
        extracted: dict[str, Any] = {}

        # Extract problem statement
        problem_match = self._extract_section(description, [
            r"problem[:\s]+(.+?)(?=success|stakeholder|context|constraint|$)",
            r"the\s+(main|core|primary)\s+(problem|issue)\s+is\s+(.+?)(?=\.|success|$)",
            r"users?\s+(cannot|can't|struggle|are unable)\s+(.+?)(?=\.|this|$)",
        ])
        if problem_match:
            extracted["problem_statement"] = problem_match.strip()

        # Extract success criteria
        success_matches = self._extract_list_items(description, [
            r"success[:\s]+(.+?)(?=stakeholder|context|constraint|$)",
            r"success\s+means?[:\s]+(.+?)(?=stakeholder|context|constraint|$)",
            r"(\d+%\s+[^.]+)",
            r"(>|<|>=|<=)\s*\d+[^.]*",
        ])
        if success_matches:
            extracted["success_criteria"] = success_matches

        # Extract stakeholders
        stakeholder_matches = self._extract_list_items(description, [
            r"stakeholder[s]?[:\s]+(.+?)(?=context|constraint|$)",
            r"(end\s+users?|customers?|[a-z]+\s+team)[^.]*",
        ])
        if stakeholder_matches:
            extracted["stakeholders"] = stakeholder_matches

        # Extract context
        context_match = self._extract_section(description, [
            r"context[:\s]+(.+?)(?=constraint|$)",
            r"background[:\s]+(.+?)(?=constraint|$)",
            r"(currently|existing)[:\s]+(.+?)(?=\.|constraint|$)",
        ])
        if context_match:
            extracted["context"] = context_match.strip()

        # Extract constraints
        constraint_matches = self._extract_list_items(description, [
            r"constraint[s]?[:\s]+(.+?)(?=$)",
            r"(must|cannot|can't)\s+[^.]+",
            r"(\d+\s*(week|day|month)[s]?\s*(timeline|deadline)?)",
        ])
        if constraint_matches:
            extracted["constraints"] = constraint_matches

        return extracted

    def _extract_section(self, text: str, patterns: list[str]) -> str | None:
        """Extract a section of text matching any pattern.

        Args:
            text: Text to search
            patterns: List of regex patterns to try

        Returns:
            First matching group or None
        """
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                # Return the last group (most specific)
                groups = match.groups()
                if groups:
                    return groups[-1]

        return None

    def _extract_list_items(self, text: str, patterns: list[str]) -> list[str]:
        """Extract list items matching patterns.

        Args:
            text: Text to search
            patterns: List of regex patterns to try

        Returns:
            List of unique matched items
        """
        items: set[str] = set()

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Use ternary to extract item from tuple or string match
                item = (match[-1] if match[-1] else match[0]) if isinstance(match, tuple) else match
                item = item.strip()
                if item and len(item) > 3:  # Skip very short matches
                    items.add(item)

        return list(items)
