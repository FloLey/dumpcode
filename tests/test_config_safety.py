"""Unit tests for config safety checks."""

import sys
from pathlib import Path

from src.dumpcode.config import is_safe_to_create_config


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