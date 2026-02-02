"""OpenAI GPT client implementation."""

from typing import Generator, Optional
import logging

from .base import AIClient, AIResponse, StreamChunk


GPT_PREFIXES = ("gpt-", "gpt_", "o1", "o3", "o4")


class OpenAIClient(AIClient):
    """Client for OpenAI's GPT API."""
    
    def __init__(self, api_key: str, logger: Optional[logging.Logger] = None):
        super().__init__(api_key, logger)
        self._client = None
    
    def _get_client(self):
        """Lazy-load and initialize the OpenAI SDK client.

        Raises:
            ImportError: If the 'openai' package is not installed.
        """
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    timeout=60.0  # Explicit timeout
                )
            except (ImportError, AttributeError):
                # AttributeError can happen if openai is in sys.modules but is None
                # or otherwise broken
                raise ImportError(
                    "OpenAI SDK not installed. "
                    "Install with: pip install 'dumpcode[openai]'"
                )
        return self._client
    
    def stream(self, prompt: str, model: str) -> Generator[StreamChunk, None, None]:
        """Stream a response from GPT.
        
        Args:
            prompt: The full prompt to send
            model: The model identifier (e.g., 'gpt-5.2')
            
        Yields:
            StreamChunk objects containing text chunks or final response
        """
        client = self._get_client()
        full_content = ""
        
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                stream_options={"include_usage": True}
            )
            
            input_tokens = None
            output_tokens = None
            
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    full_content += text
                    yield StreamChunk(text=text)
                
                # Usage comes in the final chunk
                if chunk.usage:
                    input_tokens = chunk.usage.prompt_tokens
                    output_tokens = chunk.usage.completion_tokens
            
            yield StreamChunk(response=AIResponse(
                content=full_content,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            ))
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            yield StreamChunk(response=AIResponse(
                content=full_content,
                model=model,
                error=str(e)
            ))
    
    @classmethod
    def get_provider_name(cls) -> str:
        """Return the provider name: 'openai'."""
        return "openai"
    
    @classmethod
    def supports_model(cls, model: str) -> bool:
        """Check if model string indicates a GPT model.
        
        Args:
            model: Model identifier string
        """
        lower = model.lower()
        return any(lower.startswith(p) for p in GPT_PREFIXES)
    
    def ping(self, model: str) -> None:
        """Test connectivity to OpenAI API with a minimal request.
        
        Args:
            model: The model identifier to test
            
        Raises:
            Exception: If the ping fails (connection, auth, or model not found)
        """
        client = self._get_client()
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "."}],
            max_tokens=1
        )


OpenAIClient.register()