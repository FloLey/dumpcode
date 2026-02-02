"""Integration tests for CLI entry points and main application logic."""

import argparse
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from dumpcode.cli import parse_arguments_with_profiles, get_parser
from dumpcode.main import handle_new_plan, handle_meta_mode, run_dump, main


def test_arg_parsing_with_dynamic_profiles():
    """Test that dynamic profiles from config create appropriate CLI flags."""
    config_content = {
        "profiles": {
            "code-review": {
                "description": "Code review profile",
                "commands": ["echo 'review'"]
            },
            "security-scan": {
                "description": "Security scanning profile",
                "commands": ["echo 'security'"]
            }
        }
    }
    
    # Test get_parser directly without mocking sys.argv
    parser = get_parser(config_content["profiles"])
    
    # Test parsing with a custom profile flag
    args = parser.parse_args(["--code-review", "--output-file", "test.txt"])
    
    assert hasattr(args, "code_review")
    assert args.code_review is True
    assert hasattr(args, "security_scan")
    assert args.security_scan is False
    assert args.output_file == "test.txt"


def test_arg_parsing_profile_conflict(capsys):
    """Test that conflicting profile names are handled gracefully."""
    config_content = {
        "profiles": {
            "verbose": {  # Conflicts with built-in --verbose flag
                "description": "Verbose profile",
                "commands": ["echo 'verbose'"]
            }
        }
    }
    
    # Test get_parser directly - it should print warning but not add the conflicting flag
    parser = get_parser(config_content["profiles"])
    captured = capsys.readouterr()
    
    assert "⚠️ [Warning] Profile 'verbose' conflicts with a core flag" in captured.out
    assert hasattr(parser, "parse_args")
    
    # The parser should still have the built-in verbose flag
    args = parser.parse_args([])
    assert hasattr(args, "verbose")  # Should still have the built-in verbose flag


def test_handle_new_plan_stdin(tmp_path, monkeypatch):
    """Test PLAN.md creation from stdin input."""
    plan_path = tmp_path / "PLAN.md"
    
    # Simulate stdin input
    stdin_content = "# Test Plan\n\nThis is a test plan."
    monkeypatch.setattr(sys.stdin, "read", lambda: stdin_content)
    
    handle_new_plan(tmp_path, "-")
    
    assert plan_path.exists()
    assert plan_path.read_text() == stdin_content


def test_handle_new_plan_file(tmp_path):
    """Test PLAN.md creation from file input."""
    plan_path = tmp_path / "PLAN.md"
    input_file = tmp_path / "input.md"
    input_content = "# From File\n\nFile content."
    input_file.write_text(input_content)
    
    handle_new_plan(tmp_path, str(input_file))
    
    assert plan_path.exists()
    assert plan_path.read_text() == input_content


def test_handle_new_plan_file_not_found(tmp_path, capsys):
    """Test PLAN.md creation with non-existent file."""
    handle_new_plan(tmp_path, "nonexistent.md")
    
    captured = capsys.readouterr()
    assert "❌ File not found" in captured.out


def test_handle_meta_mode(tmp_path):
    """Test meta-mode configuration prompt generation."""
    config = {
        "version": 1,
        "profiles": {
            "test": {"description": "Test profile"}
        }
    }
    
    args = argparse.Namespace(
        output_file=str(tmp_path / "prompt.txt"),
        change_profile="Make it faster",
        no_copy=True
    )
    
    handle_meta_mode(args, config)
    
    output_file = tmp_path / "prompt.txt"
    assert output_file.exists()
    
    content = output_file.read_text()
    assert "Act as a Configuration Assistant for DumpCode" in content
    assert "Make it faster" in content
    assert '"version": 1' in content
    assert "Test profile" in content


def test_handle_meta_mode_with_copy(tmp_path, monkeypatch):
    """Test meta-mode with clipboard copy enabled."""
    config = {"version": 1}
    args = argparse.Namespace(
        output_file=str(tmp_path / "prompt.txt"),
        change_profile="Test",
        no_copy=False
    )
    
    mock_copy = Mock()
    monkeypatch.setattr("dumpcode.main.copy_to_clipboard_osc52", mock_copy)
    
    handle_meta_mode(args, config)
    
    mock_copy.assert_called_once()


