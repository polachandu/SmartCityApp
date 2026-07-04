"""
Domain models for the SmartCityApp AI Maintainer.

This module contains all data models used throughout the AI maintainer bot.
All models are pure Python dataclasses with no external dependencies,
following Clean Architecture principles where domain models are at the core
and have zero knowledge of infrastructure concerns.

Models:
    - ReviewDecision: Enum for PR review outcomes
    - RuleSeverity: Enum for rule violation severity levels
    - EventType: Enum for GitHub event types handled by the bot
    - ReviewResult: Structured AI review output
    - IssueContext: GitHub issue data
    - PRContext: GitHub pull request data
    - AssignmentResult: Issue assignment attempt result
    - RuleViolation: Single rule engine finding
    - RuleEngineResult: Aggregated rule engine output
    - GitHubEvent: Parsed GitHub Actions event
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReviewDecision(Enum):
    """Possible outcomes of an AI-powered pull request review.

    The AI review engine returns one of these decisions after analyzing
    a pull request against the linked issue, coding standards, and
    deterministic rule engine results.
    """

    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    COMMENT = "COMMENT"


class RuleSeverity(Enum):
    """Severity levels for deterministic rule engine violations.

    Used by the rule engine to classify findings before AI review.
    ERROR-level violations block PR approval regardless of AI decision.
    """

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class EventType(Enum):
    """GitHub event types handled by the AI maintainer.

    Maps to GitHub Actions event names and actions. The event parser
    converts raw webhook payloads into typed GitHubEvent instances
    tagged with one of these types.
    """

    ISSUE_OPENED = "issue_opened"
    ISSUE_COMMENT = "issue_comment"
    PULL_REQUEST_OPENED = "pull_request_opened"
    PULL_REQUEST_SYNCHRONIZE = "pull_request_synchronize"
    REVIEW_SUBMITTED = "review_submitted"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ReviewResult:
    """Structured output from the AI review engine.

    Represents the AI's assessment of a pull request, including a
    decision (approve/request changes/comment), a human-readable
    summary, a numerical quality score, and specific comments.

    Attributes:
        decision: The review verdict.
        summary: Human-readable summary of the review.
        score: Quality score from 0 (worst) to 100 (best).
        comments: List of specific review comments or suggestions.
    """

    decision: ReviewDecision
    summary: str
    score: int
    comments: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReviewResult:
        """Create a ReviewResult from a dictionary (e.g., parsed AI JSON output).

        Args:
            data: Dictionary with keys matching ReviewResult fields.
                  The 'decision' value should be a string matching
                  a ReviewDecision enum member name.

        Returns:
            A new ReviewResult instance.

        Raises:
            KeyError: If required keys are missing from data.
            ValueError: If decision string doesn't match any ReviewDecision.
        """
        return cls(
            decision=ReviewDecision(data["decision"]),
            summary=data["summary"],
            score=int(data["score"]),
            comments=data.get("comments", []),
        )


@dataclass
class IssueContext:
    """Structured representation of a GitHub issue.

    Collects all relevant issue data needed by the assignment engine,
    review engine, and prompt builder. Populated by the GitHub client
    and event parser.

    Attributes:
        number: The issue number.
        title: Issue title.
        body: Issue body/description (may be empty).
        labels: List of label names attached to the issue.
        comments: List of comment dictionaries with 'user', 'body', 'created_at'.
        assignees: List of usernames currently assigned.
        author: Username of the issue creator.
        state: Issue state ('open' or 'closed').
        created_at: ISO 8601 timestamp of issue creation.
    """

    number: int
    title: str
    body: str = ""
    labels: list[str] = field(default_factory=list)
    comments: list[dict[str, Any]] = field(default_factory=list)
    assignees: list[str] = field(default_factory=list)
    author: str = ""
    state: str = "open"
    created_at: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IssueContext:
        """Create an IssueContext from a GitHub API issue response.

        Args:
            data: Dictionary from GitHub REST API issue endpoint.

        Returns:
            A new IssueContext instance with fields extracted from the API response.
        """
        return cls(
            number=data.get("number", 0),
            title=data.get("title", ""),
            body=data.get("body", "") or "",
            labels=[label["name"] for label in data.get("labels", [])],
            assignees=[user["login"] for user in data.get("assignees", [])],
            author=data.get("user", {}).get("login", ""),
            state=data.get("state", "open"),
            created_at=data.get("created_at", ""),
        )


@dataclass
class PRContext:
    """Structured representation of a GitHub pull request.

    Contains all data needed for AI-powered code review, including
    the diff, changed files, commit messages, and existing reviews.
    The review engine uses this alongside IssueContext to determine
    whether a PR correctly addresses its linked issue.

    Attributes:
        number: The PR number.
        title: PR title.
        body: PR description (may be empty).
        diff: Raw unified diff of all changes.
        files_changed: List of file change dicts with 'filename', 'status',
                       'additions', 'deletions', 'patch'.
        commits: List of commit dicts with 'sha', 'message'.
        reviews: List of existing review dicts with 'user', 'state', 'body'.
        author: Username of the PR creator.
        base_branch: Target branch (e.g., 'main').
        head_branch: Source branch (e.g., 'feature/add-search').
        linked_issue_number: Issue number this PR addresses (0 if none detected).
        labels: List of label names.
        state: PR state ('open', 'closed', 'merged').
        created_at: ISO 8601 timestamp of PR creation.
        mergeable: Whether GitHub reports the PR as mergeable (None if unknown).
    """

    number: int
    title: str
    body: str = ""
    diff: str = ""
    files_changed: list[dict[str, Any]] = field(default_factory=list)
    commits: list[dict[str, Any]] = field(default_factory=list)
    reviews: list[dict[str, Any]] = field(default_factory=list)
    author: str = ""
    base_branch: str = "main"
    head_branch: str = ""
    linked_issue_number: int = 0
    labels: list[str] = field(default_factory=list)
    state: str = "open"
    created_at: str = ""
    mergeable: bool | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PRContext:
        """Create a PRContext from a GitHub API pull request response.

        Note: This populates basic PR metadata. The diff, files_changed,
        commits, and reviews require separate API calls and should be
        set after construction by the context collector.

        Args:
            data: Dictionary from GitHub REST API pull request endpoint.

        Returns:
            A new PRContext instance with metadata fields populated.
        """
        return cls(
            number=data.get("number", 0),
            title=data.get("title", ""),
            body=data.get("body", "") or "",
            author=data.get("user", {}).get("login", ""),
            base_branch=data.get("base", {}).get("ref", "main"),
            head_branch=data.get("head", {}).get("ref", ""),
            labels=[label["name"] for label in data.get("labels", [])],
            state=data.get("state", "open"),
            created_at=data.get("created_at", ""),
            mergeable=data.get("mergeable"),
        )


@dataclass(frozen=True)
class AssignmentResult:
    """Result of an automatic issue assignment attempt.

    Returned by the assignment engine after evaluating whether a
    contributor can be assigned to an issue based on eligibility
    rules (issue state, existing assignees, user's open issue count).

    Attributes:
        success: Whether the assignment was successful.
        message: Human-readable message explaining the result.
        assignee: Username of the assigned user (empty if not assigned).
    """

    success: bool
    message: str
    assignee: str = ""


@dataclass(frozen=True)
class RuleViolation:
    """A single finding from the deterministic rule engine.

    Rule violations are generated before AI review and represent
    concrete, deterministic issues found in a pull request (e.g.,
    hardcoded passwords, TODO comments, merge conflicts).

    Attributes:
        severity: How critical this violation is.
        rule_name: Machine-readable rule identifier (e.g., 'hardcoded_secret').
        message: Human-readable description of the violation.
        file_path: Path to the file where the violation was found (empty if global).
        line_number: Line number of the violation (0 if not applicable).
    """

    severity: RuleSeverity
    rule_name: str
    message: str
    file_path: str = ""
    line_number: int = 0


@dataclass
class RuleEngineResult:
    """Aggregated output from the rule engine.

    Contains all violations found during deterministic analysis of a
    pull request. The 'passed' flag indicates whether any ERROR-level
    violations were found. This result is fed to the AI review engine
    as additional context for its review.

    Attributes:
        violations: List of all rule violations found.
        passed: True if no ERROR-level violations exist.
        summary: Human-readable summary of the rule engine run.
    """

    violations: list[RuleViolation] = field(default_factory=list)
    passed: bool = True
    summary: str = ""

    def add_violation(self, violation: RuleViolation) -> None:
        """Add a violation and update the passed flag.

        If the violation severity is ERROR, the passed flag is set to False.

        Args:
            violation: The rule violation to add.
        """
        self.violations.append(violation)
        if violation.severity == RuleSeverity.ERROR:
            self.passed = False

    @property
    def error_count(self) -> int:
        """Count of ERROR-level violations."""
        return sum(
            1 for v in self.violations if v.severity == RuleSeverity.ERROR
        )

    @property
    def warning_count(self) -> int:
        """Count of WARNING-level violations."""
        return sum(
            1 for v in self.violations if v.severity == RuleSeverity.WARNING
        )


@dataclass
class GitHubEvent:
    """Parsed GitHub Actions event.

    The event parser converts raw GitHub webhook/event payloads into
    this typed model. Downstream engines use the event_type to determine
    which workflow to execute, and the pre-parsed issue/pull_request
    context to avoid redundant API calls.

    Attributes:
        event_type: The classified type of this event.
        action: The GitHub event action (e.g., 'opened', 'created', 'synchronize').
        sender: Username of the user who triggered the event.
        repository: Full repository name in 'owner/repo' format.
        payload: The raw event payload dictionary (preserved for edge cases).
        issue: Parsed issue context (None if event is not issue-related).
        pull_request: Parsed PR context (None if event is not PR-related).
        comment_body: The comment text (for issue_comment events, empty otherwise).
    """

    event_type: EventType
    action: str
    sender: str
    repository: str
    payload: dict[str, Any] = field(default_factory=dict)
    issue: IssueContext | None = None
    pull_request: PRContext | None = None
    comment_body: str = ""
