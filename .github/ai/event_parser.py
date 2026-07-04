"""
GitHub event parser for the AI Maintainer.

Converts raw GitHub Actions event payloads into typed Python models.
This module is the single entry point for all event interpretation —
no other module should parse raw github.event payloads directly.

In GitHub Actions, event data is available via:
- GITHUB_EVENT_NAME: The event type (e.g., 'issues', 'issue_comment', 'pull_request')
- GITHUB_EVENT_PATH: Path to a JSON file containing the full event payload

The parser reads these, classifies the event, and returns a strongly-typed
GitHubEvent instance with the relevant IssueContext or PRContext pre-populated.

Classes:
    EventParser: Main parser class for GitHub Actions events.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .models import EventType, GitHubEvent, IssueContext, PRContext
from .utils import get_logger

logger = get_logger("event_parser")


class EventParser:
    """Parses raw GitHub Actions event payloads into typed GitHubEvent models.

    Reads event data from environment variables (GITHUB_EVENT_NAME,
    GITHUB_EVENT_PATH) or accepts pre-parsed payloads for testing.
    Each event type has a dedicated parser method that extracts the
    relevant context into typed dataclasses.

    Example:
        >>> parser = EventParser()
        >>> # In GitHub Actions (reads from env vars):
        >>> event = parser.parse_from_env()
        >>> # For testing (pass data directly):
        >>> event = parser.parse("issue_comment", {"action": "created", ...})
    """

    # Mapping of GitHub event name + action to internal EventType
    _EVENT_MAP: dict[tuple[str, str], EventType] = {
        ("issues", "opened"): EventType.ISSUE_OPENED,
        ("issue_comment", "created"): EventType.ISSUE_COMMENT,
        ("pull_request", "opened"): EventType.PULL_REQUEST_OPENED,
        ("pull_request", "synchronize"): EventType.PULL_REQUEST_SYNCHRONIZE,
        ("pull_request_review", "submitted"): EventType.REVIEW_SUBMITTED,
    }

    def parse_from_env(self) -> GitHubEvent:
        """Parse the GitHub event from environment variables.

        Reads GITHUB_EVENT_NAME and GITHUB_EVENT_PATH, loads the
        event payload JSON file, and delegates to parse().

        Returns:
            A typed GitHubEvent instance.

        Raises:
            FileNotFoundError: If the event payload file doesn't exist.
            json.JSONDecodeError: If the payload file contains invalid JSON.
        """
        event_name = os.environ.get("GITHUB_EVENT_NAME", "")
        event_path = os.environ.get("GITHUB_EVENT_PATH", "")

        if not event_name:
            logger.warning("GITHUB_EVENT_NAME not set, returning unknown event")
            return GitHubEvent(
                event_type=EventType.UNKNOWN,
                action="",
                sender="",
                repository=os.environ.get("GITHUB_REPOSITORY", ""),
            )

        if not event_path or not Path(event_path).exists():
            logger.warning(
                "GITHUB_EVENT_PATH not set or file missing: %s", event_path
            )
            return GitHubEvent(
                event_type=EventType.UNKNOWN,
                action="",
                sender="",
                repository=os.environ.get("GITHUB_REPOSITORY", ""),
            )

        with open(event_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        logger.info(
            "Loaded event payload from %s (event=%s)", event_path, event_name
        )
        return self.parse(event_name, payload)

    def parse(self, event_name: str, payload: dict[str, Any]) -> GitHubEvent:
        """Parse a GitHub event from its name and payload.

        Classifies the event using the event name and action field,
        then delegates to the appropriate type-specific parser method.

        Args:
            event_name: GitHub event name (e.g., 'issues', 'pull_request',
                        'issue_comment').
            payload: The full event payload dictionary.

        Returns:
            A typed GitHubEvent instance with relevant context populated.
        """
        action = payload.get("action", "")
        sender = payload.get("sender", {}).get("login", "")
        repository = payload.get("repository", {}).get("full_name", "")

        # Classify the event type
        event_type = self._EVENT_MAP.get(
            (event_name, action), EventType.UNKNOWN
        )

        logger.info(
            "Parsing event: name=%s, action=%s, type=%s, sender=%s",
            event_name,
            action,
            event_type.value,
            sender,
        )

        # Delegate to type-specific parsers
        if event_name == "issues":
            return self._parse_issue_event(
                event_type, action, sender, repository, payload
            )
        elif event_name == "issue_comment":
            return self._parse_issue_comment_event(
                event_type, action, sender, repository, payload
            )
        elif event_name == "pull_request":
            return self._parse_pull_request_event(
                event_type, action, sender, repository, payload
            )
        elif event_name == "pull_request_review":
            return self._parse_review_event(
                event_type, action, sender, repository, payload
            )

        logger.warning("Unhandled event type: %s/%s", event_name, action)
        return GitHubEvent(
            event_type=EventType.UNKNOWN,
            action=action,
            sender=sender,
            repository=repository,
            payload=payload,
        )

    def _parse_issue_event(
        self,
        event_type: EventType,
        action: str,
        sender: str,
        repository: str,
        payload: dict[str, Any],
    ) -> GitHubEvent:
        """Parse an issue event payload.

        Extracts the issue data from the payload and constructs
        an IssueContext.

        Args:
            event_type: Classified event type.
            action: Event action string.
            sender: Username who triggered the event.
            repository: Full repository name.
            payload: Raw event payload.

        Returns:
            GitHubEvent with issue context populated.
        """
        issue_data = payload.get("issue", {})
        issue = IssueContext.from_dict(issue_data)

        logger.debug(
            "Parsed issue event: #%d '%s'", issue.number, issue.title
        )

        return GitHubEvent(
            event_type=event_type,
            action=action,
            sender=sender,
            repository=repository,
            payload=payload,
            issue=issue,
        )

    def _parse_issue_comment_event(
        self,
        event_type: EventType,
        action: str,
        sender: str,
        repository: str,
        payload: dict[str, Any],
    ) -> GitHubEvent:
        """Parse an issue comment event payload.

        Extracts both the issue context and the comment text.
        Used by the assignment engine to detect assignment requests.

        Args:
            event_type: Classified event type.
            action: Event action string.
            sender: Username who triggered the event.
            repository: Full repository name.
            payload: Raw event payload.

        Returns:
            GitHubEvent with issue context and comment body populated.
        """
        issue_data = payload.get("issue", {})
        issue = IssueContext.from_dict(issue_data)

        comment_data = payload.get("comment", {})
        comment_body = comment_data.get("body", "")

        logger.debug(
            "Parsed issue comment event: #%d, comment by %s",
            issue.number,
            sender,
        )

        return GitHubEvent(
            event_type=event_type,
            action=action,
            sender=sender,
            repository=repository,
            payload=payload,
            issue=issue,
            comment_body=comment_body,
        )

    def _parse_pull_request_event(
        self,
        event_type: EventType,
        action: str,
        sender: str,
        repository: str,
        payload: dict[str, Any],
    ) -> GitHubEvent:
        """Parse a pull request event payload.

        Extracts the PR metadata. Note: the full diff and file list
        require separate API calls via GitHubClient.

        Args:
            event_type: Classified event type.
            action: Event action string.
            sender: Username who triggered the event.
            repository: Full repository name.
            payload: Raw event payload.

        Returns:
            GitHubEvent with PR context populated.
        """
        pr_data = payload.get("pull_request", {})
        pr = PRContext.from_dict(pr_data)

        logger.debug(
            "Parsed PR event: #%d '%s'", pr.number, pr.title
        )

        return GitHubEvent(
            event_type=event_type,
            action=action,
            sender=sender,
            repository=repository,
            payload=payload,
            pull_request=pr,
        )

    def _parse_review_event(
        self,
        event_type: EventType,
        action: str,
        sender: str,
        repository: str,
        payload: dict[str, Any],
    ) -> GitHubEvent:
        """Parse a pull request review event payload.

        Extracts both the PR context and the review details.

        Args:
            event_type: Classified event type.
            action: Event action string.
            sender: Username who triggered the event.
            repository: Full repository name.
            payload: Raw event payload.

        Returns:
            GitHubEvent with PR context populated.
        """
        pr_data = payload.get("pull_request", {})
        pr = PRContext.from_dict(pr_data)

        review_data = payload.get("review", {})
        review_body = review_data.get("body", "")

        logger.debug(
            "Parsed review event: PR #%d, review by %s",
            pr.number,
            sender,
        )

        return GitHubEvent(
            event_type=event_type,
            action=action,
            sender=sender,
            repository=repository,
            payload=payload,
            pull_request=pr,
            comment_body=review_body,
        )
