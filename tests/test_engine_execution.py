"""Refactored tests for command execution and output writing functionality."""

import io
import pytest

from dumpcode.engine import DumpEngine
from dumpcode.writer import DumpWriter


def test_writer_write_command_output():
    """Test DumpWriter.write_command_output with XML escaping."""
    stream = io.StringIO()
    writer = DumpWriter(stream, use_xml=True)
    
    test_output = 'Test & output <with> "special" chars'
    writer.write_command_output(test_output)
    
    result = stream.getvalue()
    assert "<execution>" in result
    assert "</execution>" in result
    # Quotes don't need to be escaped in XML content, only in attributes
    assert "Test &amp; output &lt;with&gt; \"special\" chars" in result


def test_writer_write_command_output_empty():
    """Test DumpWriter.write_command_output with empty output."""
    stream = io.StringIO()
    writer = DumpWriter(stream, use_xml=True)
    
    writer.write_command_output("")
    
    result = stream.getvalue()
    assert result == ""  # Should not write anything for empty output


def test_writer_write_command_output_no_xml():
    """Test DumpWriter.write_command_output when XML is disabled."""
    stream = io.StringIO()
    writer = DumpWriter(stream, use_xml=False)
    
    test_output = "Test output"
    writer.write_command_output(test_output)
    
    result = stream.getvalue()
    # With use_xml=False, write_command_output uses plain text headers
    assert "--- COMMAND EXECUTION OUTPUT ---" in result
    assert "Test output" in result
    assert "<execution>" not in result


def test_writer_write_command_output_newlines():
    """Test DumpWriter.write_command_output preserves newlines."""
    stream = io.StringIO()
    writer = DumpWriter(stream, use_xml=True)
    
    test_output = "Line 1\nLine 2\nLine 3"
    writer.write_command_output(test_output)
    
    result = stream.getvalue()
    assert "Line 1\nLine 2\nLine 3" in result
    assert "<execution>" in result
    assert "</execution>" in result


def test_engine_run_commands_success(project_env, default_settings):
    """Test engine running commands successfully from a profile."""
    config = {
        "version": 1,
        "profiles": {
            "test-profile": {
                "description": "Test profile",
                "run_commands": ["echo 'test output'"]
            }
        }
    }
    
    # Update settings to use the test profile
    default_settings.active_profile = config["profiles"]["test-profile"]
    
    # Create mock cmd_runner that returns success
    def mock_cmd_runner(cmd):
        return (0, f"--- COMMAND: {cmd} ---\nSTDOUT:\ntest output\n--------------------------")
    
    # Create engine with mock cmd_runner
    engine = DumpEngine(config, default_settings, cmd_runner=mock_cmd_runner)
    engine.run()
    
    # Read the output file
    output_text = default_settings.output_file.read_text()
    
    # Check that command output appears in the file
    assert "<execution>" in output_text
    assert "test output" in output_text


def test_engine_run_commands_failure(project_env, default_settings):
    """Test engine handling command failures with appropriate logging."""
    config = {
        "version": 1,
        "profiles": {
            "test-profile": {
                "description": "Test profile",
                "run_commands": ["false"]  # Command that will fail
            }
        }
    }
    
    default_settings.active_profile = config["profiles"]["test-profile"]
    
    # Create mock cmd_runner that returns failure
    def mock_cmd_runner(cmd):
        return (1, f"--- COMMAND: {cmd} ---\nSTDOUT:\n\nSTDERR:\nCommand failed\n--------------------------")
    
    engine = DumpEngine(config, default_settings, cmd_runner=mock_cmd_runner)
    engine.run()
    
    output_text = default_settings.output_file.read_text()
    
    # Command output should still appear in the file even if it failed
    assert "<execution>" in output_text
    # The mock command output should appear
    assert "Command failed" in output_text


def test_engine_run_commands_multiple(project_env, default_settings):
    """Test engine running multiple commands from a profile."""
    config = {
        "version": 1,
        "profiles": {
            "test-profile": {
                "description": "Test profile",
                "run_commands": [
                    "echo 'first command'",
                    "echo 'second command'"
                ]
            }
        }
    }
    
    default_settings.active_profile = config["profiles"]["test-profile"]
    
    # Track command calls
    command_calls = []
    
    def mock_cmd_runner(cmd):
        command_calls.append(cmd)
        # Extract the quoted part of the echo command
        content = cmd.split("'")[1] if "'" in cmd else cmd.split('"')[1]
        return (0, f"--- COMMAND: {cmd} ---\nSTDOUT:\n{content}\n--------------------------")
    
    engine = DumpEngine(config, default_settings, cmd_runner=mock_cmd_runner)
    engine.run()
    
    output_text = default_settings.output_file.read_text()
    
    # Check that both command outputs appear
    assert output_text.count("<execution>") == 2
    assert "first command" in output_text
    assert "second command" in output_text
    # Verify both commands were called
    assert len(command_calls) == 2
    assert "echo 'first command'" in command_calls
    assert "echo 'second command'" in command_calls


def test_engine_run_commands_no_profile(project_env, default_settings):
    """Test engine when no active profile is set."""
    config = {"version": 1}
    
    # Ensure no active profile
    default_settings.active_profile = None
    
    engine = DumpEngine(config, default_settings)
    engine.run()
    
    output_text = default_settings.output_file.read_text()
    
    # Should not have execution tags when no profile with commands
    assert "<execution>" not in output_text


def test_engine_run_commands_empty_command_list(project_env, default_settings):
    """Test engine with profile that has empty command list."""
    config = {
        "version": 1,
        "profiles": {
            "test-profile": {
                "description": "Test profile",
                "run_commands": []  # Empty list
            }
        }
    }
    
    default_settings.active_profile = config["profiles"]["test-profile"]
    
    engine = DumpEngine(config, default_settings)
    engine.run()
    
    output_text = default_settings.output_file.read_text()
    
    # Should not have execution tags when command list is empty
    assert "<execution>" not in output_text


@pytest.mark.edge_case
def test_writer_write_prompt_empty():
    """Cover writer.py:38 (Early return if no prompt is provided)"""
    from io import StringIO
    from dumpcode.writer import DumpWriter
    
    buf = StringIO()
    writer = DumpWriter(buf)
    writer.write_prompt("", tag="instructions")
    assert buf.getvalue() == ""