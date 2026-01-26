"""Git fixtures for DumpCode tests."""

import subprocess

import pytest


@pytest.fixture
def git_repo(tmp_path):
    """Provides a tmp_path with git init, config, and one committed file."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "ci@test.com"], cwd=tmp_path)
    subprocess.run(["git", "config", "user.name", "CI"], cwd=tmp_path)
    (tmp_path / "README.md").write_text("initial")
    subprocess.run(["git", "add", "."], cwd=tmp_path)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path)
    return tmp_path