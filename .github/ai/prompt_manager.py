"""
Prompt manager for the AI Maintainer.

Handles loading, caching, and rendering of prompt templates from the
.github/prompts/ directory. Uses {{placeholder}} syntax for variable
substitution (double curly braces to avoid conflicts with markdown).

The prompt manager ensures that:
- Prompts are loaded from disk only once and cached in memory.
- All placeholders are validated before rendering.
- Missing variables are detected and reported.

Classes:
    PromptError: Raised when a prompt cannot be loaded or rendered.
    PromptManager: Main class for prompt template management.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from .utils import get_logger

logger = get_logger("prompt_manager")


class PromptError(Exception):
    """Raised when a prompt template cannot be loaded or rendered.

    Provides actionable error messages including the prompt name
    and the specific issue (file not found, unresolved placeholders).
    """


class PromptManager:
    """Manages prompt templates for the AI Maintainer.

    Loads markdown prompt templates from a directory, caches them
    in memory, and renders them by replacing {{placeholder}} variables
    with provided values.

    Args:
        prompts_dir: Path to the directory containing prompt template files.
                     Each template is a .md file named by its purpose
                     (e.g., system.md, review.md, assignment.md).

    Example:
        >>> manager = PromptManager(".github/prompts")
        >>> prompt = manager.render_prompt("review",
        ...     issue_title="Fix login bug",
        ...     diff="+ fixed the null check",
        ... )
    """

    # Pattern matching {{variable_name}} placeholders
    _PLACEHOLDER_PATTERN = re.compile(r"\{\{(\w+)\}\}")

    def __init__(self, prompts_dir: str) -> None:
        """Initialize the prompt manager.

        Args:
            prompts_dir: Path to the prompts directory. Can be absolute
                         or relative to the current working directory.
        """
        self._prompts_dir = Path(prompts_dir)
        self._cache: dict[str, str] = {}

        logger.info(
            "PromptManager initialized (dir=%s)", self._prompts_dir
        )

    def load_prompt(self, name: str) -> str:
        """Load a prompt template by name, using the in-memory cache.

        Looks for a file named '{name}.md' in the prompts directory.
        The file is loaded once and cached for subsequent calls.

        Args:
            name: The prompt name (without .md extension).
                  e.g., 'system', 'review', 'assignment'.

        Returns:
            The raw template content as a string.

        Raises:
            PromptError: If the template file doesn't exist.
        """
        if name in self._cache:
            logger.debug("Prompt '%s' loaded from cache", name)
            return self._cache[name]

        file_path = self._prompts_dir / f"{name}.md"

        if not file_path.exists():
            raise PromptError(
                f"Prompt template '{name}' not found at '{file_path}'. "
                f"Create a '{name}.md' file in '{self._prompts_dir}'."
            )

        content = file_path.read_text(encoding="utf-8")
        self._cache[name] = content

        logger.info(
            "Loaded prompt '%s' (%d chars)", name, len(content)
        )
        return content

    def render_prompt(self, name: str, **variables: Any) -> str:
        """Load a prompt template and replace all {{placeholders}}.

        Loads the template using load_prompt() (cached), then replaces
        all {{variable}} placeholders with the provided keyword arguments.
        All values are converted to strings via str().

        Args:
            name: The prompt template name (without .md extension).
            **variables: Keyword arguments mapping placeholder names to values.

        Returns:
            The rendered prompt with all placeholders replaced.

        Raises:
            PromptError: If the template doesn't exist.

        Example:
            >>> manager.render_prompt("review",
            ...     issue_title="Fix NPE",
            ...     diff="+null check added",
            ... )
        """
        template = self.load_prompt(name)

        # Replace all provided variables
        rendered = template
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            rendered = rendered.replace(placeholder, str(value))

        # Log any unresolved placeholders
        unresolved = self.validate_variables(rendered)
        if unresolved:
            logger.warning(
                "Unresolved placeholders in '%s': %s",
                name,
                ", ".join(unresolved),
            )

        return rendered

    def get_system_prompt(self, **variables: Any) -> str:
        """Shorthand for loading and rendering the system prompt.

        Args:
            **variables: Placeholder values for the system prompt template.

        Returns:
            The rendered system prompt.
        """
        return self.render_prompt("system", **variables)

    def get_review_prompt(self, **variables: Any) -> str:
        """Shorthand for loading and rendering the review prompt.

        Args:
            **variables: Placeholder values for the review prompt template.

        Returns:
            The rendered review prompt.
        """
        return self.render_prompt("review", **variables)

    def get_assignment_prompt(self, **variables: Any) -> str:
        """Shorthand for loading and rendering the assignment prompt.

        Args:
            **variables: Placeholder values for the assignment prompt template.

        Returns:
            The rendered assignment prompt.
        """
        return self.render_prompt("assignment", **variables)

    def get_welcome_prompt(self, **variables: Any) -> str:
        """Shorthand for loading and rendering the welcome prompt.

        Args:
            **variables: Placeholder values for the welcome prompt template.

        Returns:
            The rendered welcome prompt.
        """
        return self.render_prompt("welcome", **variables)

    def validate_variables(self, text: str) -> list[str]:
        """Find unresolved {{placeholder}} variables in rendered text.

        Used after rendering to detect missing variable substitutions.
        Returns the names of any placeholders that were not replaced.

        Args:
            text: The rendered prompt text to check.

        Returns:
            List of unresolved placeholder names (empty if all resolved).

        Example:
            >>> manager.validate_variables("Hello {{name}}, welcome to {{repo}}")
            ['name', 'repo']
        """
        return self._PLACEHOLDER_PATTERN.findall(text)

    def clear_cache(self) -> None:
        """Clear the in-memory prompt cache.

        Useful when prompt files are updated at runtime (e.g., during
        development or testing).
        """
        count = len(self._cache)
        self._cache.clear()
        logger.info("Prompt cache cleared (%d entries removed)", count)

    def list_available(self) -> list[str]:
        """List all available prompt templates in the prompts directory.

        Returns:
            List of prompt names (without .md extension) found in
            the prompts directory.
        """
        if not self._prompts_dir.exists():
            return []

        return [
            f.stem
            for f in sorted(self._prompts_dir.glob("*.md"))
            if f.is_file()
        ]
