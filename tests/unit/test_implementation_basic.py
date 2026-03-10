#!/usr/bin/env python3
"""Basic integration tests to verify the implementation works."""

import sys
import tempfile
from pathlib import Path
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from models import ModuleNode, ProvenanceMetadata
from analyzers.language_router import LanguageRouter
from analyzers.tree_sitter_analyzer import ModuleAnalyzer
from analyzers.sql_lineage import SQLLineageAnalyzer
from analyzers.dag_config_parser import DBTProjectAnalyzer, AirflowDAGAnalyzer
from analyzers.git_velocity_analyzer import GitVelocityAnalyzer
from analyzers.graph_serializer import GraphSerializer
from agents.surveyor import SurveyorAgent


class TestLanguageRouter:
    """Test LanguageRouter functionality."""
    
    def test_supported_extensions(self):
        """Test that supported extensions are correctly identified."""
        router = LanguageRouter()
        
        # Test supported extensions
        assert router.is_supported('.py')
        assert router.is_supported('.js')
        assert router.is_supported('.ts')
        assert router.is_supported('.sql')
        assert router.is_supported('.yaml')
        assert router.is_supported('.yml')
        
        # Test unsupported extensions
        assert not router.is_supported('.txt')
        assert not router.is_supported('.md')
        assert not router.is_supported('.json')
    
    def test_language_names(self):
        """Test that language names are correctly returned."""
        router = LanguageRouter()
        
        assert router.get_language_name('.py') == 'python'
        assert router.get_language_name('.js') == 'javascript'
        assert router.get_language_name('.ts') == 'typescript'
        assert router.get_language_name('.sql') == 'sql'
        assert router.get_language_name('.yaml') == 'yaml'
        assert router.get_language_name('.yml') == 'yaml'
    
    def test_parser_retrieval(self):
        """Test that parsers are correctly retrieved."""
        router = LanguageRouter()
        
        # Python and JS should have parsers
        py_parser = router.get_parser('.py')
        js_parser = router.get_parser('.js')
        
        assert py_parser is not None
        assert js_parser is not None
        
        # SQL and YAML return None (handled by other libraries)
        sql_parser = router.get_parser('.sql')
        yaml_parser = router.get_parser('.yaml')
        
        assert sql_parser is None
        assert yaml_parser is None


class TestModuleAnalyzer:
    """Test ModuleAnalyzer functionality."""
    
    def test_python_module_analysis(self):
        """Test analysis of a Python module."""
        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
"""Test module docstring."""
import os
from pathlib import Path

def public_function(x: int) -> str:
    """A public function."""
    return str(x)

def _private_function():
    """A private function."""
    pass

class PublicClass:
    """A public class."""
    def method(self):
        pass

class _PrivateClass:
    """A private class."""
    pass
''')
            temp_file = f.name
        
        try:
            analyzer = ModuleAnalyzer()
            module = analyzer.analyze_module(temp_file)
            
            # Check basic properties
            assert module.path == temp_file
            assert module.language == 'python'
            assert module.docstring == 'Test module docstring.'
            
            # Check imports
            assert 'os' in module.imports
            assert any('pathlib' in imp for imp in module.imports)
            
            # Check exports (only public items)
            assert 'public_function' in module.exports
            assert 'PublicClass' in module.exports
            assert '_private_function' not in module.exports
            assert '_PrivateClass' not in module.exports
            
            # Check provenance
            assert module.provenance.evidence_type == 'tree_sitter'
            assert module.provenance.confidence == 1.0
            assert module.provenance.resolution_status == 'resolved'
        
        finally:
            Path(temp_file).unlink()
    
    def test_function_signature_extraction(self):
        """Test extraction of function signatures."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
def simple_func():
    pass

def typed_func(x: int, y: str = "default") -> bool:
    return True

async def async_func(data: dict) -> None:
    pass
''')
            temp_file = f.name
        
        try:
            analyzer = ModuleAnalyzer()
            module = analyzer.analyze_module(temp_file)
            
            # Extract function signatures
            functions = analyzer.extract_function_signatures(
                analyzer.router.get_parser('.py').parse(bytes(open(temp_file).read(), 'utf8')).root_node,
                temp_file
            )
            
            assert len(functions) >= 3
            
            # Check that function names are captured
            func_names = [f.qualified_name.split('.')[-1] for f in functions]
            assert 'simple_func' in func_names
            assert 'typed_func' in func_names
            assert 'async_func' in func_names
        
        finally:
            Path(temp_file).unlink()


