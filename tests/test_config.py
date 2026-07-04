"""
Unit tests for the configuration loader module.

Tests YAML loading, environment variable resolution, model registry
parsing, retry config parsing, and validation of required secrets.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add the .github directory to sys.path so we can import the ai package
_REPO_ROOT = Path(__file__).resolve().parent.parent
_GITHUB_DIR = _REPO_ROOT / ".github"
if str(_GITHUB_DIR) not in sys.path:
    sys.path.insert(0, str(_GITHUB_DIR))

from ai.config import (
    BotConfig,
    ConfigurationError,
    ModelConfig,
    RepositoryConfig,
    RetryConfig,
    load_config,
    _load_yaml,
    _parse_model_registry,
    _parse_retry_config,
    _resolve_active_model,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_YAML = """\
version: 1

repository:
  owner: "TestOwner"
  name: "TestRepo"

models:
  default: "test-model"
  registry:
    test-model:
      id: "test-org/test-model-id"
      max_tokens: 2048
      temperature: 0.5

retry:
  max_retries: 2
  backoff_factor: 1.5
  retry_status_codes: [429, 500]

assignment:
  trigger_phrases:
    - "assign me"
  max_open_issues_per_user: 5

logging:
  level: "DEBUG"
"""


@pytest.fixture
def sample_config_file(tmp_path: Path) -> str:
    """Create a temporary YAML config file for testing."""
    config_file = tmp_path / "bot.yml"
    config_file.write_text(SAMPLE_YAML, encoding="utf-8")
    return str(config_file)


@pytest.fixture
def env_with_secrets():
    """Set required environment variables for testing."""
    env_vars = {
        "GITHUB_TOKEN": "ghp_test_token_12345",
        "HF_TOKEN": "hf_test_token_12345",
        "GITHUB_REPOSITORY": "TestOwner/TestRepo",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


# ---------------------------------------------------------------------------
# YAML Loading Tests
# ---------------------------------------------------------------------------

class TestLoadYaml:
    """Tests for the _load_yaml function."""

    def test_load_valid_yaml(self, sample_config_file: str) -> None:
        """Successfully loads a valid YAML file."""
        result = _load_yaml(sample_config_file)
        assert isinstance(result, dict)
        assert result["version"] == 1

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """Returns empty dict when file doesn't exist."""
        result = _load_yaml(str(tmp_path / "nonexistent.yml"))
        assert result == {}

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """Raises ConfigurationError for invalid YAML."""
        bad_file = tmp_path / "bad.yml"
        bad_file.write_text(":\n  invalid: [\nyaml", encoding="utf-8")
        with pytest.raises(ConfigurationError, match="Invalid YAML"):
            _load_yaml(str(bad_file))

    def test_non_dict_yaml_returns_empty(self, tmp_path: Path) -> None:
        """Returns empty dict if YAML contains a non-dict (e.g., list)."""
        list_file = tmp_path / "list.yml"
        list_file.write_text("- item1\n- item2\n", encoding="utf-8")
        result = _load_yaml(str(list_file))
        assert result == {}


# ---------------------------------------------------------------------------
# Model Registry Tests
# ---------------------------------------------------------------------------

class TestParseModelRegistry:
    """Tests for model registry parsing."""

    def test_parse_valid_registry(self) -> None:
        """Parses a valid model registry from YAML config."""
        yaml_config = {
            "models": {
                "default": "model-a",
                "registry": {
                    "model-a": {
                        "id": "org/model-a",
                        "max_tokens": 4096,
                        "temperature": 0.3,
                    },
                    "model-b": {
                        "id": "org/model-b",
                    },
                },
            }
        }
        registry = _parse_model_registry(yaml_config)
        assert len(registry) == 2
        assert registry["model-a"].model_id == "org/model-a"
        assert registry["model-a"].max_tokens == 4096
        # model-b should get defaults
        assert registry["model-b"].max_tokens == 4096
        assert registry["model-b"].temperature == 0.3

    def test_skip_invalid_entries(self) -> None:
        """Skips model entries without an 'id' field."""
        yaml_config = {
            "models": {
                "registry": {
                    "valid": {"id": "org/valid"},
                    "invalid": {"max_tokens": 1024},
                },
            }
        }
        registry = _parse_model_registry(yaml_config)
        assert len(registry) == 1
        assert "valid" in registry

    def test_empty_registry(self) -> None:
        """Returns empty dict when no models are configured."""
        registry = _parse_model_registry({})
        assert registry == {}


# ---------------------------------------------------------------------------
# Active Model Resolution Tests
# ---------------------------------------------------------------------------

