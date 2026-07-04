"""
Configuration loader for the AI Maintainer.

Loads bot configuration from two sources in priority order:
1. Environment variables (GITHUB_TOKEN, HF_TOKEN, GITHUB_REPOSITORY, LOG_LEVEL)
2. YAML configuration file (.github/config/bot.yml)

Environment variables always override YAML values for secrets and
runtime-specific settings. The YAML file contains model registry,
retry policies, assignment rules, and other tunables.

Classes:
    ConfigurationError: Raised when required configuration is missing or invalid.
    ModelConfig: Per-model configuration (HF model ID, max_tokens, temperature).
    RetryConfig: Retry policy for external API calls.
    RepositoryConfig: Repository owner and name.
    BotConfig: Top-level configuration aggregating all sub-configs.

Functions:
    load_config: Main entry point for loading and validating configuration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .utils import get_logger, mask_secret

logger = get_logger("config")


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid.

    Provides actionable error messages to help operators diagnose
    and fix configuration issues quickly (e.g., missing secrets,
    invalid YAML, unknown model names).
    """


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for a single AI model.

    Each entry in the model registry maps a human-friendly name
    to its Hugging Face model ID and inference parameters.

    Attributes:
        name: Human-friendly model name (e.g., 'deepseek-v4-flash').
        model_id: Full Hugging Face model identifier
                  (e.g., 'deepseek-ai/DeepSeek-V3-0324').
        max_tokens: Maximum tokens for the model's response.
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative).
    """

    name: str
    model_id: str
    max_tokens: int = 4096
    temperature: float = 0.3


@dataclass(frozen=True)
class RetryConfig:
    """Retry policy for external API calls (GitHub, Hugging Face).

    Controls exponential backoff behavior when API calls fail due
    to transient errors (rate limits, server errors).

    Attributes:
        max_retries: Maximum number of retry attempts.
        backoff_factor: Multiplier for exponential backoff
                        (delay = backoff_factor ** attempt).
        retry_status_codes: HTTP status codes that trigger a retry.
    """

    max_retries: int = 3
    backoff_factor: float = 2.0
    retry_status_codes: tuple[int, ...] = (429, 500, 502, 503)


@dataclass(frozen=True)
class RepositoryConfig:
    """Repository identification.

    Parsed from the GITHUB_REPOSITORY environment variable
    (format: 'owner/name') or overridden in bot.yml for local development.

    Attributes:
        owner: Repository owner (GitHub username or organization).
        name: Repository name.
    """

    owner: str
    name: str

    @property
    def full_name(self) -> str:
        """Full repository name in 'owner/name' format."""
        return f"{self.owner}/{self.name}"


@dataclass
class BotConfig:
    """Top-level configuration for the AI Maintainer bot.

    Aggregates all sub-configurations and secrets needed by the bot.
    Created by the load_config() function and passed via dependency
    injection to all modules that need configuration.

    Attributes:
        github_token: GitHub personal access token or GITHUB_TOKEN.
        hf_token: Hugging Face API token.
        repository: Repository owner and name.
        active_model: Configuration for the currently active AI model.
        model_registry: All available model configurations keyed by name.
        retry: Retry policy for API calls.
        assignment: Assignment engine configuration.
        welcome: Welcome message configuration.
        review: Review engine configuration.
        labels: Label name mappings.
        log_level: Logging level string.
        config_version: Configuration file version for schema evolution.
    """

    github_token: str = ""
    hf_token: str = ""
    repository: RepositoryConfig = field(
        default_factory=lambda: RepositoryConfig(owner="", name="")
    )
    active_model: ModelConfig = field(
        default_factory=lambda: ModelConfig(name="default", model_id="")
    )
    model_registry: dict[str, ModelConfig] = field(default_factory=dict)
    retry: RetryConfig = field(default_factory=RetryConfig)
    assignment: dict[str, Any] = field(default_factory=dict)
    welcome: dict[str, Any] = field(default_factory=dict)
    review: dict[str, Any] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)
    log_level: str = "INFO"
    config_version: int = 1


def load_config(config_path: str | None = None) -> BotConfig:
    """Load and validate bot configuration from environment and YAML.

    This is the main entry point for configuration loading. It:
    1. Reads environment variables for secrets and runtime settings.
    2. Loads the YAML configuration file for tunables.
    3. Resolves the active AI model from the model registry.
    4. Validates that all required values are present.

    Args:
        config_path: Optional path to the YAML configuration file.
                     Defaults to '.github/config/bot.yml' relative
                     to the current working directory.

    Returns:
        A fully populated BotConfig instance.

    Raises:
        ConfigurationError: If required secrets are missing, the YAML
                           file is invalid, or the configured model
                           is not found in the registry.

    Example:
        >>> config = load_config()
        >>> print(config.repository.full_name)
        'Rajath2005/SmartCityApp'
    """
    # Determine config file path
    if config_path is None:
        config_path = os.environ.get(
            "BOT_CONFIG_PATH",
            str(Path.cwd() / ".github" / "config" / "bot.yml"),
        )

    # Load YAML configuration
    yaml_config = _load_yaml(config_path)

    # Load secrets from environment
    github_token = os.environ.get("GITHUB_TOKEN", "")
    hf_token = os.environ.get("HF_TOKEN", "")

    # Validate required secrets
    _validate_secrets(github_token, hf_token)

    # Parse repository
    repository = _parse_repository(yaml_config)

    # Parse model registry and resolve active model
    model_registry = _parse_model_registry(yaml_config)
    active_model = _resolve_active_model(yaml_config, model_registry)

    # Parse retry config
    retry = _parse_retry_config(yaml_config)

    # Parse log level (env var overrides YAML)
    log_level = os.environ.get(
        "LOG_LEVEL",
        yaml_config.get("logging", {}).get("level", "INFO"),
    )

    config = BotConfig(
        github_token=github_token,
        hf_token=hf_token,
        repository=repository,
        active_model=active_model,
        model_registry=model_registry,
        retry=retry,
        assignment=yaml_config.get("assignment", {}),
        welcome=yaml_config.get("welcome", {}),
        review=yaml_config.get("review", {}),
        labels=yaml_config.get("labels", {}),
        log_level=log_level,
        config_version=yaml_config.get("version", 1),
    )

    logger.info(
        "Configuration loaded successfully "
        "(version=%d, model=%s, repo=%s)",
        config.config_version,
        config.active_model.name,
        config.repository.full_name,
    )
    logger.debug(
        "Tokens: GITHUB_TOKEN=%s, HF_TOKEN=%s",
        mask_secret(github_token) if github_token else "<not set>",
        mask_secret(hf_token) if hf_token else "<not set>",
    )

    return config


def _load_yaml(path: str) -> dict[str, Any]:
    """Load and parse a YAML configuration file.

    Args:
        path: Absolute or relative path to the YAML file.

    Returns:
        Parsed YAML content as a dictionary.
        Returns an empty dict if the file doesn't exist.

    Raises:
        ConfigurationError: If the file exists but contains invalid YAML.
    """
    config_path = Path(path)

    if not config_path.exists():
        logger.warning(
            "Configuration file not found at '%s', using defaults", path
        )
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
            return content if isinstance(content, dict) else {}
    except yaml.YAMLError as e:
        raise ConfigurationError(
            f"Invalid YAML in configuration file '{path}': {e}"
        ) from e


def _validate_secrets(github_token: str, hf_token: str) -> None:
    """Validate that required secrets are present in the environment.

    Args:
        github_token: The GitHub token value.
        hf_token: The Hugging Face token value.

    Raises:
        ConfigurationError: If either token is missing or empty.
    """
    missing = []

    if not github_token:
        missing.append("GITHUB_TOKEN")
    if not hf_token:
        missing.append("HF_TOKEN")

    if missing:
        raise ConfigurationError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Set them in your environment or GitHub Actions secrets."
        )


def _parse_repository(yaml_config: dict[str, Any]) -> RepositoryConfig:
    """Parse repository configuration from environment and YAML.

    Priority: GITHUB_REPOSITORY env var > YAML repository section.

    Args:
        yaml_config: Parsed YAML configuration dictionary.

    Returns:
        A RepositoryConfig instance.

    Raises:
        ConfigurationError: If no repository can be determined from
                           either source.
    """
    # Try environment variable first (set by GitHub Actions)
    github_repo = os.environ.get("GITHUB_REPOSITORY", "")

    if github_repo and "/" in github_repo:
        owner, name = github_repo.split("/", 1)
        return RepositoryConfig(owner=owner, name=name)

    # Fall back to YAML config (for local development)
    repo_config = yaml_config.get("repository", {})
    if isinstance(repo_config, dict):
        owner = repo_config.get("owner", "")
        name = repo_config.get("name", "")
        if owner and name:
            return RepositoryConfig(owner=owner, name=name)

    raise ConfigurationError(
        "Cannot determine repository. Set GITHUB_REPOSITORY environment "
        "variable (format: 'owner/name') or configure repository.owner "
        "and repository.name in bot.yml."
    )


def _parse_model_registry(
    yaml_config: dict[str, Any],
) -> dict[str, ModelConfig]:
    """Parse the model registry from YAML configuration.

    Args:
        yaml_config: Parsed YAML configuration dictionary.

    Returns:
        Dictionary mapping model names to ModelConfig instances.
    """
    registry: dict[str, ModelConfig] = {}
    models_section = yaml_config.get("models", {})
    model_entries = models_section.get("registry", {})

    for name, settings in model_entries.items():
        if not isinstance(settings, dict):
            logger.warning("Skipping invalid model entry: %s", name)
            continue

        model_id = settings.get("id", "")
        if not model_id:
            logger.warning(
                "Model '%s' has no 'id' field, skipping", name
            )
            continue

        registry[name] = ModelConfig(
            name=name,
            model_id=model_id,
            max_tokens=int(settings.get("max_tokens", 4096)),
            temperature=float(settings.get("temperature", 0.3)),
        )

    return registry


def _resolve_active_model(
    yaml_config: dict[str, Any],
    registry: dict[str, ModelConfig],
) -> ModelConfig:
    """Resolve the active model from the registry.

    The active model is determined by:
    1. The AI_MODEL environment variable (if set).
    2. The models.default field in YAML configuration.
    3. The first model in the registry (fallback).

    Args:
        yaml_config: Parsed YAML configuration dictionary.
        registry: Parsed model registry.

    Returns:
        The ModelConfig for the active model.

    Raises:
        ConfigurationError: If the specified default model is not
                           found in the registry and no fallback exists.
    """
    if not registry:
        logger.warning("No models configured in registry, using empty default")
        return ModelConfig(name="unconfigured", model_id="")

    # Check environment variable override
    env_model = os.environ.get("AI_MODEL", "")
    if env_model and env_model in registry:
        logger.info("Using model from AI_MODEL env var: %s", env_model)
        return registry[env_model]

    # Check YAML default
    models_section = yaml_config.get("models", {})
    default_name = models_section.get("default", "")

    if default_name and default_name in registry:
        return registry[default_name]

    if default_name:
        raise ConfigurationError(
            f"Default model '{default_name}' not found in registry. "
            f"Available models: {', '.join(registry.keys())}"
        )

    # Fallback to first model
    first_model = next(iter(registry.values()))
    logger.warning(
        "No default model specified, falling back to: %s", first_model.name
    )
    return first_model


def _parse_retry_config(yaml_config: dict[str, Any]) -> RetryConfig:
    """Parse retry configuration from YAML.

    Args:
        yaml_config: Parsed YAML configuration dictionary.

    Returns:
        A RetryConfig instance with values from YAML or defaults.
    """
    retry_section = yaml_config.get("retry", {})

    if not isinstance(retry_section, dict):
        return RetryConfig()

    status_codes = retry_section.get("retry_status_codes", [429, 500, 502, 503])

    return RetryConfig(
        max_retries=int(retry_section.get("max_retries", 3)),
        backoff_factor=float(retry_section.get("backoff_factor", 2.0)),
        retry_status_codes=tuple(int(code) for code in status_codes),
    )
