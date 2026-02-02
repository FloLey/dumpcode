"""Anthropic Claude AI client implementation."""

from typing import Generator, Optional
import logging

from .base import AIClient, AIResponse, StreamChunk


# Model prefixes that indicate Claude models
CLAUDE_PREFIXES = ("claude-", "claude_")


class ClaudeClient(AIClient):
    """Client for Anthropic's Claude API."""
    
    def __init__(self, api_key: str, logger: Optional[logging.Logger] = None):
        super().__init__(api_key, logger)
        self._client = None
    
    def _get_client(self):
        """Lazy-load and initialize the Anthropic SDK client.

        Raises:
            ImportError: If the 'anthropic' package is not installed.
        """
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(
                    api_key=self.api_key,
                    timeout=60.0  # Explicit timeout
                )
            except (ImportError, AttributeError):
                # AttributeError can happen if anthropic is in sys.modules but is None
                # or otherwise broken
                raise ImportError(
                    "Anthropic SDK not installed. "
                    "Install with: pip install 'dumpcode[claude]'"
                )
        return self._client
    
    def stream(self, prompt: str, model: str) -> Generator[StreamChunk, None, None]:
        """Stream a response from Claude.
        
        Args:
            prompt: The full prompt to send
            model: The model identifier (e.g., 'claude-sonnet-4-5-20250929')
            
        Yields:
            StreamChunk objects containing text chunks or final response
        """
        client = self._get_client()
        full_content = ""
        input_tokens = 0
        output_tokens = 0
        
        try:
            with client.messages.stream(
                model=model,
                max_tokens=16384,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    full_content += text
                    yield StreamChunk(text=text)
                
                # Get final message for token counts
                final_message = stream.get_final_message()
                input_tokens = final_message.usage.input_tokens
                output_tokens = final_message.usage.output_tokens
            
            yield StreamChunk(response=AIResponse(
                content=full_content,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            ))
            
        except Exception as e:
            self.logger.error(f"Claude API error: {e}")
            yield StreamChunk(response=AIResponse(
                content=full_content,
                model=model,
                error=str(e)
            ))
    
    @classmethod
    def get_provider_name(cls) -> str:
        """Return the provider name: 'anthropic'."""
        return "anthropic"
    
    @classmethod
    def supports_model(cls, model: str) -> bool:
        """Check if model string indicates a Claude model.
        
        Args:
            model: Model identifier string
        """
        return model.lower().startswith(CLAUDE_PREFIXES)
    
    def ping(self, model: str) -> None:
        """Test connectivity to Claude API with a minimal request.
        
        Args:
            model: The model identifier to test
            
        Raises:
            Exception: If the ping fails (connection, auth, or model not found)
        """
        client = self._get_client()
        client.messages.create(
            model=model,
            max_tokens=1,
            messages=[{"role": "user", "content": "."}]
        )


ClaudeClient.register()