class TestResolveActiveModel:
    """Tests for active model resolution."""

    def test_resolve_default_model(self) -> None:
        """Resolves the model specified as default."""
        registry = {
            "model-a": ModelConfig("model-a", "org/a"),
            "model-b": ModelConfig("model-b", "org/b"),
        }
        yaml_config = {"models": {"default": "model-b"}}
        result = _resolve_active_model(yaml_config, registry)
        assert result.name == "model-b"

    def test_env_var_override(self) -> None:
        """AI_MODEL environment variable overrides YAML default."""
        registry = {
            "model-a": ModelConfig("model-a", "org/a"),
            "model-b": ModelConfig("model-b", "org/b"),
        }
        yaml_config = {"models": {"default": "model-a"}}
        with patch.dict(os.environ, {"AI_MODEL": "model-b"}):
            result = _resolve_active_model(yaml_config, registry)
        assert result.name == "model-b"

    def test_unknown_default_raises(self) -> None:
        """Raises ConfigurationError if default model is not in registry."""
        registry = {"model-a": ModelConfig("model-a", "org/a")}
        yaml_config = {"models": {"default": "nonexistent"}}
        with pytest.raises(ConfigurationError, match="not found in registry"):
            _resolve_active_model(yaml_config, registry)

    def test_fallback_to_first(self) -> None:
        """Falls back to first model when no default is specified."""
        registry = {"model-a": ModelConfig("model-a", "org/a")}
        result = _resolve_active_model({}, registry)
        assert result.name == "model-a"


# ---------------------------------------------------------------------------
# Retry Config Tests
# ---------------------------------------------------------------------------

class TestParseRetryConfig:
    """Tests for retry configuration parsing."""

    def test_parse_valid_retry(self) -> None:
        """Parses retry configuration from YAML."""
        yaml_config = {
            "retry": {
                "max_retries": 5,
                "backoff_factor": 3.0,
                "retry_status_codes": [429, 503],
            }
        }
        result = _parse_retry_config(yaml_config)
        assert result.max_retries == 5
        assert result.backoff_factor == 3.0
        assert result.retry_status_codes == (429, 503)

    def test_default_retry(self) -> None:
        """Returns default RetryConfig when not configured."""
        result = _parse_retry_config({})
        assert result.max_retries == 3
        assert result.backoff_factor == 2.0


# ---------------------------------------------------------------------------
# Full Config Loading Tests
# ---------------------------------------------------------------------------

class TestLoadConfig:
    """Tests for the full load_config function."""

    def test_load_full_config(
        self, sample_config_file: str, env_with_secrets: dict
    ) -> None:
        """Successfully loads full configuration from YAML + env."""
        config = load_config(sample_config_file)
        assert config.config_version == 1
        assert config.repository.owner == "TestOwner"
        assert config.repository.name == "TestRepo"
        assert config.active_model.name == "test-model"
        assert config.log_level == "DEBUG"

    def test_missing_secrets_raises(self, sample_config_file: str) -> None:
        """Raises ConfigurationError when secrets are missing."""
        with patch.dict(os.environ, {}, clear=True):
            # Need to also clear GITHUB_REPOSITORY to avoid other errors
            with pytest.raises(ConfigurationError, match="Missing required"):
                load_config(sample_config_file)

    def test_repository_from_env(self, sample_config_file: str) -> None:
        """GITHUB_REPOSITORY env var provides repository config."""
        with patch.dict(
            os.environ,
            {
                "GITHUB_TOKEN": "ghp_test",
                "HF_TOKEN": "hf_test",
                "GITHUB_REPOSITORY": "EnvOwner/EnvRepo",
            },
        ):
            config = load_config(sample_config_file)
        # Env var takes priority over YAML
        assert config.repository.owner == "EnvOwner"
        assert config.repository.name == "EnvRepo"

    def test_log_level_env_override(
        self, sample_config_file: str, env_with_secrets: dict
    ) -> None:
        """LOG_LEVEL env var overrides YAML logging.level."""
        with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}):
            config = load_config(sample_config_file)
        assert config.log_level == "ERROR"


# ---------------------------------------------------------------------------
# Dataclass Tests
# ---------------------------------------------------------------------------

class TestRepositoryConfig:
    """Tests for RepositoryConfig."""

    def test_full_name(self) -> None:
        """full_name property returns 'owner/name' format."""
        repo = RepositoryConfig(owner="Rajath2005", name="SmartCityApp")
        assert repo.full_name == "Rajath2005/SmartCityApp"
