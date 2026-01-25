"""Main entry point for DumpCode."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from .cli import parse_arguments_with_profiles
from .config import interactive_init, load_or_create_config
from .constants import DEFAULT_PROFILES
from .core import DumpSettings
from .engine import DumpEngine
from .utils import copy_to_clipboard_osc52, setup_logger


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
    active_profile = None
    profiles = config.get("profiles", {})
    merged_profiles = {**DEFAULT_PROFILES, **profiles}

    for name, data in merged_profiles.items():
        attr_name = name.replace('-', '_')
        if getattr(args, attr_name, False):
            active_profile = data
            break

    settings = DumpSettings(
        start_path=start_path,
        output_file=Path(args.output_file),
        max_depth=args.level,
        dir_only=args.dir_only,
        ignore_errors=args.ignore_errors,
        structure_only=args.structure_only,
        no_copy=args.no_copy,
        use_xml=False if args.no_xml else config.get("use_xml", True),
        git_changed_only=args.changed,
        question=args.question,
        active_profile=active_profile,
        reset_version=args.reset_version,
        verbose=args.verbose
    )

    engine = DumpEngine(config, settings)
    engine.run()


def main() -> None:
    """Primary application entry point.

    Initialize scanning, process CLI arguments, and invoke the DumpEngine.
    """
    # PEP 8 Fix: Wrapped long line
    has_arg = len(sys.argv) > 1 and not sys.argv[1].startswith("-")
    raw_path = sys.argv[1] if has_arg else "."
    start_path = Path(raw_path).resolve()

    if not start_path.is_dir():
        print(f"Error: Invalid directory '{start_path}'")
        return

    args = parse_arguments_with_profiles(start_path)

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