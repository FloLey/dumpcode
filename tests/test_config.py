"""Unit tests for configuration loading."""

import json

from src.dumpcode.config import load_or_create_config
from src.dumpcode.constants import CONFIG_FILENAME, DEFAULT_PROFILES


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