"""Standardize the public API for the dumpcode package."""

from .cli import parse_arguments_with_profiles
from .config import interactive_init, increment_config_version, is_safe_to_create_config, load_or_create_config, validate_config
from .constants import CONFIG_FILENAME, DEFAULT_PROFILES
from .formatters import PREFIX_EMPTY, PREFIX_LAST, PREFIX_MIDDLE, PREFIX_PASS
from .core import DumpSession, DumpSettings
from .engine import DumpEngine
from .processors import (
    CONTENT_PROCESSORS,
    detect_file_encoding,
    get_file_content,
    is_binary_file,
    truncate_text_lines,
)
from .utils import copy_to_clipboard_osc52, estimate_tokens, get_git_modified_files
from .writer import DumpWriter

__version__ = "1.3.0"

__all__ = [
    "parse_arguments_with_profiles",
    "load_or_create_config",
    "increment_config_version",
    "validate_config",
    "is_safe_to_create_config",
    "DumpSession",
    "DumpSettings",
    "detect_file_encoding",
    "is_binary_file",
    "get_file_content",
    "CONTENT_PROCESSORS",
    "truncate_text_lines",
    "copy_to_clipboard_osc52",
    "estimate_tokens",
    "get_git_modified_files",
    "DumpWriter",
    "interactive_init",
    "CONFIG_FILENAME",
    "DEFAULT_PROFILES",
    "PREFIX_EMPTY",
    "PREFIX_LAST",
    "PREFIX_MIDDLE",
    "PREFIX_PASS",
    "DumpEngine",
]
