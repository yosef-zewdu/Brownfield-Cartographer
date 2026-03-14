"""Unit tests for Navigator query tools."""

import pytest
import networkx as nx
from datetime import datetime

from agents.navigator import (
    FindImplementationTool,
    TraceLineageTool,
    BlastRadiusTool,
    ExplainModuleTool
)
from models.models import ModuleNode, DatasetNode, TransformationNode, ProvenanceMetadata


@pytest.fixture
def sample_modules():
    """Create sample modules for testing."""
    provenance = ProvenanceMetadata(
        evidence_type="tree_sitter",
        source_file="test.py",
        line_range=(1, 10),
        confidence=1.0,
        resolution_status="resolved"
    )
    
    modules = [
        ModuleNode(
            path="src/auth/login.py",
            language="python",
            purpose_statement="Handles user authentication and login flow",
            domain_cluster="Authentication",
            complexity_score=50,
            change_velocity=10,
            is_dead_code_candidate=False,
            last_modified=datetime.now(),
            imports=["src/db/users.py"],
            exports=["login", "logout"],
            provenance=provenance
        ),
        ModuleNode(
            path="src/db/users.py",
            language="python",
            purpose_statement="Manages user data storage and retrieval from database",
            domain_cluster="Database",
            complexity_score=80,
            change_velocity=5,
            is_dead_code_candidate=False,
            last_modified=datetime.now(),
            imports=[],
            exports=["get_user", "create_user"],
            provenance=provenance
        ),
        ModuleNode(
            path="src/api/endpoints.py",
            language="python",
            purpose_statement="Defines REST API endpoints for the application",
            domain_cluster="API",
            complexity_score=120,
            change_velocity=15,
            is_dead_code_candidate=False,
            last_modified=datetime.now(),
            imports=["src/auth/login.py"],
            exports=["app"],
            provenance=provenance
        )
    ]
    
    return modules


@pytest.fixture
def sample_module_graph(sample_modules):
    """Create sample module graph."""
    graph = nx.DiGraph()
    
    for module in sample_modules:
        graph.add_node(module.path, **module.model_dump())
    
    # Add edges
    graph.add_edge("src/auth/login.py", "src/db/users.py", edge_type="imports")
    graph.add_edge("src/api/endpoints.py", "src/auth/login.py", edge_type="imports")
    
    return graph


@pytest.fixture
def sample_lineage_graph():
    """Create sample lineage graph."""
    graph = nx.DiGraph()
    
    provenance = ProvenanceMetadata(
        evidence_type="sqlglot",
        source_file="transform.sql",
        line_range=(1, 10),
        confidence=1.0,
        resolution_status="resolved"
    )
    
    # Add dataset nodes
    graph.add_node(
        "raw_users",
        node_type="dataset",
        storage_type="table",
        discovered_in="etl/extract.py",
        provenance=provenance.model_dump()
    )
    graph.add_node(
        "staging_users",
        node_type="dataset",
        storage_type="table",
        discovered_in="etl/transform.sql",
        provenance=provenance.model_dump()
    )
    graph.add_node(
        "analytics_users",
        node_type="dataset",
        storage_type="table",
        discovered_in="etl/load.py",
        provenance=provenance.model_dump()
    )
    
    # Add transformation nodes
    graph.add_node(
        "transform_1",
        node_type="transformation",
        transformation_type="sql",
        source_file="etl/transform.sql",
        line_range=(1, 20),
        provenance=provenance.model_dump()
    )
    graph.add_node(
        "transform_2",
        node_type="transformation",
        transformation_type="python",
        source_file="etl/load.py",
        line_range=(10, 30),
        provenance=provenance.model_dump()
    )
    
    # Add edges
    graph.add_edge("transform_1", "raw_users", edge_type="consumes", confidence=1.0)
    graph.add_edge("transform_1", "staging_users", edge_type="produces", confidence=1.0)
    graph.add_edge("transform_2", "staging_users", edge_type="consumes", confidence=1.0)
    graph.add_edge("transform_2", "analytics_users", edge_type="produces", confidence=1.0)
    
    return graph


