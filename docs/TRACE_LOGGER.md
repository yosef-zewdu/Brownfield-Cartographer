# CartographyTraceLogger Documentation

## Overview

The `CartographyTraceLogger` provides a complete audit trail of all analysis actions with full provenance tracking for the Brownfield Cartographer system. It logs all agent activities, evidence sources, confidence scores, and LLM usage to a JSONL (JSON Lines) file for easy parsing and analysis.

## Features

- **Action Logging**: Track all actions taken by agents (Surveyor, Hydrologist, Semanticist, Archivist)
- **Evidence Tracking**: Distinguish between static analysis (tree_sitter, sqlglot, yaml_parse) and inference (heuristic, llm)
- **Confidence Scores**: Record confidence levels (0.0-1.0) for all logged conclusions
- **Resolution Status**: Track resolution status (resolved, partial, dynamic, inferred)
- **Error Logging**: Log errors and warnings with full provenance context
- **LLM Usage Tracking**: Monitor LLM API calls with token usage and confidence scores
- **JSONL Format**: Write logs in JSON Lines format for easy parsing and analysis
- **Statistics**: Get real-time statistics about logged entries

## Usage

### Basic Example

```python
from pathlib import Path
from agents.trace_logger import CartographyTraceLogger

# Initialize logger
logger = CartographyTraceLogger()

# Log an action
logger.log_action(
    agent="surveyor",
    action="Analyzed module structure",
    evidence_source="src/main.py",
    evidence_type="tree_sitter",
    confidence=0.95,
    resolution_status="resolved",
    details={"imports": ["os", "sys"], "exports": ["main"]}
)

# Log an error
logger.log_error(
    agent="hydrologist",
    severity="warning",
    message="Could not resolve dynamic table name",
    evidence_source="src/pipeline.py",
    evidence_type="sqlglot",
    context={"line_number": 45}
)

# Log an LLM call
logger.log_llm_call(
    agent="semanticist",
    model="gpt-4",
    prompt_tokens=150,
    completion_tokens=50,
    confidence=0.85,
    purpose="Generate module purpose statement",
    result_summary="Entry point module"
)

# Get statistics
stats = logger.get_statistics()
print(f"Total entries: {stats['total_entries']}")
print(f"Average confidence: {stats['average_confidence']:.2f}")

# Write to file
output_path = Path(".cartography") / "cartography_trace.jsonl"
logger.flush(output_path)
```

## Log Entry Types

### ActionLogEntry

Logs agent actions with full provenance tracking.

**Fields:**
- `entry_type`: "action"
- `timestamp`: ISO 8601 timestamp
- `agent`: Agent name (surveyor, hydrologist, semanticist, archivist)
- `action`: Description of the action
- `evidence_source`: Source file or component
- `evidence_type`: Type of evidence (tree_sitter, sqlglot, yaml_parse, heuristic, llm)
- `confidence`: Confidence score (0.0-1.0)
- `resolution_status`: Status (resolved, partial, dynamic, inferred)
- `details`: Optional additional details (dict)

### ErrorLogEntry

Logs errors and warnings with provenance context.

**Fields:**
- `entry_type`: "error"
- `timestamp`: ISO 8601 timestamp
- `agent`: Agent name
- `severity`: Severity level (error, warning)
- `message`: Error message
- `evidence_source`: Optional source file
- `evidence_type`: Optional evidence type
- `context`: Optional additional context (dict)

### LLMCallLogEntry

Logs LLM API calls with usage tracking.

**Fields:**
- `entry_type`: "llm_call"
- `timestamp`: ISO 8601 timestamp
- `agent`: Agent name
- `model`: Model identifier (e.g., "gpt-4", "gemini-pro")
- `prompt_tokens`: Number of prompt tokens
- `completion_tokens`: Number of completion tokens
- `total_tokens`: Total tokens (prompt + completion)
- `confidence`: Confidence score (0.0-1.0)
- `purpose`: Purpose of the LLM call
- `result_summary`: Optional summary of the result

## Evidence Types

The logger distinguishes between two categories of evidence:

### Static Analysis
- `tree_sitter`: Code structure analysis using tree-sitter parsers
- `sqlglot`: SQL query parsing and lineage extraction
- `yaml_parse`: YAML configuration file parsing

### Inference
- `heuristic`: Rule-based inference and pattern matching
- `llm`: Large Language Model inference

## Resolution Status

- `resolved`: Fully resolved with high confidence
- `partial`: Partially resolved, some information missing
- `dynamic`: Runtime-determined, cannot be statically resolved
- `inferred`: Inferred through heuristics or LLM

## JSONL Format

The trace log is written in JSONL (JSON Lines) format, with one JSON object per line:

```jsonl
{"entry_type":"action","timestamp":"2024-03-15T10:30:00.123456","agent":"surveyor","action":"Analyzed module","evidence_source":"src/main.py","evidence_type":"tree_sitter","confidence":0.95,"resolution_status":"resolved","details":null}
{"entry_type":"error","timestamp":"2024-03-15T10:30:01.234567","agent":"hydrologist","severity":"warning","message":"Could not resolve table","evidence_source":"src/query.py","evidence_type":"sqlglot","context":{"line":45}}
{"entry_type":"llm_call","timestamp":"2024-03-15T10:30:02.345678","agent":"semanticist","model":"gpt-4","prompt_tokens":150,"completion_tokens":50,"total_tokens":200,"confidence":0.85,"purpose":"Generate purpose","result_summary":"Module purpose"}
```

## Statistics

The `get_statistics()` method returns:

```python
{
    'total_entries': 10,
    'by_type': {'action': 6, 'error': 2, 'llm_call': 2},
    'by_agent': {'surveyor': 3, 'hydrologist': 4, 'semanticist': 2, 'archivist': 1},
    'by_evidence_type': {'tree_sitter': 3, 'sqlglot': 2, 'heuristic': 1},
    'total_llm_tokens': 450,
    'average_confidence': 0.87
}
```

## API Reference

### CartographyTraceLogger

#### `__init__()`
Initialize a new trace logger.

#### `log_action(agent, action, evidence_source, evidence_type, confidence, resolution_status, details=None)`
Log an agent action with full provenance tracking.

#### `log_error(agent, severity, message, evidence_source=None, evidence_type=None, context=None)`
Log an error or warning with provenance context.

#### `log_llm_call(agent, model, prompt_tokens, completion_tokens, confidence, purpose, result_summary=None)`
Log an LLM API call with usage tracking.

#### `flush(output_path)`
Write accumulated log entries to JSONL file.

#### `get_statistics()`
Get statistics about logged entries.

#### `clear()`
Clear all accumulated log entries.

## Requirements Satisfied

This implementation satisfies the following requirements:

- **17.1**: Log all agent actions with timestamps and provenance
- **17.2**: Distinguish between static analysis and inference evidence types
- **17.3**: Track confidence scores for all conclusions
- **17.4**: Log LLM API calls with token usage
- **17.5**: Write complete audit trail to JSONL format

## Testing

The implementation includes comprehensive unit tests covering:
- Basic logging functionality
- All evidence types and resolution statuses
- Error logging with context
- LLM call logging
- JSONL file writing
- Statistics calculation
- Confidence validation
- Special character handling

Run tests with:
```bash
pytest tests/unit/test_trace_logger.py -v
```

## Example Output

See `examples/trace_logger_example.py` for a complete working example that demonstrates all features of the CartographyTraceLogger.
