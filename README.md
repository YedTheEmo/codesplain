# CodeSplain

**Understand any Python codebase in minutes, not hours.**

CodeSplain is a local static analyzer that generates clear summaries, dependency graphs, call hierarchies, and API documentation for Python projects. No cloud, no guessing, no digging through files.

---

## Quick Start

```bash
# Analyze current directory
python codesplain.py .

# Analyze a specific project
python codesplain.py /path/to/project

# Faster run, skip LLM prompt generation
python codesplain.py . --no-prompts
```

Results are saved in:
`codesplain_results/yourproject_YYYY-MM-DD_HH-MM/`

---

## What It Generates

| File                  | Purpose                                                      |
| --------------------- | ------------------------------------------------------------ |
| `OVERVIEW.md`         | Summary of project type, structure, entry points, complexity |
| `STRUCTURE.md`        | Directory tree and purpose of each file                      |
| `DEPENDENCIES.md`     | Internal and external imports, graphs                        |
| `CALL_GRAPH.md`       | Function usage and call hierarchies                          |
| `API_SURFACE.md`      | Public endpoints, methods, classes                           |
| `modules/`            | File-by-file breakdowns                                      |
| `prompts/` (optional) | Pre-made LLM prompts for further insight                     |

---

## Features

* Detects frameworks (Django, Flask, FastAPI, CLI, etc.)
* Identifies main files and entry points
* Maps internal/external dependencies
* Extracts REST endpoints from decorators
* Highlights complex files and functions
* Skips irrelevant files (tests, cache, migrations)

---

## Example Use Cases

* Quickly understand unfamiliar codebases
* Prep for code reviews or architecture audits
* Help onboard new developers
* Generate context for AI-assisted refactoring

---

## Output Structure

```
codesplain_results/
└── projectname_YYYY-MM-DD_HH-MM/
    ├── OVERVIEW.md
    ├── STRUCTURE.md
    ├── DEPENDENCIES.md
    ├── CALL_GRAPH.md
    ├── API_SURFACE.md
    ├── modules/
    └── prompts/
```

---

## Installation

**Clone**

```bash
git clone https://github.com/YedTheEmo/codesplain.git
cd codesplain
python codesplain.py /path/to/project
```

Requires: **Python 3.7+**

---

## Command-Line Options

```bash
python codesplain.py [path] [options]

Arguments:
  path                  Project path (default: current directory)

Options:
  -o, --output DIR      Set custom output directory
  --no-prompts          Skip LLM prompt generation
  -h, --help            Show help
```

---

## How It Works

1. Parses Python files using `ast`
2. Maps imports, function calls, and class usage
3. Detects frameworks and entry points
4. Categorizes files by purpose and complexity
5. Outputs clean Markdown documentation

---
**Understand codebases fast. Save hours.**

