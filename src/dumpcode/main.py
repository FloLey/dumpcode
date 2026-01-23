import os
import sys
import json
import base64
import argparse
import fnmatch
from pathlib import Path
from typing import List, Set, Optional, Dict, Any

from .constants import (
    PREFIX_MIDDLE,
    PREFIX_LAST,
    PREFIX_PASS,
    PREFIX_EMPTY,
    CONFIG_FILENAME,
    DEFAULT_PROFILES
)


class DumpSession:
    """Encapsulates the state of a single dump execution."""
    
    def __init__(self, root_path: Path, excluded_patterns: Set[str], max_depth: Optional[int], dir_only: bool):
        self.root_path = root_path
        self.excluded_patterns = excluded_patterns
        self.max_depth = max_depth
        self.dir_only = dir_only
        
        # State
        self.dir_count = 0
        self.file_count = 0
        self.tree_lines: List[str] = []
        self.files_to_dump: List[Path] = []
        self.visited_paths: Set[Path] = set()  # To prevent symlink loops

    def normalize_path(self, path: str) -> str:
        """Normalizes path separators to forward slashes for consistent matching."""
        return path.replace(os.sep, "/")

    def is_excluded(self, item_path: Path) -> bool:
        """Determines if a path should be ignored based on config."""
        name = item_path.name
        if name == CONFIG_FILENAME:
            return True
        
        # Simple optimization: if no patterns, return early
        if not self.excluded_patterns:
            return False

        rel_path = item_path.relative_to(self.root_path).as_posix()
        
        for pattern in self.excluded_patterns:
            # Handle directory markers in gitignore style (e.g., "dist/")
            clean_pattern = pattern.rstrip('/')
            
            # 1. Match basename (e.g., "*.pyc")
            if "/" not in clean_pattern:
                if fnmatch.fnmatch(name, clean_pattern):
                    return True
            
            # 2. Match relative path
            if fnmatch.fnmatch(rel_path, clean_pattern):
                return True
                
            # 3. Directory prefix match (e.g., ignoring "node_modules" should ignore "node_modules/foo")
            if rel_path.startswith(clean_pattern + "/") or rel_path == clean_pattern:
                return True
                
        return False

    def generate_tree(self, current_path: Path, prefix: str = "", depth: int = 0) -> None:
        """Recursive directory walker using os.scandir for performance."""
        if self.max_depth is not None and depth > self.max_depth:
            return

        # Anti-recursion loop check (resolves symlinks)
        try:
            real_path = current_path.resolve()
            if real_path in self.visited_paths:
                self.tree_lines.append(f"{prefix}{PREFIX_MIDDLE}{current_path.name} [Recursive Link]")
                return
            self.visited_paths.add(real_path)
        except OSError:
            pass

        try:
            # scandir is faster than listdir + isdir
            with os.scandir(current_path) as it:
                entries = sorted(list(it), key=lambda e: e.name.lower())
        except PermissionError:
            self.tree_lines.append(f"{prefix}{PREFIX_MIDDLE}{current_path.name}/ [Permission Denied]")
            return
        except FileNotFoundError:
            return

        # Filter entries
        valid_entries = []
        for entry in entries:
            # Convert entry to Path for consistent handling in is_excluded
            entry_path = Path(entry.path)
            if not self.is_excluded(entry_path):
                valid_entries.append(entry)

        # Split dirs and files
        dirs = [e for e in valid_entries if e.is_dir()]
        files = [e for e in valid_entries if e.is_file()] if not self.dir_only else []
        
        items = dirs + files
        count = len(items)

        for i, entry in enumerate(items):
            is_last = (i == count - 1)
            pointer = PREFIX_LAST if is_last else PREFIX_MIDDLE
            entry_path = Path(entry.path)
            
            if entry.is_dir():
                self.tree_lines.append(f"{prefix}{pointer}{entry.name}/")
                self.dir_count += 1
                
                extension = PREFIX_EMPTY if is_last else PREFIX_PASS
                self.generate_tree(
                    entry_path, 
                    prefix=prefix + extension, 
                    depth=depth + 1
                )
            else:
                self.tree_lines.append(f"{prefix}{pointer}{entry.name}")
                self.file_count += 1
                self.files_to_dump.append(entry_path)


