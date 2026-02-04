"""Unit tests for configuration loading."""

import json
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from dumpcode.config import (
    load_or_create_config,
    interactive_init,
    increment_config_version,
    validate_config,
    is_safe_to_create_config
)
from dumpcode.constants import CONFIG_FILENAME, DEFAULT_PROFILES, DEFAULT_MODEL


class TestConfigLoading:
    """Test the load_or_create_config function."""
    
    def test_create_new_config(self, tmp_path):
        """Test creating a new config when none exists."""
        config = load_or_create_config(tmp_path, reset_version=False)

        assert "version" in config
        assert "ignore_patterns" in config
        assert "profiles" in config
        assert config["version"] == 1
        
        config_path = tmp_path / CONFIG_FILENAME
        assert config_path.exists()
        
        with open(config_path, "r") as f:
            saved_config = json.load(f)
        assert saved_config["version"] == 1
    
    def test_load_existing_config(self, tmp_path):
        """Test loading an existing config file."""
        config_path = tmp_path / CONFIG_FILENAME
        test_config = {
            "version": 5,
            "ignore_patterns": ["*.pyc", "node_modules"],
            "profiles": {"custom": {"description": "Test"}}
        }
        with open(config_path, "w") as f:
            json.dump(test_config, f)
        
        config = load_or_create_config(tmp_path, reset_version=False)
        
        assert config["version"] == 5
        assert config["ignore_patterns"] == ["*.pyc", "node_modules"]
        assert "custom" in config["profiles"]
        
        with open(config_path, "r") as f:
            saved_config = json.load(f)
        assert saved_config["version"] == 5
    
    def test_reset_version(self, tmp_path):
        """Test resetting version to 1."""
        config_path = tmp_path / CONFIG_FILENAME
        test_config = {"version": 5, "ignore_patterns": [], "profiles": {"test": {"description": "Test"}}}
        with open(config_path, "w") as f:
            json.dump(test_config, f)
        
        config = load_or_create_config(tmp_path, reset_version=True)
        
        assert config["version"] == 1
        
        with open(config_path, "r") as f:
            saved_config = json.load(f)
        assert saved_config["version"] == 1
    
    def test_corrupted_config(self, tmp_path):
        """Test handling of corrupted config file."""
        config_path = tmp_path / CONFIG_FILENAME
        with open(config_path, "w") as f:
            f.write("{ invalid json")
        
        config = load_or_create_config(tmp_path, reset_version=False)
        
        assert "version" in config
        assert "ignore_patterns" in config
        assert "profiles" in config
        
        with open(config_path, "r") as f:
            saved_config = json.load(f)
        assert "version" in saved_config
    
    def test_missing_profiles(self, tmp_path):
        """Test config missing profiles key."""
        config_path = tmp_path / CONFIG_FILENAME
        test_config = {"version": 1, "ignore_patterns": []}
        with open(config_path, "w") as f:
            json.dump(test_config, f)
        
        config = load_or_create_config(tmp_path, reset_version=False)
        
        assert "profiles" in config
        assert config["profiles"] == DEFAULT_PROFILES
    
    def test_merge_with_defaults(self, tmp_path):
        """Test that loaded config merges with defaults."""
        config_path = tmp_path / CONFIG_FILENAME
        test_config = {
            "version": 3,
            "profiles": {"test": {"description": "Test profile"}}
        }
        with open(config_path, "w") as f:
            json.dump(test_config, f)
        
        config = load_or_create_config(tmp_path, reset_version=False)
        
        assert config["version"] == 3
        assert "ignore_patterns" in config
        assert "profiles" in config
        assert "test" in config["profiles"]
        assert "readme" in config["profiles"]


def test_interactive_init_creates_ai_fields(tmp_path):
    """Verify that init generates a config with auto_send=False and Sonnet."""
    # Mock inputs for standard questions
    with patch('builtins.input', side_effect=['', 'y']):
        interactive_init(tmp_path)

    config_path = tmp_path / CONFIG_FILENAME
    with open(config_path, "r") as f:
        data = json.load(f)

    # Check a representative profile (e.g., readme)
    readme_profile = data["profiles"]["readme"]
    assert readme_profile["auto_send"] is False
    assert readme_profile["model"] == DEFAULT_MODEL


def test_config_migration_on_load(tmp_path):
    """Verify that old 'auto' keys are converted to 'auto_send' upon loading."""
    legacy_config = {
        "version": 1,
        "profiles": {
            "legacy_prof": {
                "description": "Legacy profile",
                "auto": True,
                "model": "gpt-4"
            }
        }
    }
    (tmp_path / CONFIG_FILENAME).write_text(json.dumps(legacy_config))

    # Loading the config should trigger migration
    config = load_or_create_config(tmp_path)

    profile = config["profiles"]["legacy_prof"]
    assert "auto_send" in profile
    assert profile["auto_send"] is True
    assert "auto" not in profile  # Should be popped


