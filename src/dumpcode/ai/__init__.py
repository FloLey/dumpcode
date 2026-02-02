"""AI integration module for DumpCode."""

from .base import AIClient, AIResponse
from .client import (
    get_client_for_model,
    send_to_ai,
    load_env_file,
    check_token_limits,
)
from .orchestrator import AIOrchestrator

# Import providers to trigger their .register() calls
from . import claude, gemini, openai_client, deepseek

__all__ = [
    "AIClient",
    "AIResponse",
    "get_client_for_model",
    "send_to_ai",
    "load_env_file",
    "check_token_limits",
    "AIOrchestrator",
    "claude",
    "gemini",
    "openai_client",
    "deepseek",
]