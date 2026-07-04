"""
Logging setup and shared utility functions for the AI Maintainer.

Provides centralized logging configuration with structured output format,
and common utility functions used across all modules. This module has no
dependencies on other AI maintainer modules, making it safe to import
anywhere without circular dependency concerns.

Functions:
    setup_logging: Configure the root logger with structured formatting.
    get_logger: Get a named child logger.
    truncate_text: Safely truncate text for API payloads.
    safe_json_parse: Extract and parse JSON from AI responses.
    mask_secret: Mask sensitive strings for safe logging.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from typing import Any


_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

_logging_initialized: bool = False


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure the root logger with structured ISO timestamp formatting.

    Sets up a single StreamHandler writing to stdout with a consistent
    format: ``[2026-07-02T20:00:00] [INFO] [module] message``.

    This function is idempotent — calling it multiple times will not
    add duplicate handlers. Subsequent calls update the log level only.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Defaults to 'INFO'. Case-insensitive.

    Returns:
        The configured root logger instance.

    Example:
        >>> logger = setup_logging("DEBUG")
        >>> logger.info("Bot started")
    """
    global _logging_initialized

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger = logging.getLogger("ai_maintainer")
    root_logger.setLevel(numeric_level)

    if not _logging_initialized:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric_level)
        formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        _logging_initialized = True
    else:
        # Update existing handler levels on subsequent calls
        for handler in root_logger.handlers:
            handler.setLevel(numeric_level)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a named child logger under the ai_maintainer namespace.

    All loggers are children of the 'ai_maintainer' root logger,
    ensuring consistent formatting and level inheritance.

    Args:
        name: The logger name, typically the module name
              (e.g., 'github_client', 'hf_client').

    Returns:
        A named Logger instance.

    Example:
        >>> logger = get_logger("github_client")
        >>> logger.info("Fetching issue #42")
    """
    return logging.getLogger(f"ai_maintainer.{name}")


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Safely truncate text to a maximum length.

    Used to limit the size of text sent to AI APIs (which have
    token limits) and to keep log messages readable. If the text
    is shorter than max_length, it is returned unchanged.

    Args:
        text: The text to truncate.
        max_length: Maximum allowed length of the returned string,
                    including the suffix. Must be greater than len(suffix).
        suffix: String to append when truncation occurs.
                Defaults to '...'.

    Returns:
        The original text if shorter than max_length, otherwise
        the truncated text with suffix appended.

    Raises:
        ValueError: If max_length is less than or equal to len(suffix).

    Example:
        >>> truncate_text("Hello, World!", 8)
        'Hello...'
        >>> truncate_text("Short", 100)
        'Short'
    """
    if max_length <= len(suffix):
        raise ValueError(
            f"max_length ({max_length}) must be greater than "
            f"suffix length ({len(suffix)})"
        )

    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def safe_json_parse(text: str) -> dict[str, Any] | None:
    """Extract and parse JSON from AI model responses.

    AI models often wrap JSON in markdown code fences like:
    ```json
    {"decision": "APPROVE", ...}
    ```

    This function handles such wrapping by first attempting direct
    JSON parsing, then falling back to extracting content from
    code fences.

    Args:
        text: Raw text response from the AI model, potentially
              containing JSON wrapped in markdown code fences.

    Returns:
        Parsed dictionary if valid JSON is found, None otherwise.

    Example:
        >>> safe_json_parse('{"score": 85}')
        {'score': 85}
        >>> safe_json_parse('```json\\n{"score": 85}\\n```')
        {'score': 85}
        >>> safe_json_parse('not json at all')
        None
    """
    if not text or not text.strip():
        return None

    cleaned = text.strip()

    # Attempt 1: Direct JSON parse
    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, TypeError):
        pass

    # Attempt 2: Extract from markdown code fences
    # Matches ```json ... ``` or ``` ... ```
    fence_pattern = re.compile(
        r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL
    )
    match = fence_pattern.search(cleaned)
    if match:
        try:
            result = json.loads(match.group(1).strip())
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, TypeError):
            pass

    # Attempt 3: Find first { ... } block in the text
    brace_pattern = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)
    match = brace_pattern.search(cleaned)
    if match:
        try:
            result = json.loads(match.group(0))
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, TypeError):
            pass

    return None


def mask_secret(secret: str, visible_chars: int = 4) -> str:
    """Mask a secret string for safe logging.

    Reveals only the last few characters to help with debugging
    (e.g., confirming which token is in use) without exposing
    the full secret value.

    Args:
        secret: The secret string to mask.
        visible_chars: Number of trailing characters to reveal.
                       Defaults to 4.

    Returns:
        Masked string with asterisks replacing hidden characters.
        Returns '****' if the secret is shorter than visible_chars.

    Example:
        >>> mask_secret("ghp_abc123xyz789")
        '**********z789'
        >>> mask_secret("ab")
        '****'
    """
    if len(secret) <= visible_chars:
        return "****"

    masked_length = len(secret) - visible_chars
    return "*" * masked_length + secret[-visible_chars:]
