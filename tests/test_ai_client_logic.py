"""Unit tests for AI client logic including .env parsing and token validation."""

import os
import sys
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

from dumpcode.ai.client import load_env_file, check_token_limits, send_to_ai
from dumpcode.ai.base import StreamChunk, AIResponse


class TestLoadEnvFileManualFallback:
    """Test the manual .env parser fallback when python-dotenv is not available."""
    
    def test_load_env_file_manual_fallback(self):
        """Test that manual .env parsing works when dotenv library is missing."""
        # Setup: Simulate dotenv library missing
        with patch.dict(sys.modules, {"dotenv": ImportError("No module named 'dotenv'")}):
            # Mock the .env file exists
            with patch("pathlib.Path.exists", return_value=True):
                # Mock the .env file content
                env_content = "KEY1=VAL1\n# Comment line\nKEY2='VAL2'\nKEY3=\"VAL3\"\n  KEY4  =  VAL4  \n"
                with patch("builtins.open", mock_open(read_data=env_content)):
                    # Clear any existing values
                    original_key1 = os.environ.get("KEY1")
                    original_key2 = os.environ.get("KEY2")
                    
                    try:
                        # Remove if they exist
                        if "KEY1" in os.environ:
                            del os.environ["KEY1"]
                        if "KEY2" in os.environ:
                            del os.environ["KEY2"]
                        if "KEY3" in os.environ:
                            del os.environ["KEY3"]
                        if "KEY4" in os.environ:
                            del os.environ["KEY4"]
                        
                        # Call the function
                        load_env_file(Path("/test/path"))
                        
                        # Assertions
                        assert os.environ["KEY1"] == "VAL1"
                        assert os.environ["KEY2"] == "VAL2"  # Quotes should be stripped
                        assert os.environ["KEY3"] == "VAL3"  # Double quotes should be stripped
                        assert os.environ["KEY4"] == "VAL4"  # Whitespace should be trimmed
                        
                        # Verify comment line was skipped (no KEY# in env)
                        assert "#" not in os.environ
                        
                    finally:
                        # Cleanup
                        if original_key1 is not None:
                            os.environ["KEY1"] = original_key1
                        elif "KEY1" in os.environ:
                            del os.environ["KEY1"]
                            
                        if original_key2 is not None:
                            os.environ["KEY2"] = original_key2
                        elif "KEY2" in os.environ:
                            del os.environ["KEY2"]
                            
                        if "KEY3" in os.environ:
                            del os.environ["KEY3"]
                        if "KEY4" in os.environ:
                            del os.environ["KEY4"]
    
    def test_load_env_file_with_dotenv_available(self):
        """Test that load_dotenv is called when python-dotenv is available."""
        mock_load_dotenv = Mock()
        with patch.dict(sys.modules, {"dotenv": Mock(load_dotenv=mock_load_dotenv)}):
            with patch("pathlib.Path.exists", return_value=True):
                load_env_file(Path("/test/path"))
                mock_load_dotenv.assert_called_once()
    
    def test_load_env_file_no_file(self):
        """Test that function returns early when .env file doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            # Should not raise any errors
            load_env_file(Path("/test/path"))


class TestTokenLimitEdgeCases:
    """Test edge cases for token limit checking."""
    
    def test_unknown_model_fallback(self):
        """Test token limits for unknown models (should use 128k baseline)."""
        logger = Mock()
        
        # Unknown model should use 128k baseline
        should_proceed, error = check_token_limits(100_000, "unknown-model-xyz", logger)
        
        assert should_proceed is True  # 100k < (128k - 16k = 112k)
        assert error is None
    
    def test_unknown_model_exceeds_fallback(self):
        """Test unknown model that exceeds the 128k fallback limit."""
        logger = Mock()
        
        # 120k > (128k - 16k = 112k)
        should_proceed, error = check_token_limits(120_000, "unknown-model-xyz", logger)
        
        assert should_proceed is False
        assert error is not None
        assert "❌ Prompt is too large for unknown-model-xyz" in error
    
    def test_gemini_large_context_no_warning(self):
        """Test that Gemini with large context doesn't warn at moderate usage."""
        logger = Mock()
        
        # Gemini 2.5 Pro has 1,048,576 context
        # 500k tokens is less than 80% of 1M, so no warning
        should_proceed, error = check_token_limits(500_000, "gemini-2.5-pro", logger)
        
        assert should_proceed is True
        assert error is None
        logger.warning.assert_not_called()
    
    def test_gemini_large_context_with_warning(self):
        """Test that Gemini warns at 80% of its large context."""
        logger = Mock()
        
        # 80% of 1,048,576 is ~838,861
        should_proceed, error = check_token_limits(850_000, "gemini-2.5-pro", logger)
        
        assert should_proceed is True
        assert error is None
        logger.warning.assert_called_once()
        warning_msg = logger.warning.call_args[0][0]
        assert "High context usage for gemini-2.5-pro" in warning_msg
        assert "850,000" in warning_msg
        assert "1,048,576" in warning_msg


