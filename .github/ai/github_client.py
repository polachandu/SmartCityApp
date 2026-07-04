"""
GitHub REST API client for the AI Maintainer.

Provides a typed, high-level interface to the GitHub REST API for all
operations the AI maintainer needs: reading issues, reading pull requests,
posting comments, assigning users, managing labels, and submitting reviews.

This client abstracts all HTTP details (authentication, headers, error handling,
URL construction) behind clean methods that accept and return domain models.
It follows the Repository Pattern — all GitHub API knowledge is encapsulated here,
and no other module in the AI maintainer needs to know about REST endpoints.

Classes:
    GitHubAPIError: Base exception for GitHub API errors.
    RateLimitError: Raised when GitHub rate limit is exceeded.
    NotFoundError: Raised when a requested resource doesn't exist.
    GitHubClient: Main client class wrapping the GitHub REST API.
"""

from __future__ import annotations

from typing import Any

import httpx

from .models import IssueContext, PRContext
from .utils import get_logger

logger = get_logger("github_client")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class GitHubAPIError(Exception):
    """Base exception for GitHub REST API errors.

    Attributes:
        status_code: HTTP status code from the response.
        message: Error message from the API or a description.
        response_body: Raw response body for debugging.
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        response_body: str = "",
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.response_body = response_body
        super().__init__(f"GitHub API Error {status_code}: {message}")


class RateLimitError(GitHubAPIError):
    """Raised when the GitHub API rate limit is exceeded (HTTP 403/429).

    The retry layer should wait until the rate limit resets before
    retrying the request.
    """


class NotFoundError(GitHubAPIError):
    """Raised when a requested GitHub resource is not found (HTTP 404).

    This is not a transient error and should not be retried.
    """


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class GitHubClient:
    """High-level client for the GitHub REST API.

    Encapsulates all GitHub API interactions needed by the AI maintainer.
    Uses httpx for HTTP requests with connection pooling, automatic
    authentication, and structured error handling.

    This client implements the context manager protocol for proper
    connection cleanup.

    Args:
        token: GitHub personal access token or GITHUB_TOKEN.
        repository: Full repository name in 'owner/repo' format.
        base_url: GitHub API base URL. Override for GitHub Enterprise.
        timeout: Request timeout in seconds.

    Example:
        >>> with GitHubClient(token="ghp_xxx", repository="owner/repo") as client:
        ...     issue = client.get_issue(42)
        ...     print(issue.title)
    """

    BASE_URL = "https://api.github.com"

    def __init__(
        self,
        token: str,
        repository: str,
        base_url: str = "",
        timeout: float = 30.0,
    ) -> None:
        """Initialize the GitHub client.

        Args:
            token: GitHub authentication token.
            repository: Full repository name ('owner/repo').
            base_url: Override API base URL (for GitHub Enterprise).
            timeout: HTTP request timeout in seconds.
        """
        self._repository = repository
        self._base_url = base_url or self.BASE_URL

        parts = repository.split("/", 1)
        if len(parts) != 2:
            raise ValueError(
                f"Invalid repository format: '{repository}'. "
                f"Expected 'owner/name'."
            )
        self._owner = parts[0]
        self._repo = parts[1]

        self._client = httpx.Client(
            base_url=self._base_url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=timeout,
        )

        logger.info(
            "GitHubClient initialized for %s", self._repository
        )

    def __enter__(self) -> GitHubClient:
        """Enter the context manager."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit the context manager and close the HTTP client."""
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        self._client.close()
        logger.debug("GitHubClient connection closed")

    # ------------------------------------------------------------------
    # Issue Methods
    # ------------------------------------------------------------------

    def get_issue(self, issue_number: int) -> IssueContext:
        """Fetch a GitHub issue and return it as a typed IssueContext.

        Retrieves the issue metadata and separately fetches comments
        to provide a complete picture of the issue discussion.

        Args:
            issue_number: The issue number to fetch.

        Returns:
            An IssueContext instance with all fields populated.

        Raises:
            NotFoundError: If the issue doesn't exist.
            GitHubAPIError: If the API call fails for other reasons.
        """
        logger.debug("Fetching issue #%d", issue_number)

        data = self._request("GET", f"/repos/{self._repository}/issues/{issue_number}")
        comments = self.get_issue_comments(issue_number)

        issue = IssueContext.from_dict(data)
        issue.comments = comments

        logger.info("Fetched issue #%d: %s", issue_number, issue.title)
        return issue

    def get_issue_comments(self, issue_number: int) -> list[dict[str, Any]]:
        """Fetch all comments on an issue.

        Args:
            issue_number: The issue number.

        Returns:
            List of comment dictionaries with 'user', 'body', 'created_at'.

        Raises:
            GitHubAPIError: If the API call fails.
        """
        logger.debug("Fetching comments for issue #%d", issue_number)

        data = self._request(
            "GET",
            f"/repos/{self._repository}/issues/{issue_number}/comments",
        )

        return [
            {
                "user": comment.get("user", {}).get("login", ""),
                "body": comment.get("body", ""),
                "created_at": comment.get("created_at", ""),
            }
            for comment in data
        ]

    def assign_issue(
        self, issue_number: int, assignees: list[str]
    ) -> dict[str, Any]:
        """Assign one or more users to an issue.

        Args:
            issue_number: The issue number to assign.
            assignees: List of GitHub usernames to assign.

        Returns:
            The API response dictionary.

        Raises:
            GitHubAPIError: If assignment fails (e.g., user not a collaborator).
        """
        logger.info(
            "Assigning %s to issue #%d",
            ", ".join(assignees),
            issue_number,
        )

        return self._request(
            "POST",
            f"/repos/{self._repository}/issues/{issue_number}/assignees",
            json={"assignees": assignees},
        )

    def add_comment(
        self, issue_number: int, body: str
    ) -> dict[str, Any]:
        """Post a comment on an issue or pull request.

        Args:
            issue_number: The issue/PR number (GitHub uses the same endpoint).
            body: The comment body in Markdown.

        Returns:
            The API response dictionary with the created comment.

        Raises:
            GitHubAPIError: If posting the comment fails.
        """
        logger.info("Posting comment on issue #%d", issue_number)

        return self._request(
            "POST",
            f"/repos/{self._repository}/issues/{issue_number}/comments",
            json={"body": body},
        )

    def add_labels(
        self, issue_number: int, labels: list[str]
    ) -> dict[str, Any]:
        """Add labels to an issue or pull request.

        Args:
            issue_number: The issue/PR number.
            labels: List of label names to add.

        Returns:
            The API response dictionary.

        Raises:
            GitHubAPIError: If adding labels fails.
        """
        logger.info(
            "Adding labels %s to issue #%d",
            labels,
            issue_number,
        )

        return self._request(
            "POST",
            f"/repos/{self._repository}/issues/{issue_number}/labels",
            json={"labels": labels},
        )

    # ------------------------------------------------------------------
    # Pull Request Methods
    # ------------------------------------------------------------------

    def get_pull_request(self, pr_number: int) -> PRContext:
        """Fetch a pull request and return it as a typed PRContext.

        Retrieves PR metadata only. Use get_pr_diff(), get_pr_files(),
        get_pr_commits(), and get_pr_reviews() separately for full context.

        Args:
            pr_number: The pull request number.

        Returns:
            A PRContext instance with metadata fields populated.

        Raises:
            NotFoundError: If the PR doesn't exist.
            GitHubAPIError: If the API call fails.
        """
        logger.debug("Fetching PR #%d", pr_number)

        data = self._request("GET", f"/repos/{self._repository}/pulls/{pr_number}")
        pr = PRContext.from_dict(data)

        logger.info("Fetched PR #%d: %s", pr_number, pr.title)
        return pr

    def get_pr_diff(self, pr_number: int) -> str:
        """Fetch the raw unified diff for a pull request.

        Args:
            pr_number: The pull request number.

        Returns:
            The raw diff string.

        Raises:
            GitHubAPIError: If the API call fails.
        """
        logger.debug("Fetching diff for PR #%d", pr_number)

        response = self._client.request(
            "GET",
            f"/repos/{self._repository}/pulls/{pr_number}",
            headers={"Accept": "application/vnd.github.diff"},
        )
        self._handle_api_error(response)

        return response.text

    def get_pr_files(self, pr_number: int) -> list[dict[str, Any]]:
        """Fetch the list of files changed in a pull request.

        Args:
            pr_number: The pull request number.

        Returns:
            List of file dicts with 'filename', 'status', 'additions',
            'deletions', 'changes', 'patch'.

        Raises:
            GitHubAPIError: If the API call fails.
        """
        logger.debug("Fetching files for PR #%d", pr_number)

        return self._request(
            "GET",
            f"/repos/{self._repository}/pulls/{pr_number}/files",
        )

    def get_pr_commits(self, pr_number: int) -> list[dict[str, Any]]:
        """Fetch commit list for a pull request.

        Args:
            pr_number: The pull request number.

        Returns:
            List of commit dicts with 'sha' and 'commit.message'.

        Raises:
            GitHubAPIError: If the API call fails.
        """
        logger.debug("Fetching commits for PR #%d", pr_number)

        data = self._request(
            "GET",
            f"/repos/{self._repository}/pulls/{pr_number}/commits",
        )

        return [
            {
                "sha": commit.get("sha", ""),
                "message": commit.get("commit", {}).get("message", ""),
            }
            for commit in data
        ]

    def get_pr_reviews(self, pr_number: int) -> list[dict[str, Any]]:
        """Fetch existing reviews on a pull request.

        Args:
            pr_number: The pull request number.

        Returns:
            List of review dicts with 'user', 'state', 'body'.

        Raises:
            GitHubAPIError: If the API call fails.
        """
        logger.debug("Fetching reviews for PR #%d", pr_number)

        data = self._request(
            "GET",
            f"/repos/{self._repository}/pulls/{pr_number}/reviews",
        )

        return [
            {
                "user": review.get("user", {}).get("login", ""),
                "state": review.get("state", ""),
                "body": review.get("body", ""),
            }
            for review in data
        ]

    def create_review(
        self,
        pr_number: int,
        body: str,
        event: str,
        comments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Submit a review on a pull request.

        Args:
            pr_number: The pull request number.
            body: The review body in Markdown.
            event: Review action — one of 'APPROVE', 'REQUEST_CHANGES', 'COMMENT'.
            comments: Optional list of inline review comment dicts with
                      'path', 'position', 'body'.

        Returns:
            The API response dictionary.

        Raises:
            GitHubAPIError: If submitting the review fails.
        """
        logger.info(
            "Submitting %s review on PR #%d", event, pr_number
        )

        payload: dict[str, Any] = {"body": body, "event": event}
        if comments:
            payload["comments"] = comments

        return self._request(
            "POST",
            f"/repos/{self._repository}/pulls/{pr_number}/reviews",
            json=payload,
        )

    # ------------------------------------------------------------------
    # User Methods
    # ------------------------------------------------------------------

    def is_first_contribution(self, username: str) -> bool:
        """Check if a user is a first-time contributor to this repository.

        Searches for previous issues and pull requests by the user.
        If none are found, the user is considered a first-time contributor.

        Args:
            username: GitHub username to check.

        Returns:
            True if this is the user's first contribution, False otherwise.

        Raises:
            GitHubAPIError: If the API call fails.
        """
        logger.debug(
            "Checking first contribution status for %s", username
        )

        # Search for issues authored by this user in this repo
        data = self._request(
            "GET",
            "/search/issues",
            params={
                "q": f"repo:{self._repository} author:{username}",
                "per_page": 1,
            },
        )

        total_count = data.get("total_count", 0)
        is_first = total_count <= 1  # Current issue/PR counts as 1

        logger.info(
            "User %s first contribution: %s (total: %d)",
            username,
            is_first,
            total_count,
        )
        return is_first

    def get_user_issue_count(self, username: str) -> int:
        """Count the number of open issues assigned to a user in this repo.

        Used by the assignment engine to enforce the max open issues
        per user limit.

        Args:
            username: GitHub username to check.

        Returns:
            Number of open issues currently assigned to the user.

        Raises:
            GitHubAPIError: If the API call fails.
        """
        logger.debug(
            "Counting open issues assigned to %s", username
        )

        data = self._request(
            "GET",
            "/search/issues",
            params={
                "q": (
                    f"repo:{self._repository} "
                    f"assignee:{username} "
                    f"is:issue is:open"
                ),
                "per_page": 1,
            },
        )

        count = data.get("total_count", 0)
        logger.debug("User %s has %d open issues", username, count)
        return count

    # ------------------------------------------------------------------
    # Internal Methods
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Any:
        """Execute an HTTP request against the GitHub API.

        Central request method that handles authentication (via client headers),
        response validation, and error handling for all API calls.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE).
            endpoint: API endpoint path (e.g., '/repos/owner/repo/issues/1').
            **kwargs: Additional arguments passed to httpx (json, params, etc.).

        Returns:
            Parsed JSON response (dict or list).

        Raises:
            GitHubAPIError: If the request fails.
            RateLimitError: If rate limit is exceeded.
            NotFoundError: If the resource is not found.
        """
        response = self._client.request(method, endpoint, **kwargs)
        self._handle_api_error(response)

        # Some endpoints return empty responses (e.g., 204 No Content)
        if response.status_code == 204:
            return {}

        return response.json()

    def _handle_api_error(self, response: httpx.Response) -> None:
        """Check response status and raise typed exceptions for errors.

        Maps HTTP status codes to specific exception types:
        - 404 → NotFoundError (not retryable)
        - 403/429 → RateLimitError (retryable after cooldown)
        - Other 4xx/5xx → GitHubAPIError

        Args:
            response: The httpx Response object to check.

        Raises:
            NotFoundError: For 404 responses.
            RateLimitError: For 403 (rate limit) and 429 responses.
            GitHubAPIError: For all other error responses.
        """
        if response.is_success:
            return

        status = response.status_code
        body = response.text

        try:
            error_data = response.json()
            message = error_data.get("message", body)
        except Exception:
            message = body

        if status == 404:
            raise NotFoundError(status, message, body)

        if status in (403, 429):
            # Check if it's actually a rate limit error
            if "rate limit" in message.lower() or status == 429:
                raise RateLimitError(status, message, body)

        raise GitHubAPIError(status, message, body)
