"""Graph serialization for persisting knowledge graphs to JSON."""

import json
from pathlib import Path
from typing import Any, Dict
import networkx as nx
from networkx.readwrite import json_graph


class GraphSerializer:
    """Serializes and deserializes NetworkX graphs to/from JSON."""
    
    @staticmethod
    def serialize_module_graph(graph: nx.DiGraph, output_path: str) -> None:
        """
        Serialize module graph to JSON file.
        
        Args:
            graph: NetworkX directed graph to serialize
            output_path: Path to output JSON file
        """
        # Convert graph to node-link format (preserves all attributes)
        data = json_graph.node_link_data(graph)
        
        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=GraphSerializer._json_serializer)
    
    @staticmethod
    def serialize_lineage_graph(graph: nx.DiGraph, output_path: str) -> None:
        """
        Serialize lineage graph to JSON file.
        
        Args:
            graph: NetworkX directed graph to serialize
            output_path: Path to output JSON file
        """
        # Use same serialization as module graph
        GraphSerializer.serialize_module_graph(graph, output_path)
    
    @staticmethod
    def deserialize_graph(input_path: str) -> nx.DiGraph:
        """
        Deserialize graph from JSON file.
        
        Args:
            input_path: Path to input JSON file
        
        Returns:
            NetworkX directed graph
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert from node-link format back to graph
        graph = json_graph.node_link_graph(data, directed=True)
        
        return graph
    
    @staticmethod
    def _json_serializer(obj: Any) -> Any:
        """
        Custom JSON serializer for non-standard types.
        
        Args:
            obj: Object to serialize
        
        Returns:
            JSON-serializable representation
        """
        # Handle datetime objects
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        
        # Handle Pydantic models
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        
        # Handle tuples (convert to lists)
        if isinstance(obj, tuple):
            return list(obj)
        
        # Handle sets (convert to lists)
        if isinstance(obj, set):
            return list(obj)
        
        # Fallback: convert to string
        return str(obj)
    
    @staticmethod
    def serialize_graph_to_dict(graph: nx.DiGraph) -> Dict[str, Any]:
        """
        Serialize graph to dictionary (for in-memory operations).
        
        Args:
            graph: NetworkX directed graph
        
        Returns:
            Dictionary representation of graph
        """
        return json_graph.node_link_data(graph)
    
    @staticmethod
    def deserialize_graph_from_dict(data: Dict[str, Any]) -> nx.DiGraph:
        """
        Deserialize graph from dictionary.
        
        Args:
            data: Dictionary representation of graph
        
        Returns:
            NetworkX directed graph
        """
        return json_graph.node_link_graph(data, directed=True)
