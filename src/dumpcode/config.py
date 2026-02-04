"""Configuration management for DumpCode."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .constants import CONFIG_FILENAME, DEFAULT_PROFILES

DEFAULT_CONFIG = {
    "version": 1,
    "ignore_patterns": [
        CONFIG_FILENAME, ".git", "__pycache__", "*.pyc",
        "venv", ".env", ".DS_Store", "codebase_dump.txt",
        ".claude", ".pytest_cache", "*.egg-info",
        ".github", "dist", "LICENSE", ".gitignore",
        ".mypy_cache", ".ruff_cache",
        "ai_response.md",
    ],
    "profiles": DEFAULT_PROFILES,
    "use_xml": True
}


def validate_config(config: Dict) -> bool:
    """Basic structural check for configuration.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        True if config has valid structure, False otherwise
    """
    if "version" not in config:
        return False

    if not isinstance(config["version"], int):
        return False
    
    profiles = config.get("profiles")
    if not isinstance(profiles, dict):
        return False
    
    for name, body in profiles.items():
        if not isinstance(body, dict):
            return False
        
        valid_keys = {"description", "pre", "post", "run_commands"}
        
        if not any(key in body for key in valid_keys):
            return False
    
    return True


def is_safe_to_create_config(root_path: Path) -> bool:
    """Check if the directory is a sensitive system path to prevent accidental config creation.
    
    Args:
        root_path: The directory path to check.

    Returns:
        True if the path is considered safe, False if it is a sensitive system directory.
    """
    abs_path = root_path.resolve()
    sensitive_parents = {"/bin", "/sbin", "/etc", "/usr", "/var", "/root", "/boot", "/dev"}

    if abs_path == Path.home() or abs_path == Path("/"):
        return False

    path_str = str(abs_path)
    return not any(path_str.startswith(s) for s in sensitive_parents)


def load_or_create_config(
    root_path: Path,
    reset_version: bool = False,
    logger: Optional[logging.Logger] = None
) -> Dict[str, Any]:
    """Load or create configuration file with runtime profile merging.

    Args:
        root_path: Directory to look for config.
        reset_version: If True, resets version counter to 1.
        logger: Optional logger instance.

    Returns:
        The merged configuration dictionary.
    """
    config_path = root_path / CONFIG_FILENAME
    config = DEFAULT_CONFIG.copy()

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded_config = json.load(f)
                
            if not validate_config(loaded_config):
                if logger:
                    logger.warning("Config file has invalid structure, using defaults")
                else:
                    print("[Warning] Config file has invalid structure, using defaults")
            else:
                config.update(loaded_config)
                if "profiles" in loaded_config:
                    config["profiles"] = {**DEFAULT_PROFILES, **loaded_config["profiles"]}

                # MIGRATION: Transparently rename 'auto' to 'auto_send'
                if "profiles" in config:
                    for profile in config["profiles"].values():
                        if "auto" in profile and "auto_send" not in profile:
                            profile["auto_send"] = profile.pop("auto")
        except Exception as e:
            if logger:
                logger.warning(f"Failed to read config: {e}")
            else:
                print(f"[Warning] Failed to read config: {e}")

    if reset_version:
        config["version"] = 1

    if config_path.exists() or is_safe_to_create_config(root_path):
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            if logger:
                logger.error(f"Could not save config: {e}")
            else:
                print(f"[Error] Could not save config: {e}")

    return config


def increment_config_version(root_path: Path, logger: Optional[logging.Logger] = None) -> None:
    """Increment the version number in the configuration file after a successful dump.
    
    Args:
        root_path: Directory containing the config file.
        logger: Optional logger instance for error reporting.
    """
    config_path = root_path / CONFIG_FILENAME
    if not config_path.exists():
        return
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        current_version = config.get("version", 0)
        if isinstance(current_version, (int, float)):
            config["version"] = int(current_version) + 1
        else:
            config["version"] = 1
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        if logger:
            logger.error(f"Could not increment config version: {e}")
        else:
            print(f"[Error] Could not increment config version: {e}")


def interactive_init(root_path: Path) -> None:
    """Guide the user through creating a configuration file interactively.

    Args:
        root_path: Directory where config will be created.
    """
    config_path = root_path / CONFIG_FILENAME
    if config_path.exists():
        confirm = input(f"{CONFIG_FILENAME} already exists. Overwrite? (y/N): ")
        if confirm.lower() != 'y':
            return

    print("🚀 Initializing DumpCode...")
    ignores = [
        ".git", "__pycache__", "venv", ".env", ".claude", ".pytest_cache",
        "*.egg-info", ".github", "dist", "LICENSE", ".gitignore"
    ]
    extra = input(
        "Add extra ignore patterns (comma separated, e.g. node_modules,build): "
    )
    if extra:
        ignores.extend([i.strip() for i in extra.split(",")])

    xml_pref = input(
        "Use XML tags by default? (Highly recommended for LLMs) [Y/n]: "
    ).lower()
    use_xml = False if xml_pref == 'n' else True

    config = {
        "version": 1,
        "ignore_patterns": list(set(ignores)),
        "profiles": DEFAULT_PROFILES,
        "use_xml": use_xml
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    print(f"✅ Created {CONFIG_FILENAME}")