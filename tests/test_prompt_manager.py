"""
Unit tests for the prompt manager module.

Tests prompt loading, caching, placeholder rendering,
unresolved variable detection, and error handling.
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

from ai.prompt_manager import PromptError, PromptManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    """Create a temporary prompts directory with test templates."""
    prompts = tmp_path / "prompts"
    prompts.mkdir()

    # Create test prompt templates
    (prompts / "system.md").write_text(
        "You are a reviewer for {{repository}}.\n"
        "Coding standards: {{standards}}\n",
        encoding="utf-8",
    )

    (prompts / "review.md").write_text(
        "# Review PR #{{pr_number}}\n"
        "## Issue: {{issue_title}}\n"
        "## Diff:\n{{diff}}\n",
        encoding="utf-8",
    )

    (prompts / "simple.md").write_text(
        "Hello, World! No placeholders here.\n",
        encoding="utf-8",
    )

    return prompts


@pytest.fixture
def manager(prompts_dir: Path) -> PromptManager:
    """Create a PromptManager with the test prompts directory."""
    return PromptManager(str(prompts_dir))


# ---------------------------------------------------------------------------
# Loading Tests
# ---------------------------------------------------------------------------

class TestLoadPrompt:
    """Tests for prompt loading."""

    def test_load_existing_prompt(self, manager: PromptManager) -> None:
        """Successfully loads an existing prompt template."""
        content = manager.load_prompt("system")
        assert "You are a reviewer" in content
        assert "{{repository}}" in content

    def test_load_nonexistent_raises(self, manager: PromptManager) -> None:
        """Raises PromptError for missing template."""
        with pytest.raises(PromptError, match="not found"):
            manager.load_prompt("nonexistent")

    def test_caching(self, manager: PromptManager) -> None:
        """Second load returns cached content."""
        content1 = manager.load_prompt("system")
        content2 = manager.load_prompt("system")
        assert content1 == content2
        # Verify it's actually cached (same object)
        assert content1 is content2


# ---------------------------------------------------------------------------
# Rendering Tests
# ---------------------------------------------------------------------------

class TestRenderPrompt:
    """Tests for prompt rendering with placeholder substitution."""

    def test_render_all_variables(self, manager: PromptManager) -> None:
        """All placeholders are replaced when all variables are provided."""
        result = manager.render_prompt(
            "system",
            repository="SmartCityApp",
            standards="Java naming conventions",
        )
        assert "SmartCityApp" in result
        assert "Java naming conventions" in result
        assert "{{" not in result

    def test_render_partial_variables(self, manager: PromptManager) -> None:
        """Unresolved placeholders remain when variables are missing."""
        result = manager.render_prompt("system", repository="SmartCityApp")
        assert "SmartCityApp" in result
        assert "{{standards}}" in result

    def test_render_no_placeholders(self, manager: PromptManager) -> None:
        """Templates without placeholders are returned as-is."""
        result = manager.render_prompt("simple")
        assert result == "Hello, World! No placeholders here.\n"

    def test_render_with_multiline_value(self, manager: PromptManager) -> None:
        """Multi-line values are inserted correctly."""
        diff = "+public void foo() {\n+  return;\n+}"
        result = manager.render_prompt(
            "review",
            pr_number="42",
            issue_title="Fix NPE",
            diff=diff,
        )
        assert "+public void foo()" in result
        assert "PR #42" in result


# ---------------------------------------------------------------------------
# Validation Tests
# ---------------------------------------------------------------------------

class TestValidateVariables:
    """Tests for unresolved placeholder detection."""

    def test_no_unresolved(self, manager: PromptManager) -> None:
        """Returns empty list when all placeholders are resolved."""
        result = manager.validate_variables("Hello World, no placeholders")
        assert result == []

    def test_finds_unresolved(self, manager: PromptManager) -> None:
        """Finds all unresolved placeholders."""
        result = manager.validate_variables(
            "Hello {{name}}, welcome to {{repo}}"
        )
        assert "name" in result
        assert "repo" in result

    def test_duplicate_placeholders(self, manager: PromptManager) -> None:
        """Finds duplicate placeholder names."""
        result = manager.validate_variables(
            "{{name}} and {{name}} again"
        )
        assert result.count("name") == 2


# ---------------------------------------------------------------------------
# Shorthand Methods Tests
# ---------------------------------------------------------------------------

class TestShorthandMethods:
    """Tests for the shorthand prompt loading methods."""

    def test_get_system_prompt(self, manager: PromptManager) -> None:
        """get_system_prompt() loads and renders the system template."""
        result = manager.get_system_prompt(
            repository="TestRepo", standards="PEP8"
        )
        assert "TestRepo" in result

    def test_get_review_prompt(self, manager: PromptManager) -> None:
        """get_review_prompt() loads and renders the review template."""
        result = manager.get_review_prompt(
            pr_number="10",
            issue_title="Bug fix",
            diff="+code",
        )
        assert "PR #10" in result


# ---------------------------------------------------------------------------
# Cache Management Tests
# ---------------------------------------------------------------------------

class TestCacheManagement:
    """Tests for cache clearing and listing."""

    def test_clear_cache(self, manager: PromptManager) -> None:
        """clear_cache() removes all cached prompts."""
        manager.load_prompt("system")
        manager.load_prompt("review")
        manager.clear_cache()
        # After clearing, cache should be empty
        assert len(manager._cache) == 0

    def test_list_available(self, manager: PromptManager) -> None:
        """list_available() returns all prompt template names."""
        available = manager.list_available()
        assert "system" in available
        assert "review" in available
        assert "simple" in available
