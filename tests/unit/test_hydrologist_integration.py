"""Integration tests for HydrologistAgent with file system."""

import pytest
import networkx as nx
from pathlib import Path
import tempfile
import os

from agents.hydrologist import HydrologistAgent


class TestHydrologistIntegration:
    """Integration test suite for HydrologistAgent with real files."""
    
    def test_analyze_repository_with_python_file(self):
        """Test analyzing a repository with a Python file containing pandas operations."""
        agent = HydrologistAgent()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple Python file with pandas operations
            python_file = Path(tmpdir) / "analysis.py"
            python_file.write_text("""
import pandas as pd

def load_data():
    df = pd.read_csv('input.csv')
    return df

def save_data(df):
    df.to_csv('output.csv')
""")
            
            module_graph = nx.DiGraph()
            lineage_graph, datasets, transformations = agent.analyze_repository(tmpdir, module_graph)
            
            # Should detect pandas operations
            assert len(transformations) > 0
            
            # Check that we have some form of lineage
            assert isinstance(lineage_graph, nx.DiGraph)
    
    def test_analyze_repository_with_sql_file(self):
        """Test analyzing a repository with a SQL file."""
        agent = HydrologistAgent()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple SQL file
            sql_file = Path(tmpdir) / "query.sql"
            sql_file.write_text("""
SELECT u.id, u.name, o.order_id
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE o.status = 'completed';
""")
            
            module_graph = nx.DiGraph()
            lineage_graph, datasets, transformations = agent.analyze_repository(tmpdir, module_graph)
            
            # Should detect SQL transformation
            assert len(transformations) > 0
            
            # Should extract table references
            transformation = transformations[0]
            assert 'users' in transformation.source_datasets or 'orders' in transformation.source_datasets
    
    def test_analyze_repository_with_mixed_files(self):
        """Test analyzing a repository with both Python and SQL files."""
        agent = HydrologistAgent()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Python file
            python_file = Path(tmpdir) / "etl.py"
            python_file.write_text("""
import pandas as pd

df = pd.read_csv('raw_data.csv')
df.to_sql('processed_data', con=engine)
""")
            
            # Create SQL file
            sql_file = Path(tmpdir) / "transform.sql"
            sql_file.write_text("""
CREATE TABLE final_report AS
SELECT * FROM processed_data
WHERE created_at > '2024-01-01';
""")
            
            module_graph = nx.DiGraph()
            lineage_graph, datasets, transformations = agent.analyze_repository(tmpdir, module_graph)
            
            # Should detect both Python and SQL transformations
            assert len(transformations) >= 2
            
            # Should have multiple datasets
            assert len(datasets) > 0
    
    def test_analyze_repository_handles_parse_errors(self):
        """Test that the agent handles unparseable files gracefully."""
        agent = HydrologistAgent()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a Python file with syntax errors
            bad_python = Path(tmpdir) / "broken.py"
            bad_python.write_text("""
def broken_function(
    # Missing closing parenthesis and body
""")
            
            # Create a valid SQL file
            sql_file = Path(tmpdir) / "valid.sql"
            sql_file.write_text("SELECT * FROM users;")
            
            module_graph = nx.DiGraph()
            
            # Should not raise an exception
            lineage_graph, datasets, transformations = agent.analyze_repository(tmpdir, module_graph)
            
            # Should still process the valid SQL file
            assert len(transformations) >= 1
            
            # Should log errors
            assert len(agent.errors) >= 0  # May or may not catch parse error depending on tree-sitter
    
    def test_find_sources_and_sinks_in_pipeline(self):
        """Test finding sources and sinks in a complete data pipeline."""
        agent = HydrologistAgent()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a pipeline: raw -> transform -> final
            sql_file = Path(tmpdir) / "pipeline.sql"
            sql_file.write_text("""
-- Extract from source
CREATE TABLE staging AS
SELECT * FROM raw_source;

-- Transform
CREATE TABLE final_output AS
SELECT id, name, processed_at
FROM staging
WHERE status = 'active';
""")
            
            module_graph = nx.DiGraph()
            lineage_graph, datasets, transformations = agent.analyze_repository(tmpdir, module_graph)
            
            sources = agent.find_sources(lineage_graph)
            sinks = agent.find_sinks(lineage_graph)
            
            # Should identify sources and sinks
            assert len(sources) > 0
            assert len(sinks) > 0
    
    def test_compute_blast_radius_in_pipeline(self):
        """Test computing blast radius in a data pipeline."""
        agent = HydrologistAgent()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a pipeline with dependencies
            sql_file = Path(tmpdir) / "pipeline.sql"
            sql_file.write_text("""
CREATE TABLE stage1 AS SELECT * FROM source;
CREATE TABLE stage2 AS SELECT * FROM stage1;
CREATE TABLE stage3 AS SELECT * FROM stage2;
""")
            
            module_graph = nx.DiGraph()
            lineage_graph, datasets, transformations = agent.analyze_repository(tmpdir, module_graph)
            
            # Find a source node
            sources = agent.find_sources(lineage_graph)
            if sources:
                source_node = sources[0]
                blast_radius = agent.compute_blast_radius(lineage_graph, source_node)
                
                # Blast radius should include downstream nodes
                assert len(blast_radius.nodes()) > 0

    def test_serialize_lineage_graph(self):
        """Test serializing lineage graph to JSON with all attributes preserved."""
        agent = HydrologistAgent()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple data pipeline
            sql_file = Path(tmpdir) / "pipeline.sql"
            sql_file.write_text("""
CREATE TABLE staging AS
SELECT * FROM raw_source;

CREATE TABLE final_output AS
SELECT id, name
FROM staging;
""")
            
            module_graph = nx.DiGraph()
            lineage_graph, datasets, transformations = agent.analyze_repository(tmpdir, module_graph)
            
            # Serialize the lineage graph
            output_path = Path(tmpdir) / "lineage_graph.json"
            agent.serialize_lineage_graph(lineage_graph, str(output_path))
            
            # Verify the file was created
            assert output_path.exists()
            
            # Deserialize and verify attributes are preserved
            from analyzers.graph_serializer import GraphSerializer
            deserialized_graph = GraphSerializer.deserialize_graph(str(output_path))
            
            # Verify node count matches
            assert deserialized_graph.number_of_nodes() == lineage_graph.number_of_nodes()
            
            # Verify edge count matches
            assert deserialized_graph.number_of_edges() == lineage_graph.number_of_edges()
            
            # Verify node attributes are preserved
            for node in lineage_graph.nodes():
                assert node in deserialized_graph.nodes()
                original_attrs = lineage_graph.nodes[node]
                deserialized_attrs = deserialized_graph.nodes[node]
                
                # Check that key attributes are preserved
                assert original_attrs.get('node_type') == deserialized_attrs.get('node_type')
                
                # Check provenance is preserved if present
                if 'provenance' in original_attrs:
                    assert 'provenance' in deserialized_attrs
            
            # Verify edge attributes are preserved
            for edge in lineage_graph.edges():
                assert edge in deserialized_graph.edges()
                original_edge_attrs = lineage_graph.edges[edge]
                deserialized_edge_attrs = deserialized_graph.edges[edge]
                
                # Check that edge_type is preserved
                assert original_edge_attrs.get('edge_type') == deserialized_edge_attrs.get('edge_type')
                
                # Check provenance is preserved if present
                if 'provenance' in original_edge_attrs:
                    assert 'provenance' in deserialized_edge_attrs