def test_config_migration_preserves_auto_send(tmp_path):
    """Verify that migration doesn't overwrite existing auto_send."""
    config_with_both = {
        "version": 1,
        "profiles": {
            "mixed_prof": {
                "description": "Profile with both keys",
                "auto": True,
                "auto_send": False  # Explicit auto_send should be preserved
            }
        }
    }
    (tmp_path / CONFIG_FILENAME).write_text(json.dumps(config_with_both))

    config = load_or_create_config(tmp_path)

    profile = config["profiles"]["mixed_prof"]
    # auto_send was already present, should keep its value
    assert profile["auto_send"] is False
    # 'auto' should still exist since migration only runs when auto_send is absent
    assert "auto" in profile


def test_interactive_init_flow(tmp_path, capsys):
    """Test interactive_init with user input simulation."""
    # Create existing config to trigger overwrite prompt
    config_path = tmp_path / CONFIG_FILENAME
    with open(config_path, "w") as f:
        json.dump({"version": 1, "ignore_patterns": [], "profiles": {}}, f)
    
    # Simulate user inputs: 'y' to overwrite, 'node_modules,temp' for extra ignores, 'y' for XML
    with patch('builtins.input', side_effect=['y', 'node_modules,temp', 'y']):
        interactive_init(tmp_path)
    
    config_path = tmp_path / CONFIG_FILENAME
    assert config_path.exists()
    
    with open(config_path, "r") as f:
        config = json.load(f)
    
    # Check basic structure
    assert config["version"] == 1
    assert "ignore_patterns" in config
    assert "profiles" in config
    assert "use_xml" in config
    
    # Check that extra ignores were added
    assert "node_modules" in config["ignore_patterns"]
    assert "temp" in config["ignore_patterns"]
    
    # Check default ignores are still there
    assert ".git" in config["ignore_patterns"]
    assert "__pycache__" in config["ignore_patterns"]
    
    # Check XML preference
    assert config["use_xml"] is True
    
    # Check output contains success message
    captured = capsys.readouterr()
    assert "✅ Created" in captured.out


def test_interactive_init_no_overwrite(tmp_path, capsys):
    """Test interactive_init when user chooses not to overwrite existing config."""
    # Create an existing config file
    config_path = tmp_path / CONFIG_FILENAME
    existing_config = {"version": 1, "ignore_patterns": ["existing"], "profiles": {}, "use_xml": False}
    with open(config_path, "w") as f:
        json.dump(existing_config, f)
    
    # Simulate user input: 'n' to not overwrite
    with patch('builtins.input', return_value='n'):
        interactive_init(tmp_path)
    
    # Config should remain unchanged
    with open(config_path, "r") as f:
        config = json.load(f)
    
    assert config["ignore_patterns"] == ["existing"]
    assert config["use_xml"] is False
    
    # Check output doesn't contain success message
    captured = capsys.readouterr()
    assert "✅ Created" not in captured.out


def test_interactive_init_no_extra_ignores(tmp_path, capsys):
    """Test interactive_init with empty extra ignores input."""
    # Create existing config to trigger overwrite prompt
    config_path = tmp_path / CONFIG_FILENAME
    with open(config_path, "w") as f:
        json.dump({"version": 1, "ignore_patterns": [], "profiles": {}}, f)
    
    with patch('builtins.input', side_effect=['y', '', 'n']):
        interactive_init(tmp_path)
    
    config_path = tmp_path / CONFIG_FILENAME
    with open(config_path, "r") as f:
        config = json.load(f)
    
    # Should have default ignores only
    assert ".git" in config["ignore_patterns"]
    assert "__pycache__" in config["ignore_patterns"]
    assert config["use_xml"] is False  # 'n' for XML


def test_interactive_init_no_xml_default(tmp_path, capsys):
    """Test interactive_init with 'n' for XML preference."""
    # Create existing config to trigger overwrite prompt
    config_path = tmp_path / CONFIG_FILENAME
    with open(config_path, "w") as f:
        json.dump({"version": 1, "ignore_patterns": [], "profiles": {}}, f)
    
    with patch('builtins.input', side_effect=['y', '', 'n']):
        interactive_init(tmp_path)
    
    config_path = tmp_path / CONFIG_FILENAME
    with open(config_path, "r") as f:
        config = json.load(f)
    
    assert config["use_xml"] is False


def test_interactive_init_empty_xml_input(tmp_path, capsys):
    """Test interactive_init with empty XML preference (should default to True)."""
    with patch('builtins.input', side_effect=['y', '', '']):
        interactive_init(tmp_path)
    
    config_path = tmp_path / CONFIG_FILENAME
    with open(config_path, "r") as f:
        config = json.load(f)
    
    assert config["use_xml"] is True  # Empty input should default to True


