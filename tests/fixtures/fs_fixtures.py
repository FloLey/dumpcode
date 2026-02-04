"""File system fixtures for DumpCode tests."""

import json
from pathlib import Path
from typing import Optional

import pytest

from dumpcode.core import DumpSettings, TreeEntry


@pytest.fixture
def project_env(tmp_path):
    """Generate a tmp_path with a standard project structure.
    
    Creates:
    - src/main.py
    - .gitignore
    - .dump_config.json (valid config)
    """
    # Create standard project structure
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    
    # Create main.py with some content
    main_py = src_dir / "main.py"
    main_py.write_text('print("Hello, World!")\n')
    
    # Create .gitignore
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.pyc\n__pycache__/\n")
    
    # Create valid .dump_config.json
    config = {
        "version": 1,
        "ignore_patterns": ["*.pyc", "__pycache__"],
        "profiles": {
            "test-profile": {
                "description": "Test profile for testing",
                "run_commands": ["echo 'test command'"],
                "model": "claude-3-5-sonnet-latest",
                "auto_send": False
            }
        }
    }
    config_file = tmp_path / ".dump_config.json"
    config_file.write_text(json.dumps(config, indent=2))
    
    return tmp_path


@pytest.fixture
def default_settings(project_env):
    """Provide a pre-configured DumpSettings object pointing to project_env."""
    output_file = project_env / "output.txt"
    return DumpSettings(
        start_path=project_env,
        output_file=output_file,
        use_xml=True,
        active_profile=None,
        max_depth=3,
        dir_only=False,
        git_changed_only=False,
        structure_only=False,
        ignore_errors=False,
        no_copy=True,
        reset_version=False,
        verbose=False,
        question=None
    )


@pytest.fixture
def deep_project(tmp_path):
    """Provides a 3-level deep directory structure with mixed file types.
    
    Structure:
    root/
      dir1/
        file1.txt
        dir2/
          file2.txt
          dir3/
            file3.txt
      binary.dat (binary file)
      ignored.pyc (file that would be ignored by .gitignore patterns)
    """
    # Create nested directory structure
    dir1 = tmp_path / "dir1"
    dir1.mkdir()
    dir2 = dir1 / "dir2"
    dir2.mkdir()
    dir3 = dir2 / "dir3"
    dir3.mkdir()
    
    # Create text files at each level
    (dir1 / "file1.txt").write_text("Content of file1")
    (dir2 / "file2.txt").write_text("Content of file2")
    (dir3 / "file3.txt").write_text("Content of file3")
    
    # Create binary file
    binary_file = tmp_path / "binary.dat"
    binary_file.write_bytes(b"\x00\x01\x02\x03\x04\x05")
    
    # Create file that would typically be ignored
    ignored_file = tmp_path / "ignored.pyc"
    ignored_file.write_text("Compiled Python bytecode")
    
    return tmp_path


@pytest.fixture
def tree_entry_factory():
    """Factory for creating TreeEntry objects with sensible defaults.
    
    Args:
        path: Path to the file or directory
        depth: Depth in the tree (default: 0)
        is_last: Whether this entry is the last child of its parent (default: True)
        is_dir: Whether this entry is a directory (default: False)
        is_recursive_link: Whether this entry is a recursive symlink (default: False)
        error_msg: Optional error message (default: None)
        ancestor_is_last: List indicating if each ancestor at depth N is a last child (default: [])
    
    Returns:
        A function that creates TreeEntry objects with the given parameters
    """
    def make_tree_entry(
        path: Path,
        depth: int = 0,
        is_last: bool = True,
        is_dir: bool = False,
        is_recursive_link: bool = False,
        error_msg: Optional[str] = None,
        ancestor_is_last: Optional[list[bool]] = None
    ) -> TreeEntry:
        if ancestor_is_last is None:
            ancestor_is_last = []
        return TreeEntry(
            path=path,
            depth=depth,
            is_last=is_last,
            is_dir=is_dir,
            is_recursive_link=is_recursive_link,
            error_msg=error_msg,
            ancestor_is_last=ancestor_is_last
        )
    return make_tree_entry


@pytest.fixture
def settings_factory(tmp_path):
    """Factory for creating DumpSettings objects with sensible defaults.
    
    Args:
        start_path: Path to the root of the codebase (default: tmp_path)
        output_file: Path where the resulting dump file will be saved (default: tmp_path/"output.txt")
        max_depth: Maximum recursion depth for directory traversal (default: 3)
        dir_only: Whether to only include directory structures (default: False)
        ignore_errors: Whether to suppress encoding/read errors (default: False)
        structure_only: Whether to omit file contents in the dump (default: False)
        no_copy: Whether to skip OSC52 clipboard copying (default: True)
        use_xml: Whether to wrap output in semantic XML tags (default: True)
        git_changed_only: Whether to only dump files modified in git (default: False)
        question: Optional user instruction to append to the prompt (default: None)
        active_profile: Optional profile configuration (default: None)
        reset_version: Whether to reset version counter (default: False)
        verbose: Whether to show detailed processing logs (default: False)
    
    Returns:
        A function that creates DumpSettings objects with the given parameters
    """
    def make_dump_settings(
        start_path: Optional[Path] = None,
        output_file: Optional[Path] = None,
        max_depth: int = 3,
        dir_only: bool = False,
        ignore_errors: bool = False,
        structure_only: bool = False,
        no_copy: bool = True,
        use_xml: bool = True,
        git_changed_only: bool = False,
        question: Optional[str] = None,
        active_profile: Optional[dict] = None,
        reset_version: bool = False,
        verbose: bool = False
    ) -> DumpSettings:
        if start_path is None:
            start_path = tmp_path
        if output_file is None:
            output_file = tmp_path / "output.txt"
        
        return DumpSettings(
            start_path=start_path,
            output_file=output_file,
            max_depth=max_depth,
            dir_only=dir_only,
            ignore_errors=ignore_errors,
            structure_only=structure_only,
            no_copy=no_copy,
            use_xml=use_xml,
            git_changed_only=git_changed_only,
            question=question,
            active_profile=active_profile,
            reset_version=reset_version,
            verbose=verbose
        )
    return make_dump_settings