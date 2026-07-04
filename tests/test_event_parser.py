"""
Unit tests for the event parser module.

Tests parsing of GitHub Actions event payloads (issues, issue_comment,
pull_request, pull_request_review) into typed GitHubEvent models.
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

from ai.event_parser import EventParser
from ai.models import EventType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def parser() -> EventParser:
    """Create an EventParser instance."""
    return EventParser()


def _make_issue_payload(
    action: str = "opened",
    number: int = 42,
    title: str = "Fix login bug",
    body: str = "Login fails when...",
    sender: str = "contributor1",
) -> dict:
    """Create a mock GitHub issue event payload."""
    return {
        "action": action,
        "sender": {"login": sender},
        "repository": {"full_name": "TestOwner/TestRepo"},
        "issue": {
            "number": number,
            "title": title,
            "body": body,
            "labels": [{"name": "bug"}],
            "assignees": [],
            "user": {"login": sender},
            "state": "open",
            "created_at": "2026-07-01T10:00:00Z",
        },
    }


def _make_comment_payload(
    comment_body: str = "assign me",
    sender: str = "contributor1",
    issue_number: int = 42,
) -> dict:
    """Create a mock GitHub issue_comment event payload."""
    return {
        "action": "created",
        "sender": {"login": sender},
        "repository": {"full_name": "TestOwner/TestRepo"},
        "issue": {
            "number": issue_number,
            "title": "Fix login bug",
            "body": "Login fails when...",
            "labels": [],
            "assignees": [],
            "user": {"login": "reporter"},
            "state": "open",
            "created_at": "2026-07-01T10:00:00Z",
        },
        "comment": {
            "body": comment_body,
            "user": {"login": sender},
            "created_at": "2026-07-02T10:00:00Z",
        },
    }


def _make_pr_payload(
    action: str = "opened",
    number: int = 15,
    title: str = "Fix NPE in login",
    sender: str = "contributor1",
) -> dict:
    """Create a mock GitHub pull_request event payload."""
    return {
        "action": action,
        "sender": {"login": sender},
        "repository": {"full_name": "TestOwner/TestRepo"},
        "pull_request": {
            "number": number,
            "title": title,
            "body": "Closes #42",
            "user": {"login": sender},
            "base": {"ref": "main"},
            "head": {"ref": "fix/login-npe"},
            "labels": [],
            "state": "open",
            "created_at": "2026-07-01T12:00:00Z",
            "mergeable": True,
        },
    }


def _make_review_payload(
    sender: str = "reviewer1",
    pr_number: int = 15,
    review_body: str = "Looks good!",
) -> dict:
    """Create a mock GitHub pull_request_review event payload."""
    return {
        "action": "submitted",
        "sender": {"login": sender},
        "repository": {"full_name": "TestOwner/TestRepo"},
        "pull_request": {
            "number": pr_number,
            "title": "Fix NPE",
            "body": "Closes #42",
            "user": {"login": "contributor1"},
            "base": {"ref": "main"},
            "head": {"ref": "fix/npe"},
            "labels": [],
            "state": "open",
            "created_at": "2026-07-01T12:00:00Z",
        },
        "review": {
            "body": review_body,
            "state": "approved",
            "user": {"login": sender},
        },
    }


# ---------------------------------------------------------------------------
# Issue Event Tests
# ---------------------------------------------------------------------------

class TestIssueEventParsing:
    """Tests for parsing issue events."""

    def test_issue_opened(self, parser: EventParser) -> None:
        """Correctly parses an 'issues/opened' event."""
        payload = _make_issue_payload()
        event = parser.parse("issues", payload)

        assert event.event_type == EventType.ISSUE_OPENED
        assert event.action == "opened"
        assert event.sender == "contributor1"
        assert event.repository == "TestOwner/TestRepo"
        assert event.issue is not None
        assert event.issue.number == 42
        assert event.issue.title == "Fix login bug"

    def test_issue_has_labels(self, parser: EventParser) -> None:
        """Issue labels are correctly extracted."""
        payload = _make_issue_payload()
        event = parser.parse("issues", payload)
        assert event.issue is not None
        assert "bug" in event.issue.labels


# ---------------------------------------------------------------------------
# Issue Comment Event Tests
# ---------------------------------------------------------------------------

class TestIssueCommentEventParsing:
    """Tests for parsing issue_comment events."""

    def test_comment_created(self, parser: EventParser) -> None:
        """Correctly parses an 'issue_comment/created' event."""
        payload = _make_comment_payload(comment_body="assign me")
        event = parser.parse("issue_comment", payload)

        assert event.event_type == EventType.ISSUE_COMMENT
        assert event.action == "created"
        assert event.comment_body == "assign me"
        assert event.issue is not None
        assert event.issue.number == 42

    def test_comment_sender(self, parser: EventParser) -> None:
        """Sender is correctly extracted from comment event."""
        payload = _make_comment_payload(sender="someone")
        event = parser.parse("issue_comment", payload)
        assert event.sender == "someone"


# ---------------------------------------------------------------------------
# Pull Request Event Tests
# ---------------------------------------------------------------------------

class TestPullRequestEventParsing:
    """Tests for parsing pull_request events."""

    def test_pr_opened(self, parser: EventParser) -> None:
        """Correctly parses a 'pull_request/opened' event."""
        payload = _make_pr_payload()
        event = parser.parse("pull_request", payload)

        assert event.event_type == EventType.PULL_REQUEST_OPENED
        assert event.pull_request is not None
        assert event.pull_request.number == 15
        assert event.pull_request.title == "Fix NPE in login"
        assert event.pull_request.base_branch == "main"
        assert event.pull_request.head_branch == "fix/login-npe"

    def test_pr_synchronize(self, parser: EventParser) -> None:
        """Correctly classifies 'pull_request/synchronize' event."""
        payload = _make_pr_payload(action="synchronize")
        event = parser.parse("pull_request", payload)
        assert event.event_type == EventType.PULL_REQUEST_SYNCHRONIZE


# ---------------------------------------------------------------------------
# Review Event Tests
# ---------------------------------------------------------------------------

class TestReviewEventParsing:
    """Tests for parsing pull_request_review events."""

    def test_review_submitted(self, parser: EventParser) -> None:
        """Correctly parses a 'pull_request_review/submitted' event."""
        payload = _make_review_payload()
        event = parser.parse("pull_request_review", payload)

        assert event.event_type == EventType.REVIEW_SUBMITTED
        assert event.sender == "reviewer1"
        assert event.pull_request is not None
        assert event.pull_request.number == 15
        assert event.comment_body == "Looks good!"


# ---------------------------------------------------------------------------
# Unknown Event Tests
# ---------------------------------------------------------------------------

class TestUnknownEvents:
    """Tests for handling unrecognized events."""

    def test_unknown_event_name(self, parser: EventParser) -> None:
        """Unrecognized event names produce UNKNOWN type."""
        payload = {
            "action": "completed",
            "sender": {"login": "bot"},
            "repository": {"full_name": "owner/repo"},
        }
        event = parser.parse("workflow_run", payload)
        assert event.event_type == EventType.UNKNOWN

    def test_unknown_action(self, parser: EventParser) -> None:
        """Known event name with unknown action produces UNKNOWN type."""
        payload = _make_issue_payload(action="deleted")
        event = parser.parse("issues", payload)
        assert event.event_type == EventType.UNKNOWN
        # But issue context should still be populated
        assert event.issue is not None

    def test_empty_payload(self, parser: EventParser) -> None:
        """Empty payload is handled gracefully."""
        event = parser.parse("issues", {})
        assert event.event_type == EventType.UNKNOWN
        assert event.sender == ""
