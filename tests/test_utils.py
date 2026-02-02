"""Additional tests for utility functions."""

import pytest
import sys
from unittest.mock import Mock, patch

from dumpcode.utils import copy_to_clipboard_osc52, estimate_tokens, run_shell_command


def test_copy_to_clipboard_osc52_tty(tmp_path, capsys, monkeypatch):
    """Test copy_to_clipboard_osc52 when stdout is a tty."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")
    
    # Mock isatty to return True
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    
    copy_to_clipboard_osc52(test_file)
    
    captured = capsys.readouterr()
    # Should output OSC52 escape sequence
    assert "\033]52;c;" in captured.out


def test_copy_to_clipboard_osc52_no_tty(tmp_path, capsys, ui_simulation):
    """Test copy_to_clipboard_osc52 when stdout is not a tty."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")
    
    # Use ui_simulation fixture to set non-TTY mode
    ui_simulation["set_tty"](False)
    
    copy_to_clipboard_osc52(test_file)
    
    captured = capsys.readouterr()
    assert "Output redirected, skipping clipboard copy." in captured.out


def test_copy_to_clipboard_osc52_file_too_large(tmp_path, capsys, monkeypatch):
    """Test copy_to_clipboard_osc52 with file too large for clipboard."""
    test_file = tmp_path / "test.txt"
    # Create a file larger than 1.5MB
    large_content = "x" * 2_000_000
    test_file.write_text(large_content)
    
    # Only mock isatty
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    
    copy_to_clipboard_osc52(test_file)
    
    captured = capsys.readouterr()
    # Should show warning about file too large
    assert "File too large" in captured.out
    # Should not output OSC52 escape sequence
    assert "\033]52;c;" not in captured.out


def test_copy_to_clipboard_osc52_with_logger(tmp_path, capsys, monkeypatch):
    """Test copy_to_clipboard_osc52 with logger parameter."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")
    
    # Only mock isatty
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    
    mock_logger = Mock()
    copy_to_clipboard_osc52(test_file, mock_logger)
    
    captured = capsys.readouterr()
    # Should output OSC52 escape sequence
    assert "\033]52;c;" in captured.out
    mock_logger.info.assert_called_with("Dump generated and copied to LOCAL clipboard!")


def test_copy_to_clipboard_osc52_exception(tmp_path, capsys, monkeypatch):
    """Test copy_to_clipboard_osc52 when an exception occurs."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")
    
    # Mock base64.b64encode to raise an exception
    import base64
    original_b64encode = base64.b64encode
    
    def mock_b64encode(*args, **kwargs):
        raise Exception("Encoding failed")
    
    monkeypatch.setattr(base64, "b64encode", mock_b64encode)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    
    copy_to_clipboard_osc52(test_file)
    
    captured = capsys.readouterr()
    # Should show error message
    assert "Could not copy to clipboard" in captured.out
    
    # Restore original
    monkeypatch.setattr(base64, "b64encode", original_b64encode)


