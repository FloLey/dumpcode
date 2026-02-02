"""AI Orchestrator - Handles the lifecycle of sending a dump to an AI and showing the response."""

import logging
import sys
from pathlib import Path
from typing import Optional, Any, Callable

from .client import send_to_ai
from .base import AIResponse


class AIOrchestrator:
    """Handles the lifecycle of sending a dump to an AI and showing the response."""
    
    def __init__(self, settings: Any, logger: logging.Logger) -> None:
        """Initialize the AI Orchestrator.

        Args:
            settings: DumpSettings instance containing configuration and overrides.
            logger: Logger instance for status reporting.
        """
        self.settings = settings
        self.logger = logger

    def run_ai_interaction(
        self, 
        dump_file_path: Path, 
        token_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[AIResponse]:
        """Reads the dump, sends it to AI, and streams the response.
        
        Args:
            dump_file_path: Path to the generated codebase dump file.
            token_callback: Optional callback function to handle token output.
                           If not provided, defaults to sys.stdout.write.
            
        Returns:
            The final AIResponse object or None if the process failed.
        """
        # 1. Determine which model to use (from override or profile)
        model = self.settings.model_override
        if not model and self.settings.active_profile:
            model = self.settings.active_profile.get("model")

        if not model:
            self.logger.error("Auto-mode enabled but no model found in profile.")
            return None

        # 2. Read the prompt from the file we just wrote
        try:
            prompt = dump_file_path.read_text(encoding="utf-8")
        except Exception as e:
            self.logger.error(f"Could not read dump file: {e}")
            return None

        # 3. Stream to terminal
        print(f"\n📡 Receiving AI Response from {model}...")
        
        # Use the provided callback, or fallback to sys.stdout.write
        output_func = token_callback or (lambda x: sys.stdout.write(x))
        
        generator = send_to_ai(
            prompt=prompt,
            model=model,
            output_path=self.settings.start_path,
            logger=self.logger
        )
        
        response = None
        
        try:
            for chunk in generator:
                if chunk.text:
                    output_func(chunk.text)
                    if not token_callback:  # Only flush if we are handling stdout
                        sys.stdout.flush()
                if chunk.response:
                    response = chunk.response
        except Exception as e:
            self.logger.error(f"Streaming failed: {e}")
            response = AIResponse(content="", model=model, error=str(e))
        finally:
            # Always add a newline after streaming completes, even on error
            if not token_callback:
                sys.stdout.write("\n")
                sys.stdout.flush()
        
        # Log token usage if available
        if response:
            if response.input_tokens or response.output_tokens:
                self.logger.info(
                    f"Token usage - Input: {response.input_tokens or 'N/A':,}, "
                    f"Output: {response.output_tokens or 'N/A':,}"
                )
        
            if response.error:
                self.logger.error(f"AI request failed: {response.error}")
                self.logger.info("Falling back to copying the original prompt.")
        
        return response