def is_binary_file(filepath: Path) -> bool:
    """Simple check to see if a file is likely binary."""
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(1024)
            return b'\0' in chunk  # Null byte usually indicates binary
    except Exception:
        return True


def copy_to_clipboard_osc52(filepath: Path) -> None:
    """OSC 52 Clipboard copy with safety margin for Base64 expansion."""
    try:
        size = filepath.stat().st_size
        # Base64 is ~1.33x size. Limit raw file to ~1.5MB to stay under typical 2MB buffer limits
        if size > 1_500_000: 
            print(f"⚠️  File too large ({size // 1024} KB) for auto-copy.")
            return

        with open(filepath, "rb") as f:
            content = f.read()

        encoded = base64.b64encode(content).decode("utf-8")
        sys.stdout.write(f"\033]52;c;{encoded}\a")
        sys.stdout.flush()
        print("✅ Dump generated and copied to LOCAL clipboard!")
    except Exception as e:
        print(f"⚠️  Could not copy to clipboard: {e}")


def load_or_create_config(root_path: Path, reset_version: bool = False) -> Dict[str, Any]:
    """
    Loads config, handles version increment, and ensures structure exists.
    No more legacy migration.
    """
    config_path = root_path / CONFIG_FILENAME
    
    default_config = {
        "version": 1,
        "ignore_patterns": [
            CONFIG_FILENAME,
            ".git", "__pycache__", "*.pyc", "venv", ".env", ".DS_Store",
            "codebase_dump.txt"
        ],
        "profiles": DEFAULT_PROFILES
    }

    config = default_config.copy()

    # 1. Load existing
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # Merge loaded config over defaults (shallow merge)
                config.update(loaded)
                
                # Ensure profiles exist if user deleted them
                if "profiles" not in config:
                    config["profiles"] = DEFAULT_PROFILES

        except Exception as e:
            print(f"[Warning] Failed to read config {config_path}: {e}. Using defaults.")

    # 2. Handle Version
    if config_path.exists():
        if reset_version:
            config["version"] = 1
            print("[Info] Version reset to 1.")
        else:
            config["version"] = config.get("version", 0) + 1
            print(f"[Info] Incrementing to Version {config['version']}.")
    else:
        print(f"[Info] Creating new config at {config_path}")

    # 3. Save
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"[Error] Could not save config: {e}")

    return config