class TestSendToAIGenerator:
    """Test the send_to_ai generator function."""
    
    def test_send_to_ai_successful_stream(self):
        """Test send_to_ai with successful stream and file writing."""
        mock_logger = Mock()
        mock_client = Mock()
        
        # Mock the stream to return text chunks and final response
        mock_stream = [
            StreamChunk(text="Hello "),
            StreamChunk(text="World"),
            StreamChunk(response=AIResponse(
                content="Hello World",
                model="test-model",
                input_tokens=10,
                output_tokens=20
            ))
        ]
        mock_client.stream = Mock(return_value=mock_stream)
        
        output_path = Path("/test/output")
        
        with patch('dumpcode.ai.client.get_client_for_model', return_value=mock_client):
            with patch('dumpcode.ai.client.estimate_tokens', return_value=1000):
                with patch('dumpcode.ai.client.check_token_limits', return_value=(True, None)):
                    with patch('dumpcode.ai.client.MODEL_CATALOG', {"test-model": {"model_id": "test-model-id"}}):
                        with patch('builtins.open', mock_open()) as mock_file:
                            # Call send_to_ai and collect results
                            results = list(send_to_ai(
                                "Test prompt",
                                "test-model",
                                output_path,
                                mock_logger
                            ))
                            
                            # Verify stream chunks were yielded
                            assert len(results) == 3
                            assert results[0].text == "Hello "
                            assert results[1].text == "World"
                            assert results[2].response.content == "Hello World"
                            
                            # Verify file was written with correct content
                            mock_file.assert_called_once_with(output_path / "ai_response.md", "w", encoding="utf-8")
                            handle = mock_file()
                            expected_calls = [
                                "<!-- Model: test-model -->\n",
                                "<!-- Input tokens: 10 -->\n",
                                "<!-- Output tokens: 20 -->\n",
                                "\n",
                                "Hello World"
                            ]
                            for i, expected in enumerate(expected_calls):
                                assert handle.write.call_args_list[i][0][0] == expected
    
    def test_send_to_ai_file_write_error(self):
        """Test send_to_ai when file writing fails."""
        mock_logger = Mock()
        mock_client = Mock()
        
        # Mock successful stream
        mock_stream = [
            StreamChunk(response=AIResponse(
                content="Test content",
                model="test-model"
            ))
        ]
        mock_client.stream = Mock(return_value=mock_stream)
        
        output_path = Path("/test/output")
        
        with patch('dumpcode.ai.client.get_client_for_model', return_value=mock_client):
            with patch('dumpcode.ai.client.estimate_tokens', return_value=1000):
                with patch('dumpcode.ai.client.check_token_limits', return_value=(True, None)):
                    with patch('dumpcode.ai.client.MODEL_CATALOG', {"test-model": {"model_id": "test-model-id"}}):
                        with patch('builtins.open', side_effect=OSError("Permission denied")):
                            # Call send_to_ai
                            results = list(send_to_ai(
                                "Test prompt",
                                "test-model",
                                output_path,
                                mock_logger
                            ))
                            
                            # Should still yield the response
                            assert len(results) == 1
                            assert results[0].response.content == "Test content"
                            
                            # Should log warning about file write failure
                            mock_logger.warning.assert_called_once()
                            assert "Could not save AI response" in mock_logger.warning.call_args[0][0]
    
    def test_send_to_ai_token_limit_exceeded(self):
        """Test send_to_ai when token limit is exceeded."""
        mock_logger = Mock()
        
        with patch('dumpcode.ai.client.estimate_tokens', return_value=120000):
            with patch('dumpcode.ai.client.check_token_limits', return_value=(False, "❌ Prompt is too large")):
                results = list(send_to_ai(
                    "Test prompt",
                    "gpt-4o",
                    Path("/test/output"),
                    mock_logger
                ))
                
                # Should yield error response
                assert len(results) == 1
                assert results[0].response.error == "❌ Prompt is too large"
                assert results[0].response.model == "gpt-4o"
    
    def test_send_to_ai_client_import_error(self):
        """Test send_to_ai when client cannot be loaded (ImportError)."""
        mock_logger = Mock()
        
        with patch('dumpcode.ai.client.estimate_tokens', return_value=1000):
            with patch('dumpcode.ai.client.check_token_limits', return_value=(True, None)):
                with patch('dumpcode.ai.client.get_client_for_model', 
                          side_effect=ImportError("SDK not installed")):
                    results = list(send_to_ai(
                        "Test prompt",
                        "test-model",
                        Path("/test/output"),
                        mock_logger
                    ))
                    
                    # Should yield error response
                    assert len(results) == 1
                    assert results[0].response.error == "SDK not installed"
                    assert results[0].response.model == "test-model"
    
    def test_send_to_ai_stream_exception(self):
        """Test send_to_ai when stream raises an exception."""
        mock_logger = Mock()
        mock_client = Mock()
        
        # Mock stream to raise exception
        mock_client.stream = Mock(side_effect=Exception("Network error"))
        
        output_path = Path("/test/output")
        
        with patch('dumpcode.ai.client.get_client_for_model', return_value=mock_client):
            with patch('dumpcode.ai.client.estimate_tokens', return_value=1000):
                with patch('dumpcode.ai.client.check_token_limits', return_value=(True, None)):
                    with patch('dumpcode.ai.client.MODEL_CATALOG', {"test-model": {"model_id": "test-model-id"}}):
                        results = list(send_to_ai(
                            "Test prompt",
                            "test-model",
                            output_path,
                            mock_logger
                        ))
                        
                        # Should yield error response
                        assert len(results) == 1
                        assert results[0].response.error == "Network error"
                        assert results[0].response.model == "test-model"
                        mock_logger.error.assert_called_once_with("Streaming error: Network error")


