"""Surveyor agent for static structure analysis."""

import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple
import networkx as nx

from models import ModuleNode, ImportEdge, ProvenanceMetadata
from analyzers.language_router import LanguageRouter
from analyzers.tree_sitter_analyzer import ModuleAnalyzer
from analyzers.git_velocity_analyzer import GitVelocityAnalyzer

logger = logging.getLogger(__name__)


class SurveyorAgent:
    """Orchestrates static analysis of repository structure."""
    
    def __init__(self):
        """Initialize surveyor agent."""
        self.analyzer = ModuleAnalyzer()
        self.router = LanguageRouter()
        self.errors: List[Dict[str, str]] = []
    
    def analyze_repository(self, repo_path: str) -> Tuple[nx.DiGraph, List[ModuleNode]]:
        """
        Analyze repository and extract module structure.
        
        Args:
            repo_path: Path to repository root
        
        Returns:
            Tuple of (module graph, list of module nodes)
        """
        repo_path_obj = Path(repo_path)
        
        # Find all supported files
        modules = []
        for file_path in self._find_supported_files(repo_path_obj):
            try:
                module = self.analyzer.analyze_module(str(file_path))
                modules.append(module)
            except Exception as e:
                logger.error(f"Failed to analyze {file_path}: {e}")
                self.errors.append({
                    'file': str(file_path),
                    'error': str(e),
                    'phase': 'module_analysis'
                })
        
        # Enrich with git velocity data
        git_analyzer = GitVelocityAnalyzer(repo_path)
        if git_analyzer.has_git:
            velocities = git_analyzer.get_all_file_velocities(days=90)
            for module in modules:
                # Get relative path from repo root
                rel_path = Path(module.path).relative_to(repo_path_obj)
                module.change_velocity = velocities.get(str(rel_path), 0)
        
        # Build module graph
        graph = self.build_module_graph(modules, repo_path)
        
        # Compute PageRank
        pagerank_scores = self.compute_pagerank(graph)
        
        # Store PageRank in node attributes
        for node_id, score in pagerank_scores.items():
            if graph.has_node(node_id):
                graph.nodes[node_id]['pagerank'] = score
        
        # Detect circular dependencies
        circular_deps = self.detect_circular_dependencies(graph)
        if circular_deps:
            logger.warning(f"Found {len(circular_deps)} circular dependency groups")
            for cycle in circular_deps:
                logger.warning(f"  Circular: {' -> '.join(cycle)}")
        
        # Identify dead code
        dead_code = self.identify_dead_code(graph, modules)
        for module in modules:
            if module.path in dead_code:
                module.is_dead_code_candidate = True
        
        return graph, modules
    
    def build_module_graph(self, modules: List[ModuleNode], repo_path: str) -> nx.DiGraph:
        """
        Build module dependency graph from analyzed modules.
        
        Args:
            modules: List of analyzed module nodes
            repo_path: Repository root path for resolving imports
        
        Returns:
            NetworkX directed graph with modules as nodes and imports as edges
        """
        graph = nx.DiGraph()
        
        # Add all modules as nodes
        for module in modules:
            graph.add_node(
                module.path,
                **module.model_dump(exclude={'provenance'})
            )
            # Store provenance separately if it exists
            if module.provenance:
                graph.nodes[module.path]['provenance'] = module.provenance.model_dump()
        
        # Add import edges
        repo_path_obj = Path(repo_path)
        module_paths = {m.path for m in modules}
        
        for module in modules:
            for import_name in module.imports:
                # Try to resolve import to actual file path
                target_path = self._resolve_import(
                    import_name,
                    module.path,
                    repo_path_obj,
                    module_paths
                )
                
                if target_path and target_path in module_paths:
                    # Determine import type
                    import_type = "relative" if import_name.startswith('.') else "absolute"
                    
                    # Create edge
                    if graph.has_edge(module.path, target_path):
                        # Increment import count
                        graph.edges[module.path, target_path]['import_count'] += 1
                    else:
                        # Add new edge
                        edge = ImportEdge(
                            source=module.path,
                            target=target_path,
                            import_count=1,
                            import_type=import_type,
                            provenance=ProvenanceMetadata(
                                evidence_type="tree_sitter",
                                source_file=module.path,
                                confidence=1.0 if import_type == "absolute" else 0.7,
                                resolution_status="resolved" if import_type == "absolute" else "partial"
                            )
                        )
                        graph.add_edge(
                            module.path,
                            target_path,
                            **edge.model_dump(exclude={'provenance'})
                        )
                        if edge.provenance:
                            graph.edges[module.path, target_path]['provenance'] = edge.provenance.model_dump()
        
        return graph
    
    def compute_pagerank(self, graph: nx.DiGraph) -> Dict[str, float]:
        """
        Compute PageRank scores for modules to identify architectural hubs.
        
        Args:
            graph: Module dependency graph
        
        Returns:
            Dictionary mapping module paths to PageRank scores
        """
        if len(graph.nodes) == 0:
            return {}
        
        try:
            # Use import_count as edge weight if available
            pagerank = nx.pagerank(graph, weight='import_count')
            return pagerank
        except:
            # Fallback to unweighted PageRank
            return nx.pagerank(graph)
    
    def detect_circular_dependencies(self, graph: nx.DiGraph) -> List[List[str]]:
        """
        Detect circular dependencies using strongly connected components.
        
        Args:
            graph: Module dependency graph
        
        Returns:
            List of circular dependency groups (each group is a list of module paths)
        """
        # Find strongly connected components
        sccs = list(nx.strongly_connected_components(graph))
        
        # Filter to only cycles (SCCs with more than one node)
        circular_deps = [list(scc) for scc in sccs if len(scc) > 1]
        
        return circular_deps
    
    def identify_dead_code(self, graph: nx.DiGraph, modules: List[ModuleNode]) -> Set[str]:
        """
        Identify dead code candidates (modules with exports but no imports).
        
        Args:
            graph: Module dependency graph
            modules: List of module nodes
        
        Returns:
            Set of module paths that are dead code candidates
        """
        dead_code = set()
        
        for module in modules:
            # Check if module has exports
            if module.exports:
                # Check if module has any incoming edges (is imported by anyone)
                if graph.in_degree(module.path) == 0:
                    # No one imports this module, but it has exports
                    dead_code.add(module.path)
        
        return dead_code
    
    def _find_supported_files(self, repo_path: Path) -> List[Path]:
        """Find all supported files in repository."""
        supported_extensions = {'.py', '.js', '.ts', '.sql', '.yaml', '.yml'}
        files = []
        
        # Directories to skip
        skip_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.tox'}
        
        for path in repo_path.rglob('*'):
            # Skip directories
            if path.is_dir():
                continue
            
            # Skip files in excluded directories
            if any(skip_dir in path.parts for skip_dir in skip_dirs):
                continue
            
            # Check if extension is supported
            if path.suffix in supported_extensions:
                files.append(path)
        
        return files
    
    def _resolve_import(
        self,
        import_name: str,
        source_file: str,
        repo_path: Path,
        module_paths: Set[str]
    ) -> str:
        """
        Resolve an import statement to an actual file path.
        
        Args:
            import_name: Import name (e.g., 'foo.bar' or '.baz')
            source_file: Path to file containing the import
            repo_path: Repository root path
            module_paths: Set of all known module paths
        
        Returns:
            Resolved file path, or None if not found
        """
        source_path = Path(source_file)
        
        # Handle relative imports
        if import_name.startswith('.'):
            # Get directory of source file
            source_dir = source_path.parent
            
            # Count leading dots
            level = len(import_name) - len(import_name.lstrip('.'))
            remaining = import_name.lstrip('.')
            
            # Go up 'level' directories
            target_dir = source_dir
            for _ in range(level - 1):
                target_dir = target_dir.parent
            
            # Construct target path
            if remaining:
                parts = remaining.split('.')
                target_path = target_dir / '/'.join(parts)
            else:
                target_path = target_dir
            
            # Try with .py extension
            if (target_path.with_suffix('.py')).exists():
                return str(target_path.with_suffix('.py'))
            
            # Try as package (__init__.py)
            init_path = target_path / '__init__.py'
            if init_path.exists():
                return str(init_path)
        
        # Handle absolute imports
        else:
            parts = import_name.split('.')
            
            # Try to find matching file in repo
            for module_path in module_paths:
                module_path_obj = Path(module_path)
                
                # Check if module name matches
                # This is a simplified heuristic - real resolution is complex
                if module_path_obj.stem == parts[-1]:
                    return module_path
        
        return None
