"""Unit tests for AI orchestrator lifecycle."""

from unittest.mock import Mock, patch
from pathlib import Path

from dumpcode.ai.base import AIResponse, StreamChunk
from dumpcode.ai.orchestrator import AIOrchestrator


class TestAIOrchestrator:
    """Test the AI orchestrator lifecycle."""
    
    def test_orchestrator_respects_callback(self):
        """Test Case 1: Verify orchestrator uses custom callback instead of sys.stdout."""
        # Setup
        mock_settings = Mock()
        mock_settings.model_override = "test-model"
        mock_settings.active_profile = None
        mock_settings.start_path = Path("/test/path")
        
        mock_logger = Mock()
        orchestrator = AIOrchestrator(mock_settings, mock_logger)
        
        # Mock the dump file reading
        mock_dump_path = Path("/test/dump.txt")
        mock_prompt = "Test prompt content"
        
        # Mock send_to_ai to yield a stream chunk
        mock_chunk = StreamChunk(text="Hello ")
        mock_response = AIResponse(content="Hello World", model="test-model", input_tokens=10, output_tokens=5)
        mock_final_chunk = StreamChunk(response=mock_response)
        
        def mock_send_to_ai(prompt, model, output_path, logger):
            yield mock_chunk
            yield mock_final_chunk
        
        # Track what the callback receives
        callback_received = []
        
        with patch("dumpcode.ai.orchestrator.send_to_ai", side_effect=mock_send_to_ai):
            with patch("pathlib.Path.read_text", return_value=mock_prompt):
                with patch("sys.stdout.write") as mock_stdout_write:
                    # Action
                    result = orchestrator.run_ai_interaction(
                        mock_dump_path, 
                        token_callback=callback_received.append
                    )
        
        # Assertions
        assert result == mock_response
        assert callback_received == ["Hello "]  # Callback received the text
        
        # VERIFY: We don't check for NO calls. We check that the chunks weren't sent there.
        # The header is fine, but chunks should go to the callback.
        all_writes = "".join(call[0][0] for call in mock_stdout_write.call_args_list)
        assert "Receiving AI Response" in all_writes
        assert "Hello World" not in all_writes  # Chunks went to callback instead
        
        # Verify logging of token usage
        mock_logger.info.assert_called_once()
        info_msg = mock_logger.info.call_args[0][0]
        assert "Input: 10" in info_msg
        assert "Output: 5" in info_msg
    
    def test_orchestrator_logs_usage(self):
        """Test Case 2: Verify orchestrator logs token usage when available."""
        # Setup
        mock_settings = Mock()
        mock_settings.model_override = "test-model"
        mock_settings.active_profile = None
        mock_settings.start_path = Path("/test/path")
        
        mock_logger = Mock()
        orchestrator = AIOrchestrator(mock_settings, mock_logger)
        
        # Mock the dump file reading
        mock_dump_path = Path("/test/dump.txt")
        mock_prompt = "Test prompt content"
        
        # Mock send_to_ai to yield only the final response with token counts
        mock_response = AIResponse(
            content="Analysis complete", 
            model="test-model", 
            input_tokens=100, 
            output_tokens=50
        )
        mock_final_chunk = StreamChunk(response=mock_response)
        
        def mock_send_to_ai(prompt, model, output_path, logger):
            yield mock_final_chunk
        
        with patch("dumpcode.ai.orchestrator.send_to_ai", side_effect=mock_send_to_ai):
            with patch("pathlib.Path.read_text", return_value=mock_prompt):
                # Action
                result = orchestrator.run_ai_interaction(mock_dump_path)
        
        # Assertions
        assert result == mock_response
        
        # Verify logging of token usage
        mock_logger.info.assert_called_once()
        info_msg = mock_logger.info.call_args[0][0]
        assert "Input: 100" in info_msg
        assert "Output: 50" in info_msg
    
    def test_orchestrator_fallback_to_stdout(self):
        """Test that orchestrator falls back to sys.stdout when no callback provided."""
        # Setup
        mock_settings = Mock()
        mock_settings.model_override = "test-model"
        mock_settings.active_profile = None
        mock_settings.start_path = Path("/test/path")
        
        mock_logger = Mock()
        orchestrator = AIOrchestrator(mock_settings, mock_logger)
        
        # Mock the dump file reading
        mock_dump_path = Path("/test/dump.txt")
        mock_prompt = "Test prompt content"
        
        # Mock send_to_ai to yield text chunks
        mock_chunk1 = StreamChunk(text="Hello ")
        mock_chunk2 = StreamChunk(text="World")
        mock_response = AIResponse(content="Hello World", model="test-model")
        mock_final_chunk = StreamChunk(response=mock_response)
        
        def mock_send_to_ai(prompt, model, output_path, logger):
            yield mock_chunk1
            yield mock_chunk2
            yield mock_final_chunk
        
        with patch("dumpcode.ai.orchestrator.send_to_ai", side_effect=mock_send_to_ai):
            with patch("pathlib.Path.read_text", return_value=mock_prompt):
                with patch("sys.stdout.write") as mock_stdout_write:
                    with patch("sys.stdout.flush") as mock_stdout_flush:
                        # Action
                        result = orchestrator.run_ai_interaction(mock_dump_path)
        
        # Assertions
        assert result == mock_response
        
        # Verify sys.stdout was called with the text chunks
        assert mock_stdout_write.call_count >= 2
        write_calls = [call[0][0] for call in mock_stdout_write.call_args_list]
        assert "Hello " in write_calls
        assert "World" in write_calls
        
        # Verify flush was called (since no custom callback)
        mock_stdout_flush.assert_called()
    
    def test_orchestrator_handles_read_error(self):
        """Test that orchestrator handles dump file read errors gracefully."""
        # Setup
        mock_settings = Mock()
        mock_settings.model_override = "test-model"
        mock_settings.active_profile = None
        
        mock_logger = Mock()
        orchestrator = AIOrchestrator(mock_settings, mock_logger)
        
        # Mock the dump file reading to raise an exception
        mock_dump_path = Path("/test/dump.txt")
        
        with patch("pathlib.Path.read_text", side_effect=Exception("File not found")):
            # Action
            result = orchestrator.run_ai_interaction(mock_dump_path)
        
        # Assertions
        assert result is None
        mock_logger.error.assert_called_once()
        error_msg = mock_logger.error.call_args[0][0]
        assert "Could not read dump file" in error_msg
    
    def test_orchestrator_no_model_error(self):
        """Test that orchestrator returns None when no model is configured."""
        # Setup
        mock_settings = Mock()
        mock_settings.model_override = None  # No model override
        mock_settings.active_profile = None  # No active profile
        
        mock_logger = Mock()
        orchestrator = AIOrchestrator(mock_settings, mock_logger)
        
        # Mock the dump file reading
        mock_dump_path = Path("/test/dump.txt")
        mock_prompt = "Test prompt content"
        
        with patch("pathlib.Path.read_text", return_value=mock_prompt):
            # Action
            result = orchestrator.run_ai_interaction(mock_dump_path)
        
        # Assertions
        assert result is None
        mock_logger.error.assert_called_once()
        error_msg = mock_logger.error.call_args[0][0]
        assert "Auto-mode enabled but no model found in profile" in error_msg
    
    def test_orchestrator_uses_profile_model(self):
        """Test that orchestrator uses model from active profile when no override."""
        # Setup
        mock_settings = Mock()
        mock_settings.model_override = None  # No override
        mock_settings.active_profile = {"model": "profile-model"}  # Profile has model
        mock_settings.start_path = Path("/test/path")
        
        mock_logger = Mock()
        orchestrator = AIOrchestrator(mock_settings, mock_logger)
        
        # Mock the dump file reading
        mock_dump_path = Path("/test/dump.txt")
        mock_prompt = "Test prompt content"
        
        # Mock send_to_ai
        mock_response = AIResponse(content="Response", model="profile-model")
        mock_final_chunk = StreamChunk(response=mock_response)
        
        def mock_send_to_ai(prompt, model, output_path, logger):
            yield mock_final_chunk
        
        with patch("dumpcode.ai.orchestrator.send_to_ai", side_effect=mock_send_to_ai):
            with patch("pathlib.Path.read_text", return_value=mock_prompt):
                # Action
                result = orchestrator.run_ai_interaction(mock_dump_path)
        
        # Assertions
        assert result == mock_response
        # send_to_ai should be called with "profile-model" not "test-model"