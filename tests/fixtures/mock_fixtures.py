"""Mock fixtures for DumpCode tests."""

import sys
from unittest.mock import Mock

import pytest


@pytest.fixture
def ui_simulation(monkeypatch):
    """Fixture to handle TTY and Clipboard simulations for UI tests."""
    
    # Create mock stdout with TTY simulation
    mock_stdout = Mock()
    mock_stdout.isatty.return_value = True
    mock_stdout.write = Mock()
    mock_stdout.flush = Mock()
    
    # Apply monkeypatches - only mock stdout, not clipboard function
    monkeypatch.setattr(sys, "stdout", mock_stdout)
    
    def set_tty(is_tty):
        mock_stdout.isatty.return_value = is_tty
    
    return {
        "stdout": mock_stdout,
        "set_tty": set_tty
    }