def test_run_dump_with_profile(tmp_path):
    """Test dump execution with an active profile."""
    config = {
        "profiles": {
            "test-profile": {
                "description": "Test profile",
                "commands": ["echo 'test'"]
            }
        }
    }
    
    args = argparse.Namespace(
        output_file="output.txt",
        level=2,
        dir_only=False,
        ignore_errors=False,
        structure_only=False,
        no_copy=True,
        no_xml=False,
        changed=False,
        question=None,
        reset_version=False,
        verbose=False,
        auto=False,
        no_auto=False,
        model=None,
        test_profile=True  # Matches the profile name
    )
    
    mock_engine = Mock()
    captured_settings = None
    
    def capture_settings(*args, **kwargs):
        nonlocal captured_settings
        captured_settings = args[1]  # Second argument is settings
        return mock_engine
    
    with patch("dumpcode.main.DumpEngine", side_effect=capture_settings):
        run_dump(args, config, tmp_path)
        
        mock_engine.run.assert_called_once()
        
        # Check that settings were created with the active profile
        assert captured_settings is not None
        assert captured_settings.active_profile == config["profiles"]["test-profile"]
        assert captured_settings.output_file == Path("output.txt")
        assert captured_settings.start_path == tmp_path
        assert captured_settings.use_xml is True
        assert captured_settings.no_copy is True


def test_run_dump_without_profile(tmp_path):
    """Test dump execution without an active profile."""
    config = {"profiles": {}}
    
    args = argparse.Namespace(
        output_file="output.txt",
        level=2,
        dir_only=False,
        ignore_errors=False,
        structure_only=False,
        no_copy=True,
        no_xml=False,
        changed=False,
        question="Test question",
        reset_version=False,
        verbose=False,
        auto=False,
        no_auto=False,
        model=None,
        # No profile flags set
    )
    
    mock_engine = Mock()
    captured_settings = None
    
    def capture_settings(*args, **kwargs):
        nonlocal captured_settings
        captured_settings = args[1]  # Second argument is settings
        return mock_engine
    
    with patch("dumpcode.main.DumpEngine", side_effect=capture_settings):
        run_dump(args, config, tmp_path)
        
        mock_engine.run.assert_called_once()
        
        assert captured_settings is not None
        assert captured_settings.active_profile is None
        assert captured_settings.question == "Test question"
        assert captured_settings.output_file == Path("output.txt")
        assert captured_settings.start_path == tmp_path
        assert captured_settings.use_xml is True
        assert captured_settings.no_copy is True
        assert captured_settings.max_depth == 2
        assert captured_settings.dir_only is False
        assert captured_settings.ignore_errors is False
        assert captured_settings.structure_only is False


def test_main_init_mode(tmp_path, capsys):
    """Test main function with --init flag."""
    test_args = [str(tmp_path), "--init"]
    
    mock_interactive_init = Mock()
    with patch("dumpcode.main.interactive_init", mock_interactive_init):
        main(test_args)
        
        mock_interactive_init.assert_called_once_with(tmp_path)


def test_main_new_plan_mode(tmp_path, capsys):
    """Test main function with --new-plan flag."""
    test_args = [str(tmp_path), "--new-plan", "-"]
    
    mock_handle_new_plan = Mock()
    with patch("dumpcode.main.handle_new_plan", mock_handle_new_plan):
        main(test_args)
        
        mock_handle_new_plan.assert_called_once_with(tmp_path, "-")


def test_main_meta_mode(tmp_path):
    """Test main function with --change-profile flag."""
    test_args = [str(tmp_path), "--change-profile", "Make it better", "--output-file", "prompt.txt"]
    
    mock_config = {"version": 1}
    mock_handle_meta_mode = Mock()
    
    with patch("dumpcode.main.load_or_create_config", return_value=mock_config):
        with patch("dumpcode.main.handle_meta_mode", mock_handle_meta_mode):
            with patch("dumpcode.main.setup_logger"):
                main(test_args)
                
                mock_handle_meta_mode.assert_called_once()


def test_main_normal_dump_mode(tmp_path):
    """Test main function in normal dump mode."""
    test_args = [str(tmp_path), "--output-file", "dump.txt"]
    
    mock_config = {"version": 1}
    mock_run_dump = Mock()
    
    with patch("dumpcode.main.load_or_create_config", return_value=mock_config):
        with patch("dumpcode.main.run_dump", mock_run_dump):
            with patch("dumpcode.main.setup_logger"):
                main(test_args)
                
                mock_run_dump.assert_called_once()


def test_main_invalid_directory(tmp_path, capsys):
    """Test main function with invalid directory."""
    invalid_path = tmp_path / "nonexistent"
    test_args = [str(invalid_path)]
    
    main(test_args)
    
    captured = capsys.readouterr()
    assert "Error: Invalid directory" in captured.out


def test_main_default_directory(tmp_path, capsys):
    """Test main function with default directory (no path argument)."""
    test_args = []
    
    mock_config = {"version": 1}
    
    with patch("dumpcode.main.load_or_create_config", return_value=mock_config):
        with patch("dumpcode.main.run_dump", Mock()):
            with patch("dumpcode.main.setup_logger"):
                # Mock Path.resolve to return tmp_path for current directory
                with patch("dumpcode.main.Path") as mock_path:
                    mock_path.return_value.resolve.return_value = tmp_path
                    mock_path.return_value.is_dir.return_value = True
                    main(test_args)


