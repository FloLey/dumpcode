"""Diagnostic tools for AI connectivity."""

import os
import time
import logging
import warnings
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Mapping

from .client import get_client_for_model, ENV_VAR_MAP
from .models import MODEL_CATALOG

def _silence_noisy_libraries() -> None:
    """Silence SDKs and underlying network libraries thread-safely by setting levels to CRITICAL."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    noisy_loggers = ["openai", "anthropic", "google.generativeai", "httpx", "httpcore", "urllib3"]
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)

def _ping_model(alias: str, config: Mapping[str, Any]) -> Dict[str, Any]:
    """Test connectivity for a specific model alias.
    
    Args:
        alias: The CLI model alias.
        config: The model configuration mapping.
        
    Returns:
        A dictionary containing the ping result status and timing.
    """
    provider = config["provider"]
    technical_id = config["model_id"]
    
    result = {
        "alias": alias,
        "provider": provider,
        "status": "UNKNOWN",
        "details": "",
        "time": 0.0
    }

    start_t = time.time()
    try:
        client = get_client_for_model(alias)
        client.ping(technical_id)
        result["status"] = "✅ ONLINE"
        result["details"] = "Available"

    except Exception as e:
        error_msg = str(e).replace("\n", " ").strip()
        lower_msg = error_msg.lower()

        # IMPROVED HEURISTIC: If max_tokens was reached, the model IS online
        if "max_tokens" in lower_msg or "output limit" in lower_msg:
            result["status"] = "✅ ONLINE"
            result["details"] = "Available (Limit Reached)"
        elif any(x in lower_msg for x in ("not found", "404", "does not exist", "400")):
            result["status"] = "⛔ MISSING"
            result["details"] = "Model ID not found"
        elif any(x in lower_msg for x in ("authentication", "invalid api key", "401")):
            result["status"] = "🔒 AUTH ERR"
            result["details"] = "Invalid API Key"
        elif "timeout" in lower_msg:
            result["status"] = "⏱️ TIMEOUT"
            result["details"] = "Late response"
        else:
            result["status"] = "❌ ERROR"
            result["details"] = error_msg

    result["time"] = time.time() - start_t
    return result

def run_diagnostics() -> None:
    """Run parallel connectivity tests with live UI updates."""
    _silence_noisy_libraries()
    print("\n🚀 Starting Full Model Catalog Scan...\n")
    
    active_providers = []
    for provider, env_var in ENV_VAR_MAP.items():
        if os.getenv(env_var):
            active_providers.append(provider)

    if not active_providers:
        print("⚠️  No API keys found. Please check your .env file.")
        return

    models_to_test = [
        (alias, conf) for alias, conf in MODEL_CATALOG.items() 
        if conf["provider"] in active_providers
    ]
    models_to_test.sort(key=lambda x: (x[1]["provider"], x[0]))

    # --- INITIAL RENDER ---
    print(f"{'ALIAS (CLI Flag)':<25} | {'PROVIDER':<10} | {'STATUS':<10} | {'TIME':<6} | {'DETAILS'}")
    print("-" * 120)
    for alias, conf in models_to_test:
        print(f"{alias:<25} | {conf['provider']:<10} | {'⏳ WAIT':<10} | {'--':<6} |")
    print("-" * 120)
    
    # Cursor movement math
    # We need to jump back up (number of models + 1 for the bottom separator)
    num_models = len(models_to_test)
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_alias = {
            executor.submit(_ping_model, alias, conf): alias
            for alias, conf in models_to_test
        }
        
        for future in as_completed(future_to_alias):
            alias = future_to_alias[future]
            try:
                res = future.result()
            except Exception as e:
                res = {"alias": alias, "provider": "err", "status": "💥 CRASH", "details": str(e), "time": 0.0}

            # Find index of this model in the sorted list
            idx = next(i for i, (a, c) in enumerate(models_to_test) if a == alias)
            
            # Calculate distance from bottom
            # Bottom is at current cursor. separator is 1 line. last model is 2 lines up.
            lines_up = (num_models - idx) + 1
            
            # Move cursor up, clear line, write result, move cursor back to bottom
            sys.stdout.write(f"\033[{lines_up}A") # Move Up
            sys.stdout.write(f"\r{res['alias']:<25} | {res['provider']:<10} | {res['status']:<10} | {res['time']:>4.2f}s | {res['details']}\033[K")
            sys.stdout.write(f"\033[{lines_up}B") # Move Down
            sys.stdout.flush()

    # Final jump to bottom
    print("\nScan Complete.\n")