class TestSQLLineageAnalyzer:
    """Test SQLLineageAnalyzer functionality."""
    
    def test_sql_parsing(self):
        """Test basic SQL parsing."""
        analyzer = SQLLineageAnalyzer()
        
        sql = "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
        parsed = analyzer.parse_sql(sql)
        assert parsed is not None
    
    def test_table_dependency_extraction(self):
        """Test extraction of table dependencies."""
        analyzer = SQLLineageAnalyzer()
        
        sql = "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id"
        parsed = analyzer.parse_sql(sql)
        
        if parsed:
            input_tables, output_tables = analyzer.extract_table_dependencies(parsed)
            assert 'users' in input_tables or 'u' in input_tables
            assert 'orders' in input_tables or 'o' in input_tables
    
    def test_create_table_parsing(self):
        """Test parsing of CREATE TABLE statements."""
        analyzer = SQLLineageAnalyzer()
        
        sql = """
        CREATE TABLE user_summary AS
        SELECT user_id, COUNT(*) as order_count
        FROM orders
        GROUP BY user_id
        """
        
        parsed = analyzer.parse_sql(sql)
        if parsed:
            input_tables, output_tables = analyzer.extract_table_dependencies(parsed)
            assert 'orders' in input_tables
            assert 'user_summary' in output_tables


class TestGitVelocityAnalyzer:
    """Test GitVelocityAnalyzer functionality."""
    
    def test_git_detection(self):
        """Test detection of git repository."""
        # Test with current repo (should have .git)
        analyzer = GitVelocityAnalyzer('.')
        assert analyzer.has_git
        
        # Test with non-git directory
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = GitVelocityAnalyzer(temp_dir)
            assert not analyzer.has_git
    
    def test_velocity_analysis(self):
        """Test velocity analysis functionality."""
        analyzer = GitVelocityAnalyzer('.')
        
        if analyzer.has_git:
            # Test velocity analysis (may return empty dict if no recent commits)
            velocities = analyzer.get_all_file_velocities(days=30)
            assert isinstance(velocities, dict)
            
            # Test high velocity files
            high_velocity = analyzer.get_high_velocity_files(threshold=0.8, days=30)
            assert isinstance(high_velocity, list)


class TestSurveyorAgent:
    """Test SurveyorAgent functionality."""
    
    def test_repository_analysis(self):
        """Test analysis of a simple repository."""
        # Create a temporary directory with some Python files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a simple Python file
            (temp_path / 'main.py').write_text('''
import utils

def main():
    utils.helper()
''')
            
            (temp_path / 'utils.py').write_text('''
def helper():
    return "help"

def another_function():
    pass
''')
            
            # Test surveyor
            surveyor = SurveyorAgent()
            graph, modules = surveyor.analyze_repository(str(temp_path))
            
            # Should have found 2 modules
            assert len(modules) == 2
            
            # Should have created a graph
            assert len(graph.nodes) == 2
            
            # Check that modules have the expected properties
            module_paths = [m.path for m in modules]
            assert str(temp_path / 'main.py') in module_paths
            assert str(temp_path / 'utils.py') in module_paths
            
            # Check exports
            utils_module = next(m for m in modules if m.path.endswith('utils.py'))
            assert 'helper' in utils_module.exports
            assert 'another_function' in utils_module.exports


class TestGraphSerializer:
    """Test GraphSerializer functionality."""
    
    def test_graph_serialization_roundtrip(self):
        """Test that graphs can be serialized and deserialized."""
        import networkx as nx
        
        # Create a simple graph
        graph = nx.DiGraph()
        graph.add_node('node1', attr1='value1', attr2=42)
        graph.add_node('node2', attr1='value2', attr2=24)
        graph.add_edge('node1', 'node2', weight=1.5)
        
        serializer = GraphSerializer()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            # Serialize
            serializer.serialize_module_graph(graph, temp_file)
            
            # Deserialize
            restored_graph = serializer.deserialize_graph(temp_file)
            
            # Check that the graph is the same
            assert len(restored_graph.nodes) == len(graph.nodes)
            assert len(restored_graph.edges) == len(graph.edges)
            
            # Check node attributes
            assert restored_graph.nodes['node1']['attr1'] == 'value1'
            assert restored_graph.nodes['node1']['attr2'] == 42
            
            # Check edge attributes
            assert restored_graph.edges['node1', 'node2']['weight'] == 1.5
        
        finally:
            Path(temp_file).unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])