"""
AI client abstraction and Hugging Face Inference API implementation.

Defines the abstract base class BaseAIClient that all AI providers must
implement, and provides a concrete HuggingFaceClient implementation.
This design follows the Open/Closed Principle — adding a new AI provider
(OpenAI, Ollama, GitHub Models) requires only implementing BaseAIClient,
with zero changes to the review engine or any other module.

The AI client layer knows nothing about GitHub, issues, or pull requests.
It receives prompt messages and returns text responses. All domain-specific
interpretation happens in the engine layer.

Classes:
    AIClientError: Base exception for AI client errors.
    BaseAIClient: Abstract base class for AI providers.
    HuggingFaceClient: Hugging Face Inference API implementation.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

import httpx

from .config import ModelConfig, RetryConfig
from .utils import get_logger

logger = get_logger("hf_client")


class AIClientError(Exception):
    """Base exception for AI client errors.

    Attributes:
        message: Description of the error.
        status_code: HTTP status code if applicable (0 for non-HTTP errors).
        retryable: Whether the error is transient and may succeed on retry.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 0,
        retryable: bool = False,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        super().__init__(message)


class BaseAIClient(ABC):
    """Abstract base class for AI provider clients.

    All AI providers (Hugging Face, OpenAI, Ollama, GitHub Models) must
    implement this interface. The review engine and other consumers
    depend only on this abstraction, enabling provider switching via
    configuration without code changes.

    Subclasses must implement:
        - chat_completion: Send messages and get a text response.
        - health_check: Verify that the AI service is reachable.
    """

    @abstractmethod
    def chat_completion(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """Send a chat completion request and return the response text.

        Args:
            messages: List of message dicts with 'role' and 'content'.
                      Roles: 'system', 'user', 'assistant'.
            max_tokens: Override the default max tokens for this request.
            temperature: Override the default temperature for this request.

        Returns:
            The assistant's response text.

        Raises:
            AIClientError: If the request fails after all retries.
        """

    @abstractmethod
    def health_check(self) -> bool:
        """Verify that the AI service is reachable and responsive.

        Used during startup to fail fast if the AI provider is down,
        rather than discovering failures during actual review processing.

        Returns:
            True if the service is reachable, False otherwise.
        """


class HuggingFaceClient(BaseAIClient):
    """Hugging Face Inference API client.

    Implements BaseAIClient using the Hugging Face serverless
    Inference API v1 (OpenAI-compatible chat completions endpoint).

    Supports configurable model selection, exponential backoff retries,
    rate limit detection, and timeout handling.

    Args:
        token: Hugging Face API token.
        model_config: Configuration for the AI model to use.
        retry_config: Retry policy for transient failures.
        base_url: Override the API base URL (for custom endpoints).
        timeout: HTTP request timeout in seconds.

    Example:
        >>> from .config import ModelConfig, RetryConfig
        >>> model = ModelConfig(name="qwen", model_id="Qwen/Qwen2.5-Coder-32B-Instruct")
        >>> client = HuggingFaceClient(token="hf_xxx", model_config=model, retry_config=RetryConfig())
        >>> response = client.chat_completion([{"role": "user", "content": "Hello"}])
    """

    BASE_URL = "https://router.huggingface.co/novita"

    def __init__(
        self,
        token: str,
        model_config: ModelConfig,
        retry_config: RetryConfig,
        base_url: str = "",
        timeout: float = 120.0,
    ) -> None:
        """Initialize the Hugging Face client.

        Args:
            token: Hugging Face API token.
            model_config: Model configuration with model_id and defaults.
            retry_config: Retry policy configuration.
            base_url: Override API base URL.
            timeout: HTTP request timeout in seconds.
        """
        self._model_config = model_config
        self._retry_config = retry_config
        self._base_url = base_url or self.BASE_URL

        self._client = httpx.Client(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

        logger.info(
            "HuggingFaceClient initialized (model=%s, max_tokens=%d, temp=%.2f)",
            model_config.model_id,
            model_config.max_tokens,
            model_config.temperature,
        )

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """Send a chat completion request to the Hugging Face Inference API.

        Constructs the request payload, executes with retry logic,
        and extracts the assistant's response from the API response.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            max_tokens: Override max tokens (uses model default if None).
            temperature: Override temperature (uses model default if None).

        Returns:
            The assistant's response text.

        Raises:
            AIClientError: If the request fails after all retry attempts.
        """
        payload = self._build_payload(messages, max_tokens, temperature)

        logger.debug(
            "Sending chat completion request (%d messages, model=%s)",
            len(messages),
            self._model_config.model_id,
        )

        response_text = self._execute_with_retry(payload)

        logger.debug(
            "Received response (%d chars)", len(response_text)
        )

        return response_text

    def health_check(self) -> bool:
        """Check if the Hugging Face Inference API is reachable.

        Sends a minimal chat completion request to verify connectivity
        and model availability.

        Returns:
            True if the API responds successfully, False otherwise.
        """
        try:
            self.chat_completion(
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            logger.info("Health check passed")
            return True
        except AIClientError as e:
            logger.warning("Health check failed: %s", e.message)
            return False

    def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        self._client.close()
        logger.debug("HuggingFaceClient connection closed")

    def _build_payload(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None,
        temperature: float | None,
    ) -> dict:
        """Build the request payload for the chat completions endpoint.

        Args:
            messages: Chat messages to send.
            max_tokens: Token limit override.
            temperature: Temperature override.

        Returns:
            Dictionary matching the HF Inference API request schema.
        """
        return {
            "model": self._model_config.model_id,
            "messages": messages,
            "max_tokens": max_tokens or self._model_config.max_tokens,
            "temperature": (
                temperature
                if temperature is not None
                else self._model_config.temperature
            ),
            "stream": False,
        }

    def _execute_with_retry(self, payload: dict) -> str:
        """Execute the API request with exponential backoff retry logic.

        Retries on transient errors (rate limits, server errors) up to
        the configured maximum number of attempts. Uses exponential
        backoff: delay = backoff_factor ** attempt.

        Args:
            payload: The request payload dictionary.

        Returns:
            The assistant's response text.

        Raises:
            AIClientError: If all retry attempts are exhausted or
                          a non-retryable error occurs.
        """
        last_error: Exception | None = None

        for attempt in range(self._retry_config.max_retries + 1):
            try:
                response = self._client.post(
                    "/v1/chat/completions",
                    json=payload,
                )

                # Check for retryable status codes
                if response.status_code in self._retry_config.retry_status_codes:
                    delay = self._retry_config.backoff_factor ** attempt
                    logger.warning(
                        "Retryable error (HTTP %d), attempt %d/%d, "
                        "waiting %.1fs",
                        response.status_code,
                        attempt + 1,
                        self._retry_config.max_retries + 1,
                        delay,
                    )
                    last_error = AIClientError(
                        f"HTTP {response.status_code}: {response.text}",
                        status_code=response.status_code,
                        retryable=True,
                    )
                    time.sleep(delay)
                    continue

                # Non-retryable HTTP errors
                if not response.is_success:
                    raise AIClientError(
                        f"HTTP {response.status_code}: {response.text}",
                        status_code=response.status_code,
                        retryable=False,
                    )

                # Parse successful response
                return self._parse_response(response.json())

            except httpx.TimeoutException as e:
                delay = self._retry_config.backoff_factor ** attempt
                logger.warning(
                    "Request timeout, attempt %d/%d, waiting %.1fs",
                    attempt + 1,
                    self._retry_config.max_retries + 1,
                    delay,
                )
                last_error = e
                if attempt < self._retry_config.max_retries:
                    time.sleep(delay)

            except httpx.RequestError as e:
                logger.error("Request error: %s", str(e))
                last_error = e
                break  # Connection errors are typically not transient

        raise AIClientError(
            f"All {self._retry_config.max_retries + 1} attempts failed. "
            f"Last error: {last_error}",
            retryable=False,
        )

    def _parse_response(self, response_data: dict) -> str:
        """Extract the assistant's message from the API response.

        Args:
            response_data: Parsed JSON response from the API.

        Returns:
            The text content of the assistant's response.

        Raises:
            AIClientError: If the response format is unexpected.
        """
        try:
            choices = response_data.get("choices", [])
            if not choices:
                raise AIClientError(
                    "No choices in API response",
                    retryable=False,
                )

            message = choices[0].get("message", {})
            content = message.get("content", "")

            if not content:
                raise AIClientError(
                    "Empty content in API response",
                    retryable=False,
                )

            return content

        except (KeyError, IndexError, TypeError) as e:
            raise AIClientError(
                f"Unexpected response format: {e}",
                retryable=False,
            ) from e
