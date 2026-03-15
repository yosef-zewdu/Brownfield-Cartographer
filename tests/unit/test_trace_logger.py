"""Unit tests for CartographyTraceLogger."""

import pytest
import json
from pathlib import Path
from datetime import datetime

from agents.trace_logger import (
    CartographyTraceLogger,
    ActionLogEntry,
    ErrorLogEntry,
    LLMCallLogEntry
)


@pytest.fixture
def trace_logger():
    """Create a fresh CartographyTraceLogger instance."""
    return CartographyTraceLogger()


@pytest.fixture
def temp_output_path(tmp_path):
    """Create a temporary output path for trace logs."""
    return tmp_path / "cartography_trace.jsonl"


def test_trace_logger_initialization():
    """Test CartographyTraceLogger can be initialized."""
    logger = CartographyTraceLogger()
    assert logger is not None
    assert logger.log_entries == []


def test_log_action_basic(trace_logger):
    """Test logging a basic action."""
    trace_logger.log_action(
        agent="surveyor",
        action="Analyzed module structure",
        evidence_source="src/main.py",
        evidence_type="tree_sitter",
        confidence=0.95,
        resolution_status="resolved"
    )
    
    assert len(trace_logger.log_entries) == 1
    entry = trace_logger.log_entries[0]
    
    assert isinstance(entry, ActionLogEntry)
    assert entry.entry_type == "action"
    assert entry.agent == "surveyor"
    assert entry.action == "Analyzed module structure"
    assert entry.evidence_source == "src/main.py"
    assert entry.evidence_type == "tree_sitter"
    assert entry.confidence == 0.95
    assert entry.resolution_status == "resolved"
    assert entry.details is None


def test_log_action_with_details(trace_logger):
    """Test logging an action with additional details."""
    details = {
        "module_count": 10,
        "complexity_score": 45,
        "imports": ["os", "sys"]
    }
    
    trace_logger.log_action(
        agent="hydrologist",
        action="Extracted data lineage",
        evidence_source="src/pipeline.py",
        evidence_type="sqlglot",
        confidence=0.85,
        resolution_status="partial",
        details=details
    )
    
    assert len(trace_logger.log_entries) == 1
    entry = trace_logger.log_entries[0]
    
    assert entry.details == details
    assert entry.details["module_count"] == 10


def test_log_action_all_evidence_types(trace_logger):
    """Test logging actions with all evidence types."""
    evidence_types = ["tree_sitter", "sqlglot", "yaml_parse", "heuristic", "llm"]
    
    for ev_type in evidence_types:
        trace_logger.log_action(
            agent="semanticist",
            action=f"Test action with {ev_type}",
            evidence_source="test_file.py",
            evidence_type=ev_type,
            confidence=0.8,
            resolution_status="resolved"
        )
    
    assert len(trace_logger.log_entries) == 5
    
    for i, ev_type in enumerate(evidence_types):
        assert trace_logger.log_entries[i].evidence_type == ev_type


def test_log_action_all_resolution_statuses(trace_logger):
    """Test logging actions with all resolution statuses."""
    statuses = ["resolved", "partial", "dynamic", "inferred"]
    
    for status in statuses:
        trace_logger.log_action(
            agent="archivist",
            action=f"Test action with {status}",
            evidence_source="test_file.py",
            evidence_type="heuristic",
            confidence=0.7,
            resolution_status=status
        )
    
    assert len(trace_logger.log_entries) == 4
    
    for i, status in enumerate(statuses):
        assert trace_logger.log_entries[i].resolution_status == status


def test_log_error_basic(trace_logger):
    """Test logging a basic error."""
    trace_logger.log_error(
        agent="surveyor",
        severity="error",
        message="Failed to parse file"
    )
    
    assert len(trace_logger.log_entries) == 1
    entry = trace_logger.log_entries[0]
    
    assert isinstance(entry, ErrorLogEntry)
    assert entry.entry_type == "error"
    assert entry.agent == "surveyor"
    assert entry.severity == "error"
    assert entry.message == "Failed to parse file"
    assert entry.evidence_source is None
    assert entry.evidence_type is None
    assert entry.context is None


def test_log_error_with_context(trace_logger):
    """Test logging an error with full context."""
    context = {
        "file_path": "src/broken.py",
        "line_number": 42,
        "exception": "SyntaxError"
    }
    
    trace_logger.log_error(
        agent="hydrologist",
        severity="warning",
        message="Could not extract complete lineage",
        evidence_source="src/pipeline.py",
        evidence_type="sqlglot",
        context=context
    )
    
    assert len(trace_logger.log_entries) == 1
    entry = trace_logger.log_entries[0]
    
    assert entry.severity == "warning"
    assert entry.evidence_source == "src/pipeline.py"
    assert entry.evidence_type == "sqlglot"
    assert entry.context == context
    assert entry.context["line_number"] == 42


