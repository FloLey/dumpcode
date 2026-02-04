# DumpCode: The Semantic Context Engine for LLM-Native Development

**A professional-grade codebase dumper that transforms your project into structured, LLM-ready prompts. DumpCode treats your code as a semantic hierarchy, wrapping it in XML and grounding it via a "Sandwich Architecture" to maximize the reasoning capabilities of Large Language Models.**

---

## 🧠 The Philosophy: Why the Sandwich Architecture Exists

Large Language Models excel at reasoning when given **clear boundaries between instructions, data, and tasks**. DumpCode enforces a three-layer "Sandwich Architecture" that prevents context drift and hallucinations by establishing a strict logical flow:

### Layer 1: The Instructions (`<instructions>`)
**The Top Bun** - Sets the persona and architectural rules *before* the model sees any code.
*   **Role Definition:** e.g., "Act as a Senior Technical Writer and System Architect."
*   **Rules of Engagement:** e.g., "A README is not just a CLI reference; it is the project's manifesto."

### Layer 2: The Context (`<dump>`)
**The Filling** - A semantic XML representation of your entire project.
*   **Visual Tree Structure (`<tree>`):** ASCII directory hierarchy showing project organization.
*   **File Contents (`<files>`):** Source code wrapped in semantic tags.
*   **Execution Diagnostics (`<execution>`):** Live output from linters, test suites, or shell commands.

### Layer 3: The Task (`<task>`)
**The Bottom Bun** - The specific trigger or question placed *after* full context is loaded.
*   **The Ask:** e.g., "Generate a README.md."
*   **Why last?** By placing the request at the very end, we ensure the LLM has fully parsed the codebase context before attempting a response.

---

## 🤖 AI Agents: Your Virtual Engineering Team

DumpCode comes with a suite of pre-configured profiles defined in `.dump_config.json`. Each profile adjusts the "Sandwich" to change the LLM's persona and goals.

| Profile Flag | Role | Primary Function |
| :--- | :--- | :--- |
| `--architect` | System Designer | Creates a master `PLAN.md` specification. |
| `--plan-next` | Project Manager | Syncs code with `PLAN.md` and defines the next task. |
| `--readme` | Technical Writer | Generates professional, architect-level documentation. |
| `--cleanup` | Code Reviewer | Runs `ruff`/`mypy` and asks the LLM to fix errors. |
| `--test-fixer` | QA Engineer | Runs `pytest`, ingests failures, and plans repairs. |
| `--refactor` | Senior Dev | Identifies SOLID violations and "code smells." |
| `--optimize` | Perf Engineer | Locates algorithmic inefficiencies and bottlenecks. |
| `--coverage` | SDET | Runs coverage reports and identifies untested logic. |

## 📝 Creating Custom Profiles

Profiles are defined in `.dump_config.json` and automatically become CLI flags.

### Adding a New Profile

1. **Edit `.dump_config.json`** in your project root
2. **Add your profile** under the `"profiles"` key:

```json
{
  "profiles": {
    "security-audit": {
      "description": "Security vulnerability scanner",
      "pre": [
        "Act as a Security Engineer.",
        "Analyze the code for common vulnerabilities (SQL injection, XSS, etc.)"
      ],
      "post": "List all security issues by severity (Critical/High/Medium/Low).",
      "run_commands": ["bandit -r src/"],
      "model": "claude-3-5-sonnet-latest",
      "auto_send": true
    }
  }
}
```

3. **Use it immediately:**
```bash
dumpcode --security-audit
```

### Profile Configuration Fields

| Field | Required | Type | Description |
|:------|:---------|:-----|:------------|
| `description` | No | String | Help text shown in `--help` |
| `pre` | No | String or List | Instructions placed before code context |
| `post` | No | String or List | Task placed after code context |
| `run_commands` | No | List | Shell commands to execute (output captured in `<execution>`) |
| `model` | No | String | AI model to use (e.g., `claude-3-5-sonnet-latest`) |
| `auto_send` | No | Boolean | If `true`, automatically sends to AI after generation |

**Note:** Profile names with underscores (`my_profile`) become flags with hyphens (`--my-profile`).

