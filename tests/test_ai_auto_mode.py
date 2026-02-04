"""Integration tests for AI auto mode."""

import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def ai_enabled_profile():
    """Profile with AI auto mode enabled (using new auto_send key)."""
    return {
        "description": "Test AI profile",
        "pre": ["Test instruction"],
        "post": "Test task",
        "model": "claude-3-5-sonnet-latest",
        "auto_send": True
    }


@pytest.fixture
def ai_enabled_profile_legacy():
    """Profile with AI auto mode enabled (using legacy auto key)."""
    return {
        "description": "Test AI profile (legacy)",
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


def test_settings_factory_resolves_renamed_key(tmp_path):
    """Ensure the engine correctly interprets the auto_send key from config."""
    from dumpcode.core import DumpSettings
    import argparse

    args = argparse.Namespace(
        auto=False, no_auto=False, test_profile=True,
        output_file="out.txt", level=None, dir_only=False,
        ignore_errors=False, structure_only=False, no_copy=True,
        changed=False, question=None, reset_version=False,
        verbose=False, model=None, no_xml=False
    )

    config = {
        "profiles": {
            "test_profile": {"description": "Test", "auto_send": True, "model": "sonnet"}
        }
    }

    settings = DumpSettings.from_arguments(args, config, tmp_path)
    assert settings.auto_mode is True


def test_settings_factory_resolves_legacy_key(tmp_path):
    """Ensure the engine correctly interprets the legacy auto key from config."""
    from dumpcode.core import DumpSettings
    import argparse

    args = argparse.Namespace(
        auto=False, no_auto=False, legacy_profile=True,
        output_file="out.txt", level=None, dir_only=False,
        ignore_errors=False, structure_only=False, no_copy=True,
        changed=False, question=None, reset_version=False,
        verbose=False, model=None, no_xml=False
    )

    config = {
        "profiles": {
            "legacy_profile": {"description": "Legacy", "auto": True, "model": "gpt-4"}
        }
    }

    settings = DumpSettings.from_arguments(args, config, tmp_path)
    assert settings.auto_mode is True


def test_settings_auto_send_takes_precedence_over_auto(tmp_path):
    """Ensure auto_send takes precedence when both keys exist."""
    from dumpcode.core import DumpSettings
    import argparse

    args = argparse.Namespace(
        auto=False, no_auto=False, mixed_profile=True,
        output_file="out.txt", level=None, dir_only=False,
        ignore_errors=False, structure_only=False, no_copy=True,
        changed=False, question=None, reset_version=False,
        verbose=False, model=None, no_xml=False
    )

    config = {
        "profiles": {
            "mixed_profile": {
                "description": "Mixed",
                "auto": True,  # Legacy key says True
                "auto_send": False  # New key says False - should win
            }
        }
    }

    settings = DumpSettings.from_arguments(args, config, tmp_path)
    assert settings.auto_mode is False  # auto_send takes precedence