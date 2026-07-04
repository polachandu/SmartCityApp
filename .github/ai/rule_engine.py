"""
Deterministic rule engine for the AI Maintainer.

Runs fast, deterministic checks on pull requests BEFORE invoking
the AI review. This keeps AI usage low and catches obvious issues
(merge conflicts, missing linked issues, hardcoded secrets, TODO/FIXME)
without burning inference tokens.

The rule engine flow:
    GitHub Event → Rule Engine → AI Review → GitHub Review

If the rule engine finds ERROR-level violations, the review engine
can skip AI entirely and request changes based on deterministic findings.

Classes:
    RuleEngine: Runs all enabled rules against a pull request context.

Note:
    This is a skeleton for Milestone 1. Rule implementations will be
    added in Milestone 4. The structure and interface are defined now
    so that other modules can depend on it immediately.
"""

from __future__ import annotations

from .config import BotConfig
from .models import PRContext, RuleEngineResult, RuleSeverity, RuleViolation
from .utils import get_logger

logger = get_logger("rule_engine")


class RuleEngine:
    """Runs deterministic checks on pull requests.

    Each rule is a method that receives a PRContext and returns a list
    of RuleViolation instances. Rules are executed in order, and their
    results are aggregated into a RuleEngineResult.

    Rules can be enabled/disabled via the bot configuration
    (review.enabled_rules in bot.yml).

    Args:
        config: Bot configuration containing review settings
                and enabled rules list.

    Example:
        >>> engine = RuleEngine(config)
        >>> result = engine.analyze(pr_context)
        >>> if not result.passed:
        ...     print(f"Found {result.error_count} errors")
    """

    # Maps rule names to their check methods
    # Methods are looked up dynamically by name: _check_{rule_name}
    AVAILABLE_RULES: list[str] = [
        "merge_conflicts",
        "missing_linked_issue",
        "large_pr",
        "bad_patterns",
    ]

    def __init__(self, config: BotConfig) -> None:
        """Initialize the rule engine.

        Args:
            config: Bot configuration with review settings.
        """
        self._config = config

        # Determine which rules are enabled
        review_config = config.review or {}
        self._enabled_rules: list[str] = review_config.get(
            "enabled_rules", self.AVAILABLE_RULES
        )

        logger.info(
            "RuleEngine initialized (enabled_rules=%s)",
            ", ".join(self._enabled_rules),
        )

    def analyze(self, pr_context: PRContext) -> RuleEngineResult:
        """Run all enabled rules against a pull request.

        Executes each enabled rule method, collects violations,
        and returns an aggregated result with a pass/fail flag.

        Args:
            pr_context: The pull request context to analyze.

        Returns:
            A RuleEngineResult containing all violations found.
        """
        logger.info(
            "Analyzing PR #%d with %d rules",
            pr_context.number,
            len(self._enabled_rules),
        )

        result = RuleEngineResult()

        for rule_name in self._enabled_rules:
            method_name = f"_check_{rule_name}"
            method = getattr(self, method_name, None)

            if method is None:
                logger.warning(
                    "Rule '%s' is enabled but not implemented (skipping)",
                    rule_name,
                )
                continue

            try:
                violations = method(pr_context)
                for violation in violations:
                    result.add_violation(violation)
                logger.debug(
                    "Rule '%s': %d violation(s)",
                    rule_name,
                    len(violations),
                )
            except Exception as e:
                logger.error(
                    "Rule '%s' raised an exception: %s", rule_name, e
                )
                result.add_violation(
                    RuleViolation(
                        severity=RuleSeverity.WARNING,
                        rule_name=rule_name,
                        message=f"Rule execution failed: {e}",
                    )
                )

        # Generate summary
        result.summary = (
            f"Rule engine completed: {result.error_count} error(s), "
            f"{result.warning_count} warning(s), "
            f"{len(result.violations)} total violation(s). "
            f"{'PASSED' if result.passed else 'FAILED'}"
        )

        logger.info(result.summary)
        return result

    # ------------------------------------------------------------------
    # Rule Implementations (Milestone 4)
    # ------------------------------------------------------------------

    def _check_merge_conflicts(
        self, pr_context: PRContext
    ) -> list[RuleViolation]:
        """Check if the PR has merge conflicts.

        Inspects the PR's mergeable status. If GitHub reports the PR
        as not mergeable, it likely has merge conflicts that must be
        resolved before review.

        Will be implemented in Milestone 4.

        Args:
            pr_context: The pull request context.

        Returns:
            List of violations (empty if no conflicts detected).
        """
        # Milestone 4: Implement merge conflict detection
        return []

    def _check_missing_linked_issue(
        self, pr_context: PRContext
    ) -> list[RuleViolation]:
        """Check if the PR references a linked issue.

        Scans the PR body for issue references (e.g., 'Closes #42',
        'Fixes #23', 'Resolves #15'). If no linked issue is found,
        a warning is generated because PRs should address specific issues.

        Will be implemented in Milestone 4.

        Args:
            pr_context: The pull request context.

        Returns:
            List of violations (empty if an issue reference is found).
        """
        # Milestone 4: Implement linked issue detection
        return []

    def _check_large_pr(
        self, pr_context: PRContext
    ) -> list[RuleViolation]:
        """Check if the PR is too large for effective review.

        Counts the total number of changed lines and files. If either
        exceeds the configured thresholds, a warning is generated
        recommending the PR be split into smaller, focused changes.

        Will be implemented in Milestone 4.

        Args:
            pr_context: The pull request context.

        Returns:
            List of violations (empty if PR size is within limits).
        """
        # Milestone 4: Implement large PR detection
        return []

    def _check_bad_patterns(
        self, pr_context: PRContext
    ) -> list[RuleViolation]:
        """Check for bad code patterns in the PR diff.

        Scans the diff for patterns that indicate potential issues:
        - TODO / FIXME comments (incomplete work)
        - printStackTrace() calls (poor error handling in Java)
        - Hardcoded passwords, API keys, tokens
        - Duplicate SQL queries
        - Duplicate constants

        Will be implemented in Milestone 4.

        Args:
            pr_context: The pull request context.

        Returns:
            List of violations for each bad pattern found.
        """
        # Milestone 4: Implement bad pattern detection
        return []
