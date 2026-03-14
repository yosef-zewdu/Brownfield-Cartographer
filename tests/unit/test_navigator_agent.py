"""Unit tests for NavigatorAgent."""

import pytest
import networkx as nx
from datetime import datetime
from unittest.mock import patch, MagicMock

from agents.navigator import NavigatorAgent
from models.models import ModuleNode, ProvenanceMetadata


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
        )
    ]
    
    return modules


@pytest.fixture
def sample_module_graph(sample_modules):
    """Create sample module graph."""
    graph = nx.DiGraph()
    
    for module in sample_modules:
        graph.add_node(module.path, **module.model_dump())
    
    graph.add_edge("src/auth/login.py", "src/db/users.py", edge_type="imports")
    
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
    
    return graph


@pytest.fixture
def navigator_agent(sample_modules, sample_module_graph, sample_lineage_graph):
    """Create NavigatorAgent instance."""
    return NavigatorAgent(sample_modules, sample_module_graph, sample_lineage_graph)


class TestNavigatorAgent:
    """Tests for NavigatorAgent."""
    
    def test_initialization(self, navigator_agent, sample_modules, sample_module_graph, sample_lineage_graph):
        """Test agent initialization."""
        assert navigator_agent.modules == sample_modules
        assert navigator_agent.module_graph == sample_module_graph
        assert navigator_agent.lineage_graph == sample_lineage_graph
        assert len(navigator_agent.tools) == 4
    
    def test_create_tools(self, navigator_agent):
        """Test tool creation."""
        tools = navigator_agent.create_tools()
        
        assert 'find_implementation' in tools
        assert 'trace_lineage' in tools
        assert 'blast_radius' in tools
        assert 'explain_module' in tools
        
        # Verify tools are callable
        for tool_name, tool in tools.items():
            assert callable(tool)
    
    def test_run_query_with_explicit_tool(self, navigator_agent):
        """Test running query with explicit tool selection."""
        result = navigator_agent.run_query(
            "src/auth/login.py",
            tool_name="explain_module"
        )
        
        assert 'query_metadata' in result
        assert result['query_metadata']['tool_used'] == 'explain_module'
        assert result['query_metadata']['original_query'] == "src/auth/login.py"
        assert result['found'] is True
    
    def test_run_query_with_auto_detection(self, navigator_agent):
        """Test running query with auto-detected tool."""
        # Should detect find_implementation for semantic search
        result = navigator_agent.run_query("authentication")
        
        assert 'query_metadata' in result
        assert result['query_metadata']['tool_used'] == 'find_implementation'
        assert 'results' in result
    
    def test_detect_tool_lineage(self, navigator_agent):
        """Test tool detection for lineage queries."""
        tool = navigator_agent._detect_tool("show me the lineage for raw_users")
        assert tool == 'trace_lineage'
        
        tool = navigator_agent._detect_tool("trace upstream dependencies")
        assert tool == 'trace_lineage'
    
    def test_detect_tool_blast_radius(self, navigator_agent):
        """Test tool detection for blast radius queries."""
        tool = navigator_agent._detect_tool("what breaks if I change this module")
        assert tool == 'blast_radius'
        
        tool = navigator_agent._detect_tool("show me the impact of changes")
        assert tool == 'blast_radius'
    
    def test_detect_tool_explain(self, navigator_agent):
        """Test tool detection for explanation queries."""
        tool = navigator_agent._detect_tool("explain this module")
        assert tool == 'explain_module'
        
        tool = navigator_agent._detect_tool("what does this module do")
        assert tool == 'explain_module'
    
    def test_detect_tool_default(self, navigator_agent):
        """Test tool detection defaults to find_implementation."""
        tool = navigator_agent._detect_tool("some random query")
        assert tool == 'find_implementation'
    
    def test_run_query_with_parameters(self, navigator_agent):
        """Test running query with additional parameters."""
        result = navigator_agent.run_query(
            "authentication",
            tool_name="find_implementation",
            top_k=2
        )
        
        assert 'query_metadata' in result
        assert result['query_metadata']['parameters']['top_k'] == 2
        assert len(result['results']) <= 2
    
    def test_run_query_invalid_tool(self, navigator_agent):
        """Test running query with invalid tool name."""
        result = navigator_agent.run_query(
            "test query",
            tool_name="nonexistent_tool"
        )
        
        assert 'error' in result
        assert 'available_tools' in result
        assert result['provenance']['confidence'] == 0.0
    
    def test_run_query_error_handling(self, navigator_agent):
        """Test error handling in query execution."""
        # Create a mock tool that raises an exception
        mock_tool = MagicMock(side_effect=Exception("Test error"))
        navigator_agent.tools['test_error_tool'] = mock_tool
        
        result = navigator_agent.run_query(
            "test query",
            tool_name="test_error_tool"
        )
        
        assert 'error' in result
        assert 'Test error' in result['error']
        assert result['provenance']['confidence'] == 0.0
    
    def test_run_query_find_implementation(self, navigator_agent):
        """Test find_implementation tool via run_query."""
        result = navigator_agent.run_query(
            "database operations",
            tool_name="find_implementation",
            top_k=1
        )
        
        assert result['query_metadata']['tool_used'] == 'find_implementation'
        assert 'results' in result
        assert len(result['results']) <= 1
    
    def test_run_query_trace_lineage(self, navigator_agent):
        """Test trace_lineage tool via run_query."""
        result = navigator_agent.run_query(
            "raw_users",
            tool_name="trace_lineage",
            direction="downstream"
        )
        
        assert result['query_metadata']['tool_used'] == 'trace_lineage'
        assert result['dataset'] == "raw_users"
        assert result['direction'] == "downstream"
    
    def test_run_query_blast_radius(self, navigator_agent):
        """Test blast_radius tool via run_query."""
        result = navigator_agent.run_query(
            "src/db/users.py",
            tool_name="blast_radius",
            include_data_lineage=False
        )
        
        assert result['query_metadata']['tool_used'] == 'blast_radius'
        assert result['module'] == "src/db/users.py"
        assert 'affected_modules' in result
    
    def test_query_metadata_preservation(self, navigator_agent):
        """Test that query metadata is preserved in results."""
        result = navigator_agent.run_query(
            "test query",
            tool_name="find_implementation",
            top_k=3
        )
        
        metadata = result['query_metadata']
        assert metadata['original_query'] == "test query"
        assert metadata['tool_used'] == 'find_implementation'
        assert metadata['parameters']['top_k'] == 3
    
    def test_provenance_in_results(self, navigator_agent):
        """Test that all results include provenance information."""
        # Test each tool
        tools_to_test = [
            ('find_implementation', 'authentication', {}),
            ('trace_lineage', 'raw_users', {}),
            ('blast_radius', 'src/auth/login.py', {}),
            ('explain_module', 'src/auth/login.py', {})
        ]
        
        for tool_name, query, params in tools_to_test:
            result = navigator_agent.run_query(query, tool_name=tool_name, **params)
            
            # Check for provenance or provenance_chain
            assert 'provenance' in result or 'provenance_chain' in result, \
                f"Tool {tool_name} missing provenance information"


