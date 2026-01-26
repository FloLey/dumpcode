# DumpCode

**DumpCode** is a semantic codebase dumper designed to prepare code for Large Language Models (LLMs). Unlike simple concatenation tools, DumpCode treats your codebase as a structured dataset, wrapping it in XML and sandwiching it between context-aware prompt templates.

## Key Features

*   **The "Prompt Sandwich" Architecture**: Automatically structures output as: `[Role Instructions]` + `[Code Context]` + `[Specific Task]`.
*   **Semantic XML Output**: Wraps code in `<tree>`, `<file>`, and `<dump>` tags to help LLMs distinguish between file paths, directory structures, and file contents.
*   **Native Git Integration**:
    *   **Exclusion**: Uses `pathspec` to parse `.gitignore` files exactly as Git does (handling negations and nested rules).
    *   **Detection**: Can limit dumps to only files that are modified or untracked (`--changed`).
*   **Smart Content Processing**:
    *   **Binary Detection**: Scans file headers (shebangs/null bytes) to skip binaries like images or compiled code.
    *   **Data Truncation**: Automatically detects large data files (`.csv`, `.jsonl`, `.log`) and truncates them to the first 5 lines to preserve context window.
    *   **Encoding Heuristics**: Robustly handles UTF-8, UTF-8-SIG (BOM), Latin-1, and CP1252.
*   **Dynamic Profiles**: Switch between different LLM personas (Architect, Technical Writer, QA) via CLI flags.
*   **Meta-Configuration**: A self-modifying mode that generates prompts to help you update the DumpCode configuration itself.
*   **OSC 52 Clipboard**: Pushes the generated dump directly to your local system clipboard, even over SSH.

---

## The "Sandwich" Architecture & Templating

DumpCode does not use a traditional templating engine. Instead, the `DumpEngine` constructs a specific, logical flow designed to prime an LLM effectively.

When you run `dumpcode --profile-name`, the engine assembles the output in three distinct layers:

### 1. The Top Bun (Instructions)
**Source:** `profile["pre"]` in `.dump_config.json`
**Tag:** `<instructions>`
This section sets the persona and rules for the LLM *before* it sees any code. This prevents the model from hallucinating or answering before reading the context.

### 2. The Meat (The Dump)
**Source:** The actual file system scan.
**Tag:** `<dump>`
This contains the directory tree and the file contents.

### 3. The Bottom Bun (The Task)
**Source:** `profile["post"]` OR CLI argument `-q "Question"`
**Tag:** `<task>`
This is the trigger. After processing the context, what should the LLM *do*?
*Note: If you provide a question via `-q`, it overrides the profile's default post-prompt.*

### Example Output
```xml
<instructions>
Act as a Senior Technical Writer...
</instructions>

<dump version="4">
  <tree>
    Project Root: /home/dev/project
    project/
    ├── src/
    │   └── main.py
    └── pyproject.toml
  </tree>
  <files>
    <file path="src/main.py">
def main(): print("Hello")
    </file>
  </files>
</dump>

<task>
Output the result in raw Markdown...
</task>
```

---

## Configuration & Profiles

DumpCode relies on a `.dump_config.json` file in your project root. Run `dumpcode --init` to create it interactively.

### Exclusion Logic (How it works)
DumpCode employs a **Union Strategy** for exclusions. A file is skipped if it matches ANY of the following:

1.  **Hardcoded Safety**: The system prevents scanning the config file itself or the output file.
2.  **Config Patterns**: Matches found in the `ignore_patterns` JSON list.
3.  **Gitignore**: The engine looks for a `.gitignore` file in the root and parses it using `pathspec` (native Git logic).

---

## Meta-Configuration (Profile Creator)

Creating, changing, or adding rules to complex JSON profiles manually is tedious. DumpCode includes a **Meta Mode** (`--change-profile`) to automate this.

**Scenario:** You want to add a profile for security auditing.

**Command:**
```bash
dumpcode --change-profile "Add a 'security' profile that looks for vulnerabilities and hardcoded secrets."
```

**Result:**
DumpCode generates a prompt containing your current config and your instruction, then copies it to the clipboard. You paste this into an LLM, and it returns the valid JSON update for your config.

---

## Project Management Workflow (`PLAN.md`)

DumpCode includes a specific workflow for maintaining a `PLAN.md` file using the `--new-plan` argument. This allows you to pipe LLM output directly back into your project roadmap.

**1. Generate the Plan:**
```bash
# Dump code with the architect profile to your clipboard
dumpcode --architect -q
```

**2. Update the Plan:**
Paste the dump into your LLM. Discuss with the LLM and produce a new Markdown plan. Copy that response.

**3. Save the Plan:**
Paste the content directly into `PLAN.md` using the paste mode:
```bash
# Opens stdin, paste your content, then hit Ctrl+D
dumpcode --new-plan -
```

Or update from a file:
```bash
dumpcode --new-plan /path/to/new_plan.md
```

---

## Installation

### From Source
```bash
git clone https://github.com/FloLey/dumpcode.git
cd dumpcode
pip install .
```

### Requirements
*   **Python 3.9+**
*   `pathspec`: For gitignore parsing.
*   `tiktoken` (Optional): For precise OpenAI token counting. (Install via `pip install .[token-counting]`)

### Development
For development and testing, install with dev dependencies:
```bash
pip install -e ".[token-counting,dev]"
```

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

## CLI Options

| Flag | Function |
| :--- | :--- |
| **Scanning** | |
| `startpath` | The root directory to scan (default: current dir). |
| `-L`, `--level` | Max recursion depth for the directory tree. |
| `--changed` | Only include files modified/untracked in Git. |
| `-d`, `--dir-only` | Scan directories only (no files). |
| `--structure-only` | Show the tree, but omit file contents. |
| `--ignore-errors` | specific encoding errors are skipped (files logged as skipped). |
| **Output** | |
| `-o`, `--output-file` | Target file (default: `codebase_dump.txt`). |
| `--no-copy` | Disable OSC 52 clipboard copying. |
| `--no-xml` | Use plain text delimiters instead of XML tags. |
| `--reset-version` | Reset the config version counter to 1. |
| **Meta / Profiles** | |
| `--init` | Interactive wizard to generate `.dump_config.json`. |
| `--new-plan [file\|-]`| Update `PLAN.md` from a file or stdin (`-`). |
| `--change-profile` | Generate a prompt to modify the config file. |
| `-q`, `--question` | Override the profile's `post` instruction. |

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
- Minimum 85% coverage requirement
- HTML coverage reports uploaded as artifacts
- Linting with ruff and type checking with mypy

## License

**MIT License**
Copyright © Florent Lejoly