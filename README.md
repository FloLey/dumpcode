# DumpCode

**Turn your codebase into a structured, LLM-ready prompt in one command.**

DumpCode scans your project, builds a semantic XML representation of your files and directory structure, and wraps it in a "Sandwich Architecture" prompt — instructions before, task after — so your LLM has full context before it answers.

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [CLI Reference](#cli-reference)
- [Configuration](#configuration)
- [Profiles](#profiles)
- [Built-in Profiles](#built-in-profiles)
- [AI Integration](#ai-integration)
- [Workflow Guide](#workflow-guide)

---

## Installation

### From GitHub

```bash
# Core tool only (clipboard, dump, profiles — no AI auto-send)
pip install git+https://github.com/FloLey/dumpcode.git

# With AI support (auto-send to Claude, Gemini, GPT, DeepSeek)
pip install "git+https://github.com/FloLey/dumpcode.git#egg=dumpcode[ai]"

# With a single provider
pip install "git+https://github.com/FloLey/dumpcode.git#egg=dumpcode[claude]"
pip install "git+https://github.com/FloLey/dumpcode.git#egg=dumpcode[gemini]"
pip install "git+https://github.com/FloLey/dumpcode.git#egg=dumpcode[openai]"
pip install "git+https://github.com/FloLey/dumpcode.git#egg=dumpcode[deepseek]"
```

### From Source

```bash
git clone https://github.com/FloLey/dumpcode.git
cd dumpcode
pip install -e ".[ai]"
```

**Requirements:** Python 3.9+

---

## Quick Start

```bash
# Dump the current directory to clipboard
dumpcode

# Dump a specific directory
dumpcode /path/to/project

# Dump and automatically send to Claude
dumpcode --cleanup --auto
```

DumpCode writes the output to `codebase_dump.txt` and copies it to your clipboard via OSC52 (works over SSH, Docker, and remote dev containers).

### First-time setup

```bash
# Initialize a project config (creates .dump_config.json)
dumpcode --init

# Create a .env for AI API keys
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-xxxxx
GOOGLE_API_KEY=AIzaSyxxxxx
OPENAI_API_KEY=sk-xxxxx
DEEPSEEK_API_KEY=sk-xxxxx
EOF
```

---

## How It Works

DumpCode generates a three-layer prompt called the **Sandwich Architecture**:

```
┌─────────────────────────────────────────┐
│  <instructions>                         │  ← Layer 1: Who the LLM is
│    Act as a Senior Python Developer...  │
│  </instructions>                        │
├─────────────────────────────────────────┤
│  <dump version="42">                    │  ← Layer 2: Your codebase
│    <tree>...</tree>                     │
│    <files>                              │
│      <file path="src/main.py">...</file>│
│    </files>                             │
│    <execution>ruff output...</execution>│
│  </dump>                                │
├─────────────────────────────────────────┤
│  <task>                                 │  ← Layer 3: What you want
│    Fix the type errors above.           │
│  </task>                                │
└─────────────────────────────────────────┘
```

**Why this order matters:** By placing instructions before the code and the task after, the LLM reads your rules and context before it forms a response. This reduces hallucinations and produces more grounded, accurate answers.

---

## CLI Reference

### Basic usage

```bash
dumpcode [startpath] [options]
```

`startpath` defaults to `.` (current directory).

### Scanning options

| Flag | Description |
|:-----|:------------|
| `--changed` | Only include files modified in git (staged or unstaged). Useful when you want to focus the LLM on your current work. |
| `-L N` | Limit directory traversal to N levels deep. |
| `--structure-only` | Include the directory tree but omit file contents. |
| `-d`, `--dir-only` | Include only directories in the tree, no files at all. |
| `--ignore-errors` | Suppress encoding/read errors for files that can't be decoded. |

### Output options

| Flag | Description |
|:-----|:------------|
| `-o FILE` | Write output to `FILE` instead of `codebase_dump.txt`. |
| `--no-copy` | Don't copy to clipboard via OSC52. |
| `--no-xml` | Use plain text delimiters instead of XML tags. Not recommended for LLM use. |
| `--reset-version` | Reset the version counter in `.dump_config.json` to 1. |
| `-v`, `--verbose` | Show detailed per-file processing logs. |

### AI options

| Flag | Description |
|:-----|:------------|
| `--auto` | Force auto-send to AI after generating the dump. |
| `--no-auto` | Disable auto-send even if the active profile has `auto_send: true`. |
| `--model ID` | Override the AI model for this run (e.g. `claude-sonnet-4-5-20250929`). |

### Meta commands

| Flag | Description |
|:-----|:------------|
| `--init` | Interactive setup — creates `.dump_config.json` in the current directory. |
| `--new-plan [FILE\|-]` | Write or update `PLAN.md`. Pass `-` to read from stdin (paste mode). |
| `--change-profile INSTRUCTION` | Generate a prompt to modify `.dump_config.json` via an LLM. |
| `-q TEXT` | Append a custom question/task to the prompt (overrides the profile's `post`). |
| `--test-models` | Run parallel connectivity tests for all configured AI providers. |

### Profile flags

Every profile defined in `.dump_config.json` becomes a CLI flag automatically:

```bash
dumpcode --readme        # built-in: generate README
dumpcode --cleanup       # built-in: run linters and fix errors
dumpcode --my-profile    # custom: any profile you've defined
```

Profile names use hyphens on the CLI: a profile named `security_audit` becomes `--security-audit`.

---

## Configuration

DumpCode stores project settings in `.dump_config.json` in your project root. Run `dumpcode --init` to create it interactively, or create it manually.

### Full schema

```json
{
  "version": 1,
  "use_xml": true,
  "ignore_patterns": ["venv", "*.pyc", "node_modules"],
  "include_patterns": [],
  "profiles": {}
}
```

### `version` (integer)

Auto-incremented after each successful dump. Appears in the `<dump version="N">` tag so you can track which iteration the LLM is responding to. Reset with `--reset-version`.

### `use_xml` (boolean, default: `true`)

Controls whether the output uses semantic XML tags (`<dump>`, `<files>`, `<task>`, etc.) or plain text delimiters. Keep this `true` for LLM use — the tags help models identify and separate sections.

### `ignore_patterns` (array of strings)

Glob patterns to exclude from the dump. Merged with your `.gitignore` (if present).

```json
"ignore_patterns": [
  ".git",
  "__pycache__",
  "*.pyc",
  "venv",
  ".env",
  "node_modules",
  "dist",
  "*.log"
]
```

Patterns follow gitignore syntax: wildcards (`*.pyc`), directories (`venv/`), and paths (`src/tests/*.snap`) all work.

**Note:** `.dump_config.json` itself is always excluded regardless of patterns.

### `include_patterns` (array of strings)

Glob patterns that **override** `ignore_patterns` and `.gitignore`. If a file matches an include pattern, it is included even if it would otherwise be excluded.

This is useful when you have a directory in `.gitignore` that you still want to dump:

```json
"include_patterns": ["config/secrets.example.json"]
```

---

## Profiles

A profile is a named configuration that sets the LLM persona (`pre`), the task (`post`), optional shell commands to run (`run_commands`), and file filtering overrides. Profiles become CLI flags automatically.

### Profile fields

| Field | Type | Description |
|:------|:-----|:------------|
| `description` | string | Help text shown in `--help`. |
| `pre` | string or array | Instructions placed before the code context (Layer 1). Sets the LLM's role and rules. |
| `post` | string or array | Task placed after the code context (Layer 3). What you want the LLM to do. |
| `run_commands` | array | Shell commands to run before the LLM task. Output is captured into an `<execution>` block in the dump. |
| `model` | string | Default AI model for this profile when using `--auto`. |
| `auto_send` | boolean | If `true`, automatically sends to AI when this profile is active (same as passing `--auto`). |
| `additional_excludes` | array | Extra glob patterns to exclude, on top of global `ignore_patterns`. Applied only when this profile is active. |
| `additional_includes` | array | Extra glob patterns to force-include, on top of global `include_patterns`. Applied only when this profile is active. |

### `additional_excludes` and `additional_includes`

These are per-profile file filtering overrides. They let you narrow or expand the file set for a specific task without changing global settings.

**Example — a profile that only looks at tests:**

```json
"test-review": {
  "description": "Review only the test suite",
  "pre": "Act as a QA Engineer. Review the test coverage and quality.",
  "post": "List gaps and suggest improvements.",
  "additional_excludes": ["src/"],
  "additional_includes": ["tests/"]
}
```

**Example — a profile that includes normally-ignored fixtures:**

```json
"fixture-audit": {
  "description": "Audit test fixtures including large data files",
  "pre": "Act as a Data Engineer.",
  "post": "Identify any stale or inconsistent fixtures.",
  "additional_includes": ["tests/fixtures/"]
}
```

`additional_includes` follows the same last-wins rule as global `include_patterns`: a path that matches an include pattern is included even if it matches an exclude pattern.

### Defining a custom profile

Add it to the `"profiles"` section of `.dump_config.json`:

```json
{
  "profiles": {
    "security-audit": {
      "description": "Scan for common vulnerabilities",
      "pre": [
        "Act as a Security Engineer.",
        "Look for SQL injection, XSS, path traversal, and insecure defaults."
      ],
      "post": "List all findings by severity: Critical / High / Medium / Low.",
      "run_commands": ["bandit -r src/ -q"],
      "model": "claude-3-5-sonnet-latest",
      "auto_send": false
    }
  }
}
```

Then use it:

```bash
dumpcode --security-audit
dumpcode --security-audit --auto
```

**Naming:** Profile names with underscores (`my_profile`) become flags with hyphens (`--my-profile`). Names that conflict with built-in flags are rejected with a warning.

---

## Built-in Profiles

DumpCode ships with eight profiles defined in `constants.py`. They are merged with any profiles in your `.dump_config.json` (your definitions win on conflicts).

### `--readme`

Generates a professional README.md. Instructs the LLM to act as a Technical Writer, analyze the codebase architecture, and document both the "How" and the "Why".

```bash
dumpcode --readme
dumpcode --readme --auto --model claude-3-5-sonnet-latest
```

### `--architect`

Generates a `PLAN.md` project specification. Instructs the LLM to act as a Product Manager and Software Architect, documenting current status, architecture, roadmap, missing features, and tech debt.

```bash
dumpcode --architect
dumpcode --architect -q "Focus on the authentication subsystem."
```

### `--plan-next`

Syncs `PLAN.md` with the current code. Marks completed tasks, removes obsolete ones, and defines exactly one next milestone. Stops with "PROJECT MILESTONES COMPLETE" when everything is done.

```bash
dumpcode --plan-next
```

### `--cleanup`

Runs `ruff check` and `mypy`, captures their output into `<execution>`, and instructs the LLM to fix every reported error plus any additional issues (dead code, missing docstrings).

```bash
dumpcode --cleanup
dumpcode --changed --cleanup   # fix only the files you've modified
```

### `--test-fixer`

Runs `pytest -v`, captures output, and instructs the LLM to diagnose failures and produce a `FIX_PLAN.md`. Stops with "All tests passed" when the suite is green.

```bash
dumpcode --test-fixer
```

### `--coverage`

Runs `pytest --cov=src/dumpcode --cov-report=term-missing` and instructs the LLM to plan tests for uncovered lines. Stops cleanly when coverage is already >95%.

```bash
dumpcode --coverage
```

### `--refactor`

Reviews the code for SOLID violations, code smells, and structural weaknesses. Instructs the LLM to rank suggestions by impact and avoid over-engineering.

```bash
dumpcode --refactor
```

### `--optimize`

Analyses the code for performance bottlenecks: algorithmic complexity, I/O in loops, memory usage. Explicitly avoids micro-optimizations.

```bash
dumpcode --optimize
```

---

## AI Integration

DumpCode can automatically send the generated prompt to an AI provider and stream the response to your terminal.

### Supported providers

| Provider | Models | Env var |
|:---------|:-------|:--------|
| Anthropic (Claude) | `claude-3-5-sonnet-latest`, `claude-opus-...` | `ANTHROPIC_API_KEY` |
| Google (Gemini) | `gemini-2.5-pro`, `gemini-2.0-flash` | `GOOGLE_API_KEY` |
| OpenAI (GPT) | `gpt-4o`, `o1`, `o3` | `OPENAI_API_KEY` |
| DeepSeek | `deepseek-chat`, `deepseek-reasoner` | `DEEPSEEK_API_KEY` |

### Enabling auto-send

```bash
# Force auto-send for any profile
dumpcode --cleanup --auto

# Override the model for this run
dumpcode --readme --auto --model gemini-2.5-pro

# Disable auto-send for a profile that has auto_send: true
dumpcode --my-profile --no-auto
```

Or set `"auto_send": true` in a profile to make it always auto-send when active.

### Testing connectivity

```bash
dumpcode --test-models
```

Runs parallel connectivity tests against all providers that have API keys configured, and reports which ones are reachable.

---

## Workflow Guide

### Focused fix: only changed files

When you've edited a few files and want the LLM to review only your changes:

```bash
dumpcode --changed --cleanup
```

DumpCode runs the linters against the full project (so you see all errors), but restricts the `<files>` context to only what git reports as modified. The LLM sees the linter errors and the relevant source — nothing more.

### Spec-driven development loop

Use DumpCode to maintain a living `PLAN.md` that drives development:

**Step 1 — Create the spec:**
```bash
dumpcode --architect -q "Create a specification for a plugin system."
# Copy the LLM's response
```

**Step 2 — Save it:**
```bash
# Paste the Markdown and press Ctrl+D
dumpcode --new-plan -
```

**Step 3 — Check what's next:**
```bash
dumpcode --plan-next
```

**Step 4 — Implement, then repeat from Step 3.**

`--plan-next` marks finished tasks, defines the next milestone, and stops cleanly when the project is complete.

### Ask a one-off question

Use `-q` to append a custom task without defining a profile:

```bash
dumpcode -q "Why does the DumpSession class maintain both tree_entries and files_to_dump?"
dumpcode --changed -q "Does my change introduce any race conditions?"
```

### Limit scope with depth

For large monorepos where you only want to see the top-level structure:

```bash
dumpcode -L 2 --structure-only
```

### Modify the config via LLM

If you want to add or change a profile but aren't sure of the JSON syntax:

```bash
dumpcode --change-profile "Add a profile called 'api-docs' that generates OpenAPI documentation"
```

This generates a prompt explaining the current config schema and your instruction. Send it to an LLM and paste the result into `.dump_config.json`.

---

## License

MIT — Copyright © Florent Lejoly