def test_log_llm_call_basic(trace_logger):
    """Test logging a basic LLM call."""
    trace_logger.log_llm_call(
        agent="semanticist",
        model="gpt-4",
        prompt_tokens=150,
        completion_tokens=50,
        confidence=0.9,
        purpose="Generate module purpose statement"
    )
    
    assert len(trace_logger.log_entries) == 1
    entry = trace_logger.log_entries[0]
    
    assert isinstance(entry, LLMCallLogEntry)
    assert entry.entry_type == "llm_call"
    assert entry.agent == "semanticist"
    assert entry.model == "gpt-4"
    assert entry.prompt_tokens == 150
    assert entry.completion_tokens == 50
    assert entry.total_tokens == 200
    assert entry.confidence == 0.9
    assert entry.purpose == "Generate module purpose statement"
    assert entry.result_summary is None


def test_log_llm_call_with_summary(trace_logger):
    """Test logging an LLM call with result summary."""
    trace_logger.log_llm_call(
        agent="archivist",
        model="gemini-pro",
        prompt_tokens=200,
        completion_tokens=100,
        confidence=0.85,
        purpose="Answer Day-One question",
        result_summary="Identified 3 data sources and 5 transformations"
    )
    
    assert len(trace_logger.log_entries) == 1
    entry = trace_logger.log_entries[0]
    
    assert entry.model == "gemini-pro"
    assert entry.total_tokens == 300
    assert entry.result_summary == "Identified 3 data sources and 5 transformations"


