"""
Unit tests for the domain models module.

Tests that all dataclasses instantiate correctly, enums resolve properly,
from_dict() factory methods parse API responses, and computed properties
work as expected.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add the .github directory to sys.path so we can import the ai package
_REPO_ROOT = Path(__file__).resolve().parent.parent
_GITHUB_DIR = _REPO_ROOT / ".github"
if str(_GITHUB_DIR) not in sys.path:
    sys.path.insert(0, str(_GITHUB_DIR))

from ai.models import (
    AssignmentResult,
    EventType,
    GitHubEvent,
    IssueContext,
    PRContext,
    ReviewDecision,
    ReviewResult,
    RuleEngineResult,
    RuleSeverity,
    RuleViolation,
)


# ---------------------------------------------------------------------------
# Enum Tests
# ---------------------------------------------------------------------------

class TestReviewDecision:
    """Tests for the ReviewDecision enum."""

    def test_approve_value(self) -> None:
        """APPROVE enum has the correct string value."""
        assert ReviewDecision.APPROVE.value == "APPROVE"

    def test_request_changes_value(self) -> None:
        """REQUEST_CHANGES enum has the correct string value."""
        assert ReviewDecision.REQUEST_CHANGES.value == "REQUEST_CHANGES"

    def test_comment_value(self) -> None:
        """COMMENT enum has the correct string value."""
        assert ReviewDecision.COMMENT.value == "COMMENT"

    def test_from_string(self) -> None:
        """Enum can be created from string value."""
        assert ReviewDecision("APPROVE") == ReviewDecision.APPROVE


class TestRuleSeverity:
    """Tests for the RuleSeverity enum."""

    def test_all_values(self) -> None:
        """All severity levels exist."""
        assert RuleSeverity.ERROR.value == "ERROR"
        assert RuleSeverity.WARNING.value == "WARNING"
        assert RuleSeverity.INFO.value == "INFO"


class TestEventType:
    """Tests for the EventType enum."""

    def test_all_event_types(self) -> None:
        """All expected event types exist."""
        expected = {
            "issue_opened",
            "issue_comment",
            "pull_request_opened",
            "pull_request_synchronize",
            "review_submitted",
            "unknown",
        }
        actual = {e.value for e in EventType}
        assert actual == expected


# ---------------------------------------------------------------------------
# Dataclass Tests
# ---------------------------------------------------------------------------

class TestReviewResult:
    """Tests for the ReviewResult dataclass."""

    def test_construction(self) -> None:
        """ReviewResult can be constructed with required fields."""
        result = ReviewResult(
            decision=ReviewDecision.APPROVE,
            summary="Looks good!",
            score=95,
        )
        assert result.decision == ReviewDecision.APPROVE
        assert result.summary == "Looks good!"
        assert result.score == 95
        assert result.comments == []

    def test_with_comments(self) -> None:
        """ReviewResult can include review comments."""
        result = ReviewResult(
            decision=ReviewDecision.REQUEST_CHANGES,
            summary="Issues found",
            score=60,
            comments=["Fix SQL injection", "Add Javadoc"],
        )
        assert len(result.comments) == 2

    def test_from_dict(self) -> None:
        """ReviewResult.from_dict() parses a valid dictionary."""
        data = {
            "decision": "APPROVE",
            "summary": "All good",
            "score": 90,
            "comments": ["Nice work"],
        }
        result = ReviewResult.from_dict(data)
        assert result.decision == ReviewDecision.APPROVE
        assert result.score == 90
        assert result.comments == ["Nice work"]

    def test_from_dict_missing_comments(self) -> None:
        """from_dict() defaults comments to empty list if missing."""
        data = {"decision": "COMMENT", "summary": "FYI", "score": 75}
        result = ReviewResult.from_dict(data)
        assert result.comments == []

    def test_frozen(self) -> None:
        """ReviewResult is immutable (frozen dataclass)."""
        result = ReviewResult(
            decision=ReviewDecision.APPROVE,
            summary="OK",
            score=100,
        )
        with pytest.raises(AttributeError):
            result.score = 50  # type: ignore[misc]


class TestIssueContext:
    """Tests for the IssueContext dataclass."""

    def test_default_values(self) -> None:
        """IssueContext has sensible defaults."""
        issue = IssueContext(number=1, title="Bug")
        assert issue.body == ""
        assert issue.labels == []
        assert issue.assignees == []
        assert issue.state == "open"

    def test_from_dict_github_api(self) -> None:
        """from_dict() correctly parses a GitHub API response."""
        api_response = {
            "number": 42,
            "title": "Fix login bug",
            "body": "Login fails when...",
            "labels": [{"name": "bug"}, {"name": "good first issue"}],
            "assignees": [{"login": "contributor1"}],
            "user": {"login": "reporter"},
            "state": "open",
            "created_at": "2026-07-01T10:00:00Z",
        }
        issue = IssueContext.from_dict(api_response)
        assert issue.number == 42
        assert issue.title == "Fix login bug"
        assert issue.labels == ["bug", "good first issue"]
        assert issue.assignees == ["contributor1"]
        assert issue.author == "reporter"

    def test_from_dict_null_body(self) -> None:
        """from_dict() handles null body gracefully."""
        data = {"number": 1, "title": "Test", "body": None}
        issue = IssueContext.from_dict(data)
        assert issue.body == ""


class TestPRContext:
    """Tests for the PRContext dataclass."""

    def test_default_values(self) -> None:
        """PRContext has sensible defaults."""
        pr = PRContext(number=10, title="Add feature")
        assert pr.diff == ""
        assert pr.files_changed == []
        assert pr.base_branch == "main"
        assert pr.linked_issue_number == 0

    def test_from_dict_github_api(self) -> None:
        """from_dict() correctly parses a GitHub API PR response."""
        api_response = {
            "number": 15,
            "title": "Fix NPE in login",
            "body": "Closes #42\nAdds null check.",
            "user": {"login": "contributor"},
            "base": {"ref": "main"},
            "head": {"ref": "fix/login-npe"},
            "labels": [{"name": "bug"}],
            "state": "open",
            "created_at": "2026-07-01T12:00:00Z",
            "mergeable": True,
        }
        pr = PRContext.from_dict(api_response)
        assert pr.number == 15
        assert pr.author == "contributor"
        assert pr.base_branch == "main"
        assert pr.head_branch == "fix/login-npe"
        assert pr.mergeable is True


class TestAssignmentResult:
    """Tests for the AssignmentResult dataclass."""

    def test_successful_assignment(self) -> None:
        """AssignmentResult for a successful assignment."""
        result = AssignmentResult(
            success=True,
            message="Assigned successfully!",
            assignee="contributor1",
        )
        assert result.success is True
        assert result.assignee == "contributor1"

    def test_failed_assignment(self) -> None:
        """AssignmentResult for a failed assignment."""
        result = AssignmentResult(
            success=False,
            message="Issue already has an assignee.",
        )
        assert result.success is False
        assert result.assignee == ""

    def test_frozen(self) -> None:
        """AssignmentResult is immutable (frozen dataclass)."""
        result = AssignmentResult(success=True, message="OK")
        with pytest.raises(AttributeError):
            result.success = False  # type: ignore[misc]


class TestRuleViolation:
    """Tests for the RuleViolation dataclass."""

    def test_construction(self) -> None:
        """RuleViolation can be constructed with required fields."""
        violation = RuleViolation(
            severity=RuleSeverity.ERROR,
            rule_name="hardcoded_secret",
            message="Hardcoded password found",
            file_path="src/DBConnection.java",
            line_number=42,
        )
        assert violation.severity == RuleSeverity.ERROR
        assert violation.file_path == "src/DBConnection.java"

    def test_default_file_and_line(self) -> None:
        """RuleViolation defaults file_path and line_number."""
        violation = RuleViolation(
            severity=RuleSeverity.WARNING,
            rule_name="large_pr",
            message="PR is too large",
        )
        assert violation.file_path == ""
        assert violation.line_number == 0


class TestRuleEngineResult:
    """Tests for the RuleEngineResult dataclass."""

    def test_empty_result_passes(self) -> None:
        """An empty result passes by default."""
        result = RuleEngineResult()
        assert result.passed is True
        assert result.error_count == 0
        assert result.warning_count == 0

    def test_add_error_fails(self) -> None:
        """Adding an ERROR violation sets passed to False."""
        result = RuleEngineResult()
        result.add_violation(
            RuleViolation(
                severity=RuleSeverity.ERROR,
                rule_name="test",
                message="Error found",
            )
        )
        assert result.passed is False
        assert result.error_count == 1

    def test_add_warning_still_passes(self) -> None:
        """Adding a WARNING violation does not fail the result."""
        result = RuleEngineResult()
        result.add_violation(
            RuleViolation(
                severity=RuleSeverity.WARNING,
                rule_name="test",
                message="Warning found",
            )
        )
        assert result.passed is True
        assert result.warning_count == 1

    def test_mixed_violations(self) -> None:
        """Result correctly counts mixed severity violations."""
        result = RuleEngineResult()
        result.add_violation(
            RuleViolation(RuleSeverity.ERROR, "r1", "err1")
        )
        result.add_violation(
            RuleViolation(RuleSeverity.WARNING, "r2", "warn1")
        )
        result.add_violation(
            RuleViolation(RuleSeverity.INFO, "r3", "info1")
        )
        assert result.error_count == 1
        assert result.warning_count == 1
        assert len(result.violations) == 3
        assert result.passed is False


class TestGitHubEvent:
    """Tests for the GitHubEvent dataclass."""

    def test_default_values(self) -> None:
        """GitHubEvent has sensible defaults."""
        event = GitHubEvent(
            event_type=EventType.ISSUE_OPENED,
            action="opened",
            sender="user1",
            repository="owner/repo",
        )
        assert event.issue is None
        assert event.pull_request is None
        assert event.comment_body == ""
        assert event.payload == {}

    def test_with_issue(self) -> None:
        """GitHubEvent can include an IssueContext."""
        issue = IssueContext(number=5, title="Test issue")
        event = GitHubEvent(
            event_type=EventType.ISSUE_OPENED,
            action="opened",
            sender="user1",
            repository="owner/repo",
            issue=issue,
        )
        assert event.issue is not None
        assert event.issue.number == 5