class TestNavigatorAgentInteractive:
    """Tests for NavigatorAgent interactive mode."""
    
    def test_print_help(self, navigator_agent, capsys):
        """Test help message printing."""
        navigator_agent._print_help()
        
        captured = capsys.readouterr()
        assert "Navigator Help" in captured.out
        assert "find_implementation" in captured.out
        assert "trace_lineage" in captured.out
    
    def test_print_tools(self, navigator_agent, capsys):
        """Test tools listing."""
        navigator_agent._print_tools()
        
        captured = capsys.readouterr()
        assert "Available Tools" in captured.out
        assert "find_implementation" in captured.out
        assert "FindImplementationTool" in captured.out
    
    def test_display_result_error(self, navigator_agent, capsys):
        """Test displaying error results."""
        result = {
            'error': 'Test error',
            'available_tools': ['tool1', 'tool2']
        }
        
        navigator_agent._display_result(result)
        
        captured = capsys.readouterr()
        assert "Error" in captured.out
        assert "Test error" in captured.out
    
    def test_display_result_find_implementation(self, navigator_agent, capsys):
        """Test displaying find_implementation results."""
        result = navigator_agent.run_query("authentication", tool_name="find_implementation")
        
        navigator_agent._display_result(result)
        
        captured = capsys.readouterr()
        assert "Tool: find_implementation" in captured.out
        assert "Provenance:" in captured.out
    
    def test_display_result_trace_lineage(self, navigator_agent, capsys):
        """Test displaying trace_lineage results."""
        result = navigator_agent.run_query("raw_users", tool_name="trace_lineage")
        
        navigator_agent._display_result(result)
        
        captured = capsys.readouterr()
        assert "Lineage:" in captured.out
        assert "Nodes:" in captured.out
    
    def test_display_result_blast_radius(self, navigator_agent, capsys):
        """Test displaying blast_radius results."""
        result = navigator_agent.run_query("src/auth/login.py", tool_name="blast_radius")
        
        navigator_agent._display_result(result)
        
        captured = capsys.readouterr()
        assert "Module:" in captured.out
        assert "Affected modules:" in captured.out
    
    def test_display_result_explain_module(self, navigator_agent, capsys):
        """Test displaying explain_module results."""
        result = navigator_agent.run_query("src/auth/login.py", tool_name="explain_module")
        
        navigator_agent._display_result(result)
        
        captured = capsys.readouterr()
        assert "Module: src/auth/login.py" in captured.out
        assert "Language: python" in captured.out
    
    @patch('builtins.input', side_effect=['exit'])
    def test_interactive_mode_exit(self, mock_input, navigator_agent, capsys):
        """Test exiting interactive mode."""
        navigator_agent.interactive_mode()
        
        captured = capsys.readouterr()
        assert "Navigator Interactive Mode" in captured.out
        assert "Exiting interactive mode" in captured.out
    
    @patch('builtins.input', side_effect=['help', 'exit'])
    def test_interactive_mode_help(self, mock_input, navigator_agent, capsys):
        """Test help command in interactive mode."""
        navigator_agent.interactive_mode()
        
        captured = capsys.readouterr()
        assert "Navigator Help" in captured.out
    
    @patch('builtins.input', side_effect=['tools', 'exit'])
    def test_interactive_mode_tools(self, mock_input, navigator_agent, capsys):
        """Test tools command in interactive mode."""
        navigator_agent.interactive_mode()
        
        captured = capsys.readouterr()
        assert "Available Tools" in captured.out
    
    @patch('builtins.input', side_effect=['authentication', 'exit'])
    def test_interactive_mode_query(self, mock_input, navigator_agent, capsys):
        """Test running a query in interactive mode."""
        navigator_agent.interactive_mode()
        
        captured = capsys.readouterr()
        assert "Tool:" in captured.out or "Provenance:" in captured.out
    
    @patch('builtins.input', side_effect=['explain_module: src/auth/login.py', 'exit'])
    def test_interactive_mode_explicit_tool(self, mock_input, navigator_agent, capsys):
        """Test running a query with explicit tool in interactive mode."""
        navigator_agent.interactive_mode()
        
        captured = capsys.readouterr()
        assert "Module: src/auth/login.py" in captured.out
    
    @patch('builtins.input', side_effect=['', 'exit'])
    def test_interactive_mode_empty_input(self, mock_input, navigator_agent, capsys):
        """Test handling empty input in interactive mode."""
        navigator_agent.interactive_mode()
        
        # Should not crash, just continue
        captured = capsys.readouterr()
        assert "Navigator Interactive Mode" in captured.out


