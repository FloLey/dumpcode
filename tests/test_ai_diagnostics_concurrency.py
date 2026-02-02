"""Unit tests for AI diagnostics concurrency logic."""

import time
from unittest.mock import Mock, patch

from dumpcode.ai.diagnostics import run_diagnostics, _ping_model
from dumpcode.ai.models import MODEL_CATALOG


class TestAIDiagnosticsConcurrency:
    """Test ThreadPoolExecutor logic in diagnostics.py."""
    
    def test_run_diagnostics_concurrency(self):
        """Test that run_diagnostics executes pings in parallel."""
        # Create mock environment with API keys
        mock_env = {
            'ANTHROPIC_API_KEY': 'test-claude-key',
            'GOOGLE_API_KEY': 'test-gemini-key',
            'OPENAI_API_KEY': 'test-openai-key',
            'DEEPSEEK_API_KEY': 'test-deepseek-key'
        }
        
        # Mock _ping_model to simulate network delay
        def mock_ping_model(alias, config):
            time.sleep(0.1)  # Simulate network delay
            return {
                "alias": alias,
                "provider": config["provider"],
                "status": "✅ ONLINE",
                "details": "Available",
                "time": 0.1
            }
        
        start_time = time.time()
        
        with patch.dict('os.environ', mock_env):
            with patch('dumpcode.ai.diagnostics._ping_model', side_effect=mock_ping_model):
                with patch('sys.stdout.write'):  # Suppress output
                    run_diagnostics()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # With parallel execution, total time should be significantly less than
        # 0.1 * number_of_models. Since we have multiple models in the catalog,
        # parallel execution should be much faster than sequential.
        num_models = len([m for m in MODEL_CATALOG.values() 
                         if m["provider"] in ['anthropic', 'google', 'openai', 'deepseek']])
        
        # Parallel execution should be less than half the sequential time
        # (allowing some overhead for thread management)
        assert execution_time < (0.1 * num_models) * 0.5
    
    def test_diagnostics_empty_catalog(self):
        """Test that run_diagnostics exits gracefully when no API keys are found."""
        # Empty environment - no API keys
        with patch.dict('os.environ', {}, clear=True):
            with patch('builtins.print') as mock_print:
                run_diagnostics()
                
                # Should print warning about no API keys
                mock_print.assert_any_call("⚠️  No API keys found. Please check your .env file.")
    
    def test_diagnostics_no_matching_models(self):
        """Test that run_diagnostics handles case where API keys exist but no matching models."""
        # Environment with API key for a provider that might not have models
        mock_env = {
            'ANTHROPIC_API_KEY': 'test-key'
        }
        
        # Mock MODEL_CATALOG to be empty or not contain anthropic models
        with patch.dict('os.environ', mock_env):
            with patch('dumpcode.ai.diagnostics.MODEL_CATALOG', {}):
                with patch('builtins.print') as mock_print:
                    run_diagnostics()
                    
                    # Should print the header but no models
                    mock_print.assert_any_call("\n🚀 Starting Full Model Catalog Scan...\n")
    
    def test_ping_model_success(self):
        """Test _ping_model function with successful ping."""
        mock_client = Mock()
        mock_client.ping = Mock()
        
        with patch('dumpcode.ai.diagnostics.get_client_for_model', return_value=mock_client):
            result = _ping_model("test-alias", {
                "provider": "test-provider",
                "model_id": "test-model"
            })
            
            assert result["alias"] == "test-alias"
            assert result["provider"] == "test-provider"
            assert result["status"] == "✅ ONLINE"
            assert result["details"] == "Available"
            assert result["time"] > 0
    
    def test_ping_model_authentication_error(self):
        """Test _ping_model function with authentication error."""
        mock_client = Mock()
        mock_client.ping = Mock(side_effect=Exception("Invalid API key: authentication failed"))
        
        with patch('dumpcode.ai.diagnostics.get_client_for_model', return_value=mock_client):
            result = _ping_model("test-alias", {
                "provider": "test-provider",
                "model_id": "test-model"
            })
            
            assert result["status"] == "🔒 AUTH ERR"
            assert "Invalid API Key" in result["details"]
    
    def test_ping_model_model_not_found(self):
        """Test _ping_model function with model not found error."""
        mock_client = Mock()
        mock_client.ping = Mock(side_effect=Exception("Model 'test-model' not found (404)"))
        
        with patch('dumpcode.ai.diagnostics.get_client_for_model', return_value=mock_client):
            result = _ping_model("test-alias", {
                "provider": "test-provider",
                "model_id": "test-model"
            })
            
            assert result["status"] == "⛔ MISSING"
            assert "Model ID not found" in result["details"]
    
    def test_ping_model_timeout(self):
        """Test _ping_model function with timeout error."""
        mock_client = Mock()
        mock_client.ping = Mock(side_effect=Exception("Request timeout after 30 seconds"))
        
        with patch('dumpcode.ai.diagnostics.get_client_for_model', return_value=mock_client):
            result = _ping_model("test-alias", {
                "provider": "test-provider",
                "model_id": "test-model"
            })
            
            assert result["status"] == "⏱️ TIMEOUT"
            assert "Late response" in result["details"]
    
    def test_ping_model_max_tokens_reached(self):
        """Test _ping_model function with max tokens error (should count as online)."""
        mock_client = Mock()
        mock_client.ping = Mock(side_effect=Exception("max_tokens limit reached"))
        
        with patch('dumpcode.ai.diagnostics.get_client_for_model', return_value=mock_client):
            result = _ping_model("test-alias", {
                "provider": "test-provider",
                "model_id": "test-model"
            })
            
            # Max tokens error should still count as online
            assert result["status"] == "✅ ONLINE"
            assert "Available (Limit Reached)" in result["details"]
    
    def test_ping_model_generic_error(self):
        """Test _ping_model function with generic error."""
        mock_client = Mock()
        mock_client.ping = Mock(side_effect=Exception("Some unexpected error"))
        
        with patch('dumpcode.ai.diagnostics.get_client_for_model', return_value=mock_client):
            result = _ping_model("test-alias", {
                "provider": "test-provider",
                "model_id": "test-model"
            })
            
            assert result["status"] == "❌ ERROR"
            assert "Some unexpected error" in result["details"]