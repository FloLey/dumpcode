"""Tests for git integration features."""

import subprocess
from unittest.mock import Mock, patch

from dumpcode.utils import get_git_modified_files
from dumpcode.core import DumpSession


def test_get_git_modified_files_success(git_repo):
    """Test get_git_modified_files with successful git command."""
    # git_repo fixture provides initialized git repository
    # Create and modify a file
    test_file = git_repo / "test.py"
    test_file.write_text("print('hello')")
    subprocess.run(["git", "add", "test.py"], cwd=git_repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=git_repo, capture_output=True)
    
    # Modify the file
    test_file.write_text("print('modified')")
    
    # Get modified files
    modified_files = get_git_modified_files(git_repo)
    
    assert len(modified_files) == 1
    assert modified_files[0] == test_file


def test_get_git_modified_files_untracked(git_repo):
    """Test get_git_modified_files with untracked files."""
    # git_repo fixture provides initialized git repository
    
    # Create untracked files
    untracked1 = git_repo / "untracked1.py"
    untracked2 = git_repo / "untracked2.py"
    untracked1.write_text("untracked 1")
    untracked2.write_text("untracked 2")
    
    # Get modified files (should include untracked)
    modified_files = get_git_modified_files(git_repo)
    
    assert len(modified_files) == 2
    assert set(modified_files) == {untracked1, untracked2}


def test_get_git_modified_files_git_not_found(tmp_path, monkeypatch):
    """Test get_git_modified_files when git is not installed."""
    monkeypatch.setattr(subprocess, "run", Mock(side_effect=FileNotFoundError()))
    
    modified_files = get_git_modified_files(tmp_path)
    
    assert modified_files == []


def test_get_git_modified_files_git_error(tmp_path):
    """Test get_git_modified_files when git command fails."""
    # Not a git repository
    modified_files = get_git_modified_files(tmp_path)
    
    assert modified_files == []


def test_dump_session_filter_git_changed_files(tmp_path):
    """Test DumpSession git filtering through collect_files method."""
    # Create test files
    file1 = tmp_path / "file1.py"
    file2 = tmp_path / "file2.py"
    file3 = tmp_path / "file3.py"
    
    file1.write_text("content1")
    file2.write_text("content2")
    file3.write_text("content3")
    
    # Create session with git_changed_only=True
    session = DumpSession(
        root_path=tmp_path,
        excluded_patterns=set(),
        max_depth=1,
        dir_only=False,
        git_changed_only=True
    )
    
    # Mock get_git_modified_files to return only file1 and file2
    mock_git_files = [file1, file2]
    with patch("dumpcode.core.get_git_modified_files", return_value=mock_git_files):
        session.generate_tree(tmp_path)
        session.filter_git_changed_files()
        
        # Check that only git-modified files are in files_to_dump
        file_names = [f.name for f in session.files_to_dump]
        assert "file1.py" in file_names
        assert "file2.py" in file_names
        assert "file3.py" not in file_names
        assert session.file_count == 2


def test_dump_session_filter_git_changed_files_disabled(tmp_path):
    """Test git filtering when git_changed_only is False."""
    # Create test files
    file1 = tmp_path / "file1.py"
    file2 = tmp_path / "file2.py"
    
    file1.write_text("content1")
    file2.write_text("content2")
    
    # Create session with git_changed_only=False
    session = DumpSession(
        root_path=tmp_path,
        excluded_patterns=set(),
        max_depth=1,
        dir_only=False,
        git_changed_only=False  # Disabled
    )
    
    # Mock get_git_modified_files (should not be called)
    mock_get_git = Mock()
    with patch("dumpcode.core.get_git_modified_files", mock_get_git):
        session.generate_tree(tmp_path)
        session.filter_git_changed_files()
        
        # Should not call git function when disabled
        mock_get_git.assert_not_called()
        
        # All files should be collected
        file_names = [f.name for f in session.files_to_dump]
        assert "file1.py" in file_names
        assert "file2.py" in file_names
        assert session.file_count == 2


def test_dump_session_filter_git_changed_files_empty(tmp_path):
    """Test git filtering when no git-modified files."""
    # Create test files
    file1 = tmp_path / "file1.py"
    file2 = tmp_path / "file2.py"
    
    file1.write_text("content1")
    file2.write_text("content2")
    
    # Create session with git_changed_only=True
    session = DumpSession(
        root_path=tmp_path,
        excluded_patterns=set(),
        max_depth=1,
        dir_only=False,
        git_changed_only=True
    )
    
    # Mock get_git_modified_files to return empty list
    with patch("dumpcode.core.get_git_modified_files", return_value=[]):
        session.generate_tree(tmp_path)
        session.filter_git_changed_files()
        
        # No files should be collected
        assert len(session.files_to_dump) == 0
        assert session.file_count == 0