class TestNavigatorAgentIntegration:
    """Integration tests for NavigatorAgent."""
    
    def test_full_workflow(self, navigator_agent):
        """Test complete workflow with all tools."""
        # 1. Find implementation
        result1 = navigator_agent.run_query("authentication")
        assert 'results' in result1
        
        # 2. Explain module
        if result1['results']:
            module_path = result1['results'][0]['path']
            result2 = navigator_agent.run_query(module_path, tool_name="explain_module")
            assert result2['found'] is True
            
            # 3. Blast radius
            result3 = navigator_agent.run_query(module_path, tool_name="blast_radius")
            assert 'affected_modules' in result3
        
        # 4. Trace lineage
        result4 = navigator_agent.run_query("raw_users", tool_name="trace_lineage")
        assert 'nodes' in result4
    
    def test_all_tools_accessible(self, navigator_agent):
        """Test that all tools are accessible through the agent."""
        # Test each tool can be invoked
        tools_to_test = [
            ('find_implementation', 'test query'),
            ('trace_lineage', 'raw_users'),
            ('blast_radius', 'src/auth/login.py'),
            ('explain_module', 'src/auth/login.py')
        ]
        
        for tool_name, query in tools_to_test:
            result = navigator_agent.run_query(query, tool_name=tool_name)
            
            # Should not have error (unless expected like module not found)
            if 'error' in result:
                # Only acceptable if it's a "not found" type error
                assert 'not found' in result.get('provenance', {}).get('message', '').lower()
            else:
                # Should have query metadata
                assert 'query_metadata' in result
                assert result['query_metadata']['tool_used'] == tool_name
    
    def test_provenance_consistency(self, navigator_agent):
        """Test that provenance information is consistent across all tools."""
        queries = [
            ('find_implementation', 'authentication'),
            ('trace_lineage', 'raw_users'),
            ('blast_radius', 'src/auth/login.py'),
            ('explain_module', 'src/auth/login.py')
        ]
        
        for tool_name, query in queries:
            result = navigator_agent.run_query(query, tool_name=tool_name)
            
            # Check provenance structure
            if 'provenance' in result:
                prov = result['provenance']
                assert 'evidence_type' in prov
                assert 'confidence' in prov
                assert 0.0 <= prov['confidence'] <= 1.0
                assert 'resolution_status' in prov
                assert prov['resolution_status'] in ['resolved', 'partial', 'dynamic', 'inferred']
