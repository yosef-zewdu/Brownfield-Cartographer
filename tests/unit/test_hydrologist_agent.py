"""Unit tests for HydrologistAgent orchestrator."""

import pytest
import networkx as nx
from pathlib import Path
import tempfile
import os

from agents.hydrologist import HydrologistAgent
from models import DatasetNode, TransformationNode, ProvenanceMetadata


class TestHydrologistAgent:
    """Test suite for HydrologistAgent."""
    
    def test_initialization(self):
        """Test that HydrologistAgent initializes correctly."""
        agent = HydrologistAgent()
        
        assert agent.python_analyzer is not None
        assert agent.sql_analyzer is not None
        assert agent.dbt_analyzer is not None
        assert agent.airflow_analyzer is not None
        assert agent.errors == []
    
    def test_build_lineage_graph_empty(self):
        """Test building lineage graph with no datasets or transformations."""
        agent = HydrologistAgent()
        
        graph = agent.build_lineage_graph([], [])
        
        assert isinstance(graph, nx.DiGraph)
        assert len(graph.nodes()) == 0
        assert len(graph.edges()) == 0
    
    def test_build_lineage_graph_with_datasets(self):
        """Test building lineage graph with datasets only."""
        agent = HydrologistAgent()
        
        datasets = [
            DatasetNode(
                name="users",
                storage_type="table",
                discovered_in="test.sql",
                provenance=ProvenanceMetadata(
                    evidence_type="sqlglot",
                    source_file="test.sql",
                    confidence=1.0,
                    resolution_status="resolved"
                )
            ),
            DatasetNode(
                name="orders",
                storage_type="table",
                discovered_in="test.sql",
                provenance=ProvenanceMetadata(
                    evidence_type="sqlglot",
                    source_file="test.sql",
                    confidence=1.0,
                    resolution_status="resolved"
                )
            )
        ]
        
        graph = agent.build_lineage_graph(datasets, [])
        
        assert len(graph.nodes()) == 2
        assert graph.has_node("users")
        assert graph.has_node("orders")
        assert graph.nodes["users"]["node_type"] == "dataset"
        assert graph.nodes["orders"]["node_type"] == "dataset"
    
    def test_build_lineage_graph_with_transformations(self):
        """Test building lineage graph with transformations and edges."""
        agent = HydrologistAgent()
        
        datasets = [
            DatasetNode(
                name="raw_users",
                storage_type="table",
                discovered_in="test.sql",
                provenance=ProvenanceMetadata(
                    evidence_type="sqlglot",
                    source_file="test.sql",
                    confidence=1.0,
                    resolution_status="resolved"
                )
            ),
            DatasetNode(
                name="clean_users",
                storage_type="table",
                discovered_in="test.sql",
                provenance=ProvenanceMetadata(
                    evidence_type="sqlglot",
                    source_file="test.sql",
                    confidence=1.0,
                    resolution_status="resolved"
                )
            )
        ]
        
        transformations = [
            TransformationNode(
                id="transform_1",
                source_datasets=["raw_users"],
                target_datasets=["clean_users"],
                transformation_type="sql",
                source_file="test.sql",
                line_range=(1, 10),
                provenance=ProvenanceMetadata(
                    evidence_type="sqlglot",
                    source_file="test.sql",
                    confidence=1.0,
                    resolution_status="resolved"
                )
            )
        ]
        
        graph = agent.build_lineage_graph(datasets, transformations)
        
        # Check nodes
        assert len(graph.nodes()) == 3
        assert graph.has_node("raw_users")
        assert graph.has_node("clean_users")
        assert graph.has_node("transform_1")
        
        # Check edges
        assert graph.has_edge("raw_users", "transform_1")  # CONSUMES
        assert graph.has_edge("transform_1", "clean_users")  # PRODUCES
        
        # Check edge types
        assert graph.edges["raw_users", "transform_1"]["edge_type"] == "consumes"
        assert graph.edges["transform_1", "clean_users"]["edge_type"] == "produces"
    
    def test_find_sources(self):
        """Test finding source nodes with in-degree zero."""
        agent = HydrologistAgent()
        
        datasets = [
            DatasetNode(
                name="source_data",
                storage_type="table",
                discovered_in="test.sql",
                provenance=ProvenanceMetadata(
                    evidence_type="sqlglot",
                    source_file="test.sql",
                    confidence=1.0,
                    resolution_status="resolved"
                )
            ),
            DatasetNode(
                name="derived_data",
                storage_type="table",
                discovered_in="test.sql",
                provenance=ProvenanceMetadata(
                    evidence_type="sqlglot",
                    source_file="test.sql",
                    confidence=1.0,
                    resolution_status="resolved"
                )
            )
        ]
        
        transformations = [
            TransformationNode(
                id="transform_1",
                source_datasets=["source_data"],
                target_datasets=["derived_data"],
                transformation_type="sql",
                source_file="test.sql",
                line_range=(1, 10),
                provenance=ProvenanceMetadata(
                    evidence_type="sqlglot",
                    source_file="test.sql",
                    confidence=1.0,
                    resolution_status="resolved"
                )
            )
        ]
        
        graph = agent.build_lineage_graph(datasets, transformations)
        sources = agent.find_sources(graph)
        
        assert "source_data" in sources
        assert "derived_data" not in sources
        assert "transform_1" not in sources
    
    def test_find_sinks(self):
        """Test finding sink nodes with out-degree zero."""
        agent = HydrologistAgent()
        
        datasets = [
            DatasetNode(
                name="source_data",
                storage_type="table",
                discovered_in="test.sql",
                provenance=ProvenanceMetadata(
                    evidence_type="sqlglot",
                    source_file="test.sql",
                    confidence=1.0,
                    resolution_status="resolved"
                )
            ),
            DatasetNode(
                name="sink_data",
                storage_type="table",
                discovered_in="test.sql",
                provenance=ProvenanceMetadata(
                    evidence_type="sqlglot",
                    source_file="test.sql",
                    confidence=1.0,
                    resolution_status="resolved"
                )
            )
        ]
        
        transformations = [
            TransformationNode(
                id="transform_1",
                source_datasets=["source_data"],
                target_datasets=["sink_data"],
                transformation_type="sql",
                source_file="test.sql",
                line_range=(1, 10),
                provenance=ProvenanceMetadata(
                    evidence_type="sqlglot",
                    source_file="test.sql",
                    confidence=1.0,
                    resolution_status="resolved"
                )
            )
        ]
        
        graph = agent.build_lineage_graph(datasets, transformations)
        sinks = agent.find_sinks(graph)
        
        assert "sink_data" in sinks
        assert "source_data" not in sinks
        assert "transform_1" not in sinks
    
    def test_compute_blast_radius(self):
        """Test computing blast radius for a node."""
        agent = HydrologistAgent()
        
        datasets = [
            DatasetNode(
                name="data_a",
                storage_type="table",
                discovered_in="test.sql",
                provenance=ProvenanceMetadata(
                    evidence_type="sqlglot",
                    source_file="test.sql",
                    confidence=1.0,
                    resolution_status="resolved"
                )
            ),
            DatasetNode(
                name="data_b",
                storage_type="table",
                discovered_in="test.sql",
                provenance=ProvenanceMetadata(
                    evidence_type="sqlglot",
                    source_file="test.sql",
                    confidence=1.0,
                    resolution_status="resolved"
                )
            ),
            DatasetNode(
                name="data_c",
                storage_type="table",
                discovered_in="test.sql",
                provenance=ProvenanceMetadata(
                    evidence_type="sqlglot",
                    source_file="test.sql",
                    confidence=1.0,
                    resolution_status="resolved"
                )
            )
        ]
        
        transformations = [
            TransformationNode(
                id="transform_1",
                source_datasets=["data_a"],
                target_datasets=["data_b"],
                transformation_type="sql",
                source_file="test.sql",
                line_range=(1, 10),
                provenance=ProvenanceMetadata(
                    evidence_type="sqlglot",
                    source_file="test.sql",
                    confidence=1.0,
                    resolution_status="resolved"
                )
            ),
            TransformationNode(
                id="transform_2",
                source_datasets=["data_b"],
                target_datasets=["data_c"],
                transformation_type="sql",
                source_file="test.sql",
                line_range=(11, 20),
                provenance=ProvenanceMetadata(
                    evidence_type="sqlglot",
                    source_file="test.sql",
                    confidence=1.0,
                    resolution_status="resolved"
                )
            )
        ]
        
        graph = agent.build_lineage_graph(datasets, transformations)
        blast_radius = agent.compute_blast_radius(graph, "data_a")
        
        # data_a should affect transform_1, data_b, transform_2, and data_c
        assert blast_radius.has_node("data_a")
        assert blast_radius.has_node("transform_1")
        assert blast_radius.has_node("data_b")
        assert blast_radius.has_node("transform_2")
        assert blast_radius.has_node("data_c")
        assert len(blast_radius.nodes()) == 5
    
    def test_compute_blast_radius_nonexistent_node(self):
        """Test computing blast radius for a node that doesn't exist."""
        agent = HydrologistAgent()
        
        graph = nx.DiGraph()
        graph.add_node("node_a")
        
        blast_radius = agent.compute_blast_radius(graph, "nonexistent")
        
        assert len(blast_radius.nodes()) == 0
    
    def test_analyze_repository_empty(self):
        """Test analyzing an empty repository."""
        agent = HydrologistAgent()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create empty module graph
            module_graph = nx.DiGraph()
            
            lineage_graph, datasets, transformations = agent.analyze_repository(tmpdir, module_graph)
            
            assert isinstance(lineage_graph, nx.DiGraph)
            assert isinstance(datasets, list)
            assert isinstance(transformations, list)
