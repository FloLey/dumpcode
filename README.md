# DumpCode: The Semantic Context Engine for LLM-Native Development

DumpCode is a professional-grade codebase dumper that transforms your project into a structured, LLM-ready dataset. Unlike simple concatenation scripts, DumpCode treats your code as a semantic hierarchy, wrapping it in XML and grounding it via a Sandwich Architecture to maximize the reasoning capabilities of Large Language Models.

## 🧠 The Philosophy: The Prompt Sandwich

Large Language Models (LLMs) perform best when instructions are clearly separated from data. DumpCode enforces a "Sandwich Architecture" that structures every output into three logical layers to prevent context drifting and hallucinations:

**The Instructions (`<instructions>`):** Sets the persona (e.g., Senior Architect) and the architectural rules before the model sees a single line of code.

**The Context (`<dump>`):** A semantic XML representation of your project, including a visual directory tree, file contents, and execution diagnostics (linter/test outputs).

**The Task (`<task>`):** The specific trigger or question. By placing the "Ask" at the very end, we ensure the LLM has parsed the entire context before attempting a response.

---

## 🤖 Included Profiles: Your Virtual Engineering Team

DumpCode comes with a suite of pre-configured "AI Agents" defined in `.dump_config.json`. Each profile changes the "Buns" of the sandwich to change the LLM's persona and goals.

| Profile Flag | Role | Primary Function |
| :--- | :--- | :--- |
| `--readme` | Technical Writer | Generates professional, architect-level documentation. |
| `--architect` | System Designer | Analyzes code to generate a master `PLAN.md` specification. |
| `--plan-next` | Project Manager | Syncs current code state with `PLAN.md` and defines the next task. |
| `--cleanup` | Code Reviewer | Runs `ruff` and `mypy`, then asks the LLM to fix the reported errors. |
| `--test-fixer` | QA Engineer | Runs `pytest`, ingests failures, and plans specific code repairs. |
| `--refactor` | Senior Dev | Identifies SOLID violations and structural "code smells." |
| `--optimize` | Perf Engineer | Locates algorithmic inefficiencies and I/O bottlenecks. |
| `--coverage` | SDET | Runs coverage reports and identifies untested critical logic paths. |

---


## 🔄 The Workflow: Spec-Driven Iteration

DumpCode is designed to facilitate a "Dump → Discuss → Plan → Implement" loop, keeping your project's `PLAN.md` as the single source of truth.

### 1. The Blueprinting Phase
Generate a comprehensive project roadmap by dumping your current state with the architect persona:

```bash
dumpcode --architect -q "Create a master specification for a new plugin system."
```

### 2. The Plan Sync (`--new-plan`)
Once the LLM provides a roadmap, pipe it directly back into your repository. Use the `-` argument for a safe, interactive "Paste Mode":

```bash
# This opens a buffer; paste the LLM's Markdown and hit Ctrl+D
dumpcode --new-plan -
```

### 3. Focused Implementation (`--changed`)
Don't waste tokens. Once you start coding, dump only the files you've modified in Git to provide the LLM with the specific "delta" context it needs:

```bash
dumpcode --changed --plan-next
```

---

## 🛠 Technical Feature Highlights

**Smart Content Handling:**
- **Truncation:** High-volume files (`.csv`, `.jsonl`, `.log`) are automatically truncated (e.g., first 5-10 lines) to prevent context window saturation.
- **Binary Detection:** Heuristic scanning (null-byte detection and extension checking) skips compiled objects, images, and non-text assets.
- **Encoding Resilience:** Heuristic detection of UTF-8, UTF-16, and Latin-1.

**Environment Awareness:**
- **OSC52 Clipboard:** Pushes the dump directly to your local clipboard via terminal escape sequences. This works flawlessly over SSH, inside Docker, or in remote dev containers.
- **Git-Native Logic:** Leverages `pathspec` to respect `.gitignore` rules exactly as Git does, including complex negations and nested patterns.
- **Diagnostic Integration:** The `cleanup` and `test-fixer` profiles execute shell commands (linters/test suites) and wrap the results in `<execution>` tags so the LLM can "see" the errors.
- **Meta-Configuration:** Use `--change-profile` to generate a prompt that helps you rewrite the tool's own `.dump_config.json` file.
- **Comprehensive Testing:** Maintains 95%+ test coverage with robust CI/CD pipeline.

## ⚙️ Configuration & Installation

### Requirements
- **Python 3.9+**
- `pathspec` (Included)
- `tiktoken` (Optional, for precise OpenAI token counting)

### Installation
```bash
pip install .
# Or with dev/token tools:
pip install ".[token-counting,dev]"
```

### Setup
Initialize your project-specific configuration:
```bash
dumpcode --init
```

### Configuration Schema (`.dump_config.json`)

The configuration file defines how DumpCode processes your project and what profiles are available. Here's the complete schema:

```json
{
  "version": 2,
  "ignore_patterns": [
    ".dump_config.json",
    ".git",
    "__pycache__",
    "*.pyc",
    "venv",
    ".env",
    ".DS_Store",
    "codebase_dump.txt",
    ".claude",
    ".pytest_cache",
    "*.egg-info",
    ".github",
    "dist",
    "LICENSE",
    ".gitignore",
    ".mypy_cache",
    ".ruff_cache"
  ],
  "profiles": {
    "profile-name": {
      "description": "Human-readable description of the profile",
      "pre": [
        "Instruction lines for the LLM",
        "These appear in the <instructions> tag",
        "Define the persona and rules before the model sees code"
      ],
      "post": "The task/question that appears in the <task> tag",
      "run_commands": [
        "optional shell commands to run",
        "output appears in <execution> tags",
        "e.g., ruff check . --output-format=full"
      ]
    }
  },
  "use_xml": true
}
```