class TestFindImplementationTool:
    """Tests for FindImplementationTool."""
    
    def test_initialization(self, sample_modules):
        """Test tool initialization."""
        tool = FindImplementationTool(sample_modules)
        
        assert len(tool.modules_with_purpose) == 3
        assert tool.model is not None
    
    def test_search_authentication(self, sample_modules):
        """Test searching for authentication concept."""
        tool = FindImplementationTool(sample_modules)
        
        result = tool("user authentication", top_k=2)
        
        assert result['query'] == "user authentication"
        assert len(result['results']) <= 2
        assert result['provenance']['evidence_type'] == 'heuristic'
        assert result['provenance']['confidence'] == 0.8
        
        # Top result should be login module
        top_result = result['results'][0]
        assert 'auth' in top_result['path'] or top_result['similarity_score'] > 0.5
    
    def test_search_database(self, sample_modules):
        """Test searching for database concept."""
        tool = FindImplementationTool(sample_modules)
        
        result = tool("database operations", top_k=1)
        
        assert len(result['results']) == 1
        top_result = result['results'][0]
        
        # Should find database module
        assert 'db' in top_result['path'] or 'database' in top_result['purpose'].lower()
    
    def test_provenance_chain(self, sample_modules):
        """Test provenance chain in results."""
        tool = FindImplementationTool(sample_modules)
        
        result = tool("authentication", top_k=1)
        
        top_result = result['results'][0]
        assert 'provenance_chain' in top_result
        assert len(top_result['provenance_chain']) == 2
        
        # Check purpose statement provenance
        assert top_result['provenance_chain'][0]['source'] == 'purpose_statement'
        
        # Check semantic search provenance
        assert top_result['provenance_chain'][1]['source'] == 'semantic_search'
        assert top_result['provenance_chain'][1]['evidence_type'] == 'heuristic'
    
    def test_empty_modules(self):
        """Test with no modules."""
        tool = FindImplementationTool([])
        
        result = tool("anything")
        
        assert result['results'] == []
        assert result['provenance']['confidence'] == 0.0


class TestTraceLineageTool:
    """Tests for TraceLineageTool."""
    
    def test_initialization(self, sample_lineage_graph):
        """Test tool initialization."""
        tool = TraceLineageTool(sample_lineage_graph)
        
        assert tool.lineage_graph.number_of_nodes() == 5
    
    def test_downstream_traversal(self, sample_lineage_graph):
        """Test downstream lineage traversal."""
        tool = TraceLineageTool(sample_lineage_graph)
        
        result = tool("raw_users", direction="downstream")
        
        assert result['dataset'] == "raw_users"
        assert result['direction'] == "downstream"
        assert result['node_count'] >= 1  # At least the node itself
        assert result['provenance']['evidence_type'] == 'heuristic'
        assert result['provenance']['confidence'] == 0.9
    
    def test_upstream_traversal(self, sample_lineage_graph):
        """Test upstream lineage traversal."""
        tool = TraceLineageTool(sample_lineage_graph)
        
        result = tool("analytics_users", direction="upstream")
        
        assert result['dataset'] == "analytics_users"
        assert result['direction'] == "upstream"
        assert result['node_count'] > 1
        
        # Should include upstream nodes
        node_ids = [n['id'] for n in result['nodes']]
        assert "staging_users" in node_ids or "transform_2" in node_ids
    
    def test_max_depth(self, sample_lineage_graph):
        """Test traversal with max depth."""
        tool = TraceLineageTool(sample_lineage_graph)
        
        result = tool("raw_users", direction="downstream", max_depth=1)
        
        # Should only traverse one level
        assert result['node_count'] <= 3  # raw_users + immediate neighbors
    
    def test_node_not_found(self, sample_lineage_graph):
        """Test with non-existent node."""
        tool = TraceLineageTool(sample_lineage_graph)
        
        result = tool("nonexistent_dataset")
        
        assert result['nodes'] == []
        assert result['provenance']['confidence'] == 0.0
    
    def test_provenance_in_nodes(self, sample_lineage_graph):
        """Test provenance information in nodes."""
        tool = TraceLineageTool(sample_lineage_graph)
        
        result = tool("raw_users", direction="downstream")
        
        # Check that nodes have provenance
        for node in result['nodes']:
            if 'provenance' in node:
                assert 'evidence_type' in node['provenance']
                assert 'confidence' in node['provenance']


