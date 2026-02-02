"""Integration tests for AI auto mode."""

import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def ai_enabled_profile():
    """Profile with AI auto mode enabled."""
    return {
        "description": "Test AI profile",
        "pre": ["Test instruction"],
        "post": "Test task",
        "model": "claude-sonnet-4-5-20250929",
        "auto": True
    }


class TestAutoModeIntegration:
    """Integration tests for auto mode."""
    
    def test_auto_mode_cli_override(self, tmp_path, ai_enabled_profile):
        """Test --no-auto overrides profile setting."""
        from dumpcode.main import run_dump
        import argparse
        
        args = argparse.Namespace(
            output_file="dump.txt",
            level=2,
            dir_only=False,
            ignore_errors=False,
            structure_only=False,
            no_copy=True,
            no_xml=False,
            changed=False,
            question=None,
            reset_version=False,
            verbose=False,
            auto=False,
            no_auto=True,  # Override
            model=None,
            test_profile=True
        )
        
        config = {"profiles": {"test_profile": ai_enabled_profile}}
        
        with patch("dumpcode.main.DumpEngine") as MockEngine:
            mock_instance = Mock()
            MockEngine.return_value = mock_instance
            
            run_dump(args, config, tmp_path)
            
            # Verify auto_mode is False due to --no-auto
            call_args = MockEngine.call_args
            settings = call_args[0][1]
            assert settings.auto_mode is False
    
    def test_auto_mode_profile_default(self, tmp_path, ai_enabled_profile):
        """Test profile auto setting is used when no CLI flags."""
        from dumpcode.main import run_dump
        import argparse
        
        args = argparse.Namespace(
            output_file="dump.txt",
            level=2,
            dir_only=False,
            ignore_errors=False,
            structure_only=False,
            no_copy=True,
            no_xml=False,
            changed=False,
            question=None,
            reset_version=False,
            verbose=False,
            auto=False,
            no_auto=False,
            model=None,
            test_profile=True
        )
        
        config = {"profiles": {"test_profile": ai_enabled_profile}}
        
        with patch("dumpcode.main.DumpEngine") as MockEngine:
            mock_instance = Mock()
            MockEngine.return_value = mock_instance
            
            run_dump(args, config, tmp_path)
            
            # Verify auto_mode is True from profile
            call_args = MockEngine.call_args
            settings = call_args[0][1]
            assert settings.auto_mode is True
    
    def test_auto_mode_cli_force(self, tmp_path, ai_enabled_profile):
        """Test --auto forces auto mode even if profile has auto: false."""
        from dumpcode.main import run_dump
        import argparse
        
        # Modify profile to have auto: false
        profile_without_auto = ai_enabled_profile.copy()
        profile_without_auto["auto"] = False
        
        args = argparse.Namespace(
            output_file="dump.txt",
            level=2,
            dir_only=False,
            ignore_errors=False,
            structure_only=False,
            no_copy=True,
            no_xml=False,
            changed=False,
            question=None,
            reset_version=False,
            verbose=False,
            auto=True,  # Force auto
            no_auto=False,
            model=None,
            test_profile=True
        )
        
        config = {"profiles": {"test_profile": profile_without_auto}}
        
        with patch("dumpcode.main.DumpEngine") as MockEngine:
            mock_instance = Mock()
            MockEngine.return_value = mock_instance
            
            run_dump(args, config, tmp_path)
            
            # Verify auto_mode is True due to --auto flag
            call_args = MockEngine.call_args
            settings = call_args[0][1]
            assert settings.auto_mode is True
    
    def test_model_override_cli(self, tmp_path, ai_enabled_profile):
        """Test --model CLI override."""
        from dumpcode.main import run_dump
        import argparse
        
        args = argparse.Namespace(
            output_file="dump.txt",
            level=2,
            dir_only=False,
            ignore_errors=False,
            structure_only=False,
            no_copy=True,
            no_xml=False,
            changed=False,
            question=None,
            reset_version=False,
            verbose=False,
            auto=False,
            no_auto=False,
            model="claude-opus-4-5-20251101",  # CLI override
            test_profile=True
        )
        
        config = {"profiles": {"test_profile": ai_enabled_profile}}
        
        with patch("dumpcode.main.DumpEngine") as MockEngine:
            mock_instance = Mock()
            MockEngine.return_value = mock_instance
            
            run_dump(args, config, tmp_path)
            
            # Verify model_override is set from CLI
            call_args = MockEngine.call_args
            settings = call_args[0][1]
            assert settings.model_override == "claude-opus-4-5-20251101"