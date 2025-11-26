# CodeSplain

**Understand any codebase in minutes, not hours.**

CodeSplain is a local static analyzer that generates clear summaries, dependency graphs, call hierarchies, and API documentation for **Python, JavaScript, TypeScript, and React** projects. No cloud, no guessing, no digging through files.

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

## Supported Languages & Frameworks

✅ **Python** - FastAPI, Flask, Django, CLI tools  
✅ **JavaScript** - Node.js, Express, vanilla JS  
✅ **TypeScript** - Full TypeScript support  
✅ **React** - Components, hooks, context  
✅ **Vue** - Single-file components  
✅ **Next.js** - Full-stack React applications  
✅ **NestJS** - TypeScript backend framework  
✅ **Angular** - Angular applications

---

## What It Generates

| File                  | Purpose                                                      |
| --------------------- | ------------------------------------------------------------ |
| `OVERVIEW.md`         | Summary of project type, languages, frameworks, entry points |
| `STRUCTURE.md`        | Directory tree and purpose of each file                      |
| `DEPENDENCIES.md`     | Internal and external imports, dependency graphs             |
| `CALL_GRAPH.md`       | Function usage and call hierarchies                          |
| `API_SURFACE.md`      | API endpoints, React/Vue components, public classes          |
| `modules/`            | File-by-file breakdowns                                      |
| `prompts/` (optional) | Pre-made LLM prompts for further insight                     |

---

## Features

* **Multi-language support** - Python, JavaScript, TypeScript, React, Vue
* **Framework detection** - Automatically identifies React, Vue, Angular, Express, FastAPI, etc.
* **Component analysis** - Extracts React/Vue components and their structure
* **API endpoint detection** - Finds REST endpoints from decorators and routes
* **Dependency mapping** - Maps internal/external dependencies across languages
* **Entry point identification** - Finds main files and application entry points
* **Smart filtering** - Skips tests, build artifacts, node_modules, etc.

---

## Example Use Cases

* Quickly understand unfamiliar codebases (any language)
* Prep for code reviews or architecture audits
* Help onboard new developers
* Migrate from JavaScript to TypeScript
* Understand React component hierarchies
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

**Clone & Run**

```bash
git clone https://github.com/YedTheEmo/codesplain.git
cd codesplain

# Install optional JavaScript parser (recommended for better JS/TS analysis)
pip install esprima

# Analyze any project
python codesplain.py /path/to/project
```

**Requirements:**
- Python 3.7+
- `esprima` (optional, for enhanced JavaScript/TypeScript parsing)

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

1. **Language Detection** - Scans for Python, JavaScript, TypeScript, React, Vue files
2. **Framework Identification** - Detects React, Vue, Express, FastAPI, Django, etc.
3. **AST Parsing** - Uses `ast` for Python, `esprima` for JavaScript (with regex fallback)
4. **Relationship Mapping** - Maps imports, components, functions, and API endpoints
5. **Smart Categorization** - Categorizes files by purpose and complexity
6. **Documentation Generation** - Outputs clean, structured Markdown

---

## Project Type Detection

CodeSplain automatically identifies:

- **Frontend:** React, Vue, Angular apps
- **Backend:** Express, NestJS, FastAPI, Flask, Django
- **Full-Stack:** Next.js, Nuxt applications
- **Mobile:** React Native apps
- **Desktop:** Electron apps
- **CLI Tools:** Command-line applications
- **Libraries:** Reusable packages

---
**Understand codebases fast. Multiple languages. Save hours.**

