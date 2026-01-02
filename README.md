# DumpCode

A Python CLI tool for generating comprehensive codebase dumps with auto-incrementing versions and automatic clipboard integration via OSC 52.

## Features

- **Directory Tree Generation**: Creates a visual tree structure of your project
- **File Content Extraction**: Includes full contents of all non-excluded files
- **Auto-Versioning**: Automatically increments version numbers for each dump
- **Smart Exclusions**: Configurable ignore patterns (similar to .gitignore)
- **Clipboard Integration**: Automatically copies dumps to your local clipboard via OSC 52 escape sequences
- **CSV/JSONL Handling**: Truncates large data files to first 5 lines
- **Configurable Output**: Control depth, file types, and output format

## Installation

### From GitHub (Recommended)

```bash
pip install git+https://github.com/FloLey/dumpcode.git
```

### Local Development Installation

```bash
# Clone the repository
git clone https://github.com/FloLey/dumpcode.git
cd dumpcode

# Install in editable mode
pip install -e .
```

### In a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install git+https://github.com/FloLey/dumpcode.git
```

## Usage

### Basic Usage

Generate a dump of the current directory:

```bash
dumpcode
```

This creates `codebase_dump.txt` in the current directory and copies it to your clipboard (if < 2MB).

### Common Options

```bash
# Dump a specific directory
dumpcode /path/to/project

# Specify custom output file
dumpcode -o my_dump.txt

# Limit directory depth
dumpcode -L 3

# Directory structure only (no file contents)
dumpcode --structure-only

# Directories only (no files)
dumpcode -d

# Disable automatic clipboard copy
dumpcode --no-copy

# Reset version counter to 1
dumpcode --reset-version
```

### Complete Options

```
positional arguments:
  startpath             Root directory to scan (default: current directory)

optional arguments:
  -h, --help            Show this help message and exit
  -L LEVEL, --level LEVEL
                        Maximum directory depth to traverse
  -d, --dir-only        List directories only (exclude files)
  -o OUTPUT_FILE, --output-file OUTPUT_FILE
                        Output file path (default: codebase_dump.txt)
  --ignore-errors       Ignore encoding errors when reading files
  --structure-only      Generate tree structure only (skip file contents)
  --reset-version       Reset the version counter to 1
  --no-copy             Disable automatic clipboard copy via OSC 52
```

## Configuration

DumpCode uses `.dump_config.json` in the scanned directory to manage:

- **Version tracking**: Auto-increments with each run
- **Ignore patterns**: Files and directories to exclude

### Default Ignore Patterns

```json
{
  "version": 1,
  "ignore_patterns": [
    ".dump_config.json",
    ".dirtree_ignore",
    ".git",
    "__pycache__",
    "*.pyc",
    "venv",
    ".env",
    ".DS_Store",
    "codebase_dump.txt"
  ]
}
```

### Customizing Ignore Patterns

Edit `.dump_config.json` in your project root:

```json
{
  "version": 5,
  "ignore_patterns": [
    ".git",
    "node_modules",
    "*.log",
    "dist",
    "build",
    "/tests/fixtures/*.json"
  ]
}
```

**Pattern Types:**
- `*.pyc` - Basename wildcard (matches anywhere)
- `/tests/data` - Anchored path (from project root)
- `build` - Floating pattern (matches anywhere in path)

### Legacy Migration

If you have a `.dirtree_ignore` file, it will be automatically migrated to `.dump_config.json` on first run.

## Clipboard Integration

DumpCode uses **OSC 52 escape sequences** to copy output directly to your **local** clipboard, even over SSH.

### Supported Terminals

- iTerm2 (macOS)
- VS Code integrated terminal
- Windows Terminal
- tmux (with proper configuration)
- Most modern terminal emulators

### Size Limit

Files larger than **2MB** will not be auto-copied to prevent terminal freezing. You'll see a warning instead.

### Disabling Clipboard

```bash
dumpcode --no-copy
```

## Examples

### Dump Current Project

```bash
dumpcode
```

Output: `codebase_dump.txt` with version 1

### Dump Specific Project

```bash
dumpcode ~/projects/my-app -o ~/dumps/my-app-v1.txt
```

### Structure Only (Fast)

```bash
dumpcode --structure-only
```

### Deep Scan with Custom Depth

```bash
dumpcode -L 5 -o deep_scan.txt
```

### Remote Server Dump (via SSH)

```bash
# On remote server
dumpcode ~/project

# Content is automatically copied to your LOCAL clipboard!
```

## Output Format

```
--- VERSION 1 (CODE) START ---

--- Directory Tree Structure ---
Project Root: /path/to/project
project/
├── src/
│   ├── main.py
│   └── utils.py
└── README.md

--- File Contents ---

--- File: src/main.py ---
[file content here]
--- End of File: src/main.py ---

...

--- VERSION 1 END ---
```

## Version Management

Each run automatically increments the version number stored in `.dump_config.json`.

```bash
dumpcode           # VERSION 1
dumpcode           # VERSION 2
dumpcode           # VERSION 3
dumpcode --reset-version  # VERSION 1 (reset)
```

## Troubleshooting

### Clipboard Not Working

1. **Check terminal support**: Ensure your terminal supports OSC 52
2. **Test manually**: Try `echo -e "\033]52;c;$(echo 'test' | base64)\a"`
3. **Disable if needed**: Use `--no-copy` flag

### Large Files

If your dump is >2MB, it won't auto-copy. Solutions:
- Use `--structure-only` for a smaller dump
- Use `-L` to limit depth
- Add exclusion patterns to `.dump_config.json`
- Use `--no-copy` and copy manually

### Permission Errors

Files/directories with permission errors are marked as `[Error: Permission Denied]` in the output.

## License

MIT

## Author

Florent Lejoly (florent.lejoly@gmail.com)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request
