"""Module analyzer for extracting structure from Python files using tree-sitter."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from tree_sitter import Node, Parser

from models import ModuleNode, ProvenanceMetadata, FunctionNode
from analyzers.language_router import LanguageRouter


class ModuleAnalyzer:
    """Analyzes individual modules to extract structure and metadata."""
    
    def __init__(self):
        """Initialize module analyzer with language router."""
        self.router = LanguageRouter()
    
    def analyze_module(self, path: str) -> ModuleNode:
        """
        Analyze a module and extract its structure.
        
        Args:
            path: Path to the module file
        
        Returns:
            ModuleNode with extracted metadata
        """
        file_path = Path(path)
        extension = file_path.suffix
        
        if not self.router.is_supported(extension):
            raise ValueError(f"Unsupported file type: {extension}")
        
        # Read file content
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Get parser for this language
        parser = self.router.get_parser(extension)
        language = self.router.get_language_name(extension)
        
        # Parse the file
        if parser is not None:
            tree = parser.parse(bytes(content, 'utf8'))
            root = tree.root_node
            
            # Extract information based on language
            if language == 'python':
                return self._analyze_python_module(path, content, root)
            else:
                # For other languages, create basic module node
                return ModuleNode(
                    path=path,
                    language=language,
                    complexity_score=self.compute_complexity(root),
                    provenance=ProvenanceMetadata(
                        evidence_type="tree_sitter",
                        source_file=path,
                        confidence=1.0,
                        resolution_status="resolved"
                    )
                )
        else:
            # SQL/YAML files - basic node
            return ModuleNode(
                path=path,
                language=language,
                complexity_score=len(content.split('\n')),
                provenance=ProvenanceMetadata(
                    evidence_type="yaml_parse" if language == "yaml" else "sqlglot",
                    source_file=path,
                    confidence=1.0,
                    resolution_status="resolved"
                )
            )
    
    def _analyze_python_module(self, path: str, content: str, root: Node) -> ModuleNode:
        """Analyze a Python module."""
        imports = self.extract_imports(root, path)
        exports = self.extract_exports(root)
        docstring = self._extract_docstring(root)
        complexity = self.compute_complexity(root)
        
        # Get file modification time
        try:
            from datetime import datetime
            mtime = os.path.getmtime(path)
            last_modified = datetime.fromtimestamp(mtime)
        except:
            last_modified = None
        
        return ModuleNode(
            path=path,
            language="python",
            complexity_score=complexity,
            last_modified=last_modified,
            imports=imports,
            exports=exports,
            docstring=docstring,
            provenance=ProvenanceMetadata(
                evidence_type="tree_sitter",
                source_file=path,
                confidence=1.0,
                resolution_status="resolved"
            )
        )
    
    def extract_imports(self, ast: Node, source_file: str) -> List[str]:
        """
        Extract import statements from Python AST.
        
        Args:
            ast: Tree-sitter AST root node
            source_file: Path to source file for provenance
        
        Returns:
            List of imported module names
        """
        imports = []
        
        def visit_node(node: Node):
            # Handle 'import' statements: import foo, import foo.bar
            if node.type == 'import_statement':
                for child in node.children:
                    if child.type == 'dotted_name':
                        imports.append(self._get_node_text(child))
            
            # Handle 'from' imports: from foo import bar
            elif node.type == 'import_from_statement':
                module_name = None
                for child in node.children:
                    if child.type == 'dotted_name':
                        module_name = self._get_node_text(child)
                        break
                    elif child.type == 'relative_import':
                        # Relative import like 'from . import foo'
                        module_name = self._get_node_text(child)
                        break
                
                if module_name:
                    imports.append(module_name)
            
            # Recursively visit children
            for child in node.children:
                visit_node(child)
        
        visit_node(ast)
        return imports
    
    def extract_exports(self, ast: Node) -> List[str]:
        """
        Extract public functions and classes (exports).
        
        Args:
            ast: Tree-sitter AST root node
        
        Returns:
            List of exported symbol names (functions and classes without leading underscore)
        """
        exports = []
        
        def visit_node(node: Node, depth: int = 0):
            # Only look at top-level definitions (depth 0 or 1)
            if depth > 1:
                return
            
            # Function definitions
            if node.type == 'function_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = self._get_node_text(name_node)
                    # Only export public functions (no leading underscore)
                    if not name.startswith('_'):
                        exports.append(name)
            
            # Class definitions
            elif node.type == 'class_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = self._get_node_text(name_node)
                    # Only export public classes
                    if not name.startswith('_'):
                        exports.append(name)
            
            # Recursively visit children at module level
            if depth == 0:
                for child in node.children:
                    visit_node(child, depth + 1)
        
        visit_node(ast)
        return exports
    
    def extract_function_signatures(self, ast: Node, parent_module: str) -> List[FunctionNode]:
        """
        Extract function signatures with parameters and return types.
        
        Args:
            ast: Tree-sitter AST root node
            parent_module: Path to parent module
        
        Returns:
            List of FunctionNode instances
        """
        functions = []
        
        def visit_node(node: Node):
            if node.type == 'function_definition':
                name_node = node.child_by_field_name('name')
                params_node = node.child_by_field_name('parameters')
                return_type_node = node.child_by_field_name('return_type')
                
                if name_node:
                    name = self._get_node_text(name_node)
                    params = self._get_node_text(params_node) if params_node else "()"
                    return_type = self._get_node_text(return_type_node) if return_type_node else ""
                    
                    signature = f"{name}{params}"
                    if return_type:
                        signature += f" -> {return_type}"
                    
                    is_public = not name.startswith('_')
                    
                    functions.append(FunctionNode(
                        qualified_name=f"{parent_module}.{name}",
                        parent_module=parent_module,
                        signature=signature,
                        is_public_api=is_public,
                        line_range=(node.start_point[0], node.end_point[0]),
                        provenance=ProvenanceMetadata(
                            evidence_type="tree_sitter",
                            source_file=parent_module,
                            line_range=(node.start_point[0], node.end_point[0]),
                            confidence=1.0,
                            resolution_status="resolved"
                        )
                    ))
            
            # Recursively visit children
            for child in node.children:
                visit_node(child)
        
        visit_node(ast)
        return functions
    
    def extract_class_definitions(self, ast: Node) -> List[Dict[str, any]]:
        """
        Extract class definitions with inheritance.
        
        Args:
            ast: Tree-sitter AST root node
        
        Returns:
            List of dicts with class name and parent classes
        """
        classes = []
        
        def visit_node(node: Node):
            if node.type == 'class_definition':
                name_node = node.child_by_field_name('name')
                superclasses_node = node.child_by_field_name('superclasses')
                
                if name_node:
                    name = self._get_node_text(name_node)
                    parents = []
                    
                    if superclasses_node:
                        # Extract parent class names
                        for child in superclasses_node.children:
                            if child.type in ['identifier', 'attribute']:
                                parents.append(self._get_node_text(child))
                    
                    classes.append({
                        'name': name,
                        'parents': parents,
                        'line_range': (node.start_point[0], node.end_point[0])
                    })
            
            # Recursively visit children
            for child in node.children:
                visit_node(child)
        
        visit_node(ast)
        return classes
    
    def compute_complexity(self, ast: Node) -> int:
        """
        Compute complexity score using AST node count.
        
        Args:
            ast: Tree-sitter AST root node
        
        Returns:
            Complexity score (total node count)
        """
        def count_nodes(node: Node) -> int:
            count = 1
            for child in node.children:
                count += count_nodes(child)
            return count
        
        return count_nodes(ast)
    
    def _extract_docstring(self, ast: Node) -> Optional[str]:
        """Extract module-level docstring."""
        # Look for first expression statement with a string
        for child in ast.children:
            if child.type == 'expression_statement':
                for expr_child in child.children:
                    if expr_child.type == 'string':
                        # Remove quotes and return
                        text = self._get_node_text(expr_child)
                        # Remove triple quotes or single quotes
                        text = text.strip('"""').strip("'''").strip('"').strip("'")
                        return text.strip()
                break  # Only check first expression statement
        return None
    
    def _get_node_text(self, node: Node) -> str:
        """Get text content of a node."""
        return node.text.decode('utf8') if node.text else ""
