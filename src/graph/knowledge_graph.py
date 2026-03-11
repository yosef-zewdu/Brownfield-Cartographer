"""NetworkX wrapper with serialization for knowledge graphs."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import networkx as nx
from models.models import (
    ModuleNode,
    DatasetNode,
    TransformationNode,
    ProvenanceMetadata
)


class KnowledgeGraph:
    """Wrapper around NetworkX DiGraph with serialization capabilities."""
    
    def __init__(self):
        """Initialize an empty directed graph."""
        self.graph = nx.DiGraph()
    
    def add_module_node(self, module: ModuleNode) -> None:
        """Add a module node to the graph."""
        self.graph.add_node(
            module.path,
            node_type='module',
            **module.model_dump()
        )
    
    def add_dataset_node(self, dataset: DatasetNode) -> None:
        """Add a dataset node to the graph."""
        self.graph.add_node(
            dataset.name,
            node_type='dataset',
            **dataset.model_dump()
        )
    
    def add_transformation_node(self, transformation: TransformationNode) -> None:
        """Add a transformation node to the graph."""
        self.graph.add_node(
            transformation.id,
            node_type='transformation',
            **transformation.model_dump()
        )
    
    def add_edge(self, source: str, target: str, edge_type: str, **attributes) -> None:
        """Add an edge between two nodes."""
        self.graph.add_edge(source, target, edge_type=edge_type, **attributes)
    
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get node data by ID."""
        if node_id in self.graph:
            return dict(self.graph.nodes[node_id])
        return None
    
    def get_neighbors(self, node_id: str, direction: str = 'out') -> List[str]:
        """
        Get neighbors of a node.
        
        Args:
            node_id: Node identifier
            direction: 'out' for successors, 'in' for predecessors, 'both' for both
        """
        if node_id not in self.graph:
            return []
        
        if direction == 'out':
            return list(self.graph.successors(node_id))
        elif direction == 'in':
            return list(self.graph.predecessors(node_id))
        elif direction == 'both':
            return list(set(self.graph.successors(node_id)) | set(self.graph.predecessors(node_id)))
        else:
            raise ValueError(f"Invalid direction: {direction}. Use 'in', 'out', or 'both'")
    
    def get_subgraph(self, node_ids: List[str]) -> 'KnowledgeGraph':
        """Extract a subgraph containing only specified nodes."""
        kg = KnowledgeGraph()
        kg.graph = self.graph.subgraph(node_ids).copy()
        return kg
    
    def compute_pagerank(self) -> Dict[str, float]:
        """Compute PageRank scores for all nodes."""
        return nx.pagerank(self.graph)
    
    def find_shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        """Find shortest path between two nodes."""
        try:
            return nx.shortest_path(self.graph, source, target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
    
    def find_all_paths(self, source: str, target: str, max_length: int = 10) -> List[List[str]]:
        """Find all simple paths between two nodes up to max_length."""
        try:
            return list(nx.all_simple_paths(self.graph, source, target, cutoff=max_length))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
    
    def get_descendants(self, node_id: str) -> List[str]:
        """Get all descendants (downstream nodes) of a node."""
        if node_id not in self.graph:
            return []
        return list(nx.descendants(self.graph, node_id))
    
    def get_ancestors(self, node_id: str) -> List[str]:
        """Get all ancestors (upstream nodes) of a node."""
        if node_id not in self.graph:
            return []
        return list(nx.ancestors(self.graph, node_id))
    
    def detect_cycles(self) -> List[List[str]]:
        """Detect all cycles in the graph."""
        try:
            return list(nx.simple_cycles(self.graph))
        except:
            return []
    
    def get_strongly_connected_components(self) -> List[List[str]]:
        """Get strongly connected components (circular dependencies)."""
        return [list(component) for component in nx.strongly_connected_components(self.graph)
                if len(component) > 1]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            'num_nodes': self.graph.number_of_nodes(),
            'num_edges': self.graph.number_of_edges(),
            'density': nx.density(self.graph),
            'is_directed': self.graph.is_directed(),
            'num_weakly_connected_components': nx.number_weakly_connected_components(self.graph),
            'num_strongly_connected_components': nx.number_strongly_connected_components(self.graph)
        }
    
    def serialize(self, output_path: str) -> None:
        """
        Serialize graph to JSON file.
        
        Args:
            output_path: Path to output JSON file
        """
        # Convert graph to node-link format
        data = nx.node_link_data(self.graph)
        
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Write to file
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    @classmethod
    def deserialize(cls, input_path: str) -> 'KnowledgeGraph':
        """
        Deserialize graph from JSON file.
        
        Args:
            input_path: Path to input JSON file
            
        Returns:
            KnowledgeGraph instance
        """
        with open(input_path, 'r') as f:
            data = json.load(f)
        
        kg = cls()
        kg.graph = nx.node_link_graph(data)
        return kg
    
    def merge(self, other: 'KnowledgeGraph') -> None:
        """
        Merge another graph into this one.
        
        Args:
            other: Another KnowledgeGraph to merge
        """
        self.graph = nx.compose(self.graph, other.graph)
    
    def filter_nodes(self, node_type: Optional[str] = None, **attributes) -> List[str]:
        """
        Filter nodes by type and/or attributes.
        
        Args:
            node_type: Filter by node_type attribute
            **attributes: Additional attribute filters
            
        Returns:
            List of node IDs matching the filters
        """
        matching_nodes = []
        
        for node_id, node_data in self.graph.nodes(data=True):
            # Check node_type if specified
            if node_type and node_data.get('node_type') != node_type:
                continue
            
            # Check additional attributes
            match = True
            for key, value in attributes.items():
                if node_data.get(key) != value:
                    match = False
                    break
            
            if match:
                matching_nodes.append(node_id)
        
        return matching_nodes
    
    def filter_edges(self, edge_type: Optional[str] = None, **attributes) -> List[Tuple[str, str]]:
        """
        Filter edges by type and/or attributes.
        
        Args:
            edge_type: Filter by edge_type attribute
            **attributes: Additional attribute filters
            
        Returns:
            List of (source, target) tuples matching the filters
        """
        matching_edges = []
        
        for source, target, edge_data in self.graph.edges(data=True):
            # Check edge_type if specified
            if edge_type and edge_data.get('edge_type') != edge_type:
                continue
            
            # Check additional attributes
            match = True
            for key, value in attributes.items():
                if edge_data.get(key) != value:
                    match = False
                    break
            
            if match:
                matching_edges.append((source, target))
        
        return matching_edges
    
    def __len__(self) -> int:
        """Return number of nodes in the graph."""
        return self.graph.number_of_nodes()
    
    def __contains__(self, node_id: str) -> bool:
        """Check if node exists in the graph."""
        return node_id in self.graph
    
    def __repr__(self) -> str:
        """String representation of the graph."""
        return f"KnowledgeGraph(nodes={self.graph.number_of_nodes()}, edges={self.graph.number_of_edges()})"