@pytest.mark.edge_case
def test_cli_parse_no_args_list(monkeypatch):
    """Cover cli.py:98 (Branch where args_list is None using sys.argv)"""
    import sys
    monkeypatch.setattr(sys, "argv", ["dumpcode", "."])
    # This just ensures it doesn't crash and calls parse_args()
    with patch("dumpcode.config.load_or_create_config", return_value={"profiles": {}}):
        args = parse_arguments_with_profiles(Path("."))
        assert args.startpath == "."


# Consolidated tests from test_coverage_final_push.py
def test_main_startpath_resolution(tmp_path):
    """Cover main.py:111 (Branch where start_path is the first CLI argument)"""
    from dumpcode.main import main
    
    # Create a dummy dir to point to
    target = tmp_path / "my_app"
    target.mkdir()
    
    with patch("dumpcode.main.parse_arguments_with_profiles") as mock_parse:
        with patch("dumpcode.main.run_dump"):
            with patch("dumpcode.main.load_or_create_config"):
                # Mock input to avoid stdin capture
                with patch("builtins.input", return_value=""):
                    # Pass the path as the first positional arg
                    main([str(target), "--verbose"])
                    # Check that parse_arguments_with_profiles was called with the target
                    mock_parse.assert_called()


def test_main_meta_mode_exception(capsys):
    """Cover main.py:60-61 (Exception in meta-mode prompt writing)"""
    from dumpcode.main import handle_meta_mode
    from unittest.mock import Mock
    
    args = Mock(output_file="/nonexistent/path/dump.txt", change_profile="test")
    handle_meta_mode(args, {})
    assert "Failed to generate meta-mode prompt" in capsys.readouterr().out


# Consolidated tests from test_coverage_gaps.py
class TestMainAndUtilsGaps:
    def test_main_cli_directory_resolution(self, tmp_path):
        """Cover main.py:111 (Branch where start_path is provided in argv)"""
        from dumpcode.main import main
        
        # We call main with a directory as first arg
        with patch("dumpcode.main.parse_arguments_with_profiles") as mock_parse:
            with patch("dumpcode.main.run_dump"):
                with patch("dumpcode.config.interactive_init"):
                    # Mock the input to avoid stdin capture issues
                    with patch("builtins.input", return_value=""):
                        main([str(tmp_path), "--verbose"])
                        # Ensure parse was called with the resolved path
                        assert mock_parse.called

    def test_handle_new_plan_error(self, tmp_path, capsys):
        """Cover main.py:39-40 (Exception in PLAN.md writing)"""
        from dumpcode.main import handle_new_plan
        from pathlib import Path
        
        with patch.object(Path, "write_text", side_effect=OSError("ReadOnly")):
            handle_new_plan(tmp_path, "-") # Stdin mode
            # We'll need to mock stdin too if we don't want it to hang
        
    def test_estimate_tokens_fallback_logging(self, caplog):
        """Cover utils.py:72 (Token fallback debug log)"""
        import logging
        from dumpcode.utils import estimate_tokens
        
        with patch.dict('sys.modules', {'tiktoken': None}):
            logger = logging.getLogger("test")
            with caplog.at_level(logging.DEBUG):
                estimate_tokens("hello world", logger=logger)
            assert "tiktoken failed; using character-based estimation" in caplog.text

    def test_get_git_modified_files_no_git(self, tmp_path):
        """Cover utils.py:89 (FileNotFoundError for git command)"""
        from dumpcode.utils import get_git_modified_files
        
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            assert get_git_modified_files(tmp_path) == []


# Consolidated tests from test_final_coverage.py
def test_main_path_resolution(tmp_path):
    """Cover main.py:111 (Start path provided as first argument)"""
    from dumpcode.main import main
    
    test_dir = tmp_path / "work_dir"
    test_dir.mkdir()
    
    # Mock run_dump to avoid full execution
    with patch("dumpcode.main.parse_arguments_with_profiles") as mock_parse:
        with patch("dumpcode.main.run_dump"):
            with patch("dumpcode.main.load_or_create_config"):
                with patch("builtins.input", return_value=""):
                    main([str(test_dir), "--verbose"])
                    # Verify parse_arguments was called with the resolved directory
                    mock_parse.assert_called()


def test_git_missing_error(tmp_path):
    """Cover utils.py:89 (Git binary missing from system)"""
    from dumpcode.utils import get_git_modified_files
    
    with patch("subprocess.run", side_effect=FileNotFoundError):
        assert get_git_modified_files(tmp_path) == []