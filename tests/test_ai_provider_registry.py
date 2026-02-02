"""Unit tests for AI provider registry and imports."""

from dumpcode.ai.base import AIClient


class TestProviderRegistryCompleteness:
    """Test that all AI providers are properly registered."""
    
    def test_provider_registry_completeness(self):
        """Verify that the registration mechanism actually triggers for all providers."""
        # Providers are registered via dumpcode.ai package init
        
        # Assertions
        assert "anthropic" in AIClient.registry
        assert "google" in AIClient.registry
        assert "openai" in AIClient.registry
        assert "deepseek" in AIClient.registry
        
        # Verify the registry contains the actual classes
        from dumpcode.ai.claude import ClaudeClient
        from dumpcode.ai.gemini import GeminiClient
        from dumpcode.ai.openai_client import OpenAIClient
        from dumpcode.ai.deepseek import DeepSeekClient
        
        assert AIClient.registry["anthropic"] == ClaudeClient
        assert AIClient.registry["google"] == GeminiClient
        assert AIClient.registry["openai"] == OpenAIClient
        assert AIClient.registry["deepseek"] == DeepSeekClient
    
    def test_provider_get_provider_name(self):
        """Test that each provider returns the correct provider name."""
        from dumpcode.ai.claude import ClaudeClient
        from dumpcode.ai.gemini import GeminiClient
        from dumpcode.ai.openai_client import OpenAIClient
        from dumpcode.ai.deepseek import DeepSeekClient
        
        assert ClaudeClient.get_provider_name() == "anthropic"
        assert GeminiClient.get_provider_name() == "google"
        assert OpenAIClient.get_provider_name() == "openai"
        assert DeepSeekClient.get_provider_name() == "deepseek"
    
    def test_provider_supports_model(self):
        """Test that each provider correctly identifies its own models."""
        from dumpcode.ai.claude import ClaudeClient
        from dumpcode.ai.gemini import GeminiClient
        from dumpcode.ai.openai_client import OpenAIClient
        from dumpcode.ai.deepseek import DeepSeekClient
        
        # Test Claude model detection
        assert ClaudeClient.supports_model("claude-sonnet-4-5-20250929") is True
        assert ClaudeClient.supports_model("claude-opus-4-5-20251101") is True
        assert ClaudeClient.supports_model("gpt-4o") is False  # Wrong provider
        
        # Test Gemini model detection
        assert GeminiClient.supports_model("gemini-3-flash-preview") is True
        assert GeminiClient.supports_model("gemini-2.5-pro") is True
        assert GeminiClient.supports_model("claude-sonnet") is False  # Wrong provider
        
        # Test OpenAI model detection
        assert OpenAIClient.supports_model("gpt-5.2") is True
        assert OpenAIClient.supports_model("gpt-4o") is True
        assert OpenAIClient.supports_model("o1") is True
        assert OpenAIClient.supports_model("gemini-pro") is False  # Wrong provider
        
        # Test DeepSeek model detection
        assert DeepSeekClient.supports_model("deepseek-chat") is True
        assert DeepSeekClient.supports_model("deepseek-v3.2-chat") is True
        assert DeepSeekClient.supports_model("gpt-4o") is False  # Wrong provider
    
    def test_registry_is_dictionary(self):
        """Test that the registry is a dictionary (not a list)."""
        assert isinstance(AIClient.registry, dict)
        assert not isinstance(AIClient.registry, list)
    
    def test_registry_duplicate_registration(self):
        """Test that registering the same provider twice doesn't cause issues."""
        original_registry = AIClient.registry.copy()
        
        # Try to register a provider that's already registered
        from dumpcode.ai.claude import ClaudeClient
        ClaudeClient.register()  # Should be idempotent
        
        # Registry should remain unchanged
        assert AIClient.registry == original_registry