"""Unit tests for CODEBASEGenerator."""

import pytest
import networkx as nx
from datetime import datetime

from agents.archivist import CODEBASEGenerator
from models import ModuleNode, DatasetNode, TransformationNode, ProvenanceMetadata


@pytest.fixture
def sample_provenance():
    """Create sample provenance metadata."""
    return ProvenanceMetadata(
        evidence_type="tree_sitter",
        source_file="test.py",
        line_range=(1, 10),
        confidence=1.0,
        resolution_status="resolved"
    )


@pytest.fixture
def sample_modules(sample_provenance):
    """Create sample modules for testing."""
    return [
        ModuleNode(
            path="src/main.py",
            language="python",
            purpose_statement="Main entry point for the application.",
            domain_cluster="Core",
            complexity_score=50,
            change_velocity=10,
            is_dead_code_candidate=False,
            last_modified=datetime.now(),
            imports=["src.utils", "src.config"],
            exports=["main", "run"],
            docstring="Main module",
            has_documentation_drift=False,
            provenance=sample_provenance
        ),
        ModuleNode(
            path="src/utils.py",
            language="python",
            purpose_statement="Utility functions for data processing.",
            domain_cluster="Utilities",
            complexity_score=30,
            change_velocity=5,
            is_dead_code_candidate=False,
            last_modified=datetime.now(),
            imports=[],
            exports=["process_data", "validate"],
            docstring="Utility module",
            has_documentation_drift=True,
            provenance=sample_provenance
        ),
        ModuleNode(
            path="src/config.py",
            language="python",
            purpose_statement="Configuration settings.",
            domain_cluster="Core",
            complexity_score=10,
            change_velocity=2,
            is_dead_code_candidate=True,
            last_modified=datetime.now(),
            imports=[],
            exports=["CONFIG"],
            docstring=None,
            has_documentation_drift=False,
            provenance=sample_provenance
        )
    ]


@pytest.fixture
def sample_datasets(sample_provenance):
    """Create sample datasets for testing."""
    return [
        DatasetNode(
            name="users_table",
            storage_type="table",
            schema_snapshot={"id": "int", "name": "str"},
            freshness_sla=None,
            owner=None,
            is_source_of_truth=True,
            discovered_in="src/main.py",
            provenance=sample_provenance
        ),
        DatasetNode(
            name="output_file.csv",
            storage_type="file",
            schema_snapshot=None,
            freshness_sla=None,
            owner=None,
            is_source_of_truth=False,
            discovered_in="src/utils.py",
            provenance=sample_provenance
        )
    ]


@pytest.fixture
def sample_transformations(sample_provenance):
    """Create sample transformations for testing."""
    return [
        TransformationNode(
            id="transform_1",
            source_datasets=["users_table"],
            target_datasets=["output_file.csv"],
            transformation_type="pandas",
            source_file="src/main.py",
            line_range=(20, 30),
            sql_query=None,
            provenance=sample_provenance
        )
    ]


@pytest.fixture
def sample_module_graph(sample_modules):
    """Create sample module graph."""
    graph = nx.DiGraph()
    for module in sample_modules:
        graph.add_node(module.path, **module.model_dump())
    
    # Add edges
    graph.add_edge("src/main.py", "src/utils.py", import_count=1)
    graph.add_edge("src/main.py", "src/config.py", import_count=1)
    
    return graph


@pytest.fixture
def sample_lineage_graph(sample_datasets, sample_transformations):
    """Create sample lineage graph."""
    graph = nx.DiGraph()
    
    # Add dataset nodes
    for dataset in sample_datasets:
        graph.add_node(dataset.name, node_type='dataset', **dataset.model_dump())
    
    # Add transformation nodes
    for transform in sample_transformations:
        graph.add_node(transform.id, node_type='transformation', **transform.model_dump())
    
    # Add edges
    graph.add_edge("users_table", "transform_1")
    graph.add_edge("transform_1", "output_file.csv")
    
    return graph


@pytest.fixture
def sample_pagerank():
    """Create sample PageRank scores."""
    return {
        "src/main.py": 0.5,
        "src/utils.py": 0.3,
        "src/config.py": 0.2
    }


@pytest.fixture
def sample_circular_deps():
    """Create sample circular dependencies."""
    return [
        ["src/module_a.py", "src/module_b.py", "src/module_a.py"]
    ]


@pytest.fixture
def sample_day_one_answers():
    """Create sample Day-One answers."""
    return {
        'ingestion_path': {
            'summary': 'Data enters through users_table.',
            'details': 'Primary ingestion path details...'
        },
        'logic_distribution': {
            'summary': 'Logic is concentrated in Core domain.',
            'details': 'Logic distribution details...'
        }
    }