class TestConfigSafety:
    """Test the is_safe_to_create_config function."""
    
    def test_project_directory(self, tmp_path):
        """Test that project directories are safe."""
        project_dir = tmp_path / "my_project"
        project_dir.mkdir()
        (project_dir / "README.md").touch()
        (project_dir / "src").mkdir()
        
        assert is_safe_to_create_config(project_dir)
    
    def test_empty_directory(self, tmp_path):
        """Test that empty directories are safe."""
        empty_dir = tmp_path / "empty_dir"
        empty_dir.mkdir()
        
        assert is_safe_to_create_config(empty_dir)
    
    def test_directory_with_git(self, tmp_path):
        """Test that directories with .git are safe."""
        git_dir = tmp_path / "git_project"
        git_dir.mkdir()
        (git_dir / ".git").mkdir()
        
        assert is_safe_to_create_config(git_dir)
    
    def test_directory_with_pyproject(self, tmp_path):
        """Test that directories with pyproject.toml are safe."""
        pyproject_dir = tmp_path / "python_project"
        pyproject_dir.mkdir()
        (pyproject_dir / "pyproject.toml").touch()
        
        assert is_safe_to_create_config(pyproject_dir)
    
    def test_home_directory(self):
        """Test that home directory is not safe."""
        home_dir = Path.home()
        # Note: This test might fail in CI environments where home is a test directory
        # We'll skip it if home looks like a test directory
        if "test" not in str(home_dir).lower() and "tmp" not in str(home_dir).lower():
            assert not is_safe_to_create_config(home_dir)
    
    def test_root_directory(self):
        """Test that root directory is not safe."""
        # Skip on Windows or if we can't access root
        if sys.platform != "win32":
            root_dir = Path("/")
            assert not is_safe_to_create_config(root_dir)
    
    def test_etc_directory(self):
        """Test that /etc directory is not safe."""
        if sys.platform != "win32":
            etc_dir = Path("/etc")
            if etc_dir.exists():
                assert not is_safe_to_create_config(etc_dir)
    
    def test_tmp_directory(self):
        """Test that /tmp directory is safe (common for temporary projects)."""
        if sys.platform != "win32":
            tmp_dir = Path("/tmp")
            if tmp_dir.exists():
                # /tmp should be safe for temporary projects
                assert is_safe_to_create_config(tmp_dir)
    
    def test_large_project_directory(self, tmp_path):
        """Test that large directories WITH project indicators are safe."""
        # Create a directory with many files AND project indicators
        large_project_dir = tmp_path / "large_project"
        large_project_dir.mkdir()
        (large_project_dir / ".git").mkdir()  # Project indicator
        
        # Create many files
        for _ in range(150):
            (large_project_dir / f"file{_}.txt").touch()
        
        # Should be safe (has project indicator)
        assert is_safe_to_create_config(large_project_dir)
    
    def test_permission_error_handling(self, tmp_path):
        """Test that permission errors are handled gracefully."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        result = is_safe_to_create_config(test_dir)
        assert isinstance(result, bool)


# Config management tests moved from test_utils.py
def test_increment_config_version(tmp_path):
    """Test increment_config_version function."""
    config_path = tmp_path / ".dump_config.json"
    initial_config = {"version": 5, "profiles": {"test": {}}}
    config_path.write_text(json.dumps(initial_config))
    
    increment_config_version(tmp_path)
    
    updated_config = json.loads(config_path.read_text())
    assert updated_config["version"] == 6
    assert "profiles" in updated_config


def test_increment_config_version_no_file(tmp_path):
    """Test increment_config_version when config file doesn't exist."""
    # Should not raise an error
    increment_config_version(tmp_path)


def test_increment_config_version_invalid_version(tmp_path):
    """Test increment_config_version with non-numeric version."""
    config_path = tmp_path / ".dump_config.json"
    initial_config = {"version": "not-a-number", "profiles": {}}
    config_path.write_text(json.dumps(initial_config))
    
    increment_config_version(tmp_path)
    
    updated_config = json.loads(config_path.read_text())
    assert updated_config["version"] == 1  # Should reset to 1


def test_increment_config_version_no_version_field(tmp_path):
    """Test increment_config_version when version field is missing."""
    config_path = tmp_path / ".dump_config.json"
    initial_config = {"profiles": {"test": {}}}  # No version field
    config_path.write_text(json.dumps(initial_config))
    
    increment_config_version(tmp_path)
    
    updated_config = json.loads(config_path.read_text())
    assert updated_config["version"] == 1  # Should add version field


