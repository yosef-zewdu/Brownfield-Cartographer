"""Hydrologist agent for data lineage analysis."""

import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple
import networkx as nx

from models import DatasetNode, TransformationNode, ConsumesEdge, ProducesEdge, ProvenanceMetadata
from analyzers.python_data_flow_analyzer import PythonDataFlowAnalyzer
from analyzers.sql_lineage import SQLLineageAnalyzer
from analyzers.dbt_project_analyzer import DBTProjectAnalyzer
from analyzers.dag_config_parser import AirflowDAGAnalyzer

logger = logging.getLogger(__name__)


class HydrologistAgent:
    """Orchestrates data lineage analysis across Python, SQL, and configuration files."""
    
    def __init__(self):
        """Initialize hydrologist agent with all analyzers."""
        self.python_analyzer = PythonDataFlowAnalyzer()
        self.sql_analyzer = SQLLineageAnalyzer()
        self.dbt_analyzer = DBTProjectAnalyzer()
        self.airflow_analyzer = AirflowDAGAnalyzer()
        self.errors: List[Dict[str, str]] = []
    
    def analyze_repository(self, repo_path: str, module_graph: nx.DiGraph) -> Tuple[nx.DiGraph, List[DatasetNode], List[TransformationNode]]:
        """
        Analyze repository to coordinate all data lineage analyzers.
        
        Args:
            repo_path: Path to repository root
            module_graph: Module dependency graph from Surveyor agent
        
        Returns:
            Tuple of (lineage graph, dataset nodes, transformation nodes)
        """
        repo_path_obj = Path(repo_path)
        
        all_datasets = []
        all_transformations = []
        
        # Check if this is a dbt project
        if self.dbt_analyzer.detect_dbt_project(repo_path):
            logger.info("Detected dbt project, analyzing dbt models")
            try:
                dbt_datasets, dbt_transformations = self.dbt_analyzer.analyze_project(repo_path)
                all_datasets.extend(dbt_datasets)
                all_transformations.extend(dbt_transformations)
            except Exception as e:
                logger.error(f"Failed to analyze dbt project: {e}")
                self.errors.append({
                    'component': 'dbt_analyzer',
                    'error': str(e),
                    'phase': 'dbt_analysis'
                })
        
        # Analyze all Python files for data flow
        for python_file in repo_path_obj.rglob('*.py'):
            # Skip virtual environments and cache directories
            if any(skip in python_file.parts for skip in ['.venv', 'venv', '__pycache__', '.tox', 'node_modules']):
                continue
            
            try:
                # Check if this is an Airflow DAG
                if self.airflow_analyzer.detect_airflow_dag(str(python_file)):
                    logger.info(f"Detected Airflow DAG in {python_file}")
                    airflow_tasks, airflow_datasets = self.airflow_analyzer.analyze_dag_file(str(python_file))
                    all_transformations.extend(airflow_tasks)
                    all_datasets.extend(airflow_datasets)
                else:
                    # Regular Python data flow analysis
                    transformations = self.python_analyzer.analyze_file(str(python_file))
                    all_transformations.extend(transformations)
            except Exception as e:
                logger.error(f"Failed to analyze Python file {python_file}: {e}")
                self.errors.append({
                    'file': str(python_file),
                    'error': str(e),
                    'phase': 'python_analysis'
                })
        
        # Analyze all SQL files
        for sql_file in repo_path_obj.rglob('*.sql'):
            # Skip if in dbt models directory (already handled by dbt analyzer)
            if self.dbt_analyzer.models_dir and self.dbt_analyzer.models_dir in sql_file.parents:
                continue
            
            # Skip virtual environments and cache directories
            if any(skip in sql_file.parts for skip in ['.venv', 'venv', '__pycache__', '.tox', 'node_modules']):
                continue
            
            try:
                transformations = self.sql_analyzer.analyze_file(str(sql_file))
                all_transformations.extend(transformations)
            except Exception as e:
                logger.error(f"Failed to analyze SQL file {sql_file}: {e}")
                self.errors.append({
                    'file': str(sql_file),
                    'error': str(e),
                    'phase': 'sql_analysis'
                })
        
        # Extract datasets from transformations
        dataset_names = set()
        for transformation in all_transformations:
            dataset_names.update(transformation.source_datasets)
            dataset_names.update(transformation.target_datasets)
        
        # Create DatasetNode instances for datasets not already in all_datasets
        existing_dataset_names = {ds.name for ds in all_datasets}
        for dataset_name in dataset_names:
            if dataset_name not in existing_dataset_names and dataset_name:
                # Create a basic dataset node with inferred provenance
                all_datasets.append(DatasetNode(
                    name=dataset_name,
                    storage_type="table",  # Default assumption
                    discovered_in="inferred_from_transformations",
                    provenance=ProvenanceMetadata(
                        evidence_type="heuristic",
                        source_file="inferred_from_transformations",
                        confidence=0.5,
                        resolution_status="inferred"
                    )
                ))
        
        # Build lineage graph
        lineage_graph = self.build_lineage_graph(all_datasets, all_transformations)
        
        return lineage_graph, all_datasets, all_transformations
    
    def build_lineage_graph(self, datasets: List[DatasetNode], transformations: List[TransformationNode]) -> nx.DiGraph:
        """
        Build unified data lineage graph using NetworkX DiGraph.
        
        Creates CONSUMES and PRODUCES edges between transformations and datasets.
        
        Args:
            datasets: List of dataset nodes
            transformations: List of transformation nodes
        
        Returns:
            NetworkX directed graph with datasets and transformations as nodes
        """
        graph = nx.DiGraph()
        
        # Add dataset nodes
        for dataset in datasets:
            graph.add_node(
                dataset.name,
                node_type='dataset',
                **dataset.model_dump(exclude={'provenance'})
            )
            # Store provenance separately
            if dataset.provenance:
                graph.nodes[dataset.name]['provenance'] = dataset.provenance.model_dump()
        
        # Add transformation nodes
        for transformation in transformations:
            graph.add_node(
                transformation.id,
                node_type='transformation',
                **transformation.model_dump(exclude={'provenance'})
            )
            # Store provenance separately
            if transformation.provenance:
                graph.nodes[transformation.id]['provenance'] = transformation.provenance.model_dump()
        
        # Create CONSUMES edges (dataset -> transformation)
        edges_created = 0
        for transformation in transformations:
            for source_dataset in transformation.source_datasets:
                if source_dataset and graph.has_node(source_dataset):
                    edge = ConsumesEdge(
                        source=transformation.id,
                        target=source_dataset,
                        confidence=transformation.provenance.confidence,
                        provenance=transformation.provenance
                    )
                    graph.add_edge(
                        source_dataset,
                        transformation.id,
                        edge_type='consumes',
                        **edge.model_dump(exclude={'provenance'})
                    )
                    graph.edges[source_dataset, transformation.id]['provenance'] = edge.provenance.model_dump()
                    edges_created += 1
                elif source_dataset:
                    logger.warning(f"Source dataset '{source_dataset}' not found in graph for transformation {transformation.id}")
        
        logger.info(f"Created {edges_created} CONSUMES edges")
        
        # Create PRODUCES edges (transformation -> dataset)
        edges_created = 0
        for transformation in transformations:
            for target_dataset in transformation.target_datasets:
                if target_dataset and graph.has_node(target_dataset):
                    edge = ProducesEdge(
                        source=transformation.id,
                        target=target_dataset,
                        confidence=transformation.provenance.confidence,
                        provenance=transformation.provenance
                    )
                    graph.add_edge(
                        transformation.id,
                        target_dataset,
                        edge_type='produces',
                        **edge.model_dump(exclude={'provenance'})
                    )
                    graph.edges[transformation.id, target_dataset]['provenance'] = edge.provenance.model_dump()
                    edges_created += 1
                elif target_dataset:
                    logger.warning(f"Target dataset '{target_dataset}' not found in graph for transformation {transformation.id}")
        
        logger.info(f"Created {edges_created} PRODUCES edges")
        logger.info(f"Final graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
        
        return graph
    
    def find_sources(self, graph: nx.DiGraph) -> List[str]:
        """
        Find source nodes (nodes with in-degree zero).
        
        Args:
            graph: Data lineage graph
        
        Returns:
            List of source node IDs
        """
        sources = []
        for node in graph.nodes():
            if graph.in_degree(node) == 0:
                sources.append(node)
        return sources
    
    def find_sinks(self, graph: nx.DiGraph) -> List[str]:
        """
        Find sink nodes (nodes with out-degree zero).
        
        Args:
            graph: Data lineage graph
        
        Returns:
            List of sink node IDs
        """
        sinks = []
        for node in graph.nodes():
            if graph.out_degree(node) == 0:
                sinks.append(node)
        return sinks
    
    def compute_blast_radius(self, graph: nx.DiGraph, node: str) -> nx.DiGraph:
        """
        Compute blast radius using BFS/descendants.
        
        Returns the complete subgraph of all downstream dependencies.
        
        Args:
            graph: Data lineage graph
            node: Starting node ID
        
        Returns:
            Subgraph containing the node and all its descendants
        """
        if not graph.has_node(node):
            logger.warning(f"Node {node} not found in graph")
            return nx.DiGraph()
        
        # Get all descendants (downstream nodes)
        try:
            descendants = nx.descendants(graph, node)
        except nx.NetworkXError as e:
            logger.error(f"Failed to compute descendants for {node}: {e}")
            return nx.DiGraph()
        
        # Include the starting node itself
        blast_radius_nodes = descendants | {node}
        
        # Create subgraph with all affected nodes
        subgraph = graph.subgraph(blast_radius_nodes).copy()
        
        return subgraph

    def serialize_lineage_graph(self, graph: nx.DiGraph, output_path: str) -> None:
        """
        Serialize lineage graph to JSON file.

        Uses GraphSerializer to save the lineage graph with all node and edge attributes preserved.

        Args:
            graph: Data lineage graph to serialize
            output_path: Path to output JSON file
        """
        from analyzers.graph_serializer import GraphSerializer

        logger.info(f"Serializing lineage graph to {output_path}")
        GraphSerializer.serialize_lineage_graph(graph, output_path)
        logger.info(f"Successfully serialized lineage graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")

