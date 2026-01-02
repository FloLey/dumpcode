import os
import argparse
import fnmatch
import json
import base64
import sys

# --- Constants ---
PREFIX_MIDDLE = "├── "
PREFIX_LAST = "└── "
PREFIX_PASS = "│   "
PREFIX_EMPTY = "    "

# Old ignore file for migration
LEGACY_IGNORE_FILENAME = ".dirtree_ignore"
# New config file
CONFIG_FILENAME = ".dump_config.json"

# --- Global Counters & Collectors ---
dir_count_global = 0
file_count_global = 0
tree_lines_collected = []
file_paths_for_content_collected = []


def normalize_path(path):
    """Normalizes path separators to forward slashes for consistent matching."""
    return path.replace(os.sep, "/")


def manage_configuration(root_path, reset_version=False):
    """
    Manages the configuration file (.dump_config.json).
    Handles creation, migration from .dirtree_ignore, and version incrementing.

    Args:
        root_path: The root path where the configuration file is located.
        reset_version: If True, force the version counter to 1 instead of incrementing.
    """
    config_path = os.path.join(root_path, CONFIG_FILENAME)
    legacy_ignore_path = os.path.join(root_path, LEGACY_IGNORE_FILENAME)

    default_config = {
        "version": 1,
        "ignore_patterns": [
            CONFIG_FILENAME,       # Ignore the config file itself
            LEGACY_IGNORE_FILENAME, # Ignore the old ignore file
            ".git",
            "__pycache__",
            "*.pyc",
            "venv",
            ".env",
            ".DS_Store",
            "codebase_dump.txt" # Default output filename
        ]
    }

    # 1. Scenario: Config file already exists -> Read & Increment (or Reset)
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Handle version: reset to 1 or increment
            if reset_version:
                config["version"] = 1
                print("[Info] Resetting version counter to 1.")
            else:
                config["version"] = config.get("version", 0) + 1
                print(f"[Info] Loaded config. Incrementing to Version {config['version']}.")

            # Save immediately
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)

            return config
        except Exception as e:
            print(f"[Warning] Failed to read config file {config_path}: {e}. Using defaults.")
            return default_config

    # 2. Scenario: Migration (Legacy exists, Config does not)
    elif os.path.exists(legacy_ignore_path):
        print(f"[Info] Found legacy '{LEGACY_IGNORE_FILENAME}'. Migrating to '{CONFIG_FILENAME}'...")
        migrated_patterns = set(default_config["ignore_patterns"])

        try:
            with open(legacy_ignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        migrated_patterns.add(normalize_path(line))

            # Create new config structure
            new_config = {
                "version": 1,
                "ignore_patterns": sorted(list(migrated_patterns))
            }

            # Save new config
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(new_config, f, indent=4)

            # Remove old file
            try:
                os.remove(legacy_ignore_path)
                print(f"[Info] Migration complete. Deleted '{LEGACY_IGNORE_FILENAME}'.")
            except OSError as e:
                print(f"[Warning] Could not delete legacy file: {e}")

            return new_config

        except Exception as e:
            print(f"[Error] Migration failed: {e}")
            return default_config

    # 3. Scenario: Fresh Start (Neither exists)
    else:
        print(f"[Info] No config found. Creating new '{CONFIG_FILENAME}' (Version 1).")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4)
        return default_config


def is_excluded(basename, full_path, root_path, excluded_patterns):
    """Checks if a file or directory should be excluded based on the patterns."""
    if basename == CONFIG_FILENAME or basename == LEGACY_IGNORE_FILENAME:
        return True

    if not excluded_patterns:
        return False

    item_relative_path_from_scan_root = normalize_path(
        os.path.relpath(full_path, root_path)
    )

    if item_relative_path_from_scan_root == ".":
        item_relative_path_from_scan_root = basename

    for pattern in excluded_patterns:
        pattern = normalize_path(pattern)

        if "/" not in pattern:  # Basename pattern
            if fnmatch.fnmatch(basename, pattern):
                return True
        elif pattern.startswith("/"):  # Anchored path pattern
            if fnmatch.fnmatch(item_relative_path_from_scan_root, pattern[1:]):
                if (full_path == root_path and item_relative_path_from_scan_root == pattern[1:]):
                    return True
                elif full_path != root_path:
                    return True
        else:  # Floating path pattern
            if (
                item_relative_path_from_scan_root == pattern
                or ("/" + item_relative_path_from_scan_root).endswith("/" + pattern)
                or fnmatch.fnmatch(item_relative_path_from_scan_root, pattern)
            ):
                return True
    return False


