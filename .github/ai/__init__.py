"""
SmartCityApp AI Maintainer.

An AI-powered GitHub repository maintainer that automates issue assignment,
pull request review, contributor welcoming, and code quality enforcement.

This package lives inside .github/ai/ to co-locate all automation code
with GitHub Actions workflows, prompts, and configuration.

Architecture:
    Event Layer   → event_parser.py    (GitHub payloads → typed models)
    Engine Layer  → rule_engine.py     (deterministic checks, no AI)
                  → review_engine.py   (AI-powered review orchestration)
                  → assignment_engine.py (auto issue assignment)
    AI Layer      → hf_client.py       (BaseAIClient → HuggingFaceClient)
                  → prompt_manager.py  (template loading and rendering)
    GitHub Layer  → github_client.py   (GitHub REST API wrapper)
    Foundation    → models.py          (domain dataclasses and enums)
                  → config.py          (env + YAML configuration)
                  → utils.py           (logging, JSON parsing, utilities)
"""

__version__ = "0.1.0"

from .config import BotConfig, load_config, ModelConfig, RetryConfig
from .models import (
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
from .github_client import GitHubClient
from .hf_client import BaseAIClient, HuggingFaceClient
from .event_parser import EventParser
from .prompt_manager import PromptManager
from .rule_engine import RuleEngine
from .repository_analyzer import RepositoryAnalyzer
from .utils import get_logger, setup_logging

__all__ = [
    # Version
    "__version__",
    # Config
    "BotConfig",
    "load_config",
    "ModelConfig",
    "RetryConfig",
    # Models
    "AssignmentResult",
    "EventType",
    "GitHubEvent",
    "IssueContext",
    "PRContext",
    "ReviewDecision",
    "ReviewResult",
    "RuleEngineResult",
    "RuleSeverity",
    "RuleViolation",
    # Clients
    "GitHubClient",
    "BaseAIClient",
    "HuggingFaceClient",
    # Modules
    "EventParser",
    "PromptManager",
    "RuleEngine",
    "RepositoryAnalyzer",
    # Utilities
    "get_logger",
    "setup_logging",
]