---

## 🔄 The Workflow: Spec-Driven Development Lifecycle

DumpCode is designed to facilitate a "Dump → Discuss → Plan → Implement" loop, keeping your project's `PLAN.md` as the single source of truth.

### Phase 1: Blueprinting (`--architect`)
Generate a comprehensive project roadmap by dumping your current state with the architect persona.

```bash
dumpcode --architect -q "Create a master specification for a new plugin system."
```

### Phase 2: The Plan Sync (`--new-plan`)
Once the LLM provides a roadmap, pipe it directly back into your repository using the safe, interactive "Paste Mode":

```bash
# Paste the LLM's Markdown, then hit Ctrl+D to save
dumpcode --new-plan -
```

### Phase 3: Task Planning (`--plan-next`)
The LLM compares your code against `PLAN.md`, marks completed tasks, and defines **exactly one** next milestone with technical specs.

```bash
dumpcode --plan-next
```

### Phase 4: Focused QA & Implementation (`--changed`)
**Don't waste tokens.** When fixing bugs or polishing code, you rarely need the entire codebase. Use `--changed` to dump only the files you have modified in Git (staged or unstaged) combined with other profiles.

This is particularly powerful for the cleanup workflow:

```bash
# Run linters and fix ONLY the files you just touched
dumpcode --changed --cleanup
```

**Why this works:**
1.  DumpCode runs the linters (e.g., `ruff check .`) to capture all errors.
2.  It restricts the file context (`<files>`) to only what you modified.
3.  The LLM receives the linter errors for your changes + the source code for your changes.
4.  The LLM generates a focused fix without being distracted by legacy code issues.

### Phase 5: Deep Diagnosis (`--test-fixer`)
For more complex issues, run the test suite and let the LLM analyze the failures:

```bash
# Run tests and plan fixes for failures
dumpcode --test-fixer
```

---

## 🤖 AI Integration (Auto-Mode)

DumpCode includes built-in AI integration that can automatically send generated prompts to AI models and **stream their responses directly to your terminal**.

### Supported Providers
*   **Claude (Anthropic):** `claude-sonnet-4-5-20250929`, `claude-opus...`
*   **Gemini (Google):** `gemini-3-flash`, `gemini-2.5-pro`
*   **GPT (OpenAI):** `gpt-5.2`, `gpt-4o`, `o1`, `o3`
*   **DeepSeek:** `deepseek-chat`, `deepseek-reasoner`

### Usage Examples

```bash
# Auto-send with default model defined in profile
dumpcode --cleanup --auto

# Override model for this run
dumpcode --readme --auto --model gemini-3-flash

# Disable auto mode for a profile that has it enabled
dumpcode --ai-review --no-auto
```

### Diagnostic Tools
Test connectivity to all configured providers:
```bash
dumpcode --test-models
```

---

## 🛠 Technical Feature Highlights

### Smart Content Handling
*   **Truncation:** High-volume files (`.csv`, `.jsonl`, `.log`) are automatically truncated (e.g., first 5-10 lines) to prevent context window saturation.
*   **Binary Detection:** Heuristic scanning (null-byte detection and extension checking) skips compiled objects, images, and non-text assets.
*   **Encoding Resilience:** Heuristic detection of UTF-8, UTF-16, and Latin-1.

### Environment Awareness
*   **OSC52 Clipboard:** Pushes the dump directly to your local clipboard via ANSI escape sequences. This works flawlessly over SSH, inside Docker, or in remote dev containers.
*   **Git-Native Logic:** Leverages `pathspec` to respect `.gitignore` rules exactly as Git does, including complex negations and nested patterns.
*   **Token Safety:** Warns at 500k tokens and refuses at 900k tokens to prevent accidental high costs.

---

## ⚙️ Installation & Configuration

### Installation