def generate_tree_and_collect_files(
    current_path,
    root_path,
    prefix="",
    depth=-1,
    max_depth=None,
    dir_only=False,
    excluded_patterns=None,
):
    global \
        dir_count_global, \
        file_count_global, \
        tree_lines_collected, \
        file_paths_for_content_collected

    if excluded_patterns is None:
        excluded_patterns = set()

    if max_depth is not None and depth > max_depth:
        return

    try:
        all_entries = os.listdir(current_path)
    except PermissionError:
        if not is_excluded(os.path.basename(current_path), current_path, root_path, excluded_patterns):
            tree_lines_collected.append(f"{prefix}{PREFIX_MIDDLE}{os.path.basename(current_path)}{os.sep} [Error: Permission Denied]")
        return
    except FileNotFoundError:
        return

    filtered_entry_names = []
    for entry_basename in all_entries:
        full_entry_path = os.path.join(current_path, entry_basename)
        if not is_excluded(entry_basename, full_entry_path, root_path, excluded_patterns):
            filtered_entry_names.append(entry_basename)

    sorted_entry_names = sorted(filtered_entry_names)

    dirs = [name for name in sorted_entry_names if os.path.isdir(os.path.join(current_path, name))]
    if not dir_only:
        files = [name for name in sorted_entry_names if os.path.isfile(os.path.join(current_path, name))]
        listed_entry_names = dirs + files
    else:
        listed_entry_names = dirs

    pointers = [PREFIX_MIDDLE] * (len(listed_entry_names) - 1) + [PREFIX_LAST]

    for pointer, item_name in zip(pointers, listed_entry_names):
        source_item_full_path = os.path.join(current_path, item_name)
        is_dir_item = os.path.isdir(source_item_full_path)

        if is_dir_item:
            tree_lines_collected.append(f"{prefix}{pointer}{item_name}{os.sep}")
            dir_count_global += 1
            extension = PREFIX_PASS if pointer == PREFIX_MIDDLE else PREFIX_EMPTY
            generate_tree_and_collect_files(
                source_item_full_path,
                root_path,
                prefix=prefix + extension,
                depth=depth + 1,
                max_depth=max_depth,
                dir_only=dir_only,
                excluded_patterns=excluded_patterns,
            )
        elif not dir_only:
            tree_lines_collected.append(f"{prefix}{pointer}{item_name}")
            file_count_global += 1
            file_paths_for_content_collected.append(source_item_full_path)


def copy_to_clipboard_osc52(filepath):
    """
    Copies file content to clipboard using OSC 52 escape sequence.
    Only works with terminals that support OSC 52 (iTerm2, VS Code, Windows Terminal, etc.)
    """
    try:
        size = os.path.getsize(filepath)
        if size > 2000000:
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


