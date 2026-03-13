"""Integration tests for Semanticist agent."""

import pytest
from pathlib import Path
import networkx as nx

from agents.semanticist import SemanticistAgent
from agents.context_budget import ContextWindowBudget
from models import ModuleNode, DatasetNode, TransformationNode, ProvenanceMetadata


@pytest.fixture
def sample_modules():
    """Create sample modules for testing."""
    provenance = ProvenanceMetadata(
        evidence_type="tree_sitter",
        source_file="test.py",
        confidence=1.0,
        resolution_status="resolved"
    )
    
    modules = [
        ModuleNode(
            path="src/data/loader.py",
            language="python",
            complexity_score=50,
            imports=["pandas", "sqlalchemy"],
            exports=["load_data", "DataLoader"],
            provenance=provenance
        ),
        ModuleNode(
            path="src/api/routes.py",
            language="python",
            complexity_score=75,
            imports=["flask", "src.data.loader"],
            exports=["app", "create_routes"],
            provenance=provenance
        ),
        ModuleNode(
            path="src/utils/helpers.py",
            language="python",
            complexity_score=20,
            imports=[],
            exports=["format_date", "validate_input"],
            provenance=provenance
        ),
    ]
    
    return modules


@pytest.fixture
def sample_module_graph(sample_modules):
    """Create sample module graph."""
    graph = nx.DiGraph()
    
    for module in sample_modules:
        graph.add_node(
            module.path,
            **module.model_dump(exclude={'provenance'})
        )
        graph.nodes[module.path]['provenance'] = module.provenance.model_dump()
    
    # Add some edges
    graph.add_edge("src/api/routes.py", "src/data/loader.py")
    graph.add_edge("src/data/loader.py", "src/utils/helpers.py")
    
    return graph


@pytest.fixture
def sample_lineage_graph():
    """Create sample lineage graph."""
    graph = nx.DiGraph()
    
    # Add dataset nodes
    graph.add_node("users_table", node_type="dataset")
    graph.add_node("orders_table", node_type="dataset")
    
    # Add transformation nodes
    graph.add_node("transform_1", node_type="transformation")
    
    # Add edges
    graph.add_edge("users_table", "transform_1")
    graph.add_edge("transform_1", "orders_table")
    
    return graph


def test_context_budget_initialization():
    """Test ContextWindowBudget initialization."""
    budget = ContextWindowBudget()
    
    assert budget.usage == {}
    assert budget.encoding is not None


def test_context_budget_estimate_tokens():
    """Test token estimation."""
    budget = ContextWindowBudget()
    
    text = "This is a test sentence."
    tokens = budget.estimate_tokens(text)
    
    assert tokens > 0
    assert isinstance(tokens, int)


def test_context_budget_track_usage():
    """Test usage tracking."""
    budget = ContextWindowBudget()
    
    budget.track_usage("gemini-flash", 100, 50)
    
    assert "gemini-flash" in budget.usage
    assert budget.usage["gemini-flash"]["input_tokens"] == 100
    assert budget.usage["gemini-flash"]["output_tokens"] == 50


def test_context_budget_cumulative_cost():
    """Test cost calculation."""
    budget = ContextWindowBudget()
    
    budget.track_usage("gemini-flash", 1_000_000, 500_000)
    
    cost = budget.get_cumulative_cost("gemini-flash")
    
    # Cost should be: (1M / 1M) * 0.075 + (0.5M / 1M) * 0.30 = 0.075 + 0.15 = 0.225
    assert cost == pytest.approx(0.225, rel=0.01)


def test_context_budget_select_model():
    """Test model selection."""
    budget = ContextWindowBudget()
    
    bulk_model = budget.select_model("bulk")
    assert bulk_model == "gemini-flash"
    
    synthesis_model = budget.select_model("synthesis")
    assert synthesis_model == "claude-3-sonnet"


def test_semanticist_initialization():
    """Test SemanticistAgent initialization."""
    agent = SemanticistAgent()
    
    assert agent.budget_tracker is not None
    assert agent.purpose_generator is not None
    assert agent.drift_detector is not None
    assert agent.domain_clusterer is not None
    assert agent.question_answerer is not None
    assert agent.errors == []


def test_semanticist_enrich_modules(sample_modules, mocker):
    """Test purpose statement generation."""
    agent = SemanticistAgent()
    
    # Mock file reading to avoid file not found errors
    mock_open = mocker.mock_open(read_data="def test(): pass")
    mocker.patch("builtins.open", mock_open)
    
    # This will use placeholder purposes since we don't have actual LLM
    enriched = agent.enrich_modules_with_purpose(sample_modules)
    
    assert len(enriched) == len(sample_modules)
    # Some modules might be skipped (e.g., utils with low complexity)
    # But at least the larger modules should have purposes
    modules_with_purpose = [m for m in enriched if m.purpose_statement]
    assert len(modules_with_purpose) >= 1


def test_semanticist_cluster_domains(sample_modules, mocker):
    """Test domain clustering."""
    agent = SemanticistAgent()
    
    # Mock file reading
    mock_open = mocker.mock_open(read_data="def test(): pass")
    mocker.patch("builtins.open", mock_open)
    
    # First generate purposes
    enriched = agent.enrich_modules_with_purpose(sample_modules)
    
    # Then cluster
    clustered = agent.cluster_domains(enriched)
    
    assert len(clustered) == len(sample_modules)
    # At least some modules should be clustered (those with purposes)
    modules_with_cluster = [m for m in clustered if m.domain_cluster]
    assert len(modules_with_cluster) >= 1


def test_semanticist_answer_day_one_questions(
    sample_modules,
    sample_module_graph,
    sample_lineage_graph
):
    """Test Day-One question answering."""
    agent = SemanticistAgent()
    
    # Enrich modules first
    enriched = agent.enrich_modules_with_purpose(sample_modules)
    enriched = agent.cluster_domains(enriched)
    
    # Answer questions
    answers = agent.answer_day_one_questions(
        enriched,
        sample_module_graph,
        sample_lineage_graph,
        [],  # datasets
        []   # transformations
    )
    
    assert isinstance(answers, dict)
    assert 'ingestion_path' in answers
    assert 'critical_outputs' in answers
    assert 'blast_radius' in answers
    assert 'logic_distribution' in answers
    assert 'change_velocity' in answers


def test_semanticist_full_pipeline(
    sample_modules,
    sample_module_graph,
    sample_lineage_graph
):
    """Test complete semantic analysis pipeline."""
    agent = SemanticistAgent()
    
    enriched_modules, day_one_answers = agent.analyze_repository(
        sample_modules,
        sample_module_graph,
        sample_lineage_graph,
        [],
        []
    )
    
    assert len(enriched_modules) == len(sample_modules)
    assert isinstance(day_one_answers, dict)
    assert len(day_one_answers) == 5
    
    # Check usage summary
    summary = agent.get_analysis_summary()
    assert 'token_usage' in summary
    assert 'errors' in summary


def test_semanticist_graceful_degradation(sample_modules):
    """Test that Semanticist continues on errors."""
    agent = SemanticistAgent()
    
    # Create invalid module graph
    invalid_graph = nx.DiGraph()
    
    # Should not crash
    enriched, answers = agent.analyze_repository(
        sample_modules,
        invalid_graph,
        nx.DiGraph(),
        [],
        []
    )
    
    assert len(enriched) == len(sample_modules)
    assert isinstance(answers, dict)
