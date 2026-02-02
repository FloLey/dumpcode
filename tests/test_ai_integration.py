"""Unit tests for AI integration."""

import pytest
from unittest.mock import Mock, patch, MagicMock  # MUST ADD MagicMock HERE

from dumpcode.ai.base import AIResponse
from dumpcode.ai.client import (
    get_client_for_model,
    check_token_limits,
)


class TestModelDetection:
    """Test model string detection."""
    
    @pytest.mark.parametrize("model,expected_provider", [
        ("claude-sonnet-4-5-20250929", "anthropic"),
        ("claude-opus-4-5-20251101", "anthropic"),
        ("gemini-3-pro", "google"),
        ("gemini-2.5-flash", "google"),
        ("gpt-5.2", "openai"),
        ("gpt-5.2-codex", "openai"),
        ("deepseek-chat", "deepseek"),
        ("deepseek-reasoner", "deepseek"),
    ])
    def test_model_to_provider(self, model, expected_provider):
        """Test that models are mapped to correct providers."""
        from dumpcode.ai.claude import ClaudeClient
        from dumpcode.ai.gemini import GeminiClient
        from dumpcode.ai.openai_client import OpenAIClient
        from dumpcode.ai.deepseek import DeepSeekClient
        
        provider_map = {
            "anthropic": ClaudeClient,
            "google": GeminiClient,
            "openai": OpenAIClient,
            "deepseek": DeepSeekClient,
        }
        
        expected_cls = provider_map[expected_provider]
        assert expected_cls.supports_model(model)
    
    def test_unknown_model_raises(self):
        """Test that unknown models raise ValueError."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="Unknown model"):
                get_client_for_model("unknown-model-xyz")


class TestTokenLimits:
    """Test token limit checking."""
    
    def test_gpt4o_within_limit(self):
        """Test Case A: Input 100,000 tokens for gpt-4o. (Limit is 128k - 16k = 112k). Should return (True, None)."""
        logger = Mock()
        should_proceed, error = check_token_limits(100_000, "gpt-4o", logger)
        
        assert should_proceed is True
        assert error is None
        logger.warning.assert_not_called()
    
    def test_gpt4o_exceeds_limit(self):
        """Test Case B: Input 115,000 tokens for gpt-4o. Should return (False, "❌ Prompt is too large...")."""
        logger = Mock()
        should_proceed, error = check_token_limits(115_000, "gpt-4o", logger)
        
        assert should_proceed is False
        assert error is not None
        assert "❌ Prompt is too large for gpt-4o" in error
        assert "115,000" in error
        assert "111,616" in error  # 128,000 - 16,384 = 111,616
    
    def test_gpt4o_exceeds_limit_math(self):
        """Test exact token math: 128,000 - 16,384 = 111,616."""
        logger = Mock()
        # Math: 128,000 (Context) - 16,384 (Headroom) = 111,616
        should_proceed, error = check_token_limits(115_000, "gpt-4o", logger)
        assert should_proceed is False
        assert "111,616" in error  # Fix from 112,000
    
    def test_gpt4o_limit_logic(self):
        """Test token limit logic with exact math."""
        logger = Mock()
        should_proceed, error = check_token_limits(115_000, "gpt-4o", logger)
        assert should_proceed is False
        assert "111,616" in error  # Don't guess 112,000.
    
    def test_gpt4o_warning_at_80_percent(self):
        """Test Case C: Input 105,000 tokens for gpt-4o. Should return (True, None) but logger.warning must be called (since 105k > 80% of 128k)."""
        logger = Mock()
        should_proceed, error = check_token_limits(105_000, "gpt-4o", logger)
        
        assert should_proceed is True
        assert error is None
        logger.warning.assert_called_once()
        warning_msg = logger.warning.call_args[0][0]
        assert "High context usage for gpt-4o" in warning_msg
        assert "105,000" in warning_msg
        assert "128,000" in warning_msg


class TestAIResponse:
    """Test AIResponse dataclass."""
    
    def test_success_response(self):
        """Test successful response."""
        response = AIResponse(
            content="Hello world",
            model="test-model",
            input_tokens=10,
            output_tokens=2
        )
        
        assert response.success is True
        assert response.content == "Hello world"
    
    def test_error_response(self):
        """Test error response."""
        response = AIResponse(
            content="",
            model="test-model",
            error="API Error"
        )
        
        assert response.success is False
        assert response.error == "API Error"


class TestGracefulDegradation:
    """Test graceful degradation when SDKs not installed."""
    
    def test_claude_import_error(self):
        """Test Claude client handles missing SDK."""
        from dumpcode.ai.claude import ClaudeClient
        
        # Mock __import__ to raise ImportError for anthropic
        import builtins
        original_import = builtins.__import__
        
        def mock_import(name, *args, **kwargs):
            if name == 'anthropic':
                raise ImportError("No module named 'anthropic'")
            return original_import(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=mock_import):
            client = ClaudeClient("fake-key")
            client._client = None  # Force re-initialization
            
            with pytest.raises(ImportError) as exc_info:
                client._get_client()
            
            # Verify the error message is helpful
            assert "Anthropic SDK not installed" in str(exc_info.value)
            assert "pip install 'dumpcode[claude]'" in str(exc_info.value)
    
    def test_gemini_import_error(self):
        """Test Gemini client handles missing SDK."""
        from dumpcode.ai.gemini import GeminiClient
        
        # Mock __import__ to raise ImportError for google.generativeai
        import builtins
        original_import = builtins.__import__
        
        def mock_import(name, *args, **kwargs):
            if name == 'google.generativeai':
                raise ImportError("No module named 'google.generativeai'")
            return original_import(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=mock_import):
            client = GeminiClient("fake-key")
            
            with pytest.raises(ImportError) as exc_info:
                client._get_client("gemini-3-flash")
            
            # Verify the error message is helpful
            assert "Google Generative AI SDK not installed" in str(exc_info.value)
            assert "pip install 'dumpcode[gemini]'" in str(exc_info.value)


class TestClaudeExceptionMidStream:
    """Test Claude client handles exceptions during streaming."""
    
    def test_claude_exception_mid_stream(self):
        """Test that Claude client yields AIResponse with partial content and error when stream fails."""
        from dumpcode.ai.claude import ClaudeClient
        
        # Create a mock anthropic client
        mock_anthropic = Mock()
        mock_stream = MagicMock()
        
        # Mock the stream to yield some text then raise an exception
        text_chunks = ["Hello ", "World"]
        
        def mock_text_stream():
            for chunk in text_chunks:
                yield chunk
            raise Exception("Network connection lost")
        
        mock_stream.text_stream = mock_text_stream()
        mock_stream.get_final_message = Mock(side_effect=Exception("Stream failed"))
        
        # Configure the 'with' statement for the stream
        mock_anthropic.Anthropic = Mock(return_value=Mock(
            messages=Mock(
                stream=Mock(return_value=mock_stream)
            )
        ))
        mock_anthropic.Anthropic.return_value.messages.stream.return_value.__enter__.return_value = mock_stream
        
        client = ClaudeClient("fake-key")
        
        with patch.dict('sys.modules', {'anthropic': mock_anthropic}):
            # Initialize client
            client._get_client()
            
            # Call stream and collect results
            results = []
            try:
                for chunk in client.stream("Test prompt", "claude-test-model"):
                    results.append(chunk)
            except Exception:
                pass  # We expect the generator to handle the exception
            
            # Verify we got text chunks
            assert len(results) >= 2
            assert results[0].text == "Hello "
            assert results[1].text == "World"
            
            # The last chunk should be an AIResponse with error
            last_result = results[-1]
            assert last_result.response is not None
            assert last_result.response.content == "Hello World"  # Partial content
            assert last_result.response.error == "Network connection lost"
            assert last_result.response.model == "claude-test-model"
    
    def test_claude_stream_context_manager_fixed(self):
        """Test Claude stream with proper context manager mocking."""
        from dumpcode.ai.claude import ClaudeClient
        
        mock_client = MagicMock()
        # 1. Create the object that will act as 'stream'
        mock_stream_ctx = MagicMock()
        # 2. Mock the text stream iterator
        mock_stream_ctx.text_stream = iter(["Hello", " World"])
        
        # 3. Configure the final usage data
        mock_final = MagicMock()
        mock_final.usage.input_tokens = 10
        mock_final.usage.output_tokens = 5
        mock_stream_ctx.get_final_message.return_value = mock_final

        # 4. CRITICAL: The .stream() call returns a Context Manager
        # Calling __enter__ on the return value of stream() gives us the mock_stream_ctx
        mock_client.messages.stream.return_value.__enter__.return_value = mock_stream_ctx
        
        client = ClaudeClient(api_key="key")
        client._client = mock_client
        results = list(client.stream("prompt", "model"))
        assert results[0].text == "Hello"


def test_base_logic_properties():
    """Cover base.py:78 and 84 (Properties)"""
    from dumpcode.ai.base import AIResponse, StreamChunk
    
    # Test AIResponse.success
    success_resp = AIResponse(content="hi", model="m")
    error_resp = AIResponse(content="", model="m", error="fail")
    assert success_resp.success is True
    assert error_resp.success is False
    
    # Test StreamChunk.is_final
    chunk_text = StreamChunk(text="hello")
    chunk_final = StreamChunk(response=success_resp)
    assert chunk_text.is_final is False
    assert chunk_final.is_final is True