def main():
    global \
        dir_count_global, \
        file_count_global, \
        tree_lines_collected, \
        file_paths_for_content_collected
    dir_count_global = 0
    file_count_global = 0
    tree_lines_collected = []
    file_paths_for_content_collected = []

    parser = argparse.ArgumentParser(
        description="Generate codebase dump with auto-incrementing versions.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("startpath", nargs="?", default=".", help="Root directory to scan.")
    parser.add_argument("-L", "--level", type=int, default=None, help="Max depth.")
    parser.add_argument("-d", "--dir-only", action="store_true", help="List directories only.")
    parser.add_argument("-o", "--output-file", default="codebase_dump.txt", help="Output file path (default: codebase_dump.txt).")
    parser.add_argument("--ignore-errors", action="store_true", help="Ignore encoding errors.")
    parser.add_argument("--structure-only", action="store_true", help="Tree structure only.")
    parser.add_argument("--reset-version", action="store_true", help="Force reset the version counter to 1.")
    parser.add_argument("--no-copy", action="store_true", help="Disable automatic clipboard copy via OSC 52.")

    args = parser.parse_args()

    startpath_abs = os.path.abspath(args.startpath)

    if not os.path.isdir(startpath_abs):
        print(f"Error: Source path '{startpath_abs}' is not a valid directory.")
        return

    # --- Configuration & Version Management ---
    config = manage_configuration(startpath_abs, reset_version=args.reset_version)
    current_version = config.get("version", 1)
    excluded_patterns = set(config.get("ignore_patterns", []))

    # Add the output file itself to excluded patterns for this run
    # (We don't save this exclusion to the file, just use it in memory)
    output_file_abs = os.path.abspath(args.output_file)
    try:
        output_rel = os.path.relpath(output_file_abs, startpath_abs)
        if not output_rel.startswith(".."):
            excluded_patterns.add(output_rel)
            excluded_patterns.add(os.path.basename(output_file_abs))
    except ValueError:
        pass

    # --- Generate Tree ---
    tree_lines_collected.append(f"Project Root: {normalize_path(startpath_abs)}")
    tree_lines_collected.append(f"{normalize_path(os.path.basename(startpath_abs))}{os.sep}")

    generate_tree_and_collect_files(
        current_path=startpath_abs,
        root_path=startpath_abs,
        prefix="",
        depth=0,
        max_depth=args.level,
        dir_only=args.dir_only,
        excluded_patterns=excluded_patterns,
    )

    # --- Write Output ---
    try:
        out_dir = os.path.dirname(output_file_abs)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir)

        with open(output_file_abs, "w", encoding="utf-8") as outfile:

            # 1. GLOBAL START WRAPPER
            outfile.write(f"--- VERSION {current_version} (CODE) START ---\n\n")

            # 2. Directory Tree
            outfile.write("--- Directory Tree Structure ---\n")
            for line in tree_lines_collected:
                outfile.write(line + "\n")


            # 3. File Contents
            if not args.structure_only:
                outfile.write("\n\n--- File Contents ---\n")

                if file_paths_for_content_collected:
                    for file_full_path in file_paths_for_content_collected:
                        relative_file_path = normalize_path(os.path.relpath(file_full_path, startpath_abs))

                        outfile.write(f"\n\n--- File: {relative_file_path} ---\n")

                        try:
                            is_special = relative_file_path.lower().endswith(('.csv', '.jsonl'))
                            with open(file_full_path, "r", encoding="utf-8", errors="ignore" if args.ignore_errors else "strict") as f:
                                if is_special:
                                    lines = [line for i, line in enumerate(f) if i < 5]
                                    outfile.write("".join(lines))
                                    outfile.write("\n[... truncated .csv/.jsonl ...]")
                                else:
                                    outfile.write(f.read())
                        except Exception as e:
                            outfile.write(f"[Error reading file: {e}]\n")

                        outfile.write(f"\n--- End of File: {relative_file_path} ---")
                else:
                    outfile.write("[No files found for content inclusion]\n")
            else:
                outfile.write("\n[File contents omitted --structure-only]\n")

            # 4. GLOBAL END WRAPPER
            outfile.write(f"\n\n--- VERSION {current_version} END ---\n")

        print(f"\n[Success] Dump generated at: {output_file_abs}")
        print(f"Used Version: {current_version}")

        # --- Clipboard Integration (OSC 52) ---
        if not args.no_copy:
            copy_to_clipboard_osc52(output_file_abs)

    except Exception as e:
        print(f"\nError writing output: {e}")


if __name__ == "__main__":
    main()
