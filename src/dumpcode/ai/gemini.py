"""Google Gemini AI client implementation."""

from typing import Generator, Optional, Any
import logging

from .base import AIClient, AIResponse, StreamChunk


GEMINI_PREFIXES = ("gemini-", "gemini_")


class GeminiClient(AIClient):
    """Client for Google's Gemini API."""
    
    def __init__(self, api_key: str, logger: Optional[logging.Logger] = None):
        super().__init__(api_key, logger)
        self._model_cache: dict[str, Any] = {}  # Cache models by model name
    
    def _get_client(self, model: str):
        """Lazy-load and initialize the Google Generative AI model.

        Args:
            model: Technical model identifier.

        Raises:
            ImportError: If 'google-generativeai' is not installed.
        """
        if model not in self._model_cache:
            try:
                import warnings
                # Silence the google-generativeai deprecation warning
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", FutureWarning)
                    import google.generativeai as genai
                
                genai.configure(api_key=self.api_key)
                self._model_cache[model] = genai.GenerativeModel(model)
            except (ImportError, AttributeError):
                # AttributeError can happen if google.generativeai is in sys.modules but is None
                # or otherwise broken
                raise ImportError(
                    "Google Generative AI SDK not installed. "
                    "Install with: pip install 'dumpcode[gemini]'"
                )
        return self._model_cache[model]
    
    def stream(self, prompt: str, model: str) -> Generator[StreamChunk, None, None]:
        """Stream a response from Gemini.
        
        Args:
            prompt: The full prompt to send
            model: The model identifier (e.g., 'gemini-3-flash')
            
        Yields:
            StreamChunk objects containing text chunks or final response
        """
        client = self._get_client(model)
        full_content = ""
        
        try:
            response = client.generate_content(prompt, stream=True)
            
            for chunk in response:
                if chunk.text:
                    full_content += chunk.text
                    yield StreamChunk(text=chunk.text)
            
            # Gemini provides usage metadata after streaming
            input_tokens = None
            output_tokens = None
            if hasattr(response, 'usage_metadata'):
                input_tokens = getattr(response.usage_metadata, 'prompt_token_count', None)
                output_tokens = getattr(response.usage_metadata, 'candidates_token_count', None)
            
            yield StreamChunk(response=AIResponse(
                content=full_content,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            ))
            
        except Exception as e:
            self.logger.error(f"Gemini API error: {e}")
            yield StreamChunk(response=AIResponse(
                content=full_content,
                model=model,
                error=str(e)
            ))
    
    @classmethod
    def get_provider_name(cls) -> str:
        """Return the provider name: 'google'."""
        return "google"
    
    @classmethod
    def supports_model(cls, model: str) -> bool:
        """Check if model string indicates a Gemini model.
        
        Args:
            model: Model identifier string
        """
        return model.lower().startswith(GEMINI_PREFIXES)
    
    def ping(self, model: str) -> None:
        """Test connectivity to Gemini API with a minimal request.
        
        Args:
            model: The model identifier to test
            
        Raises:
            Exception: If the ping fails (connection, auth, or model not found)
        """
        client = self._get_client(model)
        client.generate_content(".")


GeminiClient.register()