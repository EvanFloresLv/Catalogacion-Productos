# ---------------------------------------------------------------------
# Standard libraries
# ---------------------------------------------------------------------
import threading
from typing import Dict, Any, List

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from google import genai
from google.auth import default
from google.genai.types import Content, Part, GenerateContentConfig
from google.api_core import exceptions as google_exceptions

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from config.settings import gemini_settings
from utils.circuit_breaker import CircuitBreaker
from application.ports.llm_service import LLMService
from infrastructure.llm.errors import (
    TransientLLMError,
    ValidationLLMError,
    ProviderLLMError,
    PermanentLLMError,
)
from utils.retry import sync_exponential_backoff_retry_sync


class LLMClient(LLMService):
    """
    Features:
    - Circuit breaker for fault tolerance
    - Exponential backoff retry
    - Thread-safe operations
    - Comprehensive error handling
    """

    DEFAULT_MODEL = "gemini-2.5-flash"
    DEFAULT_TEMPERATURE = 0.7

    def __init__(
        self,
        *,
        model: str | None = None,
        location: str | None = None,
        scope: list[str] | None = None,
        timeout_seconds: float = 30.0,
        retry_attempts: int = 3,
        temperature: float | None = None,
        max_tokens: int | None = None,
        enable_fallback: bool = False,
    ) -> None:
        """
        Initialize Gemini LLM client.

        Args:
            model: Model name (e.g., "gemini-2.5-pro", "gemini-2.5-flash")
            location: GCP region (default from settings)
            scope: OAuth2 scopes for authentication
            timeout_seconds: Request timeout
            retry_attempts: Number of retry attempts
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
            enable_fallback: Enable model fallback on failure
        """
        self.model = model or gemini_settings.llm.model_fast or self.DEFAULT_MODEL
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.temperature = temperature or self.DEFAULT_TEMPERATURE
        self.max_tokens = max_tokens
        self.enable_fallback = enable_fallback

        self._breaker = CircuitBreaker(
            failure_threshold=5,
            reset_timeout=60
        )
        self._lock = threading.Lock()

        # Authenticate with Google Cloud
        self._credentials, self._project = default(
            scopes=scope or ["https://www.googleapis.com/auth/cloud-platform"]
        )
        self._location = location or gemini_settings.location or "us-central1"

        # Initialize Gemini client
        self._client = genai.Client(
            vertexai=True,
            project=self._project,
            location=self._location,
            credentials=self._credentials,
        )

    # =============================================================
    # PUBLIC API
    # =============================================================

    def chat(self, prompt: Dict[str, Any], **kwargs) -> str:
        """
        Send chat prompt and get response.

        Args:
            prompt: Dictionary containing:
                - 'system': System prompt (optional)
                - 'user': User message (required)
                - 'schema': Response schema (optional)
                - 'mime_type': Response MIME type (optional)
            **kwargs: Additional generation config (temperature, max_tokens, etc.)

        Returns:
            Generated text response

        Raises:
            ValidationLLMError: Invalid input
            TransientLLMError: Temporary failure (retryable)
            PermanentLLMError: Permanent failure
        """
        if not prompt or not isinstance(prompt, dict):
            raise ValidationLLMError("prompt must be a dictionary")

        if 'user' not in prompt:
            raise ValidationLLMError("prompt must contain 'user' field")

        # Check circuit breaker
        with self._lock:
            self._breaker.record_success()

        # Generate response with retry
        try:
            return self._generate_with_retry(prompt, **kwargs)
        except Exception:
            with self._lock:
                self._breaker.record_failure()
            raise

    # =============================================================
    # GENERATION
    # =============================================================

    def _generate_with_retry(self, prompt: Dict[str, Any], **kwargs) -> str:
        """Generate response with exponential backoff retry."""

        def do_request():
            return self._generate(prompt, **kwargs)

        try:
            result = sync_exponential_backoff_retry_sync(
                do_request,
                attempts=self.retry_attempts,
                base_delay=1.0,
                max_delay=10.0,
                retry_on=(TransientLLMError, PermanentLLMError)
            )

            with self._lock:
                self._breaker.record_success()

            return result

        except google_exceptions.ResourceExhausted as e:
            raise TransientLLMError(f"Rate limit exceeded: {e}") from e
        except google_exceptions.ServiceUnavailable as e:
            raise TransientLLMError(f"Service unavailable: {e}") from e
        except google_exceptions.DeadlineExceeded as e:
            raise TransientLLMError(f"Request timeout: {e}") from e
        except google_exceptions.InvalidArgument as e:
            raise ValidationLLMError(f"Invalid request: {e}") from e
        except Exception as e:
            raise PermanentLLMError(f"LLM generation failed: {e}") from e


    def _generate(self, prompt: Dict[str, Any], **kwargs) -> str:
        """Generate response from Gemini."""

        # Build contents from prompt
        contents = self._prompt_to_contents(prompt)

        # Schema and mime_type from prompt are defaults, kwargs can override
        if 'schema' in prompt and 'schema' not in kwargs:
            kwargs['schema'] = prompt['schema']
        if 'mime_type' in prompt and 'mime_type' not in kwargs:
            kwargs['mime_type'] = prompt['mime_type']

        # Debug output
        print(f"\n{'='*10} LLM | Client Debug {'='*10}")
        print(f"Schema in kwargs: {kwargs.get('schema', 'NOT SET')}")
        print(f"MIME type in kwargs: {kwargs.get('mime_type', 'NOT SET')}")
        print(f"{'='*40}\n")

        config = self._build_config(**kwargs)

        response = self._client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        print(f"Response: {response}")

        if not response.candidates:
            raise ProviderLLMError("No candidates in response")

        candidate = response.candidates[0]

        if not candidate.content or not candidate.content.parts:
            raise ProviderLLMError("No content in response")

        text_parts = [
            part.text for part in candidate.content.parts
            if hasattr(part, 'text') and part.text
        ]

        return "".join(text_parts)


    # =============================================================
    # HELPERS
    # =============================================================

    def _prompt_to_contents(self, prompt: Dict[str, Any]) -> List[Content]:
        """Convert prompt dictionary to Gemini Content format."""

        contents: List[Content] = []

        # Combine system and user messages
        user_text = prompt.get('user', '')
        system_text = prompt.get('system', '')

        # Prepend system message to user message if present
        if system_text:
            full_text = f"{system_text}\n\n{user_text}"
        else:
            full_text = user_text

        if not full_text.strip():
            raise ValidationLLMError("User message cannot be empty")

        # Create single user content
        contents.append(
            Content(
                role="user",
                parts=[Part.from_text(text=full_text)]
            )
        )

        return contents


    def _build_config(self, **kwargs) -> GenerateContentConfig:

        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        top_p = kwargs.get("top_p")
        top_k = kwargs.get("top_k")
        schema = kwargs.get("schema")
        mime_type = kwargs.get("mime_type")

        stop_sequences = kwargs.get("stop_sequences")

        config_dict = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        if top_p is not None:
            config_dict["top_p"] = top_p
        if top_k is not None:
            config_dict["top_k"] = top_k
        if stop_sequences:
            config_dict["stop_sequences"] = stop_sequences
        if mime_type is not None:
            config_dict["response_mime_type"] = mime_type
        if schema is not None:
            config_dict["response_schema"] = schema

        return GenerateContentConfig(**config_dict)