class TestBlastRadiusTool:
    """Tests for BlastRadiusTool."""
    
    def test_initialization(self, sample_module_graph, sample_lineage_graph):
        """Test tool initialization."""
        tool = BlastRadiusTool(sample_module_graph, sample_lineage_graph)
        
        assert tool.module_graph.number_of_nodes() == 3
        assert tool.lineage_graph.number_of_nodes() == 5
    
    def test_module_blast_radius(self, sample_module_graph, sample_lineage_graph):
        """Test computing module blast radius."""
        tool = BlastRadiusTool(sample_module_graph, sample_lineage_graph)
        
        result = tool("src/db/users.py", include_data_lineage=False)
        
        assert result['module'] == "src/db/users.py"
        assert 'affected_modules' in result
        assert result['provenance']['evidence_type'] == 'heuristic'
        assert result['provenance']['confidence'] == 0.9
    
    def test_with_data_lineage(self, sample_module_graph, sample_lineage_graph):
        """Test blast radius with data lineage."""
        tool = BlastRadiusTool(sample_module_graph, sample_lineage_graph)
        
        result = tool("src/auth/login.py", include_data_lineage=True)
        
        assert 'affected_datasets' in result
        assert result['affected_dataset_count'] >= 0
    
    def test_module_not_found(self, sample_module_graph, sample_lineage_graph):
        """Test with non-existent module."""
        tool = BlastRadiusTool(sample_module_graph, sample_lineage_graph)
        
        result = tool("nonexistent/module.py")
        
        assert result['affected_modules'] == []
        assert result['provenance']['confidence'] == 0.0
    
    def test_provenance_in_datasets(self, sample_module_graph, sample_lineage_graph):
        """Test provenance in affected datasets."""
        # Add transformation linked to module
        sample_lineage_graph.add_node(
            "test_transform",
            node_type="transformation",
            transformation_type="python",
            source_file="src/db/users.py",
            line_range=(1, 10)
        )
        sample_lineage_graph.add_edge("test_transform", "raw_users", edge_type="produces")
        
        tool = BlastRadiusTool(sample_module_graph, sample_lineage_graph)
        
        result = tool("src/db/users.py", include_data_lineage=True)
        
        # Check datasets have provenance if available
        for dataset in result['affected_datasets']:
            if 'provenance' in dataset:
                assert 'evidence_type' in dataset['provenance']