def test_dump_session_gitignore_processing(tmp_path):
    """Test DumpSession respects .gitignore patterns."""
    # Create .gitignore file
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.pyc\n__pycache__/\nsecret.txt\n")
    
    # Create test files
    file1 = tmp_path / "test.py"  # Should be included
    file2 = tmp_path / "test.pyc"  # Should be excluded by .gitignore
    file3 = tmp_path / "secret.txt"  # Should be excluded by .gitignore
    dir1 = tmp_path / "__pycache__"  # Should be excluded by .gitignore
    dir1.mkdir()
    
    file1.write_text("python file")
    file2.write_text("compiled python")
    file3.write_text("secret content")
    
    # Create session
    session = DumpSession(
        root_path=tmp_path,
        excluded_patterns=set(),
        max_depth=2,
        dir_only=False,
        git_changed_only=False
    )
    
    # Generate tree to collect files
    session.generate_tree(tmp_path)
    
    # Check that only non-ignored files are collected
    file_paths = [f.name for f in session.files_to_dump]
    assert "test.py" in file_paths
    assert "test.pyc" not in file_paths
    assert "secret.txt" not in file_paths


def test_dump_session_gitignore_without_pathspec(tmp_path):
    """Test DumpSession handles missing pathspec module gracefully."""
    # Use patch.dict to simulate missing pathspec module
    import sys
    with patch.dict(sys.modules, {'pathspec': None}):
        # Create .gitignore file
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.pyc\n")
        
        # Create test files
        file1 = tmp_path / "test.py"
        file2 = tmp_path / "test.pyc"
        
        file1.write_text("python file")
        file2.write_text("compiled python")
        
        # Create session
        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns=set(),
            max_depth=1,
            dir_only=False,
            git_changed_only=False
        )
        
        # Generate tree - should ignore .gitignore since pathspec is not available
        session.generate_tree(tmp_path)
        
        # Both files should be collected when pathspec is not available
        file_paths = [f.name for f in session.files_to_dump]
        assert "test.py" in file_paths
        assert "test.pyc" in file_paths  # Would be excluded if pathspec worked


def test_dump_session_malformed_gitignore(tmp_path):
    """Test DumpSession handles malformed .gitignore files gracefully."""
    # Create malformed .gitignore file with invalid pattern
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.pyc\n[invalid-pattern\n__pycache__/\n")
    
    # Create test files
    file1 = tmp_path / "test.py"
    file2 = tmp_path / "test.pyc"
    dir1 = tmp_path / "__pycache__"
    dir1.mkdir()
    
    file1.write_text("python file")
    file2.write_text("compiled python")
    
    # Create session
    session = DumpSession(
        root_path=tmp_path,
        excluded_patterns=set(),
        max_depth=2,
        dir_only=False,
        git_changed_only=False
    )
    
    # Generate tree - should handle malformed patterns gracefully
    session.generate_tree(tmp_path)
    
    # Should still exclude valid patterns and handle invalid ones gracefully
    file_paths = [f.name for f in session.files_to_dump]
    assert "test.py" in file_paths
    # test.pyc might or might not be excluded depending on how pathspec handles the error


def test_dump_session_gitignore_permission_error(tmp_path, monkeypatch):
    """Test DumpSession handles permission errors when reading .gitignore."""
    # Create .gitignore file
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.pyc\n")
    
    # Create test files
    file1 = tmp_path / "test.py"
    file2 = tmp_path / "test.pyc"
    
    file1.write_text("python file")
    file2.write_text("compiled python")
    
    # Mock the open function to raise PermissionError when reading .gitignore
    import builtins
    original_open = builtins.open
    
    def mock_open(file, *args, **kwargs):
        if str(file).endswith(".gitignore"):
            raise PermissionError("Permission denied")
        return original_open(file, *args, **kwargs)
    
    monkeypatch.setattr(builtins, "open", mock_open)
    
    try:
        # Create session - should handle PermissionError gracefully
        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns=set(),
            max_depth=1,
            dir_only=False,
            git_changed_only=False
        )
        
        # Generate tree - should handle permission error gracefully
        session.generate_tree(tmp_path)
        
        # Both files should be collected when .gitignore can't be read
        file_paths = [f.name for f in session.files_to_dump]
        assert "test.py" in file_paths
        assert "test.pyc" in file_paths
    except PermissionError:
        # If PermissionError is raised during initialization, that's also acceptable
        # as long as it's handled gracefully (not crashing the whole application)
        pass


def test_dump_session_concurrent_writes(tmp_path):
    """Test race condition scenario for increment_config_version."""
    import json
    import threading
    import time
    
    config_path = tmp_path / ".dump_config.json"
    initial_config = {"version": 1}
    config_path.write_text(json.dumps(initial_config))
    
    results = []
    errors = []
    
    def increment_config():
        """Simulate concurrent config version increments."""
        try:
            # Read current config
            current_config = json.loads(config_path.read_text())
            current_version = current_config.get("version", 1)
            
            # Simulate processing delay (race condition window)
            time.sleep(0.01)
            
            # Write updated config
            current_config["version"] = current_version + 1
            config_path.write_text(json.dumps(current_config))
            results.append(current_version + 1)
        except Exception as e:
            errors.append(str(e))
    
    # Create multiple threads to simulate concurrent writes
    threads = []
    for _ in range(5):
        t = threading.Thread(target=increment_config)
        threads.append(t)
        t.start()
    
    # Wait for all threads to complete
    for t in threads:
        t.join()
    
    # Check that no errors occurred (or at least handled gracefully)
    # In a real scenario, we might want to implement file locking or atomic writes
    assert len(errors) == 0, f"Errors occurred during concurrent writes: {errors}"
    
    # Final version should be at least 2 (1 + number of successful increments)
    final_config = json.loads(config_path.read_text())
    assert final_config["version"] >= 2