class TestLoadEnvFileEdgeCases:
    """Test edge cases for load_env_file function."""
    
    def test_load_env_file_no_env_file(self):
        """Test load_env_file when .env file doesn't exist."""
        from dumpcode.ai.client import load_env_file
        from pathlib import Path
        
        # Test with path that doesn't have .env file
        test_path = Path("/tmp/nonexistent")
        
        # Should not raise any errors
        load_env_file(test_path)
        
        # Also test with dotenv available but no file
        with patch("pathlib.Path.exists", return_value=False):
            load_env_file(test_path)


def test_stream_chunk_is_final():
    """Test StreamChunk.is_final property."""
    from dumpcode.ai.base import StreamChunk, AIResponse
    
    # Test with response (should be final)
    response = AIResponse(content="test", model="test-model")
    chunk_with_response = StreamChunk(response=response)
    assert chunk_with_response.is_final is True
    
    # Test with text only (should not be final)
    chunk_with_text = StreamChunk(text="Hello")
    assert chunk_with_text.is_final is False
    
    # Test with both text and response (should be final)
    chunk_with_both = StreamChunk(text="Hello", response=response)
    assert chunk_with_both.is_final is True
    
    # Test with neither (should not be final)
    chunk_empty = StreamChunk()
    assert chunk_empty.is_final is False


def test_load_env_file_manual_logic(tmp_path):
    """Cover client.py:46-47 (Manual .env parser fallback)"""
    from dumpcode.ai.client import load_env_file
    import os
    
    env_file = tmp_path / ".env"
    env_file.write_text("MANUAL_KEY=MANUAL_VALUE\n# Comment\nINVALID_LINE")
    
    # Force the ImportError to trigger manual parsing
    with patch.dict("sys.modules", {"dotenv": None}):
        load_env_file(tmp_path)
        assert os.environ.get("MANUAL_KEY") == "MANUAL_VALUE"


def test_send_to_ai_import_safety(caplog):
    """Cover client.py:164-168 (Graceful failure when AI module is broken)"""
    from dumpcode.ai.client import send_to_ai
    from pathlib import Path
    
    # Mocking a failed lazy import
    with patch("dumpcode.ai.client.get_client_for_model", side_effect=ImportError("No SDK")):
        gen = send_to_ai("prompt", "claude-sonnet-4.5", Path("."), Mock())
        results = list(gen)
        assert "No SDK" in results[0].response.error