class TestExplainModuleTool:
    """Tests for ExplainModuleTool."""
    
    def test_initialization(self, sample_modules, sample_module_graph):
        """Test tool initialization."""
        tool = ExplainModuleTool(sample_modules, sample_module_graph)
        
        assert len(tool.modules_by_path) == 3
    
    def test_explain_module(self, sample_modules, sample_module_graph):
        """Test explaining a module."""
        tool = ExplainModuleTool(sample_modules, sample_module_graph)
        
        result = tool("src/auth/login.py")
        
        assert result['found'] is True
        assert result['module']['path'] == "src/auth/login.py"
        assert result['module']['purpose_statement'] is not None
        assert 'provenance_chain' in result
        assert 'summary' in result
    
    def test_module_metadata(self, sample_modules, sample_module_graph):
        """Test module metadata extraction."""
        tool = ExplainModuleTool(sample_modules, sample_module_graph)
        
        result = tool("src/auth/login.py")
        
        module = result['module']
        assert module['language'] == "python"
        assert module['complexity_score'] == 50
        assert module['change_velocity'] == 10
        assert 'imports' in module
        assert 'exports' in module
    
    def test_graph_context(self, sample_modules, sample_module_graph):
        """Test graph context in explanation."""
        tool = ExplainModuleTool(sample_modules, sample_module_graph)
        
        result = tool("src/auth/login.py")
        
        module = result['module']
        assert 'import_count' in module
        assert 'imported_by_count' in module
        assert 'imported_by' in module
    
    def test_module_not_found(self, sample_modules, sample_module_graph):
        """Test with non-existent module."""
        tool = ExplainModuleTool(sample_modules, sample_module_graph)
        
        result = tool("nonexistent/module.py")
        
        assert result['found'] is False
        assert result['provenance']['confidence'] == 0.0
    
    def test_provenance_chain(self, sample_modules, sample_module_graph):
        """Test provenance chain construction."""
        tool = ExplainModuleTool(sample_modules, sample_module_graph)
        
        result = tool("src/auth/login.py")
        
        chain = result['provenance_chain']
        assert len(chain) >= 1
        
        # First should be module provenance
        assert chain[0]['evidence_type'] == 'tree_sitter'
        assert chain[0]['confidence'] == 1.0
    
    def test_summary_generation(self, sample_modules, sample_module_graph):
        """Test summary generation."""
        tool = ExplainModuleTool(sample_modules, sample_module_graph)
        
        result = tool("src/auth/login.py")
        
        summary = result['summary']
        assert "src/auth/login.py" in summary
        assert "python" in summary.lower()
        assert "Complexity" in summary


class TestNavigatorToolsIntegration:
    """Integration tests for Navigator tools."""
    
    def test_all_tools_with_provenance(self, sample_modules, sample_module_graph, sample_lineage_graph):
        """Test that all tools return provenance information."""
        find_tool = FindImplementationTool(sample_modules)
        trace_tool = TraceLineageTool(sample_lineage_graph)
        blast_tool = BlastRadiusTool(sample_module_graph, sample_lineage_graph)
        explain_tool = ExplainModuleTool(sample_modules, sample_module_graph)
        
        # Test each tool returns provenance
        find_result = find_tool("authentication")
        assert 'provenance' in find_result
        
        trace_result = trace_tool("raw_users")
        assert 'provenance' in trace_result
        
        blast_result = blast_tool("src/auth/login.py")
        assert 'provenance' in blast_result
        
        explain_result = explain_tool("src/auth/login.py")
        assert 'provenance_chain' in explain_result
    
    def test_confidence_scores(self, sample_modules, sample_module_graph, sample_lineage_graph):
        """Test that all tools return confidence scores."""
        find_tool = FindImplementationTool(sample_modules)
        trace_tool = TraceLineageTool(sample_lineage_graph)
        blast_tool = BlastRadiusTool(sample_module_graph, sample_lineage_graph)
        
        find_result = find_tool("authentication")
        assert 0.0 <= find_result['provenance']['confidence'] <= 1.0
        
        trace_result = trace_tool("raw_users")
        assert 0.0 <= trace_result['provenance']['confidence'] <= 1.0
        
        blast_result = blast_tool("src/auth/login.py")
        assert 0.0 <= blast_result['provenance']['confidence'] <= 1.0
    
    def test_resolution_status(self, sample_modules, sample_module_graph, sample_lineage_graph):
        """Test that all tools return resolution status."""
        find_tool = FindImplementationTool(sample_modules)
        trace_tool = TraceLineageTool(sample_lineage_graph)
        blast_tool = BlastRadiusTool(sample_module_graph, sample_lineage_graph)
        
        find_result = find_tool("authentication")
        assert find_result['provenance']['resolution_status'] in [
            'resolved', 'partial', 'dynamic', 'inferred'
        ]
        
        trace_result = trace_tool("raw_users")
        assert trace_result['provenance']['resolution_status'] in [
            'resolved', 'partial', 'dynamic', 'inferred'
        ]
        
        blast_result = blast_tool("src/auth/login.py")
        assert blast_result['provenance']['resolution_status'] in [
            'resolved', 'partial', 'dynamic', 'inferred'
        ]
