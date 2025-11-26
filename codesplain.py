#!/usr/bin/env python3
"""
CodeSplain - Local Codebase Analyzer & Summarizer
Analyze Python, JavaScript, TypeScript, and React projects.
Generate comprehensive summaries, relationships, and call graphs.
"""

import os
import ast
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Optional, Any
import re

try:
    import esprima
    HAS_ESPRIMA = True
except ImportError:
    HAS_ESPRIMA = False

class CodeSplainAnalyzer:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self.project_name = self.project_path.name
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        self.output_dir = Path("codesplain_results") / f"{self.project_name}_{self.timestamp}"
        
        # Analysis storage
        self.files_data = {}  # file_path -> analysis data
        self.imports = defaultdict(set)  # file -> set of imports
        self.reverse_imports = defaultdict(set)  # imported_module -> set of files that import it
        self.function_calls = defaultdict(set)  # function -> set of callers
        self.classes = {}  # file -> list of classes
        self.functions = {}  # file -> list of functions
        self.api_endpoints = []  # detected API endpoints
        self.entry_points = []  # main files
        
        # Project metadata
        self.language_stats = defaultdict(int)
        self.primary_language = None
        self.project_type = None
        self.frameworks = set()
        self.package_manager = None
        
    def analyze_project(self):
        """Main analysis pipeline"""
        print(f"🔍 Analyzing {self.project_name}...")
        
        # Detect project type first
        self._detect_project_structure()
        
        # Find all relevant files based on detected languages
        all_files = self._collect_source_files()
        
        if not all_files:
            print("❌ No source files found!")
            return
        
        print(f"\n📊 Project Analysis:")
        print(f"   Primary Language: {self.primary_language}")
        print(f"   Project Type: {self.project_type}")
        if self.frameworks:
            print(f"   Frameworks: {', '.join(self.frameworks)}")
        if self.package_manager:
            print(f"   Package Manager: {self.package_manager}")
        
        print(f"\n📁 Files by Language:")
        for lang, count in sorted(self.language_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"   {lang}: {count} files")
        
        # Analyze each file
        for file_path in all_files:
            try:
                self._analyze_file(file_path)
            except Exception as e:
                print(f"Warning: Could not analyze {file_path}: {e}")
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate all analysis files
        self._generate_overview()
        self._generate_structure()
        self._generate_dependencies()
        self._generate_call_graph()
        self._generate_api_surface()
        self._generate_module_summaries()
        self._generate_prompts()
        
        print(f"✅ Analysis complete! Results saved to: {self.output_dir}")
        
    def _detect_project_structure(self):
        """Detect project type, languages, and frameworks"""
        # Check for package managers and config files
        if (self.project_path / "package.json").exists():
            self.package_manager = "npm/yarn"
            self._analyze_package_json()
        elif (self.project_path / "package-lock.json").exists():
            self.package_manager = "npm"
        elif (self.project_path / "yarn.lock").exists():
            self.package_manager = "yarn"
        elif (self.project_path / "pnpm-lock.yaml").exists():
            self.package_manager = "pnpm"
        
        if (self.project_path / "requirements.txt").exists() or (self.project_path / "setup.py").exists() or (self.project_path / "pyproject.toml").exists():
            self.package_manager = self.package_manager or "pip/poetry"
        
        # Detect TypeScript
        if (self.project_path / "tsconfig.json").exists():
            self.frameworks.add("TypeScript")
        
        # Count files by language
        for ext, lang in [
            ("*.py", "Python"),
            ("*.js", "JavaScript"),
            ("*.jsx", "JavaScript/React"),
            ("*.ts", "TypeScript"),
            ("*.tsx", "TypeScript/React"),
            ("*.vue", "Vue"),
            ("*.svelte", "Svelte")
        ]:
            files = list(self.project_path.rglob(ext))
            files = [f for f in files if not self._should_skip_file(f)]
            if files:
                self.language_stats[lang] = len(files)
        
        # Determine primary language
        if self.language_stats:
            self.primary_language = max(self.language_stats.items(), key=lambda x: x[1])[0]
        else:
            self.primary_language = "Unknown"
        
        # Detect frameworks from file structure
        if (self.project_path / "src" / "App.jsx").exists() or (self.project_path / "src" / "App.tsx").exists():
            self.frameworks.add("React")
        if (self.project_path / "angular.json").exists():
            self.frameworks.add("Angular")
        if (self.project_path / "nuxt.config.js").exists() or (self.project_path / "nuxt.config.ts").exists():
            self.frameworks.add("Nuxt")
        if (self.project_path / "next.config.js").exists() or (self.project_path / "next.config.ts").exists():
            self.frameworks.add("Next.js")
        if (self.project_path / "vite.config.js").exists() or (self.project_path / "vite.config.ts").exists():
            self.frameworks.add("Vite")
        if (self.project_path / "webpack.config.js").exists():
            self.frameworks.add("Webpack")
        if (self.project_path / "manage.py").exists():
            self.frameworks.add("Django")
        if any((self.project_path / f).exists() for f in ["app.py", "wsgi.py", "application.py"]):
            self.frameworks.add("Flask/FastAPI")
    
    def _analyze_package_json(self):
        """Extract framework info from package.json"""
        try:
            package_json = self.project_path / "package.json"
            with open(package_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
            
            # Detect frameworks
            if 'react' in deps:
                self.frameworks.add("React")
            if 'vue' in deps:
                self.frameworks.add("Vue")
            if 'angular' in deps or '@angular/core' in deps:
                self.frameworks.add("Angular")
            if 'next' in deps:
                self.frameworks.add("Next.js")
            if 'nuxt' in deps:
                self.frameworks.add("Nuxt")
            if 'svelte' in deps:
                self.frameworks.add("Svelte")
            if 'express' in deps:
                self.frameworks.add("Express")
            if 'fastify' in deps:
                self.frameworks.add("Fastify")
            if 'nestjs' in deps or '@nestjs/core' in deps:
                self.frameworks.add("NestJS")
            if 'vite' in deps:
                self.frameworks.add("Vite")
            if 'webpack' in deps:
                self.frameworks.add("Webpack")
            if 'gatsby' in deps:
                self.frameworks.add("Gatsby")
            
            # Determine project type
            if any(fw in self.frameworks for fw in ['React', 'Vue', 'Angular', 'Svelte']):
                self.project_type = "Frontend Web Application"
            elif any(fw in self.frameworks for fw in ['Express', 'Fastify', 'NestJS']):
                self.project_type = "Backend/API Server"
            elif 'Next.js' in self.frameworks or 'Nuxt' in self.frameworks:
                self.project_type = "Full-Stack Web Application"
            elif 'electron' in deps:
                self.project_type = "Desktop Application (Electron)"
            elif 'react-native' in deps:
                self.project_type = "Mobile Application (React Native)"
                
        except Exception as e:
            print(f"Warning: Could not parse package.json: {e}")
    
    def _collect_source_files(self):
        """Collect all relevant source files based on detected languages"""
        extensions = []
        
        # Add extensions based on detected languages
        if "Python" in self.language_stats:
            extensions.append("*.py")
        if any(lang in self.language_stats for lang in ["JavaScript", "JavaScript/React"]):
            extensions.extend(["*.js", "*.jsx", "*.mjs", "*.cjs"])
        if any(lang in self.language_stats for lang in ["TypeScript", "TypeScript/React"]):
            extensions.extend(["*.ts", "*.tsx"])
        if "Vue" in self.language_stats:
            extensions.append("*.vue")
        if "Svelte" in self.language_stats:
            extensions.append("*.svelte")
        
        # If no languages detected, scan for common extensions
        if not extensions:
            extensions = ["*.py", "*.js", "*.jsx", "*.ts", "*.tsx"]
        
        all_files = []
        for ext in extensions:
            files = list(self.project_path.rglob(ext))
            files = [f for f in files if not self._should_skip_file(f)]
            all_files.extend(files)
        
        return all_files
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Skip test files, migrations, cache, build artifacts, etc."""
        skip_patterns = [
            "__pycache__", ".pytest_cache", ".git", "node_modules",
            "venv", "env", ".env", "migrations", "test_", "_test",
            "tests.py", "conftest.py", ".spec.", ".test.",
            "dist", "build", "coverage", ".next", ".nuxt",
            "out", "bundle", ".cache", "vendor", "target"
        ]
        path_str = str(file_path).lower()
        return any(pattern in path_str for pattern in skip_patterns)
    
    def _analyze_file(self, file_path: Path):
        """Analyze a single source file based on its language"""
        relative_path = file_path.relative_to(self.project_path)
        file_ext = file_path.suffix.lower()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Initialize file data
            self.files_data[str(relative_path)] = {
                'path': relative_path,
                'lines': len(content.splitlines()),
                'classes': [],
                'functions': [],
                'imports': [],
                'components': [],  # React/Vue components
                'exports': [],     # JavaScript exports
                'docstring': '',
                'complexity': 0,
                'is_entry_point': False,
                'language': self._detect_file_language(file_ext)
            }
            
            # Route to appropriate analyzer based on file type
            if file_ext == '.py':
                self._analyze_python_file(file_path, content, str(relative_path))
            elif file_ext in ['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs']:
                self._analyze_javascript_file(file_path, content, str(relative_path))
            elif file_ext == '.vue':
                self._analyze_vue_file(file_path, content, str(relative_path))
            else:
                # Basic analysis for unknown types
                self.files_data[str(relative_path)]['docstring'] = "Unknown file type"
            
            if self.files_data[str(relative_path)]['is_entry_point']:
                self.entry_points.append(str(relative_path))
                
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
    
    def _detect_file_language(self, ext: str) -> str:
        """Detect language from file extension"""
        lang_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.jsx': 'JavaScript/React',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript/React',
            '.mjs': 'JavaScript (ESM)',
            '.cjs': 'JavaScript (CommonJS)',
            '.vue': 'Vue',
            '.svelte': 'Svelte'
        }
        return lang_map.get(ext, 'Unknown')
    
    def _analyze_python_file(self, file_path: Path, content: str, relative_path: str):
        """Analyze Python file using AST"""
        try:
            tree = ast.parse(content)
            
            self.files_data[relative_path]['docstring'] = self._extract_module_docstring(tree)
            self.files_data[relative_path]['is_entry_point'] = self._is_python_entry_point(content)
            
            # Analyze AST
            visitor = PythonFileAnalyzer(self, relative_path)
            visitor.visit(tree)
        except Exception as e:
            print(f"Error parsing Python file {file_path}: {e}")
    
    def _analyze_javascript_file(self, file_path: Path, content: str, relative_path: str):
        """Analyze JavaScript/TypeScript file"""
        if not HAS_ESPRIMA and file_path.suffix in ['.js', '.jsx', '.mjs', '.cjs']:
            # Fallback to regex-based analysis
            self._analyze_js_with_regex(content, relative_path)
            return
        
        try:
            # Try to parse with esprima for JS files
            if HAS_ESPRIMA and file_path.suffix in ['.js', '.jsx', '.mjs', '.cjs']:
                tree = esprima.parseModule(content, {'jsx': True, 'tolerant': True})
                visitor = JavaScriptAnalyzer(self, relative_path, content)
                visitor.analyze(tree)
                # Also run regex extraction for components (esprima doesn't detect them well)
                self._extract_react_components(content, relative_path)
            else:
                # Use regex-based analysis for TypeScript
                self._analyze_js_with_regex(content, relative_path)
            
            # Detect entry points
            self.files_data[relative_path]['is_entry_point'] = self._is_js_entry_point(content, file_path)
            
        except Exception as e:
            # Fallback to regex-based analysis
            self._analyze_js_with_regex(content, relative_path)
    
    def _extract_react_components(self, content: str, relative_path: str):
        """Extract React/Vue components using regex"""
        component_patterns = [
            r"(?:export\s+(?:default\s+)?)?(?:function|const)\s+([A-Z]\w+)",
            r"class\s+([A-Z]\w+)\s+extends\s+(?:React\.)?Component"
        ]
        for pattern in component_patterns:
            for match in re.finditer(pattern, content):
                comp_name = match.group(1)
                if comp_name not in [c['name'] for c in self.files_data[relative_path]['components']]:
                    self.files_data[relative_path]['components'].append({
                        'name': comp_name,
                        'type': 'React Component'
                    })
    
    def _analyze_js_with_regex(self, content: str, relative_path: str):
        """Regex-based JavaScript/TypeScript analysis"""
        # Extract imports
        import_patterns = [
            r"import\s+.*?\s+from\s+['\"](.+?)['\"]",
            r"require\(['\"](.+?)['\"]\)",
            r"import\(['\"](.+?)['\"]\)"
        ]
        for pattern in import_patterns:
            for match in re.finditer(pattern, content):
                module = match.group(1)
                self.files_data[relative_path]['imports'].append({
                    'module': module,
                    'type': 'import'
                })
                self.imports[relative_path].add(module)
        
        # Extract functions
        func_patterns = [
            r"(?:export\s+)?(?:async\s+)?function\s+(\w+)",
            r"(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>",
            r"(\w+)\s*:\s*(?:async\s*)?function",
        ]
        for pattern in func_patterns:
            for match in re.finditer(pattern, content):
                func_name = match.group(1)
                if not func_name.startswith('_'):
                    self.files_data[relative_path]['functions'].append({
                        'name': func_name,
                        'args': [],
                        'line_number': content[:match.start()].count('\n') + 1
                    })
        
        # Extract classes
        class_pattern = r"class\s+(\w+)"
        for match in re.finditer(class_pattern, content):
            self.files_data[relative_path]['classes'].append({
                'name': match.group(1),
                'methods': [],
                'line_number': content[:match.start()].count('\n') + 1
            })
        
        # Extract React components
        component_patterns = [
            r"(?:export\s+(?:default\s+)?)?(?:function|const)\s+([A-Z]\w+)",
            r"class\s+([A-Z]\w+)\s+extends\s+(?:React\.)?Component"
        ]
        for pattern in component_patterns:
            for match in re.finditer(pattern, content):
                comp_name = match.group(1)
                if comp_name not in [c['name'] for c in self.files_data[relative_path]['components']]:
                    self.files_data[relative_path]['components'].append({
                        'name': comp_name,
                        'type': 'React Component'
                    })
        
        # Extract API routes/endpoints
        route_patterns = [
            r"(?:app|router)\.(get|post|put|delete|patch)\(['\"](.+?)['\"]",
            r"@(Get|Post|Put|Delete|Patch)\(['\"](.+?)['\"]\)"  # NestJS decorators
        ]
        for pattern in route_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                method = match.group(1).upper()
                path = match.group(2) if len(match.groups()) > 1 else 'unknown'
                self.api_endpoints.append({
                    'method': method,
                    'path': path,
                    'file': relative_path
                })
    
    def _analyze_vue_file(self, file_path: Path, content: str, relative_path: str):
        """Analyze Vue single-file component"""
        # Extract component name from file name
        comp_name = file_path.stem
        self.files_data[relative_path]['components'].append({
            'name': comp_name,
            'type': 'Vue Component'
        })
        
        # Extract script section and analyze
        script_match = re.search(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
        if script_match:
            script_content = script_match.group(1)
            self._analyze_js_with_regex(script_content, relative_path)
        
        self.files_data[relative_path]['is_entry_point'] = 'App.vue' in str(file_path)
    
    def _is_js_entry_point(self, content: str, file_path: Path) -> bool:
        """Check if JS/TS file is an entry point"""
        file_name = file_path.name.lower()
        
        # Check filename
        entry_files = ['index.js', 'index.ts', 'main.js', 'main.ts', 'app.js', 'app.ts',
                      'server.js', 'server.ts', 'index.jsx', 'index.tsx', 'app.jsx', 'app.tsx']
        if file_name in entry_files:
            return True
        
        # Check for common entry point patterns
        entry_indicators = [
            'ReactDOM.render',
            'ReactDOM.createRoot',
            'createApp(',
            'app.listen(',
            'server.listen(',
            'express()',
            'fastify()',
            'new Vue(',
        ]
        return any(indicator in content for indicator in entry_indicators)
    
    def _extract_module_docstring(self, tree: ast.Module) -> str:
        """Extract module-level docstring"""
        if (tree.body and isinstance(tree.body[0], ast.Expr) and 
            isinstance(tree.body[0].value, ast.Constant) and 
            isinstance(tree.body[0].value.value, str)):
            return tree.body[0].value.value.strip()
        return ""
    
    def _is_python_entry_point(self, content: str) -> bool:
        """Check if Python file is likely an entry point"""
        entry_indicators = [
            "if __name__ == '__main__':",
            "app = FastAPI(",
            "app = Flask(",
            "def main(",
            "uvicorn.run(",
            "app.run("
        ]
        return any(indicator in content for indicator in entry_indicators)
    
    def _generate_overview(self):
        """Generate OVERVIEW.md"""
        total_files = len(self.files_data)
        total_lines = sum(data['lines'] for data in self.files_data.values())
        
        # Detect project type
        project_type = self._detect_project_type()
        
        overview = f"""# {self.project_name} - Project Overview

**ANALYZED:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**FILES:** {total_files} Python files ({total_lines:,} total lines)  
**TYPE:** {project_type}  
**ENTRY POINTS:** {len(self.entry_points)} detected  

## Quick Summary

{self._generate_quick_summary()}

## Key Entry Points
{self._format_entry_points()}

## Project Structure Highlights
- **Main directories:** {len(set(str(Path(f).parent) for f in self.files_data.keys() if '/' in f))}
- **Classes defined:** {sum(len(data['classes']) for data in self.files_data.values())}
- **Functions defined:** {sum(len(data['functions']) for data in self.files_data.values())}
- **Import relationships:** {len(self.imports)} files import from others

## Complexity Overview
{self._generate_complexity_overview()}
"""
        
        with open(self.output_dir / "OVERVIEW.md", 'w', encoding='utf-8') as f:
            f.write(overview)
    
    def _detect_project_type(self) -> str:
        """Detect what type of project this is"""
        # Return already detected type if available
        if self.project_type:
            return self.project_type
        
        # Detect based on imports and structure
        all_imports = set()
        for file_data in self.files_data.values():
            all_imports.update(imp['module'] for imp in file_data['imports'])
        
        all_imports_str = ' '.join(all_imports).lower()
        files_str = ' '.join(self.files_data.keys()).lower()
        
        # Web frameworks
        if any(fw in self.frameworks for fw in ['React', 'Vue', 'Angular']):
            return "Frontend Web Application"
        elif any(fw in self.frameworks for fw in ['Next.js', 'Nuxt', 'Gatsby']):
            return "Full-Stack Web Application"
        elif any(fw in self.frameworks for fw in ['Express', 'Fastify', 'NestJS']):
            return "Backend/API Server"
        elif 'Django' in self.frameworks or 'django' in all_imports_str:
            return "Django Web Application"
        elif 'fastapi' in all_imports_str or 'uvicorn' in all_imports_str:
            return "FastAPI Application"
        elif 'flask' in all_imports_str:
            return "Flask Application"
        
        # Other types
        if any(keyword in all_imports_str for keyword in ['pandas', 'numpy', 'matplotlib', 'jupyter']):
            return "Data Science/Analytics"
        elif any(keyword in all_imports_str for keyword in ['argparse', 'click', 'typer']):
            return "CLI Tool"
        
        # Default based on primary language
        if self.primary_language and 'JavaScript' in self.primary_language:
            return "JavaScript Application"
        elif self.primary_language and 'TypeScript' in self.primary_language:
            return "TypeScript Application"
        elif self.primary_language == 'Python':
            return "Python Application"
        
        return "Mixed/Unknown"
    
    def _generate_quick_summary(self) -> str:
        """Generate a quick project summary"""
        summaries = []
        
        # Framework summary
        if self.frameworks:
            summaries.append(f"- Uses {', '.join(list(self.frameworks)[:3])}")
        
        # Language summary
        if len(self.language_stats) > 1:
            langs = [f"{lang} ({count})" for lang, count in sorted(self.language_stats.items(), key=lambda x: x[1], reverse=True)[:3]]
            summaries.append(f"- Multi-language project: {', '.join(langs)}")
        
        # Component summary
        total_components = sum(len(data.get('components', [])) for data in self.files_data.values())
        if total_components > 0:
            summaries.append(f"- {total_components} UI components detected")
        
        # API endpoints
        if self.api_endpoints:
            summaries.append(f"- {len(self.api_endpoints)} API endpoints")
        
        # Database
        all_imports_str = ' '.join(str(data['imports']) for data in self.files_data.values()).lower()
        if 'sqlalchemy' in all_imports_str or 'mongoose' in all_imports_str or 'sequelize' in all_imports_str:
            summaries.append("- Database integration detected")
        
        # Auth
        if any('auth' in f.lower() or 'jwt' in all_imports_str for f in self.files_data.keys()):
            summaries.append("- Authentication system")
        
        return '\n'.join(summaries) if summaries else f"- {self.primary_language} application"
    
    def _format_entry_points(self) -> str:
        """Format entry points list"""
        if not self.entry_points:
            return "None detected"
        
        result = []
        for ep in self.entry_points:
            data = self.files_data[ep]
            result.append(f"- **{ep}** ({data['lines']} lines)")
        
        return '\n'.join(result)
    
    def _generate_complexity_overview(self) -> str:
        """Generate complexity metrics"""
        lines_by_file = [(f, data['lines']) for f, data in self.files_data.items()]
        lines_by_file.sort(key=lambda x: x[1], reverse=True)
        
        result = "**Largest files:**\n"
        for file_path, lines in lines_by_file[:5]:
            result += f"- {file_path}: {lines} lines\n"
        
        return result
    
    def _generate_structure(self):
        """Generate STRUCTURE.md"""
        structure = f"""# {self.project_name} - Directory Structure & File Purposes

## Directory Tree
```
{self._generate_tree_view()}
```

## File Purposes

{self._generate_file_purposes()}
"""
        
        with open(self.output_dir / "STRUCTURE.md", 'w', encoding='utf-8') as f:
            f.write(structure)
    
    def _generate_tree_view(self) -> str:
        """Generate directory tree view"""
        # Build tree structure
        tree = {}
        for file_path in self.files_data.keys():
            parts = Path(file_path).parts
            current = tree
            for part in parts[:-1]:  # directories
                if part not in current:
                    current[part] = {}
                current = current[part]
            # Add file
            current[parts[-1]] = None
        
        def build_tree_string(node, prefix="", is_last=True):
            if node is None:
                return ""
            
            result = ""
            items = list(node.items())
            for i, (name, subtree) in enumerate(items):
                is_last_item = i == len(items) - 1
                current_prefix = "└── " if is_last_item else "├── "
                result += prefix + current_prefix + name + "\n"
                
                if subtree is not None:  # directory
                    extension = "    " if is_last_item else "│   "
                    result += build_tree_string(subtree, prefix + extension, is_last_item)
            
            return result
        
        return build_tree_string(tree)
    
    def _generate_file_purposes(self) -> str:
        """Generate file purpose descriptions"""
        result = []
        
        for file_path, data in sorted(self.files_data.items()):
            purpose = self._infer_file_purpose(file_path, data)
            result.append(f"**{file_path}** - {purpose}")
        
        return '\n\n'.join(result)
    
    def _infer_file_purpose(self, file_path: str, data: Dict) -> str:
        """Infer what a file is for based on name and contents"""
        file_name = Path(file_path).name.lower()
        language = data.get('language', 'Unknown')
        
        # Use docstring if available
        if data.get('docstring'):
            return data['docstring'].split('\n')[0]
        
        # JavaScript/TypeScript specific patterns
        if 'JavaScript' in language or 'TypeScript' in language:
            if file_name in ['index.js', 'index.ts', 'index.jsx', 'index.tsx']:
                return "Module entry point / barrel export"
            elif file_name in ['app.js', 'app.ts', 'app.jsx', 'app.tsx']:
                return "Main application component"
            elif file_name in ['server.js', 'server.ts']:
                return "Server entry point"
            elif file_name.endswith('.config.js') or file_name.endswith('.config.ts'):
                return "Configuration file"
            elif file_name.endswith('.test.js') or file_name.endswith('.spec.ts'):
                return "Test file"
            elif 'route' in file_name or 'router' in file_name:
                return "API routes and routing"
            elif 'controller' in file_name:
                return "Request controller"
            elif 'service' in file_name:
                return "Business logic service"
            elif 'hook' in file_name and 'React' in str(data.get('imports', [])):
                return "React custom hooks"
            elif 'context' in file_name and 'React' in str(data.get('imports', [])):
                return "React context provider"
            elif data.get('components'):
                comp_names = [c['name'] for c in data['components'][:3]]
                return f"UI Components: {', '.join(comp_names)}"
        
        # Vue specific
        if language == 'Vue':
            return f"Vue component: {Path(file_path).stem}"
        
        # Python specific patterns
        if language == 'Python':
            if file_name == '__init__.py':
                return "Package initialization"
            elif file_name in ['main.py', 'app.py']:
                return "Main application entry point"
            elif file_name == 'config.py' or file_name == 'settings.py':
                return "Configuration and settings"
            elif file_name.startswith('test_') or file_name.endswith('_test.py'):
                return "Test module"
            elif 'model' in file_name:
                return "Data models and database schemas"
        
        # Common patterns across languages
        if 'api' in file_name:
            return "API endpoints and routing"
        elif 'auth' in file_name:
            return "Authentication and authorization"
        elif 'util' in file_name or 'helper' in file_name:
            return "Utility functions and helpers"
        elif 'middleware' in file_name:
            return "Middleware components"
        elif 'handler' in file_name:
            return "Request/event handlers"
        elif 'service' in file_name:
            return "Business logic services"
        elif 'database' in file_name or 'db' in file_name:
            return "Database connection and operations"
        elif 'type' in file_name and 'TypeScript' in language:
            return "TypeScript type definitions"
        elif 'interface' in file_name:
            return "Interface definitions"
        elif 'constant' in file_name or file_name == 'constants.js' or file_name == 'constants.ts':
            return "Application constants"
        
        # Infer from content
        if data.get('components'):
            comp_names = [c['name'] for c in data['components'][:3]]
            return f"Components: {', '.join(comp_names)}"
        elif data.get('classes'):
            class_names = [cls['name'] for cls in data['classes'][:3]]
            return f"Defines classes: {', '.join(class_names)}"
        elif data.get('functions'):
            func_names = [func['name'] for func in data['functions'][:3]]
            return f"Functions: {', '.join(func_names)}"
        
        return f"{language} module ({data['lines']} lines)"
    
    def _generate_dependencies(self):
        """Generate DEPENDENCIES.md"""
        deps = f"""# {self.project_name} - Dependencies & Import Relationships

## Import Graph

{self._generate_import_graph()}

## External Dependencies

{self._generate_external_deps()}

## Internal Dependencies

{self._generate_internal_deps()}
"""
        
        with open(self.output_dir / "DEPENDENCIES.md", 'w', encoding='utf-8') as f:
            f.write(deps)
    
    def _generate_import_graph(self) -> str:
        """Generate visual import relationships"""
        result = []
        
        for file_path, imports in self.imports.items():
            if imports:
                result.append(f"**{file_path}**")
                for imp in imports:
                    result.append(f"  └── {imp}")
                result.append("")
        
        return '\n'.join(result)
    
    def _generate_external_deps(self) -> str:
        """List external package dependencies"""
        external_deps = set()
        
        # Python standard library modules to exclude
        py_stdlib = {'os', 'sys', 'json', 're', 'datetime', 'pathlib', 'typing', 'collections',
                     'argparse', 'logging', 'unittest', 'time', 'math', 'random', 'itertools',
                     'functools', 'copy', 'io', 'tempfile', 'shutil', 'subprocess', 'threading'}
        
        # JavaScript/Node.js built-in modules to exclude
        js_builtins = {'fs', 'path', 'http', 'https', 'url', 'util', 'events', 'stream',
                      'crypto', 'os', 'process', 'buffer', 'querystring', 'child_process',
                      'cluster', 'dns', 'net', 'tls', 'zlib', 'assert', 'console'}
        
        for file_data in self.files_data.values():
            for imp in file_data['imports']:
                module = imp['module'].split('/')[0].split('.')[0]
                
                # Skip relative imports
                if module.startswith('.'):
                    continue
                
                # Skip standard library
                if module in py_stdlib or module in js_builtins:
                    continue
                
                # Skip scoped packages prefix for counting
                if module.startswith('@'):
                    # Include the full scope name like @angular/core
                    parts = imp['module'].split('/')
                    if len(parts) >= 2:
                        module = f"{parts[0]}/{parts[1]}"
                    else:
                        module = parts[0]
                
                external_deps.add(module)
        
        if not external_deps:
            return "None detected"
        
        return '\n'.join(f"- {dep}" for dep in sorted(external_deps))
    
    def _generate_internal_deps(self) -> str:
        """Show internal module dependencies"""
        internal_deps = defaultdict(set)
        
        for file_path, file_data in self.files_data.items():
            for imp in file_data['imports']:
                if imp['module'].startswith('.') or imp['module'] in [f.replace('/', '.').replace('.py', '') for f in self.files_data.keys()]:
                    internal_deps[file_path].add(imp['module'])
        
        if not internal_deps:
            return "No internal dependencies detected"
        
        result = []
        for file_path, deps in internal_deps.items():
            result.append(f"**{file_path}**")
            for dep in sorted(deps):
                result.append(f"  → {dep}")
            result.append("")
        
        return '\n'.join(result)
    
    def _generate_call_graph(self):
        """Generate CALL_GRAPH.md"""
        call_graph = f"""# {self.project_name} - Function Call Graph

## High-Traffic Functions

{self._generate_high_traffic_functions()}

## Call Relationships

{self._generate_call_relationships()}
"""
        
        with open(self.output_dir / "CALL_GRAPH.md", 'w', encoding='utf-8') as f:
            f.write(call_graph)
    
    def _generate_high_traffic_functions(self) -> str:
        """Find most-called functions"""
        call_counts = Counter()
        
        for file_data in self.files_data.values():
            for func in file_data['functions']:
                if 'calls' in func:
                    for call in func['calls']:
                        call_counts[call] += 1
        
        if not call_counts:
            return "No function calls detected"
        
        result = []
        for func, count in call_counts.most_common(10):
            result.append(f"{count}. **{func}** - Called {count} times")
        
        return '\n'.join(result)
    
    def _generate_call_relationships(self) -> str:
        """Generate function call hierarchy"""
        result = []
        
        for file_path, file_data in self.files_data.items():
            if file_data['functions']:
                result.append(f"## {file_path}")
                result.append("")
                
                for func in file_data['functions']:
                    result.append(f"**{func['name']}()**")
                    if 'calls' in func and func['calls']:
                        for call in func['calls'][:5]:  # Limit to first 5 calls
                            result.append(f"  └── {call}")
                    result.append("")
        
        return '\n'.join(result)
    
    def _generate_api_surface(self):
        """Generate API_SURFACE.md"""
        components_section = ""
        if any(data.get('components') for data in self.files_data.values()):
            components_section = f"""
## UI Components

{self._generate_components_list()}
"""
        
        api_surface = f"""# {self.project_name} - API Surface

## Public API Endpoints

{self._generate_api_endpoints()}
{components_section}
## Public Classes & Methods

{self._generate_public_classes()}

## Utility Functions

{self._generate_utility_functions()}
"""
        
        with open(self.output_dir / "API_SURFACE.md", 'w', encoding='utf-8') as f:
            f.write(api_surface)
    
    def _generate_components_list(self) -> str:
        """List all UI components (React, Vue, etc.)"""
        components = []
        
        for file_path, file_data in self.files_data.items():
            if file_data.get('components'):
                for comp in file_data['components']:
                    components.append(f"**{comp['name']}** ({comp['type']}) - {file_path}")
        
        return '\n'.join(components) if components else "No components detected"
    
    def _generate_api_endpoints(self) -> str:
        """Extract API endpoints from code"""
        if not self.api_endpoints:
            # Fallback to decorator-based detection
            endpoints = []
            for file_path, file_data in self.files_data.items():
                for func in file_data.get('functions', []):
                    if 'decorators' in func:
                        for decorator in func['decorators']:
                            if any(keyword in decorator.lower() for keyword in ['route', 'get', 'post', 'put', 'delete']):
                                endpoints.append(f"{decorator} → {file_path}:{func['name']}")
            return '\n'.join(endpoints) if endpoints else "No API endpoints detected"
        
        # Group endpoints by file
        endpoints_by_file = defaultdict(list)
        for endpoint in self.api_endpoints:
            endpoints_by_file[endpoint['file']].append(endpoint)
        
        result = []
        for file_path, endpoints in sorted(endpoints_by_file.items()):
            result.append(f"**{file_path}**")
            for ep in endpoints:
                result.append(f"  {ep['method']:6} {ep['path']}")
            result.append("")
        
        return '\n'.join(result)
    
    def _generate_public_classes(self) -> str:
        """List public classes and their methods"""
        result = []
        
        for file_path, file_data in self.files_data.items():
            if file_data['classes']:
                for cls in file_data['classes']:
                    if not cls['name'].startswith('_'):  # Public class
                        result.append(f"**{cls['name']}** ({file_path})")
                        if 'methods' in cls:
                            for method in cls['methods'][:5]:  # Limit methods shown
                                result.append(f"  └── {method}")
                        result.append("")
        
        return '\n'.join(result) if result else "No public classes detected"
    
    def _generate_utility_functions(self) -> str:
        """List utility functions"""
        utils = []
        
        for file_path, file_data in self.files_data.items():
            if 'util' in file_path.lower() or 'helper' in file_path.lower():
                for func in file_data['functions']:
                    if not func['name'].startswith('_'):
                        utils.append(f"**{func['name']}()** - {file_path}")
        
        return '\n'.join(utils) if utils else "No utility functions detected"
    
    def _generate_module_summaries(self):
        """Generate detailed module summaries"""
        modules_dir = self.output_dir / "modules"
        modules_dir.mkdir(exist_ok=True)
        
        for file_path, file_data in self.files_data.items():
            summary = self._generate_module_summary(file_path, file_data)
            
            # Create safe filename
            safe_name = file_path.replace('/', '_').replace('\\', '_').replace('.py', '.md').replace('.js', '.md').replace('.ts', '.md').replace('.jsx', '.md').replace('.tsx', '.md').replace('.vue', '.md')
            
            with open(modules_dir / safe_name, 'w', encoding='utf-8') as f:
                f.write(summary)
    
    def _generate_module_summary(self, file_path: str, file_data: Dict) -> str:
        """Generate detailed summary for a single module"""
        components_section = ""
        if file_data.get('components'):
            components_section = f"""
## Components
{self._format_components(file_data['components'])}
"""
        
        return f"""# {file_path}

**PURPOSE:** {self._infer_file_purpose(file_path, file_data)}

**LINES:** {file_data['lines']}

## Classes
{self._format_classes(file_data.get('classes', []))}

## Functions
{self._format_functions(file_data.get('functions', []))}
{components_section}
## Imports
{self._format_imports(file_data.get('imports', []))}

## Dependencies
- **Used by:** {self._get_reverse_dependencies(file_path)}
- **Uses:** {self._get_dependencies(file_path)}

**COMPLEXITY:** {self._calculate_complexity(file_data)}
"""
    
    def _format_components(self, components: List[Dict]) -> str:
        """Format component information"""
        if not components:
            return "None"
        
        result = []
        for comp in components:
            comp_type = comp.get('type', 'Component')
            result.append(f"- **{comp['name']}** ({comp_type})")
        
        return '\n'.join(result)
    
    def _format_classes(self, classes: List[Dict]) -> str:
        """Format class information"""
        if not classes:
            return "None"
        
        result = []
        for cls in classes:
            result.append(f"- **{cls['name']}**")
            if 'methods' in cls:
                for method in cls['methods'][:3]:  # Show first 3 methods
                    result.append(f"  - {method}")
        
        return '\n'.join(result)
    
    def _format_functions(self, functions: List[Dict]) -> str:
        """Format function information"""
        if not functions:
            return "None"
        
        result = []
        for func in functions:
            args = func.get('args', [])
            args_str = ', '.join(args) if args else ''
            result.append(f"- **{func['name']}**({args_str})")
        
        return '\n'.join(result)
    
    def _format_imports(self, imports: List[Dict]) -> str:
        """Format import information"""
        if not imports:
            return "None"
        
        return '\n'.join(f"- {imp['module']}" for imp in imports)
    
    def _get_reverse_dependencies(self, file_path: str) -> str:
        """Get files that import this file"""
        # This would need more sophisticated analysis
        return "Analysis needed"
    
    def _get_dependencies(self, file_path: str) -> str:
        """Get what this file imports"""
        file_data = self.files_data[file_path]
        imports = [imp['module'] for imp in file_data['imports']]
        return ', '.join(imports[:5]) if imports else "None"
    
    def _calculate_complexity(self, file_data: Dict) -> str:
        """Calculate complexity rating"""
        lines = file_data['lines']
        classes = len(file_data['classes'])
        functions = len(file_data['functions'])
        
        score = lines + classes * 10 + functions * 5
        
        if score < 100:
            return "Low"
        elif score < 300:
            return "Medium"
        else:
            return "High"
    
    def _generate_prompts(self):
        """Generate LLM prompts for deeper analysis"""
        prompts_dir = self.output_dir / "prompts"
        prompts_dir.mkdir(exist_ok=True)
        
        # Full project prompt
        full_prompt = self._generate_full_project_prompt()
        with open(prompts_dir / "full_analysis_prompt.txt", 'w', encoding='utf-8') as f:
            f.write(full_prompt)
        
        # Individual module prompts
        individual_dir = prompts_dir / "individual_module_prompts"
        individual_dir.mkdir(exist_ok=True)
        
        for file_path in self.files_data.keys():
            module_prompt = self._generate_module_prompt(file_path)
            safe_name = file_path.replace('/', '_').replace('\\', '_').replace('.py', '.txt').replace('.js', '.txt').replace('.ts', '.txt').replace('.jsx', '.txt').replace('.tsx', '.txt')
            
            with open(individual_dir / safe_name, 'w', encoding='utf-8') as f:
                f.write(module_prompt)
    
    def _generate_full_project_prompt(self) -> str:
        """Generate comprehensive project analysis prompt"""
        lang_summary = ', '.join([f"{lang} ({count} files)" for lang, count in self.language_stats.items()])
        
        return f"""I'm analyzing a {self.primary_language} project called "{self.project_name}". Here's the comprehensive structure:

PROJECT OVERVIEW:
- Type: {self.project_type or 'Unknown'}
- Languages: {lang_summary}
- Frameworks: {', '.join(self.frameworks) if self.frameworks else 'None detected'}
- Total files: {len(self.files_data)}
- Total lines: {sum(data['lines'] for data in self.files_data.values())}
- Entry points: {', '.join(self.entry_points) if self.entry_points else 'None detected'}

DIRECTORY STRUCTURE:
{self._generate_tree_view()}

KEY COMPONENTS:
{self._generate_key_components_summary()}

Please provide:
1. Architectural analysis - How is this project structured?
2. Design patterns - What patterns are being used?
3. Code quality assessment - Areas for improvement?
4. Security considerations - Any potential issues?
5. Performance considerations - Bottlenecks or optimizations?
6. Maintainability - How easy is this to maintain and extend?

Focus on high-level insights rather than line-by-line details.
"""
    
    def _generate_key_components_summary(self) -> str:
        """Generate summary of key components for prompt"""
        summary = []
        
        for file_path, file_data in self.files_data.items():
            if file_data['lines'] > 50 or file_data.get('classes') or file_data.get('components') or file_path in self.entry_points:
                parts = []
                parts.append(f"{file_data['lines']} lines")
                
                if file_data.get('classes'):
                    parts.append(f"{len(file_data['classes'])} classes")
                if file_data.get('functions'):
                    parts.append(f"{len(file_data['functions'])} functions")
                if file_data.get('components'):
                    parts.append(f"{len(file_data['components'])} components")
                
                summary.append(f"- {file_path}: {', '.join(parts)}")
        
        return '\n'.join(summary[:15])  # Show top 15 files
    
    def _generate_module_prompt(self, file_path: str) -> str:
        """Generate focused prompt for a specific module"""
        file_data = self.files_data[file_path]
        language = file_data.get('language', 'Unknown')
        
        structure_parts = []
        if file_data.get('classes'):
            structure_parts.append(f"Classes: {len(file_data['classes'])}")
        if file_data.get('functions'):
            structure_parts.append(f"Functions: {len(file_data['functions'])}")
        if file_data.get('components'):
            structure_parts.append(f"Components: {len(file_data['components'])}")
        structure_str = ', '.join(structure_parts) if structure_parts else 'No major structures'
        
        return f"""I'm analyzing a {language} module: {file_path}

PURPOSE: {self._infer_file_purpose(file_path, file_data)}
LINES: {file_data['lines']}
COMPLEXITY: {self._calculate_complexity(file_data)}

STRUCTURE:
- Classes: {len(file_data['classes'])}
- Functions: {len(file_data['functions'])}
- Imports: {len(file_data['imports'])}

DEPENDENCIES:
{self._format_imports(file_data['imports'])}

Please analyze:
1. What is this module's primary responsibility?
2. How does it fit into the larger application architecture?
3. Are there any code quality or design concerns?
4. What would you change or improve?
5. How testable is this code?

Focus on architectural insights and improvement suggestions.
"""


class PythonFileAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze individual Python files"""
    
    def __init__(self, analyzer: CodeSplainAnalyzer, file_path: str):
        self.analyzer = analyzer
        self.file_path = file_path
        self.current_class = None
        self.current_function = None
    
    def visit_Import(self, node: ast.Import):
        """Handle import statements"""
        for alias in node.names:
            import_info = {
                'module': alias.name,
                'alias': alias.asname,
                'type': 'import'
            }
            self.analyzer.files_data[self.file_path]['imports'].append(import_info)
            self.analyzer.imports[self.file_path].add(alias.name)
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Handle from ... import ... statements"""
        module = node.module or ''
        for alias in node.names:
            import_info = {
                'module': f"{module}.{alias.name}" if module else alias.name,
                'alias': alias.asname,
                'type': 'from_import'
            }
            self.analyzer.files_data[self.file_path]['imports'].append(import_info)
            self.analyzer.imports[self.file_path].add(module or alias.name)
        
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Handle class definitions"""
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(item.name)
        
        class_info = {
            'name': node.name,
            'methods': methods,
            'decorators': [self._get_decorator_name(d) for d in node.decorator_list],
            'line_number': node.lineno
        }
        
        self.analyzer.files_data[self.file_path]['classes'].append(class_info)
        
        # Visit class body
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Handle function definitions"""
        args = [arg.arg for arg in node.args.args]
        
        function_info = {
            'name': node.name,
            'args': args,
            'decorators': [self._get_decorator_name(d) for d in node.decorator_list],
            'line_number': node.lineno,
            'calls': []
        }
        
        # Find function calls within this function
        call_visitor = CallVisitor()
        call_visitor.visit(node)
        function_info['calls'] = call_visitor.calls
        
        self.analyzer.files_data[self.file_path]['functions'].append(function_info)
        
        # Check for API endpoints
        if any('route' in dec.lower() or method in dec.lower() 
               for dec in function_info['decorators'] 
               for method in ['get', 'post', 'put', 'delete', 'patch']):
            endpoint_info = {
                'method': 'UNKNOWN',
                'path': 'UNKNOWN',
                'function': f"{self.file_path}:{node.name}",
                'decorators': function_info['decorators']
            }
            self.analyzer.api_endpoints.append(endpoint_info)
        
        self.generic_visit(node)
    
    def _get_decorator_name(self, decorator) -> str:
        """Extract decorator name from AST node"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{self._get_attr_name(decorator.value)}.{decorator.attr}"
        elif isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        else:
            return str(decorator)
    
    def _get_attr_name(self, node) -> str:
        """Get attribute name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_attr_name(node.value)}.{node.attr}"
        else:
            return "unknown"


class JavaScriptAnalyzer:
    """Analyzer for JavaScript/TypeScript files using esprima"""
    
    def __init__(self, analyzer: CodeSplainAnalyzer, file_path: str, content: str):
        self.analyzer = analyzer
        self.file_path = file_path
        self.content = content
    
    def analyze(self, tree):
        """Analyze JavaScript AST from esprima"""
        try:
            self._visit_node(tree)
        except Exception as e:
            print(f"Warning: Error analyzing JS AST for {self.file_path}: {e}")
    
    def _visit_node(self, node):
        """Recursively visit AST nodes"""
        if not isinstance(node, dict):
            return
        
        node_type = node.get('type')
        
        if node_type == 'ImportDeclaration':
            self._handle_import(node)
        elif node_type == 'FunctionDeclaration':
            self._handle_function(node)
        elif node_type == 'ClassDeclaration':
            self._handle_class(node)
        elif node_type == 'VariableDeclaration':
            self._handle_variable(node)
        elif node_type == 'ExpressionStatement':
            self._handle_expression(node)
        
        # Recursively visit child nodes
        for key, value in node.items():
            if isinstance(value, dict):
                self._visit_node(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._visit_node(item)
    
    def _handle_import(self, node):
        """Handle import declarations"""
        source = node.get('source', {}).get('value', '')
        if source:
            self.analyzer.files_data[self.file_path]['imports'].append({
                'module': source,
                'type': 'import'
            })
            self.analyzer.imports[self.file_path].add(source)
    
    def _handle_function(self, node):
        """Handle function declarations"""
        func_id = node.get('id', {})
        if func_id and func_id.get('name'):
            func_name = func_id['name']
            params = node.get('params', [])
            args = [p.get('name', '') for p in params if p.get('name')]
            
            self.analyzer.files_data[self.file_path]['functions'].append({
                'name': func_name,
                'args': args,
                'line_number': node.get('loc', {}).get('start', {}).get('line', 0)
            })
    
    def _handle_class(self, node):
        """Handle class declarations"""
        class_id = node.get('id', {})
        if class_id and class_id.get('name'):
            class_name = class_id['name']
            body = node.get('body', {}).get('body', [])
            methods = []
            
            for item in body:
                if item.get('type') == 'MethodDefinition':
                    key = item.get('key', {})
                    if key.get('name'):
                        methods.append(key['name'])
            
            self.analyzer.files_data[self.file_path]['classes'].append({
                'name': class_name,
                'methods': methods,
                'line_number': node.get('loc', {}).get('start', {}).get('line', 0)
            })
    
    def _handle_variable(self, node):
        """Handle variable declarations (could be functions)"""
        declarations = node.get('declarations', [])
        for decl in declarations:
            var_id = decl.get('id', {})
            init = decl.get('init', {})
            
            if var_id.get('name') and init:
                var_name = var_id['name']
                init_type = init.get('type', '')
                
                # Check if it's a function
                if init_type in ['FunctionExpression', 'ArrowFunctionExpression']:
                    params = init.get('params', [])
                    args = [p.get('name', '') for p in params if p.get('name')]
                    
                    self.analyzer.files_data[self.file_path]['functions'].append({
                        'name': var_name,
                        'args': args,
                        'line_number': node.get('loc', {}).get('start', {}).get('line', 0)
                    })
    
    def _handle_expression(self, node):
        """Handle expression statements (like require calls)"""
        expr = node.get('expression', {})
        if expr.get('type') == 'CallExpression':
            callee = expr.get('callee', {})
            if callee.get('name') == 'require':
                args = expr.get('arguments', [])
                if args and args[0].get('value'):
                    module = args[0]['value']
                    self.analyzer.files_data[self.file_path]['imports'].append({
                        'module': module,
                        'type': 'require'
                    })
                    self.analyzer.imports[self.file_path].add(module)


class CallVisitor(ast.NodeVisitor):
    """Visitor to find function calls within a function"""
    
    def __init__(self):
        self.calls = []
    
    def visit_Call(self, node: ast.Call):
        """Handle function calls"""
        call_name = self._get_call_name(node.func)
        if call_name:
            self.calls.append(call_name)
        self.generic_visit(node)
    
    def _get_call_name(self, node) -> str:
        """Extract function call name"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_attr_name(node.value)}.{node.attr}"
        else:
            return ""
    
    def _get_attr_name(self, node) -> str:
        """Get attribute name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_attr_name(node.value)}.{node.attr}"
        else:
            return "unknown"


def main():
    """Main CLI interface"""
    # Configure console for UTF-8 output
    import sys
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except:
            pass
    
    parser = argparse.ArgumentParser(
        description="CodeSplain - Analyze Python, JavaScript, TypeScript, and React projects"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to project (default: current directory)"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output directory (default: codesplain_results/project_timestamp/)"
    )
    parser.add_argument(
        "--no-prompts",
        action="store_true",
        help="Skip generating LLM prompts"
    )
    
    args = parser.parse_args()
    
    # Check if path exists
    project_path = Path(args.path).resolve()
    if not project_path.exists():
        print(f"❌ Error: Path {project_path} does not exist")
        sys.exit(1)
    
    # Initialize and run analyzer
    try:
        analyzer = CodeSplainAnalyzer(str(project_path))
        
        if args.output:
            analyzer.output_dir = Path(args.output)
        
        # Skip prompts if requested
        if args.no_prompts:
            analyzer._generate_prompts = lambda: None
        
        analyzer.analyze_project()
        
        if not analyzer.files_data:
            print("❌ No analyzable source files found in project")
            sys.exit(1)
        
        print("\n📊 Analysis Summary:")
        print(f"   Files analyzed: {len(analyzer.files_data)}")
        print(f"   Total lines: {sum(data['lines'] for data in analyzer.files_data.values()):,}")
        print(f"   Classes found: {sum(len(data.get('classes', [])) for data in analyzer.files_data.values())}")
        print(f"   Functions found: {sum(len(data.get('functions', [])) for data in analyzer.files_data.values())}")
        
        components = sum(len(data.get('components', [])) for data in analyzer.files_data.values())
        if components > 0:
            print(f"   Components found: {components}")
        
        print(f"   Entry points: {len(analyzer.entry_points)}")
        
        print(f"\n📁 Results saved to: {analyzer.output_dir}")
        print("\n📋 Generated files:")
        print("   ├── OVERVIEW.md - Project summary and quick insights")
        print("   ├── STRUCTURE.md - Directory tree and file purposes")  
        print("   ├── DEPENDENCIES.md - Import relationships and dependencies")
        print("   ├── CALL_GRAPH.md - Function call relationships")
        print("   ├── API_SURFACE.md - Public interfaces, components and endpoints")
        print("   ├── modules/ - Detailed analysis of each file")
        if not args.no_prompts:
            print("   └── prompts/ - Ready-to-use LLM analysis prompts")
        
        print(f"\n🎯 Next steps:")
        print(f"   1. Read OVERVIEW.md for quick project understanding")
        print(f"   2. Check STRUCTURE.md to understand file organization")
        print(f"   3. Review modules/ for detailed file analysis")
        if not args.no_prompts:
            print(f"   4. Use prompts/ for AI-powered deeper analysis")
        
    except KeyboardInterrupt:
        print("\n❌ Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
