"""Base class for AI provider clients."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generator, Optional
import logging


@dataclass
class AIResponse:
    """Container for AI model response.
    
    Attributes:
        content: The full text response from the model
        model: The model that generated the response
        input_tokens: Number of input tokens (if available)
        output_tokens: Number of output tokens (if available)
        error: Error message if the request failed
    """
    content: str
    model: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    error: Optional[str] = None
    
    @property
    def success(self) -> bool:
        """Check if the AI response was successful (no errors)."""
        return self.error is None


@dataclass
class StreamChunk:
    """A single packet of data from the AI stream."""
    text: Optional[str] = None
    response: Optional[AIResponse] = None

    @property
    def is_final(self) -> bool:
        """Check if this chunk contains the final AIResponse metadata."""
        return self.response is not None


class AIClient(ABC):
    """Abstract base class for AI provider clients."""
    
    registry: dict[str, type["AIClient"]] = {}
    
    @classmethod
    def register(cls) -> None:
        """Register the provider by its name."""
        name = cls.get_provider_name()
        AIClient.registry[name] = cls
    
    def __init__(self, api_key: str, logger: Optional[logging.Logger] = None):
        """Initialize the AI client.
        
        Args:
            api_key: API key for the provider
            logger: Optional logger instance
        """
        self.api_key = api_key
        self.logger = logger or logging.getLogger(__name__)
    
    @abstractmethod
    def stream(self, prompt: str, model: str) -> Generator[StreamChunk, None, None]:
        """Stream a response from the AI model.
        
        Args:
            prompt: The full prompt to send
            model: The model identifier
            
        Yields:
            Chunks of the response text as they arrive
            
        Returns:
            AIResponse with full content and metadata after completion
        """
        pass
    
    @classmethod
    @abstractmethod
    def get_provider_name(cls) -> str:
        """Return the provider name (e.g., 'anthropic', 'google')."""
        pass
    
    @classmethod
    @abstractmethod
    def supports_model(cls, model: str) -> bool:
        """Check if this client supports the given model string.
        
        Args:
            model: Model identifier string
            
        Returns:
            True if this client can handle the model
        """
        pass
    
    @abstractmethod
    def ping(self, model: str) -> None:
        """Test connectivity to the AI provider with a minimal request.
        
        Args:
            model: The model identifier to test
            
        Raises:
            Exception: If the ping fails (connection, auth, or model not found)
        """
        pass