"""Navigator agent query tools with provenance tracking."""

import logging
from typing import Dict, List, Literal, Optional, Tuple, Any
import networkx as nx
import numpy as np
from sentence_transformers import SentenceTransformer

from models.models import ModuleNode, DatasetNode, TransformationNode, ProvenanceMetadata

logger = logging.getLogger(__name__)


class FindImplementationTool:
    """Semantic search over purpose statements with confidence scores."""
    
    def __init__(self, modules: List[ModuleNode], embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize semantic search tool.
        
        Args:
            modules: List of module nodes with purpose statements
            embedding_model: Sentence transformer model name
        """
        self.modules = modules
        self.model = SentenceTransformer(embedding_model)
        
        # Pre-compute embeddings for all purpose statements
        self.purpose_embeddings = {}
        self.modules_with_purpose = []
        
        for module in modules:
            if module.purpose_statement:
                self.modules_with_purpose.append(module)
                self.purpose_embeddings[module.path] = None  # Will compute lazily
        
        logger.info(f"Initialized FindImplementationTool with {len(self.modules_with_purpose)} modules")
    
    def __call__(self, concept: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Search for modules implementing a concept.
        
        Args:
            concept: Natural language description of what to find
            top_k: Number of top results to return
        
        Returns:
            Dictionary with results and provenance information
        """
        logger.info(f"Searching for concept: '{concept}'")
        
        if not self.modules_with_purpose:
            return {
                'results': [],
                'provenance': {
                    'evidence_type': 'heuristic',
                    'confidence': 0.0,
                    'resolution_status': 'inferred',
                    'message': 'No modules with purpose statements found'
                }
            }
        
        # Embed query
        query_embedding = self.embed_query(concept)
        
        # Search purposes — fetch more candidates to allow deduplication
        results = self.search_purposes(query_embedding, top_k * 3)
        
        # Deduplicate: keep only the highest-scoring file per model stem
        # e.g. customers.sql and customers.yml → keep whichever scores higher
        seen_stems: dict = {}
        deduped = []
        for module, score in results:
            import os
            stem = os.path.splitext(os.path.basename(module.path))[0]
            parent = os.path.basename(os.path.dirname(module.path))
            key = f"{parent}/{stem}"
            if key not in seen_stems:
                seen_stems[key] = True
                deduped.append((module, score))
            if len(deduped) >= top_k:
                break
        
        # Format results with provenance
        formatted_results = self.format_results(deduped)
        
        return {
            'query': concept,
            'results': formatted_results,
            'provenance': {
                'evidence_type': 'heuristic',
                'confidence': 0.8,  # Embedding similarity is heuristic
                'resolution_status': 'inferred',
                'method': 'sentence_transformer_embedding',
                'model': self.model._model_card_vars.get('model_name', 'unknown')
            }
        }
    
    def embed_query(self, concept: str) -> np.ndarray:
        """
        Embed query concept using sentence transformer.
        
        Args:
            concept: Natural language query
        
        Returns:
            Embedding vector
        """
        return self.model.encode(concept, convert_to_numpy=True)
    
    def search_purposes(self, query_embedding: np.ndarray, top_k: int) -> List[Tuple[ModuleNode, float]]:
        """
        Search purpose statements using cosine similarity.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of top results
        
        Returns:
            List of (module, similarity_score) tuples
        """
        # Compute embeddings for all purposes if not cached
        for module in self.modules_with_purpose:
            if self.purpose_embeddings[module.path] is None:
                self.purpose_embeddings[module.path] = self.model.encode(
                    module.purpose_statement,
                    convert_to_numpy=True
                )
        
        # Compute similarities
        similarities = []
        for module in self.modules_with_purpose:
            purpose_embedding = self.purpose_embeddings[module.path]
            similarity = np.dot(query_embedding, purpose_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(purpose_embedding)
            )
            similarities.append((module, float(similarity)))
        
        # Sort by similarity and return top k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def format_results(self, results: List[Tuple[ModuleNode, float]]) -> List[Dict[str, Any]]:
        """
        Format search results with provenance chain.
        
        Args:
            results: List of (module, similarity_score) tuples
        
        Returns:
            List of formatted result dictionaries
        """
        formatted = []
        
        for module, similarity in results:
            result = {
                'path': module.path,
                'purpose': module.purpose_statement,
                'similarity_score': round(similarity, 3),
                'domain_cluster': module.domain_cluster,
                'complexity_score': module.complexity_score,
                'provenance_chain': [
                    {
                        'source': 'purpose_statement',
                        'evidence_type': module.provenance.evidence_type,
                        'confidence': module.provenance.confidence,
                        'resolution_status': module.provenance.resolution_status,
                        'source_file': module.provenance.source_file
                    },
                    {
                        'source': 'semantic_search',
                        'evidence_type': 'heuristic',
                        'confidence': similarity,
                        'resolution_status': 'inferred',
                        'method': 'cosine_similarity'
                    }
                ]
            }
            formatted.append(result)
        
        return formatted


class TraceLineageTool:
    """Traverse lineage graph with provenance chain."""
    
    def __init__(self, lineage_graph: nx.DiGraph):
        """
        Initialize lineage traversal tool.
        
        Args:
            lineage_graph: Data lineage graph
        """
        self.lineage_graph = lineage_graph
        logger.info(f"Initialized TraceLineageTool with {lineage_graph.number_of_nodes()} nodes")
    
    def __call__(
        self,
        dataset: str,
        direction: Literal["upstream", "downstream"] = "downstream",
        max_depth: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Trace lineage for a dataset.
        
        Args:
            dataset: Dataset name or transformation ID
            direction: Traversal direction
            max_depth: Maximum traversal depth (None for unlimited)
        
        Returns:
            Dictionary with lineage information and provenance
        """
        logger.info(f"Tracing {direction} lineage for: {dataset}")
        
        if dataset not in self.lineage_graph:
            return {
                'dataset': dataset,
                'direction': direction,
                'nodes': [],
                'edges': [],
                'provenance': {
                    'evidence_type': 'heuristic',
                    'confidence': 0.0,
                    'resolution_status': 'inferred',
                    'message': f'Dataset {dataset} not found in lineage graph'
                }
            }
        
        # Traverse graph
        if direction == "upstream":
            subgraph = self.traverse_upstream(dataset, max_depth)
        else:
            subgraph = self.traverse_downstream(dataset, max_depth)
        
        # Format lineage with provenance
        formatted = self.format_lineage(subgraph, dataset, direction)
        
        return formatted
    
    def traverse_upstream(self, node: str, max_depth: Optional[int] = None) -> nx.DiGraph:
        """
        Traverse upstream (ancestors) from a node.
        
        Args:
            node: Starting node
            max_depth: Maximum depth to traverse
        
        Returns:
            Subgraph containing upstream nodes
        """
        if max_depth is None:
            # Get all ancestors
            ancestors = nx.ancestors(self.lineage_graph, node)
            ancestors.add(node)
            return self.lineage_graph.subgraph(ancestors).copy()
        else:
            # BFS with depth limit
            visited = {node}
            current_level = {node}
            
            for _ in range(max_depth):
                next_level = set()
                for n in current_level:
                    predecessors = set(self.lineage_graph.predecessors(n))
                    next_level.update(predecessors - visited)
                
                visited.update(next_level)
                current_level = next_level
                
                if not current_level:
                    break
            
            return self.lineage_graph.subgraph(visited).copy()
    
    def traverse_downstream(self, node: str, max_depth: Optional[int] = None) -> nx.DiGraph:
        """
        Traverse downstream (descendants) from a node.
        
        Args:
            node: Starting node
            max_depth: Maximum depth to traverse
        
        Returns:
            Subgraph containing downstream nodes
        """
        if max_depth is None:
            # Get all descendants
            descendants = nx.descendants(self.lineage_graph, node)
            descendants.add(node)
            return self.lineage_graph.subgraph(descendants).copy()
        else:
            # BFS with depth limit
            visited = {node}
            current_level = {node}
            
            for _ in range(max_depth):
                next_level = set()
                for n in current_level:
                    successors = set(self.lineage_graph.successors(n))
                    next_level.update(successors - visited)
                
                visited.update(next_level)
                current_level = next_level
                
                if not current_level:
                    break
            
            return self.lineage_graph.subgraph(visited).copy()
    
    def format_lineage(
        self,
        subgraph: nx.DiGraph,
        start_node: str,
        direction: str
    ) -> Dict[str, Any]:
        """
        Format lineage subgraph with provenance chain.
        
        Args:
            subgraph: Lineage subgraph
            start_node: Starting node
            direction: Traversal direction
        
        Returns:
            Formatted lineage dictionary
        """
        nodes = []
        edges = []
        
        # Extract node information with provenance
        for node_id in subgraph.nodes():
            node_data = subgraph.nodes[node_id]
            node_type = node_data.get('node_type', 'unknown')
            
            node_info = {
                'id': node_id,
                'type': node_type,
            }
            
            # Add provenance if available
            if 'provenance' in node_data:
                prov = node_data['provenance']
                if isinstance(prov, dict):
                    node_info['provenance'] = prov
                elif isinstance(prov, ProvenanceMetadata):
                    node_info['provenance'] = {
                        'evidence_type': prov.evidence_type,
                        'source_file': prov.source_file,
                        'line_range': prov.line_range,
                        'confidence': prov.confidence,
                        'resolution_status': prov.resolution_status
                    }
            
            # Add type-specific information
            if node_type == 'dataset':
                node_info['storage_type'] = node_data.get('storage_type')
                node_info['discovered_in'] = node_data.get('discovered_in')
            elif node_type == 'transformation':
                node_info['transformation_type'] = node_data.get('transformation_type')
                node_info['source_file'] = node_data.get('source_file')
                node_info['line_range'] = node_data.get('line_range')
            
            nodes.append(node_info)
        
        # Extract edge information with provenance
        for source, target in subgraph.edges():
            edge_data = subgraph.edges[source, target]
            edge_type = edge_data.get('edge_type', 'unknown')
            
            edge_info = {
                'source': source,
                'target': target,
                'type': edge_type,
            }
            
            # Add provenance if available
            if 'provenance' in edge_data:
                prov = edge_data['provenance']
                if isinstance(prov, dict):
                    edge_info['provenance'] = prov
                elif isinstance(prov, ProvenanceMetadata):
                    edge_info['provenance'] = {
                        'evidence_type': prov.evidence_type,
                        'source_file': prov.source_file,
                        'line_range': prov.line_range,
                        'confidence': prov.confidence,
                        'resolution_status': prov.resolution_status
                    }
            
            # Add confidence if available
            if 'confidence' in edge_data:
                edge_info['confidence'] = edge_data['confidence']
            
            edges.append(edge_info)
        
        return {
            'dataset': start_node,
            'direction': direction,
            'node_count': len(nodes),
            'edge_count': len(edges),
            'nodes': nodes,
            'edges': edges,
            'provenance': {
                'evidence_type': 'heuristic',
                'confidence': 0.9,  # Graph traversal is deterministic
                'resolution_status': 'resolved',
                'method': 'networkx_graph_traversal'
            }
        }


class BlastRadiusTool:
    """Compute downstream dependencies with provenance."""
    
    def __init__(self, module_graph: nx.DiGraph, lineage_graph: nx.DiGraph):
        """
        Initialize blast radius tool.
        
        Args:
            module_graph: Module dependency graph
            lineage_graph: Data lineage graph
        """
        self.module_graph = module_graph
        self.lineage_graph = lineage_graph
        logger.info(
            f"Initialized BlastRadiusTool with {module_graph.number_of_nodes()} modules, "
            f"{lineage_graph.number_of_nodes()} lineage nodes"
        )
    
    def __call__(self, module_path: str, include_data_lineage: bool = True) -> Dict[str, Any]:
        """
        Compute blast radius for a module.
        
        Args:
            module_path: Path to module
            include_data_lineage: Whether to include data lineage dependencies
        
        Returns:
            Dictionary with blast radius information and provenance
        """
        logger.info(f"Computing blast radius for: {module_path}")
        
        if module_path not in self.module_graph:
            # Fall back to lineage graph lookup
            if module_path in self.lineage_graph:
                try:
                    descendants = nx.descendants(self.lineage_graph, module_path)
                    affected = sorted(list(descendants))
                    return {
                        'module': module_path,
                        'affected_module_count': len(affected),
                        'affected_modules': affected,
                        'affected_dataset_count': len(affected),
                        'affected_datasets': [
                            {'name': n, **{k: v for k, v in self.lineage_graph.nodes[n].items()
                                           if k in ('storage_type', 'node_type', 'discovered_in')}}
                            for n in affected
                        ],
                        'provenance': {
                            'evidence_type': 'heuristic',
                            'confidence': 0.9,
                            'resolution_status': 'resolved',
                            'method': 'networkx_descendants',
                            'note': 'Blast radius computed from lineage graph (not module graph)'
                        }
                    }
                except nx.NetworkXError:
                    pass
            return {
                'module': module_path,
                'affected_module_count': 0,
                'affected_modules': [],
                'affected_dataset_count': 0,
                'affected_datasets': [],
                'provenance': {
                    'evidence_type': 'heuristic',
                    'confidence': 0.0,
                    'resolution_status': 'inferred',
                    'message': f'Module {module_path} not found in module graph or lineage graph'
                }
            }
        
        # Compute module dependencies
        module_radius = self.compute_module_radius(module_path)
        
        # Compute data lineage impact if requested
        data_radius = []
        if include_data_lineage:
            data_radius = self.compute_data_radius(module_path)
        
        # Format results
        formatted = self.format_blast_radius(module_path, module_radius, data_radius)
        
        return formatted
    
    def compute_module_radius(self, module_path: str) -> List[str]:
        """
        Compute downstream module dependencies.
        
        Args:
            module_path: Starting module path
        
        Returns:
            List of affected module paths
        """
        try:
            descendants = nx.descendants(self.module_graph, module_path)
            return sorted(list(descendants))
        except nx.NetworkXError:
            return []
    
    def compute_data_radius(self, module_path: str) -> List[Dict[str, Any]]:
        """
        Compute downstream data lineage impact.
        
        Args:
            module_path: Starting module path
        
        Returns:
            List of affected datasets with provenance
        """
        affected_datasets = []
        
        # Find transformations in this module
        transformations_in_module = []
        for node_id in self.lineage_graph.nodes():
            node_data = self.lineage_graph.nodes[node_id]
            if (node_data.get('node_type') == 'transformation' and
                node_data.get('source_file') == module_path):
                transformations_in_module.append(node_id)
        
        # For each transformation, find downstream datasets
        for trans_id in transformations_in_module:
            try:
                descendants = nx.descendants(self.lineage_graph, trans_id)
                for desc_id in descendants:
                    node_data = self.lineage_graph.nodes[desc_id]
                    if node_data.get('node_type') == 'dataset':
                        dataset_info = {
                            'name': desc_id,
                            'storage_type': node_data.get('storage_type'),
                            'discovered_in': node_data.get('discovered_in')
                        }
                        
                        # Add provenance if available
                        if 'provenance' in node_data:
                            prov = node_data['provenance']
                            if isinstance(prov, dict):
                                dataset_info['provenance'] = prov
                            elif isinstance(prov, ProvenanceMetadata):
                                dataset_info['provenance'] = {
                                    'evidence_type': prov.evidence_type,
                                    'source_file': prov.source_file,
                                    'confidence': prov.confidence,
                                    'resolution_status': prov.resolution_status
                                }
                        
                        affected_datasets.append(dataset_info)
            except nx.NetworkXError:
                continue
        
        return affected_datasets
    
    def format_blast_radius(
        self,
        module_path: str,
        module_radius: List[str],
        data_radius: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Format blast radius results with provenance.
        
        Args:
            module_path: Starting module
            module_radius: Affected modules
            data_radius: Affected datasets
        
        Returns:
            Formatted blast radius dictionary
        """
        return {
            'module': module_path,
            'affected_module_count': len(module_radius),
            'affected_modules': module_radius,
            'affected_dataset_count': len(data_radius),
            'affected_datasets': data_radius,
            'provenance': {
                'evidence_type': 'heuristic',
                'confidence': 0.9,  # Graph traversal is deterministic
                'resolution_status': 'resolved',
                'method': 'networkx_descendants',
                'note': 'Blast radius computed using graph traversal of module and lineage graphs'
            }
        }


class ExplainModuleTool:
    """Explain module purpose and metadata with provenance."""
    
    def __init__(self, modules: List[ModuleNode], module_graph: nx.DiGraph, lineage_graph: nx.DiGraph = None):
        """
        Initialize module explanation tool.
        
        Args:
            modules: List of module nodes
            module_graph: Module dependency graph
            lineage_graph: Data lineage graph (optional, for dbt/SQL context)
        """
        self.modules_by_path = {m.path: m for m in modules}
        self.module_graph = module_graph
        self.lineage_graph = lineage_graph
        logger.info(f"Initialized ExplainModuleTool with {len(modules)} modules")
    
    def __call__(self, path: str) -> Dict[str, Any]:
        """
        Explain a module's purpose and metadata.
        
        Args:
            path: Module path
        
        Returns:
            Dictionary with module information and provenance
        """
        logger.info(f"Explaining module: {path}")
        
        if path not in self.modules_by_path:
            return {
                'path': path,
                'found': False,
                'provenance': {
                    'evidence_type': 'heuristic',
                    'confidence': 0.0,
                    'resolution_status': 'inferred',
                    'message': f'Module {path} not found'
                }
            }
        
        module = self.modules_by_path[path]
        
        # Get module info
        module_info = self.get_module_info(module)
        
        # Format explanation
        formatted = self.format_explanation(module_info)
        
        return formatted
    
    def get_module_info(self, module: ModuleNode) -> Dict[str, Any]:
        """
        Extract module information with graph context.
        
        Args:
            module: Module node
        
        Returns:
            Dictionary with module information
        """
        info = {
            'path': module.path,
            'language': module.language,
            'purpose_statement': module.purpose_statement,
            'domain_cluster': module.domain_cluster,
            'complexity_score': module.complexity_score,
            'change_velocity': module.change_velocity,
            'is_dead_code_candidate': module.is_dead_code_candidate,
            'has_documentation_drift': module.has_documentation_drift,
            'last_modified': module.last_modified.isoformat() if module.last_modified else None,
            'imports': module.imports,
            'exports': module.exports,
            'docstring': module.docstring,
        }
        
        # Add graph context
        if module.path in self.module_graph:
            info['import_count'] = self.module_graph.in_degree(module.path)
            info['imported_by_count'] = self.module_graph.out_degree(module.path)
            info['imported_by'] = list(self.module_graph.successors(module.path))
        
        # Add lineage context for SQL/dbt models
        if hasattr(self, 'lineage_graph') and self.lineage_graph is not None:
            # Find the dataset node matching this file
            for node_id in self.lineage_graph.nodes():
                node_data = self.lineage_graph.nodes[node_id]
                src = node_data.get('discovered_in', '') or node_data.get('source_file', '') or ''
                if src and (module.path.endswith(src) or src in module.path):
                    if node_data.get('node_type') == 'dataset':
                        # Find transformation that produces this dataset
                        producers = [u for u, v in self.lineage_graph.in_edges(node_id)
                                     if self.lineage_graph.nodes[u].get('node_type') == 'transformation']
                        consumers = [v for u, v in self.lineage_graph.out_edges(node_id)
                                     if self.lineage_graph.nodes[v].get('node_type') == 'transformation']
                        if producers or consumers:
                            info['lineage_node'] = node_id
                            info['consumed_by'] = [self.lineage_graph.nodes[t].get('source_file', t)
                                                   for t in consumers]
                            info['produced_from'] = [self.lineage_graph.nodes[p].get('source_datasets', [])
                                                     for p in producers]
                            break
        
        # Add provenance
        info['provenance'] = {
            'evidence_type': module.provenance.evidence_type,
            'source_file': module.provenance.source_file,
            'line_range': module.provenance.line_range,
            'confidence': module.provenance.confidence,
            'resolution_status': module.provenance.resolution_status
        }
        
        return info
    
    def format_explanation(self, module_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format module explanation with provenance chain.
        
        Args:
            module_info: Module information dictionary
        
        Returns:
            Formatted explanation
        """
        # Build provenance chain
        provenance_chain = [module_info['provenance']]
        
        # Add purpose statement provenance if available
        if module_info.get('purpose_statement'):
            provenance_chain.append({
                'source': module_info['provenance'].get('source_file', ''),
                'evidence_type': 'llm',
                'confidence': 0.7,
                'resolution_status': 'inferred',
                'line_range': module_info['provenance'].get('line_range'),
                'note': 'Purpose statement generated by LLM from source file'
            })
        
        # Add domain cluster provenance if available
        if module_info.get('domain_cluster'):
            provenance_chain.append({
                'source': module_info['provenance'].get('source_file', ''),
                'evidence_type': 'heuristic',
                'confidence': 0.8,
                'resolution_status': 'inferred',
                'line_range': None,
                'note': 'Domain cluster assigned by k-means clustering on purpose embeddings'
            })
        
        return {
            'found': True,
            'module': module_info,
            'provenance_chain': provenance_chain,
            'summary': self._generate_summary(module_info)
        }
    
    def _generate_summary(self, module_info: Dict[str, Any]) -> str:
        """
        Generate human-readable summary.
        
        Args:
            module_info: Module information
        
        Returns:
            Summary string
        """
        lines = []
        
        lines.append(f"Module: {module_info['path']}")
        lines.append(f"Language: {module_info['language']}")
        
        if module_info.get('purpose_statement'):
            lines.append(f"\nPurpose: {module_info['purpose_statement']}")
        
        if module_info.get('domain_cluster'):
            lines.append(f"Domain: {module_info['domain_cluster']}")
        
        lines.append(f"\nComplexity: {module_info['complexity_score']}")
        
        if module_info.get('change_velocity'):
            lines.append(f"Change Velocity: {module_info['change_velocity']} commits")
        
        # Show lineage context for SQL/dbt models, import context for Python
        if module_info.get('lineage_node'):
            lines.append(f"Lineage node: {module_info['lineage_node']}")
            if module_info.get('produced_from'):
                sources = [s for sublist in module_info['produced_from'] for s in sublist]
                if sources:
                    lines.append(f"Consumes: {', '.join(sources[:6])}")
            if module_info.get('consumed_by'):
                lines.append(f"Consumed by: {', '.join(module_info['consumed_by'][:4])}")
        elif module_info.get('import_count') is not None:
            lines.append(f"Imports: {module_info['import_count']} modules")
            lines.append(f"Imported by: {module_info['imported_by_count']} modules")
        
        if module_info.get('is_dead_code_candidate'):
            lines.append("\n⚠️  Flagged as potential dead code")
        
        if module_info.get('has_documentation_drift'):
            lines.append("⚠️  Documentation drift detected")
        
        return '\n'.join(lines)


class NavigatorAgent:
    """
    Navigator agent for querying the knowledge graph.
    
    Provides a unified interface for semantic search, lineage traversal,
    blast radius analysis, and module explanation with full provenance tracking.
    """
    
    def __init__(
        self,
        modules: List[ModuleNode],
        module_graph: nx.DiGraph,
        lineage_graph: nx.DiGraph
    ):
        """
        Initialize NavigatorAgent with knowledge graphs.
        
        Args:
            modules: List of module nodes with purpose statements
            module_graph: Module dependency graph
            lineage_graph: Data lineage graph
        """
        self.modules = modules
        self.module_graph = module_graph
        self.lineage_graph = lineage_graph
        
        # Initialize tools
        self.tools = self.create_tools()
        
        logger.info(
            f"Initialized NavigatorAgent with {len(modules)} modules, "
            f"{module_graph.number_of_nodes()} module nodes, "
            f"{lineage_graph.number_of_nodes()} lineage nodes"
        )
    
    def create_tools(self) -> Dict[str, Any]:
        """
        Create and register all four query tools.
        
        Returns:
            Dictionary mapping tool names to tool instances
        """
        tools = {
            'find_implementation': FindImplementationTool(self.modules),
            'trace_lineage': TraceLineageTool(self.lineage_graph),
            'blast_radius': BlastRadiusTool(self.module_graph, self.lineage_graph),
            'explain_module': ExplainModuleTool(self.modules, self.module_graph, self.lineage_graph)
        }
        
        logger.info(f"Created {len(tools)} query tools")
        return tools
    
    def run_query(self, query: str, tool_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Execute a single query using the appropriate tool.
        
        Args:
            query: Natural language query or specific parameter
            tool_name: Specific tool to use (optional, auto-detected if not provided)
            **kwargs: Additional tool-specific parameters
        
        Returns:
            Query results with provenance information
        """
        logger.info(f"Running query: '{query}' with tool: {tool_name}")
        
        # Auto-detect tool if not specified
        if tool_name is None:
            tool_name = self._detect_tool(query)
            logger.info(f"Auto-detected tool: {tool_name}")
        
        # Validate tool name
        if tool_name not in self.tools:
            return {
                'error': f"Unknown tool: {tool_name}",
                'available_tools': list(self.tools.keys()),
                'provenance': {
                    'evidence_type': 'heuristic',
                    'confidence': 0.0,
                    'resolution_status': 'inferred',
                    'message': 'Tool not found'
                }
            }
        
        # Execute query with appropriate tool
        try:
            tool = self.tools[tool_name]
            
            # Route to appropriate tool with parameters
            if tool_name == 'find_implementation':
                top_k = kwargs.get('top_k', 5)
                result = tool(query, top_k=top_k)
            
            elif tool_name == 'trace_lineage':
                max_depth = kwargs.get('max_depth', None)
                # Extract dataset name from natural language query
                dataset = self._extract_dataset_name(query)
                # Use explicit direction kwarg if provided; otherwise infer from query
                if 'direction' in kwargs:
                    direction = kwargs['direction']
                else:
                    query_lower = query.lower()
                    if any(kw in query_lower for kw in ['downstream', 'descendants', 'consumers', 'feeds into', 'impacts']):
                        direction = 'downstream'
                    else:
                        direction = 'upstream'
                result = tool(dataset, direction=direction, max_depth=max_depth)
            
            elif tool_name == 'blast_radius':
                include_data_lineage = kwargs.get('include_data_lineage', True)
                module_path = self._extract_dataset_name(query)
                result = tool(module_path, include_data_lineage=include_data_lineage)
            
            elif tool_name == 'explain_module':
                module_path = self._extract_dataset_name(query)
                result = tool(module_path)
            
            else:
                result = tool(query)
            
            # Add query metadata
            result['query_metadata'] = {
                'original_query': query,
                'tool_used': tool_name,
                'parameters': kwargs
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Error executing query: {e}", exc_info=True)
            return {
                'error': str(e),
                'query': query,
                'tool': tool_name,
                'provenance': {
                    'evidence_type': 'heuristic',
                    'confidence': 0.0,
                    'resolution_status': 'inferred',
                    'message': f'Query execution failed: {str(e)}'
                }
            }
    
    def _extract_dataset_name(self, query: str) -> str:
        """
        Extract a dataset/node name or file path from a natural language query.

        Tries to match known graph nodes first (longest match wins); also
        detects file paths embedded in the query; falls back to the last token.
        """
        query_lower = query.lower()

        # Check for an embedded file path (contains '/' or '.sql'/'.py'/'.yml')
        import re
        path_match = re.search(r'[\w./\-]+(?:/[\w./\-]+)+', query)
        if path_match:
            candidate = path_match.group(0).rstrip('.')
            # Check module graph first (full paths)
            if candidate in self.tools['explain_module'].modules_by_path:
                return candidate
            # Try with absolute prefix from known modules
            for known_path in self.tools['explain_module'].modules_by_path:
                if known_path.endswith(candidate) or candidate in known_path:
                    return known_path

        # Try to match a known lineage node name (longest match wins)
        known_nodes = list(self.tools['trace_lineage'].lineage_graph.nodes())
        matches = [n for n in known_nodes if n.lower() in query_lower]
        if matches:
            return max(matches, key=len)

        # Fallback: last token
        tokens = query.strip().split()
        return tokens[-1] if tokens else query

    def _detect_tool(self, query: str) -> str:
        """
        Auto-detect appropriate tool based on query keywords.
        
        Args:
            query: Natural language query
        
        Returns:
            Tool name
        """
        query_lower = query.lower()
        
        # Lineage / provenance questions
        if any(kw in query_lower for kw in [
            'lineage', 'upstream', 'downstream', 'trace', 'flow',
            'produces', 'produced by', 'what produces', 'where does',
            'comes from', 'source of', 'feeds into', 'depends on',
            'what creates', 'what generates', 'origin of'
        ]):
            return 'trace_lineage'
        
        # Blast radius / impact questions
        if any(kw in query_lower for kw in [
            'blast', 'impact', 'affect', 'break', 'change',
            'dependency', 'what breaks', 'if i change', 'cascade'
        ]):
            return 'blast_radius'
        
        # Module explanation questions
        if any(kw in query_lower for kw in [
            'explain', 'what is', 'what does', 'module', 'info',
            'metadata', 'describe', 'tell me about'
        ]):
            return 'explain_module'
        
        # Default to semantic search
        return 'find_implementation'
    
    def interactive_mode(self):
        """
        Launch interactive query mode for continuous querying.
        
        Provides a REPL-style interface for exploring the knowledge graph.
        """
        print("\n" + "=" * 80)
        print("Navigator Interactive Mode")
        print("=" * 80)
        print("\nAvailable tools:")
        print("  1. find_implementation - Semantic search over purpose statements")
        print("  2. trace_lineage - Traverse data lineage upstream/downstream")
        print("  3. blast_radius - Compute downstream dependencies")
        print("  4. explain_module - Explain module purpose and metadata")
        print("\nCommands:")
        print("  help - Show this help message")
        print("  tools - List available tools")
        print("  exit/quit - Exit interactive mode")
        print("\nQuery format:")
        print("  <query>                    - Auto-detect tool")
        print("  <tool_name>: <query>       - Use specific tool")
        print("=" * 80)
        
        while True:
            try:
                # Get user input
                user_input = input("\n🔍 Query> ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() in ['exit', 'quit']:
                    print("\nExiting interactive mode...")
                    break
                
                if user_input.lower() == 'help':
                    self._print_help()
                    continue
                
                if user_input.lower() == 'tools':
                    self._print_tools()
                    continue
                
                # Parse query
                tool_name = None
                query = user_input
                
                if ':' in user_input:
                    parts = user_input.split(':', 1)
                    potential_tool = parts[0].strip()
                    if potential_tool in self.tools:
                        tool_name = potential_tool
                        query = parts[1].strip()
                
                # Execute query
                result = self.run_query(query, tool_name=tool_name)
                
                # Display results
                self._display_result(result)
            
            except KeyboardInterrupt:
                print("\n\nInterrupted. Type 'exit' to quit.")
                continue
            
            except Exception as e:
                logger.error(f"Error in interactive mode: {e}", exc_info=True)
                print(f"\n❌ Error: {e}")
    
    def _print_help(self):
        """Print help message."""
        print("\n" + "=" * 80)
        print("Navigator Help")
        print("=" * 80)
        print("\nTool Usage:")
        print("\n1. find_implementation")
        print("   Example: find_implementation: user authentication")
        print("   Example: where is payment processing")
        print("\n2. trace_lineage")
        print("   Example: trace_lineage: raw_events")
        print("   Example: show lineage for analytics_users")
        print("\n3. blast_radius")
        print("   Example: blast_radius: src/db/users.py")
        print("   Example: what breaks if I change src/auth/login.py")
        print("\n4. explain_module")
        print("   Example: explain_module: src/api/endpoints.py")
        print("   Example: what does src/utils/crypto.py do")
        print("=" * 80)
    
    def _print_tools(self):
        """Print available tools."""
        print("\n" + "=" * 80)
        print("Available Tools")
        print("=" * 80)
        for tool_name, tool in self.tools.items():
            print(f"\n{tool_name}:")
            print(f"  Type: {type(tool).__name__}")
            print(f"  Description: {tool.__class__.__doc__.strip()}")
        print("=" * 80)
    
    def _display_result(self, result: Dict[str, Any]):
        """Display query result with natural-language answer and full evidence citations."""
        print("\n" + "-" * 80)

        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            if 'available_tools' in result:
                print(f"Available tools: {', '.join(result['available_tools'])}")
            print("-" * 80)
            return

        metadata = result.get('query_metadata', {})
        tool_used = metadata.get('tool_used', 'unknown')
        original_query = metadata.get('original_query', '')

        print(f"Tool: {tool_used}")
        print(f"Query: {original_query}")

        def fmt_evidence(prov: dict, label: str = "") -> str:
            """Format a single provenance dict as a citation line."""
            if not prov:
                return ""
            ev = prov.get('evidence_type', '?')
            conf = prov.get('confidence', 0.0)
            src = prov.get('source_file', '') or ''
            lr = prov.get('line_range')
            status = prov.get('resolution_status', '')
            # Trust label
            if ev in ('tree_sitter', 'sqlglot', 'yaml_parse'):
                trust = 'static-analysis'
            elif ev == 'llm':
                trust = 'llm-inference'
            else:
                trust = 'heuristic'
            src_short = src.split('/')[-1] if src else ''
            line_part = f":{lr[0]}-{lr[1]}" if lr else ""
            prefix = f"[{label}] " if label else ""
            return f"  {prefix}evidence={trust}({ev})  conf={conf:.2f}  status={status}  file={src_short}{line_part}"

        # ── FindImplementationTool ──────────────────────────────────────────
        if 'results' in result:
            results = result['results']
            if not results:
                print("\nNo matching modules found.")
            else:
                print(f"\nFound {len(results)} result(s):\n")
                for i, res in enumerate(results[:5], 1):
                    path = res['path']
                    score = res['similarity_score']
                    purpose = res.get('purpose', '')
                    domain = res.get('domain_cluster', '')
                    prov = res.get('provenance', {})
                    src_file = prov.get('source_file', path)
                    lr = prov.get('line_range')
                    line_part = f":{lr[0]}-{lr[1]}" if lr else ""
                    print(f"  {i}. {src_file}{line_part}")
                    if domain:
                        print(f"     Domain: {domain}  |  Similarity: {score:.3f}")
                    if purpose:
                        wrapped = purpose if len(purpose) <= 220 else purpose[:217] + '...'
                        print(f"     {wrapped}")
                    ev = prov.get('evidence_type', '?')
                    conf = prov.get('confidence', 0.0)
                    src = prov.get('source_file', '') or path
                    status = prov.get('resolution_status', '')
                    print(f"  Provenance: evidence={ev}  conf={conf:.2f}  status={status}  file={src}")
                    print()

        # ── TraceLineageTool ────────────────────────────────────────────────
        elif 'nodes' in result and 'direction' in result:
            direction = result.get('direction', 'upstream')
            node_count = result.get('node_count', 0)
            edge_count = result.get('edge_count', 0)
            dataset = result.get('dataset', '')
            nodes = result.get('nodes', [])

            print(f"\nLineage: {direction} from `{dataset}`")
            print(f"Nodes: {node_count}  Edges: {edge_count}")

            if node_count <= 1:
                if direction == 'downstream':
                    print(f"\n`{dataset}` is a terminal sink — nothing depends on it downstream.")
                else:
                    print(f"\n`{dataset}` has no upstream dependencies — it is a raw source.")
            else:
                datasets = [n for n in nodes if n.get('type') == 'dataset' and n['id'] != dataset]
                transforms = [n for n in nodes if n.get('type') == 'transformation']
                direction_word = "upstream ancestors" if direction == 'upstream' else "downstream dependents"
                print(f"\n`{dataset}` has {node_count - 1} {direction_word} across {edge_count} edges.")
                if datasets:
                    ds_names = ', '.join(f"`{n['id']}`" for n in datasets[:6])
                    suffix = f" (and {len(datasets)-6} more)" if len(datasets) > 6 else ""
                    print(f"Datasets:        {ds_names}{suffix}")
                if transforms:
                    tr_names = ', '.join(f"`{n['id']}`" for n in transforms[:4])
                    suffix = f" (and {len(transforms)-4} more)" if len(transforms) > 4 else ""
                    print(f"Transformations: {tr_names}{suffix}")

            if nodes and node_count > 1:
                print(f"\nEvidence citations ({min(node_count, 12)} of {node_count}):")
                for node in nodes[:12]:
                    prov = node.get('provenance', {})
                    ev = prov.get('evidence_type', '?')
                    conf = prov.get('confidence', 0.0)
                    src = prov.get('source_file', '') or ''
                    lr = prov.get('line_range')
                    status = prov.get('resolution_status', '')
                    if ev in ('tree_sitter', 'sqlglot', 'yaml_parse'):
                        trust = 'static'
                    elif ev == 'llm':
                        trust = 'llm'
                    else:
                        trust = 'heuristic'
                    src_short = src.split('/')[-1] if src else '—'
                    line_part = f":{lr[0]}-{lr[1]}" if lr else ""
                    print(f"  {node['id']:30s}  [{trust}/{ev}  {conf:.2f}  {src_short}{line_part}  {status}]")

        # ── BlastRadiusTool ─────────────────────────────────────────────────
        elif 'affected_modules' in result:
            module = result['module']
            amc = result.get('affected_module_count', 0)
            affected = result.get('affected_modules', [])
            affected_datasets = result.get('affected_datasets', [])
            ds_map = {d.get('name', ''): d for d in affected_datasets if isinstance(d, dict)}

            print(f"\nModule: {module}")
            print(f"Affected modules: {amc}")

            if amc == 0:
                print(f"\n`{module}` has no downstream dependents — safe to change in isolation.")
            else:
                print(f"\nBreaking `{module}` cascades to {amc} downstream node(s):\n")
                for item in affected[:15]:
                    name = item if isinstance(item, str) else item.get('name', str(item))
                    ds = ds_map.get(name, {})
                    prov = ds.get('provenance', {})
                    ev = prov.get('evidence_type', '?')
                    conf = prov.get('confidence', 0.0)
                    src = prov.get('source_file', ds.get('discovered_in', '')) or ''
                    lr = prov.get('line_range')
                    if ev in ('tree_sitter', 'sqlglot', 'yaml_parse'):
                        trust = 'static'
                    elif ev == 'llm':
                        trust = 'llm'
                    else:
                        trust = 'heuristic'
                    src_short = src.split('/')[-1] if src else '—'
                    line_part = f":{lr[0]}-{lr[1]}" if lr else ""
                    node_type = ds.get('node_type', '')
                    type_label = f" ({node_type})" if node_type else ""
                    print(f"  - {name}{type_label}")
                    if ev != '?':
                        print(f"    [{trust}/{ev}  conf={conf:.2f}  file={src_short}{line_part}]")
                if amc > 15:
                    print(f"  ... and {amc - 15} more")

        # ── ExplainModuleTool ───────────────────────────────────────────────
        elif 'summary' in result:
            module_info = result.get('module', {})
            prov_chain = result.get('provenance_chain', [])

            print(f"\n{result['summary']}")

            if prov_chain:
                print("\nEvidence citations:")
                labels = ['structure', 'purpose', 'domain']
                for i, p in enumerate(prov_chain):
                    ev = p.get('evidence_type', '?')
                    conf = p.get('confidence', 0.0)
                    src = p.get('source', p.get('source_file', '')) or ''
                    lr = p.get('line_range')
                    status = p.get('resolution_status', '')
                    if ev in ('tree_sitter', 'sqlglot', 'yaml_parse'):
                        trust = 'static-analysis'
                    elif ev == 'llm':
                        trust = 'llm-inference'
                    else:
                        trust = 'heuristic'
                    src_short = src.split('/')[-1] if '/' in src else src
                    line_part = f":{lr[0]}-{lr[1]}" if lr else ""
                    label = labels[i] if i < len(labels) else f"step{i}"
                    print(f"  [{label}]  method={trust}({ev})  conf={conf:.2f}  status={status}  file={src_short}{line_part}")

        elif result.get('found') is False:
            path = result.get('path', '')
            msg = result.get('provenance', {}).get('message', 'not found')
            print(f"\n`{path}` — {msg}")
            modules_by_path = self.tools['explain_module'].modules_by_path
            query_lower = path.lower()
            suggestions = [p for p in modules_by_path if query_lower.split('/')[-1] in p.lower()][:3]
            if suggestions:
                print("Did you mean:")
                for s in suggestions:
                    print(f"  - {s}")

        else:
            for k, v in result.items():
                if k not in ('query_metadata', 'provenance'):
                    print(f"  {k}: {v}")

        print("-" * 80)