def test_copy_to_clipboard_osc52_file_unreadable(tmp_path, capsys, monkeypatch):
    """Test copy_to_clipboard_osc52 when file exists but is unreadable."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")
    
    # Mock the open function to raise PermissionError when reading the file
    import builtins
    original_open = builtins.open
    
    def mock_open(file, *args, **kwargs):
        if str(file) == str(test_file):
            raise PermissionError("Permission denied")
        return original_open(file, *args, **kwargs)
    
    monkeypatch.setattr(builtins, "open", mock_open)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    
    copy_to_clipboard_osc52(test_file)
    
    captured = capsys.readouterr()
    # Should show error message about file reading
    assert "Could not copy to clipboard" in captured.out


def test_estimate_tokens_with_tiktoken(monkeypatch):
    """Test estimate_tokens when tiktoken is available."""
    test_text = "Hello world! This is a test."
    
    # Create a mock tiktoken module
    mock_tiktoken = Mock()
    mock_encoder = Mock()
    mock_encoder.encode.return_value = [1, 2, 3, 4, 5]  # 5 tokens
    mock_tiktoken.get_encoding.return_value = mock_encoder
    
    # Mock sys.modules to provide our mock tiktoken
    import sys
    original_tiktoken = sys.modules.get('tiktoken')
    sys.modules['tiktoken'] = mock_tiktoken
    
    try:
        result = estimate_tokens(test_text)
        assert result == 5
        mock_tiktoken.get_encoding.assert_called_with("cl100k_base")
    finally:
        # Restore original
        if original_tiktoken is not None:
            sys.modules['tiktoken'] = original_tiktoken
        else:
            del sys.modules['tiktoken']


def test_estimate_tokens_without_tiktoken():
    """Test estimate_tokens when tiktoken is not available."""
    test_text = "Hello world! This is a test."
    
    # Use patch.dict to set tiktoken to None in sys.modules
    with patch.dict('sys.modules', {'tiktoken': None}):
        result = estimate_tokens(test_text)
        
        # Should fall back to character-based estimation
        expected = len(test_text) // 4
        assert result == expected


def test_estimate_tokens_empty_string():
    """Test estimate_tokens with empty string."""
    result = estimate_tokens("")
    
    assert result == 0


def test_estimate_tokens_tiktoken_import_error():
    """Test estimate_tokens when tiktoken import fails."""
    test_text = "Hello world!"
    
    # Use patch.dict to set tiktoken to None in sys.modules
    with patch.dict('sys.modules', {'tiktoken': None}):
        result = estimate_tokens(test_text)
        
        # Should use fallback estimation
        assert result == len(test_text) // 4


def test_run_shell_command_success():
    """Test run_shell_command with successful command."""
    returncode, output = run_shell_command("echo 'test_success'")
    
    assert returncode == 0
    assert "test_success" in output
    assert "Exit Code: 0" in output
    assert "STDOUT:" in output


def test_run_shell_command_failure():
    """Test run_shell_command with failing command."""
    returncode, output = run_shell_command("false")
    
    assert returncode != 0
    assert "Exit Code:" in output
    # 'false' command typically returns 1
    assert returncode == 1 or "Exit Code: 1" in output


def test_run_shell_command_invalid_command():
    """Test run_shell_command with invalid command."""
    returncode, output = run_shell_command("nonexistent_command_xyz123")
    
    # With shell=True, non-existent commands return exit code 127
    assert returncode == 127
    assert "Exit Code: 127" in output
    assert "nonexistent_command_xyz123" in output


def test_run_shell_command_with_stderr():
    """Test run_shell_command that produces stderr output."""
    # Use a command that writes to stderr
    returncode, output = run_shell_command("echo 'error' >&2")
    
    assert returncode == 0
    assert "STDERR:" in output
    assert "error" in output


def test_run_shell_command_with_both_stdout_stderr():
    """Test run_shell_command that produces both stdout and stderr."""
    returncode, output = run_shell_command("echo 'stdout' && echo 'stderr' >&2")
    
    assert returncode == 0
    assert "STDOUT:" in output
    assert "STDERR:" in output
    assert "stdout" in output
    assert "stderr" in output


@pytest.mark.edge_case
def test_run_shell_command_execution_failure():
    """Cover utils.py:151-153 (Exception handling for subprocess crashes)"""
    with patch("subprocess.run", side_effect=RuntimeError("Subprocess failed")):
        code, out = run_shell_command("ls")
        assert code == -1
        assert "[Execution Failed]" in out


@pytest.mark.edge_case
def test_estimate_tokens_generic_exception(caplog):
    """Cover utils.py:30 (Tiktoken generic exception fallback)"""
    from unittest.mock import MagicMock
    mock_tiktoken = MagicMock()
    mock_tiktoken.get_encoding.side_effect = AttributeError("Bug")
    
    with patch.dict('sys.modules', {'tiktoken': mock_tiktoken}):
        res = estimate_tokens("test string", logger=Mock())
        # Should fallback to len // 4
        assert res == 2


# Consolidated tests from test_coverage_final_push.py
def test_utils_tiktoken_fallback_log(caplog):
    """Cover utils.py:72 ( tiktoken debug fallback log)"""
    import logging
    from dumpcode.utils import estimate_tokens
    
    with patch.dict('sys.modules', {'tiktoken': None}):
        logger = logging.getLogger("test_logger")
        with caplog.at_level(logging.DEBUG):
            estimate_tokens("test string", logger=logger)
        assert "tiktoken failed; using character-based estimation" in caplog.text


def test_utils_git_missing_binary():
    """Cover utils.py:89 (Subprocess fails if git is not on path)"""
    from dumpcode.utils import get_git_modified_files
    from pathlib import Path
    
    with patch("subprocess.run", side_effect=FileNotFoundError):
        assert get_git_modified_files(Path(".")) == []

def test_utils_git_called_process_error():
    """Cover utils.py:89 (CalledProcessError when directory is not a git repo)"""
    from dumpcode.utils import get_git_modified_files
    from pathlib import Path
    import subprocess
    
    # Mock subprocess.run to raise CalledProcessError (simulating non-git directory)
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(128, "git", stderr="fatal: not a git repository")):
        result = get_git_modified_files(Path("/tmp/not-a-git-repo"))
        assert result == []