def main() -> None:
    # --- Pass 1: Find the Start Path ---
    # We need to know where the project is to load the correct config
    # before we can define the dynamic profile arguments.
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("startpath", nargs="?", default=".")
    pre_parser.add_argument("--reset-version", action="store_true") # Need this early for config load
    
    # Parse only known args to extract path, ignore the rest for now
    pre_args, _ = pre_parser.parse_known_args()
    
    start_path = Path(pre_args.startpath).resolve()
    
    if not start_path.is_dir():
        print(f"Error: Invalid directory '{start_path}'")
        return

    # --- Load Config & Profiles ---
    config = load_or_create_config(start_path, reset_version=pre_args.reset_version)
    current_version = config.get("version", 1)
    profiles = config.get("profiles", {})

    # --- Pass 2: Build Full CLI ---
    parser = argparse.ArgumentParser(
        description="DumpCode: Codebase dumper with dynamic profiles.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Standard Args
    parser.add_argument("startpath", nargs="?", default=".", help="Root directory")
    parser.add_argument("-L", "--level", type=int, default=None, help="Max depth")
    parser.add_argument("-d", "--dir-only", action="store_true", help="Dirs only")
    parser.add_argument("-o", "--output-file", default="codebase_dump.txt", help="Output file")
    parser.add_argument("--ignore-errors", action="store_true", help="Ignore encoding errors")
    parser.add_argument("--structure-only", action="store_true")
    parser.add_argument("--no-copy", action="store_true")
    parser.add_argument("--reset-version", action="store_true") # Re-add to show in help
    
    # DYNAMIC PROFILES: Add flags for every key in config['profiles']
    # Example: if "security" is in config, allow --security
    active_profile_key = None
    
    # We add a group so they look organized in --help
    profile_group = parser.add_argument_group("Available Prompt Profiles")
    
    for profile_name, profile_data in profiles.items():
        desc = profile_data.get("description", f"Run the {profile_name} profile")
        flag_name = f"--{profile_name}"
        
        # Avoid collision with built-ins
        if flag_name in [x.option_strings for x in parser._actions]:
            print(f"[Warning] Profile '{profile_name}' conflicts with built-in flags. Skipping.")
            continue
            
        profile_group.add_argument(
            flag_name, 
            action="store_true", 
            help=f"{desc} (Prepend prompt)"
        )

    # Now parse the full set of arguments
    args = parser.parse_args()

    # Determine which profile was selected
    selected_profile = None
    selected_profile_name = None
    for profile_name in profiles:
        if getattr(args, profile_name, False):
            selected_profile = profiles[profile_name]
            selected_profile_name = profile_name
            print(f"[Info] Profile '{profile_name}' active.")
            break # Only allow one profile at a time

    # --- Execution Logic ---
    
    excluded_patterns = set(config.get("ignore_patterns", []))
    # Exclude output file
    output_file = Path(args.output_file).resolve()
    try:
        output_rel = output_file.relative_to(start_path)
        if not str(output_rel).startswith(".."):
            excluded_patterns.add(str(output_rel))
            excluded_patterns.add(output_file.name)
    except: 
        pass

    # Initialize Session
    session = DumpSession(
        root_path=start_path,
        excluded_patterns=excluded_patterns,
        max_depth=args.level,
        dir_only=args.dir_only
    )

    # Tree Generation
    session.tree_lines.append(f"Project Root: {start_path.as_posix()}")
    session.tree_lines.append(f"{start_path.name}/")
    
    session.generate_tree(start_path)

    # Write Output
    try:
        out_dir = output_file.parent
        if out_dir and not out_dir.exists():
            out_dir.mkdir(parents=True)

        with open(output_file, "w", encoding="utf-8") as outfile:
            
            # 1. WRITE PRE-PROMPT (If profile active)
            if selected_profile and selected_profile.get("pre"):
                outfile.write(selected_profile["pre"])
                outfile.write("\n\n" + ("="*40) + "\n\n")

            # 2. STANDARD CONTENT
            outfile.write(f"--- VERSION {current_version} (CODE) START ---\n\n")
            
            outfile.write("--- Directory Tree Structure ---\n")
            for line in session.tree_lines:
                outfile.write(line + "\n")
            
            if not args.structure_only:
                outfile.write("\n\n--- File Contents ---\n")
                if session.files_to_dump:
                    for file_path in session.files_to_dump:
                        rel = file_path.relative_to(start_path).as_posix()
                        outfile.write(f"\n\n--- File: {rel} ---\n")
                        try:
                            is_special = rel.lower().endswith(('.csv', '.jsonl'))
                            if is_special:
                                with open(file_path, "r", encoding="utf-8", errors="ignore" if args.ignore_errors else "strict") as f:
                                    lines = [line for i, line in enumerate(f) if i < 5]
                                    outfile.write("".join(lines))
                                    outfile.write("\n[... truncated .csv/.jsonl ...]")
                            elif is_binary_file(file_path):
                                outfile.write("[Binary file content omitted]\n")
                            else:
                                with open(file_path, "r", encoding="utf-8", errors="ignore" if args.ignore_errors else "strict") as f:
                                    outfile.write(f.read())
                        except Exception as e:
                            outfile.write(f"[Error reading file: {e}]")
                        outfile.write(f"\n--- End of File: {rel} ---")
                else:
                    outfile.write("[No files found]")
            
            outfile.write(f"\n\n--- VERSION {current_version} END ---\n")

            # 3. WRITE POST-PROMPT (If profile active)
            if selected_profile and selected_profile.get("post"):
                outfile.write("\n" + ("="*40) + "\n\n")
                outfile.write(selected_profile["post"] + "\n")

        print(f"\n[Success] Dumped to {output_file} (Version {current_version})")
        print(f"Directories: {session.dir_count}, Files: {session.file_count}")
        if selected_profile_name:
            print(f"[Info] Profile '{selected_profile_name}' prepended to output.")

        # --- Clipboard Integration (OSC 52) ---
        if not args.no_copy:
            copy_to_clipboard_osc52(output_file)

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()