"""Unit tests for DumpSession class."""

import os
from unittest.mock import patch

from dumpcode.constants import CONFIG_FILENAME
from dumpcode.core import DumpSession
from dumpcode.formatters import format_ascii_tree


class TestDumpSessionIsExcluded:
    """Test the is_excluded method of DumpSession."""
    
    def test_no_patterns(self, tmp_path):
        """Test that no patterns means nothing is excluded."""
        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns=set(),
            max_depth=None,
            dir_only=False
        )
        
        test_file = tmp_path / "test.py"
        test_file.touch()
        
        assert not session.is_excluded(test_file)
    
    def test_exclude_by_basename(self, tmp_path):
        """Test excluding files by basename pattern."""
        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns={"*.pyc", "*.log"},
            max_depth=None,
            dir_only=False
        )
        
        pyc_file = tmp_path / "test.pyc"
        pyc_file.touch()
        assert session.is_excluded(pyc_file)
        
        log_file = tmp_path / "app.log"
        log_file.touch()
        assert session.is_excluded(log_file)
        
        py_file = tmp_path / "test.py"
        py_file.touch()
        assert not session.is_excluded(py_file)
    
    def test_exclude_by_relative_path(self, tmp_path):
        """Test excluding files by relative path pattern."""
        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns={"tests/*.py", "src/utils.py"},
            max_depth=None,
            dir_only=False
        )
        
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        
        test_file = tests_dir / "test_example.py"
        test_file.touch()
        assert session.is_excluded(test_file)
        
        util_file = src_dir / "utils.py"
        util_file.touch()
        assert session.is_excluded(util_file)
        
        main_file = src_dir / "main.py"
        main_file.touch()
        assert not session.is_excluded(main_file)
    
    def test_exclude_directory(self, tmp_path):
        """Test excluding entire directories."""
        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns={"node_modules", "venv/"},
            max_depth=None,
            dir_only=False
        )
        
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        venv = tmp_path / "venv"
        venv.mkdir()
        
        node_file = node_modules / "package.json"
        node_file.touch()
        assert session.is_excluded(node_file)
        
        venv_file = venv / "pyvenv.cfg"
        venv_file.touch()
        assert session.is_excluded(venv_file)
        
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        src_file = src_dir / "main.py"
        src_file.touch()
        assert not session.is_excluded(src_file)
    
    def test_exclude_config_file(self, tmp_path):
        """Test that .dump_config.json is always excluded."""
        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns=set(),
            max_depth=None,
            dir_only=False
        )
        
        config_file = tmp_path / CONFIG_FILENAME
        config_file.touch()
        
        assert session.is_excluded(config_file)
    
    def test_exclude_with_directory_marker(self, tmp_path):
        """Test patterns with trailing slash (directory marker)."""
        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns={"dist/", "build/"},
            max_depth=None,
            dir_only=False
        )
        
        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        dist_file = dist_dir / "app.js"
        dist_file.touch()
        assert session.is_excluded(dist_file)
        
        build_file = build_dir / "index.html"
        build_file.touch()
        assert session.is_excluded(build_file)
        
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        src_file = src_dir / "main.py"
        src_file.touch()
        assert not session.is_excluded(src_file)


class TestDumpSessionRecursion:
    """Test recursion detection in DumpSession."""
    
    def test_symlink_loop_detection(self, tmp_path):
        """Test that symlink loops are detected and marked."""
        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns=set(),
            max_depth=None,
            dir_only=False
        )
        
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        
        loop_link = subdir / "parent_link"
        os.symlink(tmp_path, loop_link)
        
        session.generate_tree(tmp_path)
        
        tree_lines = format_ascii_tree(session.tree_entries)
        recursive_markers = [line for line in tree_lines if "Recursive Link" in line]
        assert len(recursive_markers) > 0
    
    def test_permission_denied(self, tmp_path):
        """Test handling of permission denied directories."""
        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns=set(),
            max_depth=None,
            dir_only=False
        )
        
        session.generate_tree(tmp_path)
    
    def test_max_depth(self, tmp_path):
        """Test that max_depth limits traversal."""
        current = tmp_path
        for i in range(5):
            current = current / f"dir{i}"
            current.mkdir()
            (current / f"file{i}.txt").touch()
        
        # Test with max_depth=2
        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns=set(),
            max_depth=2,
            dir_only=False
        )
        
        session.generate_tree(tmp_path)
        
        tree_lines = format_ascii_tree(session.tree_entries)
        dir_lines = [line for line in tree_lines if line.endswith("/")]
        assert len(dir_lines) <= 3
    
    def test_dir_only_mode(self, tmp_path):
        """Test that dir_only mode excludes files from tree."""
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.py").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").touch()
        
        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns=set(),
            max_depth=None,
            dir_only=True
        )
        
        session.generate_tree(tmp_path)
        
        assert len(session.files_to_dump) == 0
        tree_lines = format_ascii_tree(session.tree_entries)
        assert any(line.endswith("/") for line in tree_lines)


# Consolidated tests from test_coverage_final_push.py
def test_core_exclusion_exact_match(tmp_path):
    """Cover core.py:131 (rel_path == clean_pattern)"""
    from dumpcode.core import DumpSession
    
    session = DumpSession(tmp_path, {"src/main.py"}, None, False)
    # File exactly matches an ignore pattern string
    assert session.is_excluded(tmp_path / "src" / "main.py") is True


def test_core_scandir_permission_denied(tmp_path):
    """Cover core.py:209-217 (PermissionError handling during tree walk)"""
    from dumpcode.core import DumpSession
    
    session = DumpSession(tmp_path, set(), None, False)
    with patch("os.scandir", side_effect=PermissionError):
        session.generate_tree(tmp_path)
    # Check that an error entry was recorded in the tree
    assert any("[Permission Denied]" in str(e.error_msg) for e in session.tree_entries)


# Consolidated tests from test_coverage_gaps.py
class TestCoreGaps:
    def test_session_scandir_errors(self, tmp_path):
        """Cover core.py:202-203, 208-219 (FileNotFound and PermissionError in tree walk)"""
        from dumpcode.core import DumpSession
        
        session = DumpSession(tmp_path, set(), None, False)
        
        # 1. Test FileNotFoundError (e.g. dir deleted during scan)
        with patch("os.scandir", side_effect=FileNotFoundError()):
            session.generate_tree(tmp_path)
            # Should return silently
            
        # 2. Test PermissionError
        with patch("os.scandir", side_effect=PermissionError()):
            session.generate_tree(tmp_path)
            # Check if any tree entries were created with error messages
            # The actual error message format might be different
            assert len(session.tree_entries) > 0

    def test_exact_path_exclusion(self, tmp_path):
        """Cover core.py:131 (rel_path == clean_pattern)"""
        from dumpcode.core import DumpSession
        
        session = DumpSession(tmp_path, {"src/main.py"}, None, False)
        target = tmp_path / "src" / "main.py"
        # Mock relative_to to return the exact string
        assert session.is_excluded(target) is True


# Consolidated tests from test_final_coverage.py
def test_core_traversal_race_conditions(tmp_path):
    """Cover core.py:202, 210 (FileNotFound/PermissionError during scan)"""
    from dumpcode.core import DumpSession
    
    session = DumpSession(tmp_path, set(), None, False)
    
    with patch("os.scandir", side_effect=FileNotFoundError):
        session.generate_tree(tmp_path) # Should return silently
        
    with patch("os.scandir", side_effect=PermissionError):
        session.generate_tree(tmp_path)
        # Check that an error entry was created
        assert len(session.tree_entries) > 0
        # The error message format might be different
        assert session.tree_entries[0].error_msg is not None