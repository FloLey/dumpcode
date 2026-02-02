"""Unit tests for AI diagnostics UI and threading."""

from unittest.mock import Mock, patch, MagicMock

from dumpcode.ai.diagnostics import _ping_model, run_diagnostics, _silence_noisy_libraries


class TestDiagnosticsCursorMath:
    """Test the cursor movement math in diagnostics UI."""
    
    def test_diagnostics_cursor_math(self):
        """Test that cursor movement calculations are correct for 2 models."""
        # Setup: Mock MODEL_CATALOG to have exactly 2 models
        mock_catalog = {
            "model1": {"provider": "openai", "model_id": "gpt-4o", "context": 128000},
            "model2": {"provider": "anthropic", "model_id": "claude-sonnet", "context": 200000},
        }
        
        # Mock os.getenv so both providers are "active"
        def mock_getenv(key):
            if key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
                return "test-key"
            return None
        
        # Mock sys.stdout.write to capture cursor movements
        stdout_writes = []
        def capture_stdout_write(text):
            stdout_writes.append(text)
        
        with patch("dumpcode.ai.diagnostics.MODEL_CATALOG", mock_catalog):
            with patch("os.getenv", side_effect=mock_getenv):
                with patch("sys.stdout.write", side_effect=capture_stdout_write):
                    with patch("dumpcode.ai.diagnostics.ThreadPoolExecutor") as mock_exec_class:
                        # 1. Class() returns the instance
                        mock_instance = mock_exec_class.return_value 
                        # 2. Instance.__enter__() returns the object used inside the 'with' block
                        mock_instance.__enter__.return_value = mock_instance 
                        
                        # Mock the futures
                        mock_future1 = Mock()
                        mock_future2 = Mock()
                        
                        # Now you can mock the methods called on the executor
                        mock_instance.submit.side_effect = [mock_future1, mock_future2]
                        mock_instance.as_completed.return_value = [mock_future1]
                        
                        # Mock the future result for model1 (index 0)
                        mock_future1.result.return_value = {
                            "alias": "model1",
                            "provider": "openai",
                            "status": "✅ ONLINE",
                            "details": "Available",
                            "time": 0.5
                        }
                        mock_future2.result.return_value = {
                            "alias": "model2",
                            "provider": "anthropic",
                            "status": "✅ ONLINE",
                            "details": "Available",
                            "time": 0.7
                        }
                        
                        # We need to mock the dict creation - let's patch the loop
                        with patch("dumpcode.ai.diagnostics.as_completed", return_value=[mock_future1]):
                            # Action
                            run_diagnostics()
        
        # Find the cursor movement for the first model (index 0)
        # When model1 (index 0) finishes, lines_up = (num_models - idx) + 1 = (2 - 0) + 1 = 3
        # But wait, the spec says for idx=1 (second model), lines_up = (2 - 1) + 1 = 2
        # Let me trace through the logic more carefully...
        
        # Actually, looking at the code:
        # idx = next(i for i, (a, c) in enumerate(models_to_test) if a == alias)
        # lines_up = (num_models - idx) + 1
        
        # For the FIRST model (idx=0) to finish: lines_up = (2 - 0) + 1 = 3
        # We should see "\033[3A" (Move Up 3 lines)
        
        cursor_movements = [write for write in stdout_writes if "\033[" in write]
        assert len(cursor_movements) > 0
        
        # The cursor movement should be in the format "\033[3A" 
        # where 3 is lines_up
        found_cursor_move = False
        for movement in cursor_movements:
            if "\x1b[" in movement and "A" in movement:
                # Extract the number
                import re
                match = re.search(r'\x1b\[(\d+)A', movement)
                if match:
                    lines_up = int(match.group(1))
                    # For the first model (idx=0) with 2 total models
                    # lines_up should be (2 - 0) + 1 = 3
                    if lines_up == 3:
                        found_cursor_move = True
                        break
        
        assert found_cursor_move, f"Expected cursor movement \\033[3A not found in: {cursor_movements}"
    
    def test_ping_error_heuristics(self):
        """Test that error heuristics correctly classify different error types."""
        # Test Case: Model not found error
        mock_config = {"provider": "openai", "model_id": "gpt-5"}
        
        with patch("dumpcode.ai.diagnostics.get_client_for_model") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # Mock the ping to raise an exception with "not found" message
            mock_client.ping.side_effect = Exception("The model gpt-5 does not exist")
            
            # Action
            result = _ping_model("gpt-5", mock_config)
        
        # Assertions
        assert result["status"] == "⛔ MISSING"
        assert result["details"] == "Model ID not found"
        assert result["alias"] == "gpt-5"
        assert result["provider"] == "openai"
    
    def test_ping_authentication_error(self):
        """Test that authentication errors are correctly classified."""
        mock_config = {"provider": "openai", "model_id": "gpt-4o"}
        
        with patch("dumpcode.ai.diagnostics.get_client_for_model") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # Mock authentication error
            mock_client.ping.side_effect = Exception("Invalid API Key: authentication failed (401)")
            
            # Action
            result = _ping_model("gpt-4o", mock_config)
        
        # Assertions
        assert result["status"] == "🔒 AUTH ERR"
        assert result["details"] == "Invalid API Key"
    
    def test_ping_timeout_error(self):
        """Test that timeout errors are correctly classified."""
        mock_config = {"provider": "anthropic", "model_id": "claude-sonnet"}
        
        with patch("dumpcode.ai.diagnostics.get_client_for_model") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # Mock timeout error
            mock_client.ping.side_effect = Exception("Request timeout after 30 seconds")
            
            # Action
            result = _ping_model("claude-sonnet", mock_config)
        
        # Assertions
        assert result["status"] == "⏱️ TIMEOUT"
        assert result["details"] == "Late response"
    
    def test_ping_limit_reached_success(self):
        """Test that limit reached errors are treated as success (model is online)."""
        mock_config = {"provider": "google", "model_id": "gemini-pro"}
        
        with patch("dumpcode.ai.diagnostics.get_client_for_model") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # Mock limit reached error (this means the model IS online)
            mock_client.ping.side_effect = Exception("max_tokens limit reached for this model")
            
            # Action
            result = _ping_model("gemini-pro", mock_config)
        
        # Assertions
        assert result["status"] == "✅ ONLINE"
        assert result["details"] == "Available (Limit Reached)"
    
    def test_ping_success(self):
        """Test successful ping."""
        mock_config = {"provider": "deepseek", "model_id": "deepseek-chat"}
        
        with patch("dumpcode.ai.diagnostics.get_client_for_model") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # Mock successful ping
            mock_client.ping.return_value = None
            
            # Action
            result = _ping_model("deepseek-chat", mock_config)
        
        # Assertions
        assert result["status"] == "✅ ONLINE"
        assert result["details"] == "Available"
        assert result["time"] > 0
    
    def test_silence_noisy_libraries(self):
        """Test that noisy libraries are silenced."""
        import logging
        
        # Capture original levels
        original_levels = {}
        noisy_loggers = ["openai", "anthropic", "google.generativeai", "httpx", "httpcore", "urllib3"]
        
        for logger_name in noisy_loggers:
            logger = logging.getLogger(logger_name)
            original_levels[logger_name] = logger.level
        
        try:
            # Action
            _silence_noisy_libraries()
            
            # Assertions
            for logger_name in noisy_loggers:
                logger = logging.getLogger(logger_name)
                assert logger.level == logging.CRITICAL, f"{logger_name} not silenced"
                
        finally:
            # Restore original levels
            for logger_name, original_level in original_levels.items():
                logging.getLogger(logger_name).setLevel(original_level)
    
    def test_run_diagnostics_no_api_keys(self):
        """Test diagnostics when no API keys are configured."""
        # Mock os.getenv to return None for all keys
        with patch("os.getenv", return_value=None):
            with patch("sys.stdout.write") as mock_stdout_write:
                # Action
                run_diagnostics()
        
        # Assertions
        # Should print warning about no API keys
        warning_calls = [call[0][0] for call in mock_stdout_write.call_args_list if "⚠️" in str(call[0])]
        assert len(warning_calls) > 0
        assert "No API keys found" in warning_calls[0]
    
    def test_run_diagnostics_exception_handling(self):
        """Test that diagnostics handles exceptions in futures gracefully."""
        # Setup
        mock_catalog = {
            "model1": {"provider": "openai", "model_id": "gpt-4o", "context": 128000},
        }
        
        with patch("dumpcode.ai.diagnostics.MODEL_CATALOG", mock_catalog):
            with patch("os.getenv", return_value="test-key"):
                with patch("sys.stdout.write"):
                    with patch("dumpcode.ai.diagnostics.ThreadPoolExecutor") as mock_exec_class:
                        mock_instance = MagicMock() # Use MagicMock for protocols
                        mock_exec_class.return_value = mock_instance
                        mock_instance.__enter__.return_value = mock_instance # CRITICAL FIX
                        
                        # Mock submit to return a future that raises when result() is called
                        mock_future = Mock()
                        mock_future.result.side_effect = Exception("Test crash")
                        mock_instance.submit.return_value = mock_future
                        
                        # Patch as_completed to return the future
                        with patch("dumpcode.ai.diagnostics.as_completed", return_value=[mock_future]):
                            run_diagnostics()
        
        # Should not crash, should handle the exception
    
    def test_run_diagnostics_mock_fix(self):
        """Test ThreadPoolExecutor context manager mocking fix."""
        mock_executor = MagicMock()
        # The return value of __enter__ must be the mock itself
        mock_executor.__enter__.return_value = mock_executor
        mock_executor.submit.return_value = MagicMock()
        
        with patch("dumpcode.ai.diagnostics.ThreadPoolExecutor", return_value=mock_executor):
            with patch("dumpcode.ai.diagnostics.as_completed", return_value=[]):
                with patch("os.getenv", return_value="test-key"):
                    with patch("sys.stdout.write"):
                        # Should no longer raise AttributeError
                        run_diagnostics()
    
    def test_diagnostics_executor_fix(self):
        """Test ThreadPoolExecutor context manager mocking with correct pattern."""
        mock_executor = MagicMock()
        # YOU MUST DO THIS:
        mock_executor.__enter__.return_value = mock_executor
        
        with patch("dumpcode.ai.diagnostics.ThreadPoolExecutor", return_value=mock_executor):
            with patch("dumpcode.ai.diagnostics.as_completed", return_value=[]):
                run_diagnostics()  # This will now pass.