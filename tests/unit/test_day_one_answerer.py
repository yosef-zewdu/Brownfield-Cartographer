"""Unit tests for DayOneQuestionAnswerer agent."""

import pytest
import networkx as nx
from unittest.mock import Mock, patch

from agents.day_one_answerer import DayOneQuestionAnswerer
from models import ModuleNode, DatasetNode, TransformationNode, ProvenanceMetadata


@pytest.fixture
def sample_provenance():
    """Create sample provenance metadata."""
    return ProvenanceMetadata(
        evidence_type="tree_sitter",
        source_file="test.py",
        line_range=(1, 10),
        confidence=0.9,
        resolution_status="resolved"
    )


@pytest.fixture
def sample_modules(sample_provenance):
    """Create sample module nodes."""
    return [
        ModuleNode(
            path="src/data_loader.py",
            language="python",
            purpose_statement="Loads data from CSV files and databases",
            domain_cluster="Data Processing",
            complexity_score=50,
            change_velocity=15,
            exports=["load_csv", "load_db"],
            provenance=sample_provenance
        ),
        ModuleNode(
            path="src/api_handler.py",
            language="python",
            purpose_statement="Handles API requests and responses",
            domain_cluster="API Integration",
            complexity_score=80,
            change_velocity=25,
            exports=["handle_request", "send_response"],
            provenance=sample_provenance
        ),
    ]



@pytest.fixture
def sample_datasets(sample_provenance):
    """Create sample dataset nodes."""
    return [
        DatasetNode(
            name="users.csv",
            storage_type="file",
            discovered_in="src/data_loader.py",
            provenance=sample_provenance
        ),
        DatasetNode(
            name="orders_table",
            storage_type="table",
            discovered_in="src/database.py",
            provenance=sample_provenance
        ),
    ]


@pytest.fixture
def sample_transformations(sample_provenance):
    """Create sample transformation nodes."""
    return [
        TransformationNode(
            id="transform_1",
            source_datasets=["users.csv"],
            target_datasets=["processed_users"],
            transformation_type="pandas",
            source_file="src/data_loader.py",
            line_range=(10, 20),
            provenance=sample_provenance
        ),
    ]


@pytest.fixture
def sample_lineage_graph(sample_datasets, sample_transformations):
    """Create sample lineage graph."""
    graph = nx.DiGraph()
    
    # Add dataset nodes
    for dataset in sample_datasets:
        graph.add_node(dataset.name, node_type='dataset', **dataset.model_dump(exclude={'provenance'}))
    
    # Add transformation nodes
    for transformation in sample_transformations:
        graph.add_node(transformation.id, node_type='transformation', **transformation.model_dump(exclude={'provenance'}))
    
    # Add edges
    graph.add_edge("users.csv", "transform_1", edge_type='consumes')
    graph.add_edge("transform_1", "processed_users", edge_type='produces')
    
    return graph



@pytest.fixture
def sample_module_graph(sample_modules):
    """Create sample module graph."""
    graph = nx.DiGraph()
    
    for module in sample_modules:
        graph.add_node(module.path, **module.model_dump(exclude={'provenance'}))
    
    # Add import edge
    graph.add_edge("src/api_handler.py", "src/data_loader.py", import_count=1)
    
    return graph


def test_day_one_answerer_initialization():
    """Test DayOneQuestionAnswerer initialization."""
    answerer = DayOneQuestionAnswerer()
    assert answerer is not None
    assert answerer.llm_config is not None


def test_answer_ingestion_path(sample_lineage_graph, sample_datasets, sample_transformations):
    """Test answering ingestion path question."""
    answerer = DayOneQuestionAnswerer()
    
    result = answerer.answer_ingestion_path(
        sample_lineage_graph,
        sample_datasets,
        sample_transformations
    )
    
    assert 'answer' in result
    assert 'evidence' in result
    assert 'provenance' in result
    assert isinstance(result['evidence'], list)
    assert result['provenance'].evidence_type == "heuristic"


def test_answer_critical_outputs(sample_lineage_graph, sample_module_graph, sample_datasets, sample_modules):
    """Test answering critical outputs question."""
    answerer = DayOneQuestionAnswerer()
    
    result = answerer.answer_critical_outputs(
        sample_lineage_graph,
        sample_module_graph,
        sample_datasets,
        sample_modules
    )
    
    assert 'answer' in result
    assert 'evidence' in result
    assert 'provenance' in result
    assert isinstance(result['evidence'], list)



def test_answer_blast_radius(sample_lineage_graph, sample_module_graph):
    """Test answering blast radius question."""
    answerer = DayOneQuestionAnswerer()
    
    result = answerer.answer_blast_radius(
        sample_lineage_graph,
        sample_module_graph
    )
    
    assert 'answer' in result
    assert 'evidence' in result
    assert 'provenance' in result
    assert result['provenance'].evidence_type == "heuristic"


def test_answer_logic_distribution(sample_modules):
    """Test answering logic distribution question."""
    answerer = DayOneQuestionAnswerer()
    
    result = answerer.answer_logic_distribution(sample_modules)
    
    assert 'answer' in result
    assert 'evidence' in result
    assert 'provenance' in result
    assert isinstance(result['evidence'], list)


def test_answer_change_velocity(sample_modules):
    """Test answering change velocity question."""
    answerer = DayOneQuestionAnswerer()
    
    result = answerer.answer_change_velocity(sample_modules, top_n=5)
    
    assert 'answer' in result
    assert 'evidence' in result
    assert 'provenance' in result
    assert result['provenance'].confidence == 1.0  # Git data is highly reliable


def test_answer_all_questions(sample_module_graph, sample_lineage_graph, sample_modules, sample_datasets, sample_transformations):
    """Test answering all five Day-One questions."""
    answerer = DayOneQuestionAnswerer()
    
    answers = answerer.answer_all_questions(
        sample_module_graph,
        sample_lineage_graph,
        sample_modules,
        sample_datasets,
        sample_transformations
    )
    
    assert 'ingestion_path' in answers
    assert 'critical_outputs' in answers
    assert 'blast_radius' in answers
    assert 'logic_distribution' in answers
    assert 'change_velocity' in answers
    
    # Verify each answer has required fields
    for question_name, answer_dict in answers.items():
        assert 'answer' in answer_dict
        assert 'evidence' in answer_dict
        assert 'provenance' in answer_dict
