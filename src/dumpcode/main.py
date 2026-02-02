"""Main entry point for DumpCode."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .cli import parse_arguments_with_profiles
from .config import interactive_init, load_or_create_config
from .core import DumpSettings
from .engine import DumpEngine
from .utils import copy_to_clipboard_osc52, setup_logger
from .ai.client import load_env_file


def handle_new_plan(start_path: Path, plan_input: str) -> None:
    """Write content to PLAN.md from file or stdin.

    Args:
        start_path: Directory where PLAN.md should be created
        plan_input: Path to plan content or '-' for stdin
    """
    plan_path = start_path / "PLAN.md"

    try:
        if plan_input == '-':
            print("📋 [Paste Mode] Paste your Markdown content below and press Ctrl+D to save:")
            content = sys.stdin.read()
        else:
            input_path = Path(plan_input)
            if not input_path.exists():
                print(f"❌ File not found: {input_path}")
                return
            content = input_path.read_text(encoding="utf-8")

        plan_path.write_text(content, encoding="utf-8")
        print(f"✅ Successfully updated {plan_path}")
    except Exception as e:
        print(f"❌ Error writing PLAN.md: {e}")


def handle_meta_mode(args: argparse.Namespace, config: Dict[str, Any]) -> None:
    """Generate a prompt to help the user modify their config.

    Args:
        args: Parsed command-line arguments.
        config: Current configuration dictionary.
    """
    output_file = Path(args.output_file).resolve()
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("Act as a Configuration Assistant for DumpCode.\n")
            f.write(f"USER INSTRUCTION: {args.change_profile}\n\n")
            f.write(f"CURRENT CONFIG:\n{json.dumps(config, indent=4)}\n\n")
            f.write("Output ONLY raw JSON to update .dump_config.json.\n")
        print(f"[Meta-Mode] Configuration prompt generated in {output_file}")
        if not args.no_copy:
            copy_to_clipboard_osc52(output_file)
    except Exception as e:
        print(f"[Error] Failed to generate meta-mode prompt: {e}")


def run_dump(args: argparse.Namespace, config: Dict[str, Any], start_path: Path) -> None:
    """Orchestrate the dump execution based on parsed arguments and config.

    Args:
        args: Parsed CLI arguments.
        config: Loaded configuration dictionary.
        start_path: Resolved path to begin scanning.
    """
    settings = DumpSettings.from_arguments(args, config, start_path)
    engine = DumpEngine(config, settings)
    engine.run()


def main(args_list: Optional[list[str]] = None) -> None:
    """Primary application entry point.

    Initialize scanning, process CLI arguments, and invoke the DumpEngine.

    Args:
        args_list: Optional list of command-line arguments. If None, uses sys.argv[1:].
    """
    if args_list is None:
        args_list = sys.argv[1:]
    
    start_path = Path(".").resolve()
    if args_list and not args_list[0].startswith("-"):
        start_path = Path(args_list[0]).resolve()
        args_list = args_list[1:]
    
    if not start_path.is_dir():
        print(f"Error: Invalid directory '{start_path}'")
        return

    # Load environment variables from .env file at the very beginning
    load_env_file(start_path)

    # Parse arguments with the start path
    args = parse_arguments_with_profiles(start_path, args_list)

    if args.test_models:
        from .ai.diagnostics import run_diagnostics
        run_diagnostics()
        return

    if args.init:
        interactive_init(start_path)
        return
    if args.new_plan:
        handle_new_plan(start_path, args.new_plan)
        return

    logger = setup_logger("dumpcode", verbose=args.verbose)
    config = load_or_create_config(start_path, reset_version=args.reset_version, logger=logger)

    if args.change_profile:
        handle_meta_mode(args, config)
    else:
        run_dump(args, config, start_path)


if __name__ == "__main__":
    main()