**Key Fields:**
- `version`: Auto-incremented with each config change (used for tracking iterations)
- `ignore_patterns`: List of glob patterns to exclude from dumps (union with `.gitignore`)
- `profiles`: Dictionary of named profiles that define LLM personas and tasks
- `use_xml`: Boolean to toggle between XML tags (`<dump>`) or plain text delimiters

**Profile Structure:**
- `description`: Brief explanation shown in CLI help
- `pre`: Array of strings forming the `<instructions>` section (sets LLM persona)
- `post`: String forming the `<task>` section (the specific ask/trigger)
- `run_commands`: Optional array of shell commands to execute (output in `<execution>`)

**Meta-Configuration:** Use `dumpcode --change-profile "description of new profile"` to generate a prompt that helps you modify the config via an LLM.

---

## Usage Examples

### 1. The "Snapshot" (Standard Dump)
Dump everything to `codebase_dump.txt` and copy to clipboard.
```bash
dumpcode
```

### 2. The "Planner" (Using a Profile)
Use the `architect` profile to generate a project plan.
```bash
dumpcode --architect
```

### 3. The "Focus" (Profile + Specific Question)
Use the `cleanup` profile, but override the final task.
```bash
dumpcode --cleanup -q "Focus strictly on 'utils.py'. Do not touch main.py."
```

### 4. Git-Delta Dump
Only dump files that you have modified (staged or unstaged) or untracked files.
```bash
dumpcode --changed --readme
```

### 5. Structure Only
Dump only the tree view (no file contents) to map the project.
```bash
dumpcode --structure-only
```

---

## ⌨️ CLI Reference

| Flag | Category | Description |
| :--- | :--- | :--- |
| `startpath` | Scanning | Root directory to scan (default: `.`). |
| `-L`, `--level` | Scanning | Max recursion depth for the directory tree. |
| `--changed` | Scanning | Only include files modified/untracked in Git. |
| `--structure-only` | Scanning | Output the visual tree, but omit file contents. |
| `-o [file]` | Output | Target output file (default: `codebase_dump.txt`). |
| `--no-copy` | Output | Disable the automatic OSC52 clipboard copy. |
| `--no-xml` | Output | Use plain text delimiters instead of semantic XML. |
| `-q [query]` | Meta | Override a profile's task with a specific question. |
| `--new-plan [file\|-]` | Meta | Update `PLAN.md` from a file or stdin. |
| `--change-profile` | Meta | Generate a prompt to modify your `.dump_config.json`. |

## How DumpCode Was Built (Using DumpCode)

In the beginning, I needed a simple "dump tool" for one reason: reliably pasting a whole codebase into Gemini to start (or restart) a focused discussion about the project. That "dump step" kept coming back, every time.

DumpCode was created to make that workflow fast, repeatable, and less mentally taxing — with prompts ready instantly, and easy to evolve over time.

### My typical workflow

1. **Dump the codebase into the LLM**
   - Run `dumpcode` (often with a profile like `--readme`, `--cleanup`, or `--architect`)
   - Paste the output into Gemini (or another LLM)

2. **Force shared understanding before writing code**
   - Ask the model to **explain the codebase**, modules, and flows in detail
   - Describe the feature I want to add, plus any constraints/edge-cases I can think of
   - Ask the model to **explain the idea back to me** *without coding yet*
   - Ask whether clarifications are needed
   - Iterate until we clearly match on intent (this can take time, and that's normal)

3. **Turn the idea into an implementation plan**
   - Ask the model to break the work into **steps**
   - For each step, ask it to produce a **developer spec** explaining:
     - what to change
     - where in the codebase
     - why the change is needed
     - what "done" looks like (tests / acceptance criteria)

4. **Execute in an implementation environment**
   - Take the step specs and implement them (often using Claude Code)
   - Re-run `dumpcode` and repeat the loop when needed (variants of the same flow)

### Why DumpCode exists

DumpCode isn't just "concat files into a text blob". The point is to make iteration easy:

- **The prompt sandwich** keeps instructions + code context + task consistently ordered.
- **Profiles in `.dump_config.json`** make it quick to reuse and refine prompt rules.
- **Auto-versioning** helps track iterations as the project evolves.

In practice: DumpCode made it effortless to restart high-quality conversations about the code — and to update the prompt rules quickly as the project (and my needs) changed.

### The Self-Improvement Loop

DumpCode's development followed this same recursive pattern:
1. **Initial Prototype**: Built as a simple Python script using the workflow above
2. **Self-Referential Development**: Each new feature was spec'd by using DumpCode to dump the DumpCode codebase
3. **Profile Evolution**: Default profiles were refined through actual use on real projects
4. **Meta-Configuration**: The `--change-profile` feature emerged from needing to update prompts without manual JSON editing

This created a virtuous cycle: DumpCode improved itself by being used on itself, demonstrating its own value in real-time.

## Testing & Coverage

### Running Tests
```bash
# Run all tests
pytest tests/

# Run tests with coverage report
pytest --cov=src/dumpcode --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=src/dumpcode --cov-report=html --cov-report=xml --cov-report=term-missing
```

### Coverage Reports
- **Terminal**: Shows missed lines with `--cov-report=term-missing`
- **HTML**: Detailed browser report at `htmlcov/index.html`
- **XML**: Machine-readable `coverage.xml` for CI tools

### CI/CD
GitHub Actions runs tests with coverage on every push and PR:
- Tests across Python 3.9-3.12
- Minimum 95% coverage requirement
- HTML coverage reports uploaded as artifacts
- Linting with ruff and type checking with mypy

## License

**MIT License**
Copyright © Florent Lejoly