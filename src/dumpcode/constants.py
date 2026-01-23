"""Constants for the DumpCode application."""

# --- Constants ---
PREFIX_MIDDLE = "├── "
PREFIX_LAST = "└── "
PREFIX_PASS = "│   "
PREFIX_EMPTY = "    "

# Config file
CONFIG_FILENAME = ".dump_config.json"

DEFAULT_PROFILES = {
    "readme": {
        "description": "Generate or Update README.md based on actual code logic",
        "pre": "Act as a Senior Technical Writer. Analyze the codebase structure and logic to write a comprehensive README.md.\n\nYour goal is to accurately document:\n1. The Project Title & Description (One-liner).\n2. Key Features (Derived from actual function/class capabilities).\n3. Installation Instructions (Detect requirements.txt, pyproject.toml, etc).\n4. Usage Examples (Based on CLI arguments or main entry points).\n5. Configuration Options (Explain .dump_config.json structure).\n\nDo not hallucinate features. Only document what is present in the code.",
        "post": "Output the result in raw Markdown format suitable for direct copy-pasting into README.md."
    },
    "cleanup": {
        "description": "Clean code: formatting, docstrings, unused imports",
        "pre": "Act as a Senior Python Developer and Code Reviewer. Your task is to perform a 'Spring Cleaning' on the codebase.\n\nFocus strictly on:\n1. Removing unused imports.\n2. Removing commented-out code (dead code).\n3. Removing trivial comments (e.g., '# increments i').\n4. Adding or fixing PEP 257 docstrings for all modules, classes, and functions.\n5. Enforcing PEP 8 styling (naming conventions, layout).\n\nCRITICAL: Do not change the logic or behavior of the code. Only improve readability and maintainability.",
        "post": "Provide the refactored code files in full. If a file requires no changes, state 'No changes needed for [filename]'."
    },
    "optimize": {
        "description": "Identify bottlenecks and suggest performance improvements",
        "pre": "Act as a Lead Performance Engineer. Analyze the provided codebase for performance bottlenecks.\n\nLook for:\n1. Algorithmic inefficiencies (High Big-O complexity).\n2. I/O bottlenecks (File operations, Network calls).\n3. Memory leaks or excessive memory usage.\n4. Inefficient string concatenations or loop logic.\n\nFor every issue found, explain *why* it is slow.",
        "post": "Output a numbered list of optimizations ordered by impact (High/Medium/Low). Follow each point with a specific code snippet showing the optimized implementation."
    },
    "plan": {
        "description": "Create or Update PLAN.md (Project Roadmap & Spec)",
        "pre": "Act as a Product Manager and Software Architect. Analyze the current state of the codebase to create a master specification file named 'PLAN.md'.\n\nThis file should serve as the source of truth for the project. Include:\n1. **Current Status**: What is currently implemented and working?\n2. **Architecture**: High-level overview of how modules interact.\n3. **Roadmap**: A logical step-by-step plan for future development.\n4. **Missing Features**: Gaps between the implied goal and current code.\n5. **Tech Debt**: Areas that need refactoring (identified from the code).",
        "post": "Output the content in Markdown format. This will be saved as PLAN.md and used as context for future prompts."
    }
}