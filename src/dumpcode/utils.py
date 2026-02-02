"""Utility functions for DumpCode."""

import base64
import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


def estimate_tokens(text: str, logger: Optional[logging.Logger] = None) -> int:
    """Estimate the number of tokens in a text string.

    Attempt to use tiktoken for cl100k_base encoding, falling back to 
    a character-based estimate if unavailable.

    Args:
        text: String to analyze.
        logger: Optional logger for reporting fallback usage.

    Returns:
        Estimated token count.
    """
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception: # Catch ALL errors here to ensure fallback
        if logger:
            logger.debug("tiktoken failed; using character-based estimation")
        return len(text) // 4


def get_git_modified_files(root_path: Path) -> List[Path]:
    """Get files modified or untracked in git.

    Args:
        root_path: Root of the git repository.

    Returns:
        List of Path objects representing modified/untracked files.
    """
    try:
        cmd = ["git", "ls-files", "-m", "-o", "--exclude-standard"]
        result = subprocess.run(
            cmd, cwd=root_path, capture_output=True, text=True, check=True
        )
        return [root_path / line for line in result.stdout.splitlines() if line.strip()]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def copy_to_clipboard_osc52(filepath: Path, logger: Optional[logging.Logger] = None) -> None:
    """Copy file content to clipboard via OSC 52 escape sequences if TTY is present.
    
    Args:
        filepath: Path to the file whose content should be copied.
        logger: Optional logger instance.
    """
    if not sys.stdout.isatty():
        if logger:
            logger.info("Output redirected, skipping clipboard copy.")
        else:
            print("Output redirected, skipping clipboard copy.")
        return

    try:
        size = filepath.stat().st_size
        if size > 1_500_000:
            if logger:
                logger.warning(f"File too large ({size // 1024} KB) for auto-copy.")
            else:
                print(f"⚠️  File too large ({size // 1024} KB) for auto-copy.")
            return

        with open(filepath, "rb") as f:
            content = f.read()

        encoded = base64.b64encode(content).decode("utf-8")
        sys.stdout.write(f"\033]52;c;{encoded}\a")
        sys.stdout.flush()
        if logger:
            logger.info("Dump generated and copied to LOCAL clipboard!")
        else:
            print("✅ Dump generated and copied to LOCAL clipboard!")
    except Exception as e:
        if logger:
            logger.warning(f"Could not copy to clipboard: {e}")
        else:
            print(f"⚠️  Could not copy to clipboard: {e}")


def setup_logger(name: str, verbose: bool = False) -> logging.Logger:
    """Set up and return a configured logger instance.
    
    Args:
        name: Logger name.
        verbose: If True, sets log level to DEBUG.

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    
    if not logger.handlers:
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    return logger


@dataclass
class CommandResult:
    """Container for the results of an external shell command execution.

    Attributes:
        success: Whether the subprocess ran without crashing.
        exit_code: The return code from the shell.
        output: Formatted string containing stdout and stderr.
        error: Optional string containing the exception message if execution failed.
    """
    success: bool
    exit_code: int
    output: str
    error: Optional[str] = None
    
    @classmethod
    def from_success(cls, exit_code: int, stdout: str, stderr: str) -> 'CommandResult':
        """Create a CommandResult from successful execution."""
        output_lines = [
            f"Exit Code: {exit_code}",
        ]
        
        if stdout:
            output_lines.extend(["STDOUT:", stdout.strip()])
        
        if stderr:
            output_lines.extend(["STDERR:", stderr.strip()])
            
        output = "\n".join(output_lines)
        return cls(success=True, exit_code=exit_code, output=output)
    
    @classmethod
    def from_failure(cls, error: str) -> 'CommandResult':
        """Create a CommandResult from failed execution."""
        return cls(success=False, exit_code=-1, output="", error=error)
    
    def formatted_output(self, command: str) -> str:
        """Get the formatted output block with command header."""
        if self.success:
            return f"--- COMMAND: {command} ---\n{self.output}\n--------------------------"
        else:
            return f"--- COMMAND: {command} ---\n[Execution Failed]: {self.error}\n--------------------------"


def run_shell_command(command: str) -> Tuple[int, str]:
    """Execute a shell command and return exit code and formatted output.
    
    Args:
        command: The shell command to run.
        
    Returns:
        Tuple[int, str]: (Exit Code, Formatted Output Block)
        Note: Returns -1 as exit code if execution crashes (e.g. binary not found).
    """
    try:
        # shell=True allows using flags and pipes easily in the config
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        
        cmd_result = CommandResult.from_success(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr
        )
        
        return result.returncode, cmd_result.formatted_output(command)
        
    except Exception as e:
        cmd_result = CommandResult.from_failure(str(e))
        return cmd_result.exit_code, cmd_result.formatted_output(command)
