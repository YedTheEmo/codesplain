#!/usr/bin/env python3
"""
CodeSplain - Local Codebase Analyzer & Summarizer
Analyze Python projects and generate comprehensive summaries, relationships, and call graphs.
"""

import os
import ast
import sys
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Optional, Any
import re

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
        
    def analyze_project(self):
        """Main analysis pipeline"""
        print(f"🔍 Analyzing {self.project_name}...")
        
        # Find and analyze Python files
        python_files = list(self.project_path.rglob("*.py"))
        python_files = [f for f in python_files if not self._should_skip_file(f)]
        
        print(f"Found {len(python_files)} Python files")
        
        # Analyze each file
        for file_path in python_files:
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
        
    def _should_skip_file(self, file_path: Path) -> bool:
        """Skip test files, migrations, cache, etc."""
        skip_patterns = [
            "__pycache__", ".pytest_cache", ".git", "node_modules",
            "venv", "env", ".env", "migrations", "test_", "_test",
            "tests.py", "conftest.py"
        ]
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def _analyze_file(self, file_path: Path):
        """Analyze a single Python file"""
        relative_path = file_path.relative_to(self.project_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Initialize file data
            self.files_data[str(relative_path)] = {
                'path': relative_path,
                'lines': len(content.splitlines()),
                'classes': [],
                'functions': [],
                'imports': [],
                'docstring': self._extract_module_docstring(tree),
                'complexity': 0,
                'is_entry_point': self._is_entry_point(content)
            }
            
            # Analyze AST
            visitor = FileAnalyzer(self, str(relative_path))
            visitor.visit(tree)
            
            if self.files_data[str(relative_path)]['is_entry_point']:
                self.entry_points.append(str(relative_path))
                
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
    
    def _extract_module_docstring(self, tree: ast.Module) -> str:
        """Extract module-level docstring"""
        if (tree.body and isinstance(tree.body[0], ast.Expr) and 
            isinstance(tree.body[0].value, ast.Constant) and 
            isinstance(tree.body[0].value.value, str)):
            return tree.body[0].value.value.strip()
        return ""
    
    def _is_entry_point(self, content: str) -> bool:
        """Check if file is likely an entry point"""
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
        
        with open(self.output_dir / "OVERVIEW.md", 'w') as f:
            f.write(overview)
    
    def _detect_project_type(self) -> str:
        """Detect what type of project this is"""
        indicators = {
            'FastAPI': ['fastapi', 'uvicorn'],
            'Flask': ['flask', 'werkzeug'],
            'Django': ['django', 'manage.py'],
            'Data Science': ['pandas', 'numpy', 'matplotlib', 'jupyter'],
            'CLI Tool': ['argparse', 'click', 'typer'],
            'Library': ['setup.py', '__init__.py'],
        }
        
        all_imports = set()
        for file_data in self.files_data.values():
            all_imports.update(imp['module'] for imp in file_data['imports'])
        
        for project_type, keywords in indicators.items():
            if any(keyword in str(all_imports).lower() or 
                   keyword in ' '.join(self.files_data.keys()).lower() 
                   for keyword in keywords):
                return project_type
        
        return "Python Application"
    
    def _generate_quick_summary(self) -> str:
        """Generate a quick project summary"""
        summaries = []
        
        # Check for web framework
        if any('fastapi' in str(data['imports']).lower() for data in self.files_data.values()):
            summaries.append("- FastAPI web application")
        elif any('flask' in str(data['imports']).lower() for data in self.files_data.values()):
            summaries.append("- Flask web application")
        elif any('django' in str(data['imports']).lower() for data in self.files_data.values()):
            summaries.append("- Django web application")
        
        # Check for database
        if any('sqlalchemy' in str(data['imports']).lower() for data in self.files_data.values()):
            summaries.append("- SQLAlchemy database integration")
        elif any('django.db' in str(data['imports']).lower() for data in self.files_data.values()):
            summaries.append("- Django ORM database models")
        
        # Check for API endpoints
        if self.api_endpoints:
            summaries.append(f"- RESTful API with {len(self.api_endpoints)} endpoints")
        
        # Check for auth
        if any('auth' in f.lower() or 'jwt' in f.lower() for f in self.files_data.keys()):
            summaries.append("- Authentication system")
        
        return '\n'.join(summaries) if summaries else "- Python application"
    
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
        
        with open(self.output_dir / "STRUCTURE.md", 'w') as f:
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
        
        # Use docstring if available
        if data['docstring']:
            return data['docstring'].split('\n')[0]
        
        # Infer from filename
        if file_name == '__init__.py':
            return "Package initialization"
        elif file_name in ['main.py', 'app.py']:
            return "Main application entry point"
        elif file_name == 'config.py':
            return "Configuration and settings"
        elif file_name.startswith('test_') or file_name.endswith('_test.py'):
            return "Test module"
        elif 'model' in file_name:
            return "Data models and database schemas"
        elif 'api' in file_name or 'route' in file_name:
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
        
        # Infer from content
        if data['classes']:
            class_names = [cls['name'] for cls in data['classes']]
            return f"Defines classes: {', '.join(class_names[:3])}"
        elif data['functions']:
            func_names = [func['name'] for func in data['functions']]
            return f"Utility functions: {', '.join(func_names[:3])}"
        
        return f"Python module ({data['lines']} lines)"
    
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
        
        with open(self.output_dir / "DEPENDENCIES.md", 'w') as f:
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
        
        for file_data in self.files_data.values():
            for imp in file_data['imports']:
                module = imp['module'].split('.')[0]
                if not module.startswith('.') and module not in ['os', 'sys', 'json', 're', 'datetime']:
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
        
        with open(self.output_dir / "CALL_GRAPH.md", 'w') as f:
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
        api_surface = f"""# {self.project_name} - API Surface

## Public API Endpoints

{self._generate_api_endpoints()}

## Public Classes & Methods

{self._generate_public_classes()}

## Utility Functions

{self._generate_utility_functions()}
"""
        
        with open(self.output_dir / "API_SURFACE.md", 'w') as f:
            f.write(api_surface)
    
    def _generate_api_endpoints(self) -> str:
        """Extract API endpoints from code"""
        endpoints = []
        
        for file_path, file_data in self.files_data.items():
            for func in file_data['functions']:
                # Look for FastAPI/Flask decorators
                if 'decorators' in func:
                    for decorator in func['decorators']:
                        if any(keyword in decorator.lower() for keyword in ['route', 'get', 'post', 'put', 'delete']):
                            endpoints.append(f"{decorator} → {file_path}:{func['name']}")
        
        return '\n'.join(endpoints) if endpoints else "No API endpoints detected"
    
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
            safe_name = file_path.replace('/', '_').replace('.py', '.md')
            
            with open(modules_dir / safe_name, 'w') as f:
                f.write(summary)
    
    def _generate_module_summary(self, file_path: str, file_data: Dict) -> str:
        """Generate detailed summary for a single module"""
        return f"""# {file_path}

**PURPOSE:** {self._infer_file_purpose(file_path, file_data)}

**LINES:** {file_data['lines']}

## Classes
{self._format_classes(file_data['classes'])}

## Functions
{self._format_functions(file_data['functions'])}

## Imports
{self._format_imports(file_data['imports'])}

## Dependencies
- **Used by:** {self._get_reverse_dependencies(file_path)}
- **Uses:** {self._get_dependencies(file_path)}

**COMPLEXITY:** {self._calculate_complexity(file_data)}
"""
    
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
        with open(prompts_dir / "full_analysis_prompt.txt", 'w') as f:
            f.write(full_prompt)
        
        # Individual module prompts
        individual_dir = prompts_dir / "individual_module_prompts"
        individual_dir.mkdir(exist_ok=True)
        
        for file_path in self.files_data.keys():
            module_prompt = self._generate_module_prompt(file_path)
            safe_name = file_path.replace('/', '_').replace('.py', '_prompt.txt')
            
            with open(individual_dir / safe_name, 'w') as f:
                f.write(module_prompt)
    
    def _generate_full_project_prompt(self) -> str:
        """Generate comprehensive project analysis prompt"""
        return f"""I'm analyzing a Python project called "{self.project_name}". Here's the comprehensive structure:

PROJECT OVERVIEW:
- {len(self.files_data)} Python files
- {sum(data['lines'] for data in self.files_data.values())} total lines
- Entry points: {', '.join(self.entry_points)}

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
            if file_data['lines'] > 50 or file_data['classes'] or file_path in self.entry_points:
                classes_str = f"{len(file_data['classes'])} classes" if file_data['classes'] else "no classes"
                functions_str = f"{len(file_data['functions'])} functions" if file_data['functions'] else "no functions"
                summary.append(f"- {file_path}: {file_data['lines']} lines, {classes_str}, {functions_str}")
        
        return '\n'.join(summary[:10])  # Limit to top 10 files
    
    def _generate_module_prompt(self, file_path: str) -> str:
        """Generate focused prompt for a specific module"""
        file_data = self.files_data[file_path]
        
        return f"""I'm analyzing a Python module: {file_path}

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


class FileAnalyzer(ast.NodeVisitor):
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
    parser = argparse.ArgumentParser(
        description="CodeSplain - Analyze Python projects and generate comprehensive summaries"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to Python project (default: current directory)"
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
    
    # Check if path exists and contains Python files
    project_path = Path(args.path).resolve()
    if not project_path.exists():
        print(f"❌ Error: Path {project_path} does not exist")
        sys.exit(1)
    
    python_files = list(project_path.rglob("*.py"))
    if not python_files:
        print(f"❌ Error: No Python files found in {project_path}")
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
        
        print("\n📊 Analysis Summary:")
        print(f"   Files analyzed: {len(analyzer.files_data)}")
        print(f"   Total lines: {sum(data['lines'] for data in analyzer.files_data.values()):,}")
        print(f"   Classes found: {sum(len(data['classes']) for data in analyzer.files_data.values())}")
        print(f"   Functions found: {sum(len(data['functions']) for data in analyzer.files_data.values())}")
        print(f"   Entry points: {len(analyzer.entry_points)}")
        
        print(f"\n📁 Results saved to: {analyzer.output_dir}")
        print("\n📋 Generated files:")
        print("   ├── OVERVIEW.md - Project summary and quick insights")
        print("   ├── STRUCTURE.md - Directory tree and file purposes")  
        print("   ├── DEPENDENCIES.md - Import relationships and dependencies")
        print("   ├── CALL_GRAPH.md - Function call relationships")
        print("   ├── API_SURFACE.md - Public interfaces and endpoints")
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