#### From GitHub (Recommended)
```bash
# Basic installation
pip install git+https://github.com/FloLey/dumpcode.git

# With AI support (all providers)
pip install "git+https://github.com/FloLey/dumpcode.git#egg=dumpcode[ai]"

# With specific AI providers
pip install "git+https://github.com/FloLey/dumpcode.git#egg=dumpcode[claude]"      # Anthropic
pip install "git+https://github.com/FloLey/dumpcode.git#egg=dumpcode[gemini]"      # Google
pip install "git+https://github.com/FloLey/dumpcode.git#egg=dumpcode[openai]"      # OpenAI
pip install "git+https://github.com/FloLey/dumpcode.git#egg=dumpcode[deepseek]"    # DeepSeek
```

#### From Source (Development)
```bash
# Clone the repository
git clone https://github.com/FloLey/dumpcode.git
cd dumpcode

# Install in development mode
pip install -e .

# Or with AI support
pip install -e ".[ai]"
```

### Configuration Setup

Initialize your project-specific configuration:
```bash
dumpcode --init
```

Create a `.env` file for your API keys:
```bash
ANTHROPIC_API_KEY=sk-ant-xxxxx
GOOGLE_API_KEY=AIzaSyxxxxx
OPENAI_API_KEY=sk-xxxxx
DEEPSEEK_API_KEY=sk-xxxxx
```

## 📋 Configuration Reference

### File Location
DumpCode looks for `.dump_config.json` in your project root. If it doesn't exist, running `dumpcode --init` will create it interactively.

### Schema

#### `version` (Integer)
Auto-increments after each successful dump. Used to track iteration count in the output header. Reset with `--reset-version`.

#### `ignore_patterns` (Array of Strings)
Glob patterns to exclude from dumps. These are **merged** with your `.gitignore` (if present). Supports:
- Wildcards: `*.pyc`, `*.log`
- Directories: `node_modules/`, `venv/`
- Paths: `src/tests/*.py`

**Note:** `.dump_config.json` itself is always excluded.

#### `use_xml` (Boolean)
Controls semantic XML wrapping. **Strongly recommended** to keep as `true` for LLM prompts. Disable only if piping output to non-LLM text processors.

#### `profiles` (Object)
See [Creating Custom Profiles](#-creating-custom-profiles) above.

### Example Configuration

```json
{
  "version": 1,
  "ignore_patterns": [".git", "__pycache__", "node_modules"],
  "profiles": {
    "custom-agent": {
      "description": "Your custom profile",
      "pre": ["Act as a Rust Expert.", "Analyze memory safety."],
      "post": "Suggest refactoring for the borrow checker.",
      "run_commands": ["cargo check"],
      "model": "claude-3-5-sonnet-latest",
      "auto_send": true
    }
  },
  "use_xml": true
}
```

---

## ⌨️ CLI Reference

| Flag | Category | Description |
| :--- | :--- | :--- |
| `dumpcode` | Basic | Dump current directory to clipboard. |
| `--init` | Setup | Initialize project config. |
| `--changed` | Scanning | Only dump git-modified/untracked files. |
| `-L [N]` | Scanning | Limit tree depth to N levels. |
| `--structure-only` | Scanning | Show tree but omit file contents. |
| `-o [file]` | Output | Set output filename (default: `codebase_dump.txt`). |
| `--no-copy` | Output | Disable OSC52 clipboard copy. |
| `--new-plan` | Meta | Update `PLAN.md` from stdin. |
| `--change-profile` | Meta | Generate prompt to modify `.dump_config.json`. |
| `--auto` | AI | Force auto-send to AI. |
| `--model [ID]` | AI | Override AI model for this run. |

---

## 🧪 How DumpCode Was Built (Recursive Self-Improvement)

DumpCode was created using the exact workflow it implements—a recursive loop where the tool improved itself by being used on its own codebase.

1.  **Initial Problem:** I needed a way to paste code into Gemini reliably, and I was using variations of the same prompts over and over again.
2.  **The Sandwich:** I realized LLMs hallucinate less when instructions come *before* code and tasks come *after*.
3.  **Self-Refinement:** Every feature (Git integration, XML tags, Auto-Mode) was added because I needed it while using DumpCode to build DumpCode.

This recursive pattern created a virtuous cycle: DumpCode demonstrates its own value by being the primary tool used to build itself.

### License
**MIT License** - Copyright © Florent Lejoly