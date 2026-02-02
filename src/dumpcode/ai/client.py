"""AI client factory and orchestration."""

import os
from pathlib import Path
from typing import Generator, Optional, Tuple, Type, cast
import logging

from .base import AIClient, AIResponse, StreamChunk
from .models import MODEL_CATALOG
from ..utils import estimate_tokens


# Provider to environment variable mapping
ENV_VAR_MAP = {
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}


def load_env_file(start_path: Path) -> None:
    """Load .env file from project directory if it exists.
    
    Attempts to use python-dotenv if available, otherwise falls back to a 
    simple manual parser to avoid requiring external dependencies for basic usage.
    """
    env_file = start_path / ".env"
    if not env_file.exists():
        return
    
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
    except ImportError:
        try:
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key, value)
        except OSError as e:
            logging.getLogger(__name__).debug(f"Manual .env parsing skipped: {e}")


def get_client_for_model(model_alias: str, logger: Optional[logging.Logger] = None) -> AIClient:
    """Get the appropriate AI client for a model string based on registry and catalog."""
    logger = logger or logging.getLogger(__name__)
    
    model_config = MODEL_CATALOG.get(model_alias.lower())
    client_cls = None
    
    if model_config:
        provider = model_config["provider"]
        client_cls = AIClient.registry.get(provider)
    else:
        # Fallback for unknown models (scan via .supports_model)
        client_cls = next((c for c in AIClient.registry.values() if c.supports_model(model_alias)), None)
    
    if client_cls is None:
        raise ValueError(f"Unknown model or provider for: '{model_alias}'")

    provider_name = client_cls.get_provider_name()
    env_var = ENV_VAR_MAP.get(provider_name)
    if not env_var:
        raise ValueError(f"No environment variable configured for provider: {provider_name}")

    api_key = os.environ.get(env_var)
    if not api_key:
        raise ValueError(f"Missing API Key {env_var} for provider {provider_name}")

    return cast(Type[AIClient], client_cls)(api_key, logger)


def check_token_limits(estimated_tokens: int, model_alias: str, logger: logging.Logger) -> Tuple[bool, Optional[str]]:
    """Check if token count exceeds model-specific physical limits."""
    
    # 1. Lookup the model in the catalog
    model_info = MODEL_CATALOG.get(model_alias.lower())
    
    # 2. Fallback for unknown models (unsupported/raw IDs)
    # Use 128k as a safe baseline for unknown models
    max_window = model_info["context"] if model_info else 128_000
    
    # 3. Calculate Response Headroom
    RESERVED_FOR_OUTPUT = 16_384
    effective_limit = max_window - RESERVED_FOR_OUTPUT
    
    # 4. Critical Refusal
    if estimated_tokens > effective_limit:
        return False, (
            f"❌ Prompt is too large for {model_alias}.\n"
            f"Size: {estimated_tokens:,} tokens. "
            f"Limit: {effective_limit:,} (Context: {max_window:,} minus 16k for output).\n"
            f"Try using --changed to reduce file count."
        )
    
    # 5. Proactive Warning (at 80% usage)
    if estimated_tokens > (max_window * 0.8):
        logger.warning(
            f"⚠️  High context usage for {model_alias}: "
            f"{estimated_tokens:,} / {max_window:,} tokens. "
            f"Performance may degrade or the response may be cut short."
        )
        
    return True, None


def send_to_ai(
    prompt: str,
    model: str,
    output_path: Path,
    logger: logging.Logger
) -> Generator[StreamChunk, None, None]:
    """Send prompt to AI, stream response, and save record to disk."""
    estimated_tokens = estimate_tokens(prompt, logger)
    
    should_proceed, error_msg = check_token_limits(estimated_tokens, model, logger)
    if not should_proceed:
        yield StreamChunk(response=AIResponse(content="", model=model, error=error_msg))
        return
    
    logger.info(f"🤖 Sending to {model} (~{estimated_tokens:,} tokens)...")
    
    try:
        client = get_client_for_model(model, logger)
    except (ValueError, ImportError) as e:
        yield StreamChunk(response=AIResponse(content="", model=model, error=str(e)))
        return
    
    full_content = ""
    response = None
    
    config = MODEL_CATALOG.get(model.lower())
    technical_id = config["model_id"] if config else model
    
    try:
        for chunk in client.stream(prompt, technical_id):
            yield chunk
            if chunk.text:
                full_content += chunk.text
            if chunk.response:
                response = chunk.response
                
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        response = AIResponse(content=full_content, model=model, error=str(e))
        yield StreamChunk(response=response)
        return
    
    if response is None:
        response = AIResponse(content=full_content, model=model)
        yield StreamChunk(response=response)
    
    # Persistent record of AI interaction
    ai_response_path = output_path / "ai_response.md"
    try:
        with open(ai_response_path, "w", encoding="utf-8") as f:
            f.write(f"<!-- Model: {model} -->\n")
            if response.input_tokens:
                f.write(f"<!-- Input tokens: {response.input_tokens:,} -->\n")
            if response.output_tokens:
                f.write(f"<!-- Output tokens: {response.output_tokens:,} -->\n")
            f.write("\n")
            f.write(response.content)
        
        logger.info(f"💾 Response saved to {ai_response_path}")
    except Exception as e:
        logger.warning(f"Could not save AI response: {e}")