def test_codebase_generator_initialization():
    """Test CODEBASEGenerator can be initialized."""
    generator = CODEBASEGenerator()
    assert generator is not None


def test_generate_complete_codebase(
    sample_modules,
    sample_module_graph,
    sample_lineage_graph,
    sample_datasets,
    sample_transformations,
    sample_pagerank,
    sample_circular_deps,
    sample_day_one_answers
):
    """Test generating complete CODEBASE.md."""
    generator = CODEBASEGenerator()
    
    result = generator.generate(
        modules=sample_modules,
        module_graph=sample_module_graph,
        lineage_graph=sample_lineage_graph,
        datasets=sample_datasets,
        transformations=sample_transformations,
        pagerank_scores=sample_pagerank,
        circular_dependencies=sample_circular_deps,
        day_one_answers=sample_day_one_answers
    )
    
    # Verify result is a string
    assert isinstance(result, str)
    assert len(result) > 0
    
    # Verify all required sections are present
    assert "# CODEBASE.md" in result
    assert "## Architecture Overview" in result
    assert "## Critical Path" in result
    assert "## Data Sources & Sinks" in result
    assert "## Known Debt" in result
    assert "## High-Velocity Files" in result
    assert "## Module Purpose Index" in result


def test_write_architecture_overview(
    sample_modules,
    sample_module_graph,
    sample_lineage_graph,
    sample_day_one_answers
):
    """Test writing architecture overview section."""
    generator = CODEBASEGenerator()
    
    result = generator.write_architecture_overview(
        modules=sample_modules,
        module_graph=sample_module_graph,
        lineage_graph=sample_lineage_graph,
        day_one_answers=sample_day_one_answers
    )
    
    assert "## Architecture Overview" in result
    assert "3 modules" in result
    assert "semantic domains" in result


def test_write_critical_path(sample_modules, sample_pagerank):
    """Test writing critical path section."""
    generator = CODEBASEGenerator()
    
    result = generator.write_critical_path(
        pagerank_scores=sample_pagerank,
        modules=sample_modules
    )
    
    assert "## Critical Path" in result
    assert "src/main.py" in result
    assert "PageRank" in result
    assert "Main entry point" in result


def test_write_data_sources_sinks(sample_lineage_graph, sample_datasets):
    """Test writing data sources and sinks section."""
    generator = CODEBASEGenerator()
    
    result = generator.write_data_sources_sinks(
        lineage_graph=sample_lineage_graph,
        datasets=sample_datasets
    )
    
    assert "## Data Sources & Sinks" in result
    assert "### Data Sources" in result
    assert "### Data Sinks" in result
    assert "users_table" in result
    assert "output_file.csv" in result


def test_write_known_debt(sample_modules, sample_circular_deps):
    """Test writing known debt section."""
    generator = CODEBASEGenerator()
    
    result = generator.write_known_debt(
        circular_dependencies=sample_circular_deps,
        modules=sample_modules
    )
    
    assert "## Known Debt" in result
    assert "### Circular Dependencies" in result
    assert "### Documentation Drift" in result
    assert "src/utils.py" in result  # Has drift


def test_write_high_velocity_files(sample_modules):
    """Test writing high-velocity files section."""
    generator = CODEBASEGenerator()
    
    result = generator.write_high_velocity_files(modules=sample_modules)
    
    assert "## High-Velocity Files" in result
    assert "src/main.py" in result  # Highest velocity
    assert "10 commits" in result


def test_write_module_purpose_index(sample_modules):
    """Test writing module purpose index section."""
    generator = CODEBASEGenerator()
    
    result = generator.write_module_purpose_index(modules=sample_modules)
    
    assert "## Module Purpose Index" in result
    assert "### Core" in result
    assert "### Utilities" in result
    assert "src/main.py" in result
    assert "Main entry point" in result
    assert "dead code candidate" in result  # For config.py


def test_empty_circular_dependencies(sample_modules):
    """Test handling empty circular dependencies."""
    generator = CODEBASEGenerator()
    
    result = generator.write_known_debt(
        circular_dependencies=[],
        modules=sample_modules
    )
    
    assert "No circular dependencies detected" in result


def test_no_change_velocity(sample_provenance):
    """Test handling modules with no change velocity data."""
    modules = [
        ModuleNode(
            path="src/test.py",
            language="python",
            purpose_statement="Test module",
            domain_cluster="Test",
            complexity_score=10,
            change_velocity=None,
            is_dead_code_candidate=False,
            last_modified=datetime.now(),
            imports=[],
            exports=[],
            docstring=None,
            has_documentation_drift=False,
            provenance=sample_provenance
        )
    ]
    
    generator = CODEBASEGenerator()
    result = generator.write_high_velocity_files(modules=modules)
    
    assert "No git history available" in result