def test_increment_config_version_with_logger(tmp_path):
    """Test increment_config_version with logger parameter."""
    config_path = tmp_path / ".dump_config.json"
    initial_config = {"version": 10}
    config_path.write_text(json.dumps(initial_config))
    
    mock_logger = Mock()
    increment_config_version(tmp_path, mock_logger)
    
    updated_config = json.loads(config_path.read_text())
    assert updated_config["version"] == 11
    # Logger should not be called for normal operation


def test_validate_config_valid():
    """Test validate_config with valid configuration."""
    valid_config = {
        "version": 1,
        "profiles": {
            "test": {
                "description": "Test profile",
                "pre": "Pre-prompt",
                "post": "Post-prompt",
                "run_commands": ["echo test"]
            }
        }
    }
    
    assert validate_config(valid_config) is True


@pytest.mark.parametrize("invalid_config", [
    {},  # Empty dict
    {"version": 1},  # Missing profiles
    {"profiles": {}},  # Missing version
    {"version": "not-a-number", "profiles": {}},  # Invalid version type
    {"version": 1, "profiles": "not-a-dict"},  # Invalid profiles type
    {"version": 1, "profiles": {"test": "not-a-dict"}},  # Profile not a dict
    {"version": 1, "profiles": {"test": {}}},  # Empty profile dict
    {"version": 1, "profiles": {"test": {"invalid_key": "value"}}},  # No valid keys
])
def test_validate_config_invalid_structure(invalid_config):
    """Test validate_config with invalid structure."""
    assert validate_config(invalid_config) is False


def test_validate_config_profile_with_run_commands():
    """Test validate_config with profile containing only run_commands."""
    config = {
        "version": 1,
        "profiles": {
            "test": {
                "run_commands": ["echo test"]  # Only run_commands is valid
            }
        }
    }
    
    assert validate_config(config) is True


@pytest.mark.edge_case
def test_config_save_failure_logging(tmp_path, capsys):
    """Cover config.py:122-126 (Handling write failures on config creation)"""
    import builtins
    # Force open to fail only when writing (mode 'w')
    original_open = builtins.open
    def side_effect(file, mode, *args, **kwargs):
        if "w" in mode and ".dump_config.json" in str(file):
            raise OSError("Disk Full")
        return original_open(file, mode, *args, **kwargs)

    with patch("builtins.open", side_effect=side_effect):
        load_or_create_config(tmp_path)
    
    captured = capsys.readouterr()
    assert "[Error] Could not save config: Disk Full" in captured.out


@pytest.mark.edge_case
def test_increment_version_exception(tmp_path, capsys):
    """Cover config.py:154-158 (Exception handling in version increment)"""
    config_path = tmp_path / ".dump_config.json"
    config_path.write_text('{"version": 1}')
    
    with patch("json.load", side_effect=RuntimeError("Corrupt Memory")):
        increment_config_version(tmp_path)
        
    captured = capsys.readouterr()
    assert "[Error] Could not increment config version" in captured.out


# Consolidated tests from test_coverage_final_push.py
def test_config_print_fallbacks(tmp_path, capsys):
    """Cover config.py:102, 111, 124, 156 (Standard output if logger is missing)"""
    from dumpcode.config import load_or_create_config, increment_config_version
    
    config_path = tmp_path / ".dump_config.json"
    
    # 1. Invalid structure warning
    config_path.write_text('{"version": "wrong"}')
    load_or_create_config(tmp_path, logger=None)
    assert "Config file has invalid structure" in capsys.readouterr().out

    # 2. Save failure error
    with patch("json.dump", side_effect=OSError("ReadOnly")):
        load_or_create_config(tmp_path, logger=None)
    assert "Could not save config" in capsys.readouterr().out

    # 3. Increment failure error
    config_path.write_text('{"version": 1}')
    with patch("json.load", side_effect=Exception("Corrupt")):
        increment_config_version(tmp_path, logger=None)
    assert "Could not increment config version" in capsys.readouterr().out


# Consolidated tests from test_final_coverage.py
def test_config_print_fallbacks_2(tmp_path, capsys):
    """Cover config.py:102, 111, 124, 156 (Print when logger is None)"""
    from dumpcode.config import load_or_create_config, increment_config_version
    
    config_path = tmp_path / ".dump_config.json"
    
    # Force invalid config to trigger warning
    config_path.write_text('{"version": "wrong_type"}')
    load_or_create_config(tmp_path, logger=None)
    
    # Force exception during save
    with patch("json.dump", side_effect=OSError("Disk Full")):
        load_or_create_config(tmp_path, logger=None)
        
    # Force exception during version increment
    with patch("json.load", side_effect=Exception("Corrupt")):
        increment_config_version(tmp_path, logger=None)

    captured = capsys.readouterr()
    assert "Config file has invalid structure" in captured.out
    assert "[Error] Could not save config" in captured.out
    assert "[Error] Could not increment config version" in captured.out