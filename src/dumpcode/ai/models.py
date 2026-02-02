"""Model registry and provider mapping for DumpCode."""

from typing import Dict, TypedDict

class ModelConfig(TypedDict):
    """Configuration schema for supported AI models in the catalog."""
    provider: str
    model_id: str
    context: int
    label: str
    token_param: str  # 'max_tokens' or 'max_completion_tokens'

# Full catalog of supported AI models.
# This serves as the source of truth for context window limits, technical model IDs,
# and provider mapping across the application.
MODEL_CATALOG: Dict[str, ModelConfig] = {
    # --- OpenAI ---
    "gpt-5.1": {
        "provider": "openai", "model_id": "gpt-5.1", "context": 400000, "label": "GPT-5.1",
        "token_param": "max_completion_tokens"
    },
    "gpt-5.2": {
        "provider": "openai", "model_id": "gpt-5.2", "context": 400000, "label": "GPT-5.2",
        "token_param": "max_completion_tokens"
    },
    "gpt-5-mini": {
        "provider": "openai", "model_id": "gpt-5-mini", "context": 400000, "label": "GPT-5 Mini",
        "token_param": "max_completion_tokens"
    },
    "gpt-5-nano": {
        "provider": "openai", "model_id": "gpt-5-nano", "context": 400000, "label": "GPT-5 Nano",
        "token_param": "max_completion_tokens"
    },
    "gpt-5": {
        "provider": "openai", "model_id": "gpt-5", "context": 400000, "label": "GPT-5",
        "token_param": "max_completion_tokens"
    },
    "gpt-4.1": {
        "provider": "openai", "model_id": "gpt-4.1", "context": 1000000, "label": "GPT-4.1",
        "token_param": "max_tokens"
    },
    "gpt-4o": {
        "provider": "openai", "model_id": "gpt-4o", "context": 128000, "label": "GPT-4o",
        "token_param": "max_tokens"
    },

    # --- Google ---
    # Google uses its own SDK methods, so this param is informative/unused for now but good for consistency
    "gemini-3-pro-preview": {
        "provider": "google", "model_id": "gemini-3-pro-preview", "context": 1048576, "label": "Gemini 3 Pro",
        "token_param": "max_output_tokens" 
    },
    "gemini-2.5-pro": {
        "provider": "google", "model_id": "gemini-2.5-pro", "context": 1048576, "label": "Gemini 2.5 Pro",
        "token_param": "max_output_tokens"
    },
    "gemini-2.5-flash": {
        "provider": "google", "model_id": "gemini-2.5-flash", "context": 1048576, "label": "Gemini 2.5 Flash",
        "token_param": "max_output_tokens"
    },
    "gemini-2.5-flash-lite": {
        "provider": "google", "model_id": "gemini-2.5-flash-lite", "context": 1048576, "label": "Gemini 2.5 Flash-Lite",
        "token_param": "max_output_tokens"
    },
    "gemini-3-flash-preview": {
        "provider": "google", "model_id": "gemini-3-flash-preview", "context": 200000, "label": "Gemini 3 Flash Preview",
        "token_param": "max_output_tokens"
    },

    # --- Anthropic ---
    "claude-sonnet-4.5": {
        "provider": "anthropic", "model_id": "claude-sonnet-4-5-20250929", "context": 200000, "label": "Claude 4.5 Sonnet",
        "token_param": "max_tokens"
    },
    "claude-opus-4.5": {
        "provider": "anthropic", "model_id": "claude-opus-4-5-20251101", "context": 200000, "label": "Claude 4.5 Opus",
        "token_param": "max_tokens"
    },
    "claude-haiku-4.5": {
        "provider": "anthropic", "model_id": "claude-haiku-4-5-20251001", "context": 200000, "label": "Claude 4.5 Haiku",
        "token_param": "max_tokens"
    },

    # --- DeepSeek ---
    "deepseek-v3.2-chat": {
        "provider": "deepseek", "model_id": "deepseek-chat", "context": 128000, "label": "DeepSeek V3.2",
        "token_param": "max_tokens"
    },
    "deepseek-chat": {
        "provider": "deepseek", "model_id": "deepseek-chat", "context": 128000, "label": "DeepSeek Chat",
        "token_param": "max_tokens"
    },
}