def test_flush_creates_jsonl_file(trace_logger, temp_output_path):
    """Test flushing log entries to JSONL file."""
    # Add some log entries
    trace_logger.log_action(
        agent="surveyor",
        action="Test action 1",
        evidence_source="file1.py",
        evidence_type="tree_sitter",
        confidence=0.9,
        resolution_status="resolved"
    )
    
    trace_logger.log_error(
        agent="hydrologist",
        severity="warning",
        message="Test warning"
    )
    
    trace_logger.log_llm_call(
        agent="semanticist",
        model="gpt-4",
        prompt_tokens=100,
        completion_tokens=50,
        confidence=0.85,
        purpose="Test purpose"
    )
    
    # Flush to file
    trace_logger.flush(temp_output_path)
    
    # Verify file exists
    assert temp_output_path.exists()
    
    # Read and verify JSONL content
    with open(temp_output_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    assert len(lines) == 4
    
    # Parse each line as JSON
    header = json.loads(lines[0])
    entry1 = json.loads(lines[1])
    entry2 = json.loads(lines[2])
    entry3 = json.loads(lines[3])
    
    assert header['entry_type'] == 'run_start'
    assert 'run_id' in header
    
    assert entry1['entry_type'] == 'action'
    assert entry1['agent'] == 'surveyor'
    assert entry1['action'] == 'Test action 1'
    
    assert entry2['entry_type'] == 'error'
    assert entry2['severity'] == 'warning'
    
    assert entry3['entry_type'] == 'llm_call'
    assert entry3['model'] == 'gpt-4'
    assert entry3['total_tokens'] == 150


def test_flush_creates_parent_directory(trace_logger, tmp_path):
    """Test that flush creates parent directories if they don't exist."""
    nested_path = tmp_path / "nested" / "dir" / "trace.jsonl"
    
    trace_logger.log_action(
        agent="surveyor",
        action="Test",
        evidence_source="test.py",
        evidence_type="tree_sitter",
        confidence=0.9,
        resolution_status="resolved"
    )
    
    trace_logger.flush(nested_path)
    
    assert nested_path.exists()
    assert nested_path.parent.exists()


def test_flush_handles_empty_log(trace_logger, temp_output_path):
    """Test flushing an empty log writes only the run_start header."""
    trace_logger.flush(temp_output_path)
    
    assert temp_output_path.exists()
    
    with open(temp_output_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Only the run_start header should be present
    assert len(lines) == 1
    header = json.loads(lines[0])
    assert header['entry_type'] == 'run_start'
    assert header['entry_count'] == 0


def test_get_statistics_empty(trace_logger):
    """Test getting statistics from empty log."""
    stats = trace_logger.get_statistics()
    
    assert stats['total_entries'] == 0
    assert stats['by_type'] == {}
    assert stats['by_agent'] == {}
    assert stats['by_evidence_type'] == {}
    assert stats['total_llm_tokens'] == 0
    assert stats['average_confidence'] == 0.0


def test_get_statistics_with_entries(trace_logger):
    """Test getting statistics with various log entries."""
    # Add action entries
    trace_logger.log_action(
        agent="surveyor",
        action="Action 1",
        evidence_source="file1.py",
        evidence_type="tree_sitter",
        confidence=0.9,
        resolution_status="resolved"
    )
    
    trace_logger.log_action(
        agent="surveyor",
        action="Action 2",
        evidence_source="file2.py",
        evidence_type="heuristic",
        confidence=0.8,
        resolution_status="partial"
    )
    
    # Add error entry
    trace_logger.log_error(
        agent="hydrologist",
        severity="warning",
        message="Warning message"
    )
    
    # Add LLM call entries
    trace_logger.log_llm_call(
        agent="semanticist",
        model="gpt-4",
        prompt_tokens=100,
        completion_tokens=50,
        confidence=0.95,
        purpose="Purpose 1"
    )
    
    trace_logger.log_llm_call(
        agent="archivist",
        model="gemini-pro",
        prompt_tokens=200,
        completion_tokens=100,
        confidence=0.85,
        purpose="Purpose 2"
    )
    
    stats = trace_logger.get_statistics()
    
    assert stats['total_entries'] == 5
    assert stats['by_type'] == {'action': 2, 'error': 1, 'llm_call': 2}
    assert stats['by_agent'] == {'surveyor': 2, 'hydrologist': 1, 'semanticist': 1, 'archivist': 1}
    assert stats['by_evidence_type'] == {'tree_sitter': 1, 'heuristic': 1}
    assert stats['total_llm_tokens'] == 450  # 150 + 300
    assert stats['average_confidence'] == pytest.approx(0.875)  # (0.9 + 0.8 + 0.95 + 0.85) / 4


def test_clear(trace_logger):
    """Test clearing log entries."""
    # Add some entries
    trace_logger.log_action(
        agent="surveyor",
        action="Test",
        evidence_source="test.py",
        evidence_type="tree_sitter",
        confidence=0.9,
        resolution_status="resolved"
    )
    
    assert len(trace_logger.log_entries) == 1
    
    # Clear
    trace_logger.clear()
    
    assert len(trace_logger.log_entries) == 0


def test_timestamp_format(trace_logger):
    """Test that timestamps are in ISO 8601 format."""
    trace_logger.log_action(
        agent="surveyor",
        action="Test",
        evidence_source="test.py",
        evidence_type="tree_sitter",
        confidence=0.9,
        resolution_status="resolved"
    )
    
    entry = trace_logger.log_entries[0]
    
    # Verify timestamp can be parsed as ISO 8601
    timestamp = datetime.fromisoformat(entry.timestamp)
    assert isinstance(timestamp, datetime)


def test_confidence_validation():
    """Test that confidence scores are validated."""
    # Valid confidence scores
    entry = ActionLogEntry(
        timestamp=datetime.now().isoformat(),
        agent="surveyor",
        action="Test",
        evidence_source="test.py",
        evidence_type="tree_sitter",
        confidence=0.5,
        resolution_status="resolved"
    )
    assert entry.confidence == 0.5
    
    # Invalid confidence scores should raise validation error
    with pytest.raises(Exception):  # Pydantic ValidationError
        ActionLogEntry(
            timestamp=datetime.now().isoformat(),
            agent="surveyor",
            action="Test",
            evidence_source="test.py",
            evidence_type="tree_sitter",
            confidence=1.5,  # Invalid: > 1.0
            resolution_status="resolved"
        )
    
    with pytest.raises(Exception):  # Pydantic ValidationError
        ActionLogEntry(
            timestamp=datetime.now().isoformat(),
            agent="surveyor",
            action="Test",
            evidence_source="test.py",
            evidence_type="tree_sitter",
            confidence=-0.1,  # Invalid: < 0.0
            resolution_status="resolved"
        )


def test_multiple_agents_logging(trace_logger):
    """Test that all four agents can log actions."""
    agents = ["surveyor", "hydrologist", "semanticist", "archivist"]
    
    for agent in agents:
        trace_logger.log_action(
            agent=agent,
            action=f"Action by {agent}",
            evidence_source="test.py",
            evidence_type="tree_sitter",
            confidence=0.9,
            resolution_status="resolved"
        )
    
    assert len(trace_logger.log_entries) == 4
    
    for i, agent in enumerate(agents):
        assert trace_logger.log_entries[i].agent == agent


def test_jsonl_format_integrity(trace_logger, temp_output_path):
    """Test that JSONL format maintains integrity with special characters."""
    # Add entry with special characters
    trace_logger.log_action(
        agent="surveyor",
        action="Test with \"quotes\" and \n newlines",
        evidence_source="file with spaces.py",
        evidence_type="tree_sitter",
        confidence=0.9,
        resolution_status="resolved",
        details={"key": "value with 'quotes'"}
    )
    
    trace_logger.flush(temp_output_path)
    
    # Read back and verify — first line is run_start header, second is the action entry
    with open(temp_output_path, 'r', encoding='utf-8') as f:
        f.readline()  # skip run_start header
        line = f.readline()
    
    entry = json.loads(line)
    assert "quotes" in entry['action']
    assert entry['details']['key'] == "value with 'quotes'"
