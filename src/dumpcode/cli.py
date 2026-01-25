"""Command line interface for DumpCode."""

import argparse
from pathlib import Path
from typing import List

from .constants import CONFIG_FILENAME
from .config import load_or_create_config


def parse_arguments_with_profiles(start_path: Path) -> argparse.Namespace:
    """Parse command-line arguments with dynamic profiles loaded from config.

    Load profiles from the local configuration to generate dynamic CLI flags.

    Args:
        start_path: The directory where the configuration is located.

    Returns:
        The parsed argparse Namespace.
    """
    config = load_or_create_config(start_path, reset_version=False)
    profiles = config.get("profiles", {})

    parser = argparse.ArgumentParser(
        description="DumpCode: Semantic Codebase Dumper for LLMs.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    scan_group = parser.add_argument_group("Scanning Options")
    scan_group.add_argument("startpath", nargs="?", default=".", help="Root directory")
    scan_group.add_argument("-L", "--level", type=int, help="Max depth")
    scan_group.add_argument(
        "--changed", action="store_true", help="Only git-modified files"
    )
    scan_group.add_argument("-d", "--dir-only", action="store_true", help="Dirs only")
    scan_group.add_argument(
        "--ignore-errors", action="store_true", help="Ignore encoding errors"
    )
    scan_group.add_argument(
        "--structure-only",
        action="store_true",
        help="Directory tree only (no file contents)"
    )

    out_group = parser.add_argument_group("Output Options")
    out_group.add_argument("-o", "--output-file", default="codebase_dump.txt", help="Output file")
    out_group.add_argument("--no-copy", action="store_true", help="Disable clipboard")
    out_group.add_argument(
        "--no-xml", action="store_true", help="Use text delimiters (XML is default)"
    )
    out_group.add_argument("--reset-version", action="store_true", help="Reset version counter to 1")
    out_group.add_argument("-v", "--verbose", action="store_true", help="Show detailed processing logs")

    meta_group = parser.add_argument_group("Meta Commands")
    meta_group.add_argument("--init", action="store_true", help="Interactive configuration setup")
    meta_group.add_argument("--new-plan", nargs="?", const="-", help="Update PLAN.md")
    meta_group.add_argument("--change-profile", type=str, help="Instruction to modify .dump_config.json")
    meta_group.add_argument("-q", "--question", type=str, help="Post-dump instruction (overrides profile)")

    profile_group = parser.add_argument_group("LLM Prompt Profiles")

    built_in_flags: List[str] = []
    for action in parser._actions:  # noqa: SLF001
        built_in_flags.extend(action.option_strings)

    for profile_name, profile_data in profiles.items():
        flag_name = f"--{profile_name.replace('_', '-')}"

        if flag_name in built_in_flags:
            print(f"⚠️ [Warning] Profile '{profile_name}' conflicts with a core flag. "
                  f"To use this profile, rename it in {CONFIG_FILENAME}.")
            continue

        desc = profile_data.get("description", f"Run the {profile_name} profile")
        profile_group.add_argument(
            flag_name,
            action="store_true",
            help=desc
        )

    return parser.parse_args()