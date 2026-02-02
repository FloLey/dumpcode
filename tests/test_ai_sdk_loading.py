"""Unit tests for AI provider SDK lazy-loading logic."""

import sys
from unittest.mock import patch, MagicMock

import pytest

from dumpcode.ai.claude import ClaudeClient
from dumpcode.ai.gemini import GeminiClient
from dumpcode.ai.openai_client import OpenAIClient
from dumpcode.ai.deepseek import DeepSeekClient


class TestProviderLazyLoading:
    """Test lazy-loading of AI provider SDKs."""
    
    def test_claude_lazy_load_success(self):
        """Test successful lazy-loading of Anthropic SDK."""
        # Create a mock anthropic module
        mock_anthropic = MagicMock()
        mock_client_instance = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client_instance
        
        # Create client and test lazy loading
        client = ClaudeClient(api_key="test-key")
        
        # Patch sys.modules to include our mock
        with patch.dict(sys.modules, {'anthropic': mock_anthropic}):
            # First call should initialize the client
            result = client._get_client()
            
            # Verify client was created with correct parameters
            mock_anthropic.Anthropic.assert_called_once_with(
                api_key="test-key",
                timeout=60.0
            )
            assert result == mock_client_instance
            assert client._client == mock_client_instance
            
            # Second call should return cached client
            result2 = client._get_client()
            assert result2 == mock_client_instance
            # Should not create a new client
            assert mock_anthropic.Anthropic.call_count == 1
    
    def test_claude_lazy_load_import_error(self):
        """Test ImportError when Anthropic SDK is not installed."""
        client = ClaudeClient(api_key="test-key")
        
        # Remove anthropic from sys.modules
        with patch.dict(sys.modules, {'anthropic': None}):
            with pytest.raises(ImportError) as exc_info:
                client._get_client()
            
            assert "Anthropic SDK not installed" in str(exc_info.value)
            assert "pip install 'dumpcode[claude]'" in str(exc_info.value)
    
    def test_gemini_lazy_load_success(self):
        """Test successful lazy-loading of Google Gemini SDK."""
        mock_google = MagicMock()
        mock_google_genai = MagicMock()
        mock_google_genai.configure.return_value = None
        mock_generative_model = MagicMock()
        mock_google_genai.GenerativeModel.return_value = mock_generative_model
        mock_google.generativeai = mock_google_genai
        
        client = GeminiClient(api_key="test-key")
        
        with patch.dict(sys.modules, {'google': mock_google, 'google.generativeai': mock_google_genai}):
            result = client._get_client("gemini-1.5-pro")
            
            mock_google_genai.configure.assert_called_once_with(api_key="test-key")
            mock_google_genai.GenerativeModel.assert_called_once_with("gemini-1.5-pro")
            assert result == mock_generative_model
            assert "gemini-1.5-pro" in client._model_cache
    
    def test_gemini_lazy_load_import_error(self):
        """Test ImportError when Google Generative AI SDK is not installed."""
        client = GeminiClient(api_key="test-key")
        
        with patch.dict(sys.modules, {'google.generativeai': None}):
            with pytest.raises(ImportError) as exc_info:
                client._get_client("gemini-1.5-pro")
            
            assert "Google Generative AI SDK not installed" in str(exc_info.value)
            assert "pip install 'dumpcode[gemini]'" in str(exc_info.value)
    
    def test_openai_lazy_load_success(self):
        """Test successful lazy-loading of OpenAI SDK."""
        mock_openai = MagicMock()
        mock_openai_module = MagicMock()
        mock_openai.OpenAI = mock_openai_module
        mock_client_instance = MagicMock()
        mock_openai_module.return_value = mock_client_instance
        
        client = OpenAIClient(api_key="test-key")
        
        with patch.dict(sys.modules, {'openai': mock_openai}):
            result = client._get_client()
            
            mock_openai_module.assert_called_once_with(
                api_key="test-key",
                timeout=60.0
            )
            assert result == mock_client_instance
            assert client._client == mock_client_instance
    
    def test_openai_lazy_load_import_error(self):
        """Test ImportError when OpenAI SDK is not installed."""
        client = OpenAIClient(api_key="test-key")
        
        with patch.dict(sys.modules, {'openai': None}):
            with pytest.raises(ImportError) as exc_info:
                client._get_client()
            
            assert "OpenAI SDK not installed" in str(exc_info.value)
            assert "pip install 'dumpcode[openai]'" in str(exc_info.value)
    
    def test_deepseek_lazy_load_success(self):
        """Test successful lazy-loading of DeepSeek SDK."""
        mock_openai = MagicMock()
        mock_openai.OpenAI.return_value = MagicMock()
        
        client = DeepSeekClient(api_key="test-key")
        
        with patch.dict(sys.modules, {'openai': mock_openai}):
            result = client._get_client()
            
            mock_openai.OpenAI.assert_called_once_with(
                api_key="test-key",
                base_url="https://api.deepseek.com",
                timeout=60.0  # MUST include this
            )
            assert result is not None
            assert client._client is not None
    
    def test_deepseek_lazy_load_import_error(self):
        """Test ImportError when OpenAI SDK is not installed (DeepSeek uses OpenAI SDK)."""
        client = DeepSeekClient(api_key="test-key")
        
        with patch.dict(sys.modules, {'openai': None}):
            with pytest.raises(ImportError) as exc_info:
                client._get_client()
            
            assert "OpenAI SDK not installed" in str(exc_info.value)
            assert "pip install 'dumpcode[deepseek]'" in str(exc_info.value)
    
    def test_deepseek_stream_full_coverage(self):
        """Test DeepSeek stream method for full coverage."""
        from dumpcode.ai.deepseek import DeepSeekClient
        
        mock_client = MagicMock()
        
        # Mock the chunk objects
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock(delta=MagicMock(content="Deep"))]
        chunk1.usage = None
        
        chunk2 = MagicMock()
        chunk2.choices = [MagicMock(delta=MagicMock(content="Seek"))]
        chunk2.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
        
        # The create call MUST return an iterable (list)
        mock_client.chat.completions.create.return_value = [chunk1, chunk2]
        
        client = DeepSeekClient(api_key="key")
        client._client = mock_client
        
        results = list(client.stream("p", "m"))
        assert results[0].text == "Deep"
        assert results[2].response.output_tokens == 5
    
    def test_gemini_stream_full_coverage(self):
        """Test Gemini stream method for full coverage."""
        from dumpcode.ai.gemini import GeminiClient
        
        mock_model = MagicMock()
        # Mock the chunks returned by Gemini
        chunk1 = MagicMock()
        chunk1.text = "Hello"
        chunk2 = MagicMock()
        chunk2.text = " World"
        
        # Simulate the usage metadata Gemini provides at the end
        mock_response = MagicMock()
        mock_response.__iter__.return_value = [chunk1, chunk2]
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 5
        
        mock_model.generate_content.return_value = mock_response
        
        client = GeminiClient(api_key="fake")
        # Patch _get_client to return our mock model
        with patch.object(client, '_get_client', return_value=mock_model):
            results = list(client.stream("prompt", "model-id"))
        
        assert results[0].text == "Hello"
        assert results[1].text == " World"
        assert results[2].response.input_tokens == 10
        assert results[2].response.output_tokens == 5
    
    def test_openai_full_stream_coverage(self):
        """Test OpenAI client stream method for full coverage."""
        from dumpcode.ai.openai_client import OpenAIClient
        
        # Create mock OpenAI client
        mock_openai = MagicMock()
        
        # Mock the response to be an iterable list of chunks
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock(delta=MagicMock(content="Hi"))]
        mock_chunk.usage = None
        
        mock_final_chunk = MagicMock()
        mock_final_chunk.choices = []
        mock_final_chunk.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
        
        # Create a mock stream that yields our chunks
        mock_stream = [mock_chunk, mock_final_chunk]
        
        # Mock the chat.completions.create to return our stream
        mock_openai.chat.completions.create.return_value = mock_stream
        
        # Create client and inject mock
        client = OpenAIClient(api_key="test")
        client._client = mock_openai  # Inject mock client
        
        # Call stream and collect results
        results = list(client.stream("prompt", "gpt-4o"))
        
        # Verify results
        assert len(results) == 2
        assert results[0].text == "Hi"
        assert results[1].response.input_tokens == 10
        assert results[1].response.output_tokens == 5
        assert results[1].response.model == "gpt-4o"
        assert results[1].response.content == "Hi"


def test_gemini_stream_exception_handling(caplog):
    """Verify lines 82-84: Gemini handles mid-stream exceptions gracefully."""
    from dumpcode.ai.gemini import GeminiClient
    
    mock_model = MagicMock()
    # Force generate_content to raise an error
    mock_model.generate_content.side_effect = Exception("Google API Down")
    
    client = GeminiClient(api_key="fake")
    with patch.object(client, '_get_client', return_value=mock_model):
        results = list(client.stream("prompt", "model"))
    
    assert results[0].response.error == "Google API Down"
    assert "Gemini API error" in caplog.text


def test_openai_stream_exception_coverage(caplog):
    """Cover openai_client.py:83-85 (Exception during stream)"""
    from dumpcode.ai.openai_client import OpenAIClient
    
    mock_client = MagicMock()
    # Mock the stream to raise an error immediately
    mock_client.chat.completions.create.side_effect = Exception("API Connection Lost")
    
    client = OpenAIClient(api_key="test")
    client._client = mock_client
    
    results = list(client.stream("prompt", "gpt-4o"))
    assert results[0].response.error == "API Connection Lost"
    assert "OpenAI API error" in caplog.text