# Navigator Query Tools

The Navigator provides four specialized query tools for exploring the knowledge graph with full provenance tracking. Each tool returns results with evidence citations, confidence scores, and resolution status.

## Overview

All Navigator tools follow these principles:

1. **Provenance Tracking**: Every result includes evidence_type, confidence, and resolution_status
2. **Evidence Citations**: Results cite source_file and line_range where applicable
3. **Confidence Scores**: All inferences include confidence levels (0.0-1.0)
4. **Provenance Chains**: Complex queries show the full chain of evidence sources

## Tools

### 1. FindImplementationTool

Semantic search over module purpose statements using sentence embeddings.

**Use Cases:**
- "Where is authentication implemented?"
- "Find modules that handle database connections"
- "Which code deals with payment processing?"

**Example:**

```python
from agents.navigator import FindImplementationTool

tool = FindImplementationTool(modules)
result = tool("user authentication", top_k=5)

# Result structure:
{
    'query': 'user authentication',
    'results': [
        {
            'path': 'src/auth/login.py',
            'purpose': 'Handles user authentication...',
            'similarity_score': 0.856,
            'domain_cluster': 'Authentication',
            'complexity_score': 75,
            'provenance_chain': [
                {
                    'source': 'purpose_statement',
                    'evidence_type': 'llm',
                    'confidence': 0.7,
                    'resolution_status': 'inferred'
                },
                {
                    'source': 'semantic_search',
                    'evidence_type': 'heuristic',
                    'confidence': 0.856,
                    'resolution_status': 'inferred',
                    'method': 'cosine_similarity'
                }
            ]
        }
    ],
    'provenance': {
        'evidence_type': 'heuristic',
        'confidence': 0.8,
        'resolution_status': 'inferred',
        'method': 'sentence_transformer_embedding'
    }
}
```

**Provenance:**
- Evidence Type: `heuristic` (embedding-based similarity)
- Confidence: 0.8 (semantic similarity is approximate)
- Resolution Status: `inferred` (not directly observed)

---

### 2. TraceLineageTool

Traverse data lineage graph upstream or downstream from a dataset or transformation.

**Use Cases:**
- "What datasets feed into analytics_users?"
- "What downstream tables are affected by raw_events?"
- "Show me the full lineage for this dataset"

**Example:**

```python
from agents.navigator import TraceLineageTool

tool = TraceLineageTool(lineage_graph)
result = tool("raw_events", direction="downstream", max_depth=None)

# Result structure:
{
    'dataset': 'raw_events',
    'direction': 'downstream',
    'node_count': 5,
    'edge_count': 4,
    'nodes': [
        {
            'id': 'raw_events',
            'type': 'dataset',
            'storage_type': 'table',
            'discovered_in': 'etl/extract.py',
            'provenance': {
                'evidence_type': 'sqlglot',
                'source_file': 'etl/transform.sql',
                'line_range': (1, 50),
                'confidence': 1.0,
                'resolution_status': 'resolved'
            }
        },
        # ... more nodes
    ],
    'edges': [
        {
            'source': 'transform_1',
            'target': 'raw_events',
            'type': 'consumes',
            'confidence': 1.0,
            'provenance': { ... }
        },
        # ... more edges
    ],
    'provenance': {
        'evidence_type': 'heuristic',
        'confidence': 0.9,
        'resolution_status': 'resolved',
        'method': 'networkx_graph_traversal'
    }
}
```

**Parameters:**
- `dataset`: Dataset name or transformation ID
- `direction`: "upstream" or "downstream"
- `max_depth`: Maximum traversal depth (None for unlimited)

**Provenance:**
- Evidence Type: `heuristic` (graph traversal algorithm)
- Confidence: 0.9 (graph structure is deterministic)
- Resolution Status: `resolved` (directly observed in graph)

---

### 3. BlastRadiusTool

Compute downstream dependencies for a module, including both code and data impacts.

**Use Cases:**
- "What breaks if I change this module?"
- "Show me all downstream dependencies"
- "What's the blast radius of this change?"

**Example:**

```python
from agents.navigator import BlastRadiusTool

tool = BlastRadiusTool(module_graph, lineage_graph)
result = tool("src/db/users.py", include_data_lineage=True)

# Result structure:
{
    'module': 'src/db/users.py',
    'affected_module_count': 3,
    'affected_modules': [
        'src/auth/login.py',
        'src/api/endpoints.py',
        'src/admin/users.py'
    ],
    'affected_dataset_count': 2,
    'affected_datasets': [
        {
            'name': 'staging_users',
            'storage_type': 'table',
            'discovered_in': 'etl/transform.sql',
            'provenance': {
                'evidence_type': 'sqlglot',
                'source_file': 'etl/transform.sql',
                'confidence': 1.0,
                'resolution_status': 'resolved'
            }
        },
        # ... more datasets
    ],
    'provenance': {
        'evidence_type': 'heuristic',
        'confidence': 0.9,
        'resolution_status': 'resolved',
        'method': 'networkx_descendants',
        'note': 'Blast radius computed using graph traversal...'
    }
}
```

**Parameters:**
- `module_path`: Path to module
- `include_data_lineage`: Whether to include data lineage impacts (default: True)

**Provenance:**
- Evidence Type: `heuristic` (graph traversal)
- Confidence: 0.9 (deterministic graph analysis)
- Resolution Status: `resolved` (directly computed from graph)

---

### 4. ExplainModuleTool

Explain a module's purpose, metadata, and graph context.

**Use Cases:**
- "What does this module do?"
- "Show me module metadata"
- "What imports this module?"

**Example:**

```python
from agents.navigator import ExplainModuleTool

tool = ExplainModuleTool(modules, module_graph)
result = tool("src/auth/login.py")

# Result structure:
{
    'found': True,
    'module': {
        'path': 'src/auth/login.py',
        'language': 'python',
        'purpose_statement': 'Handles user authentication...',
        'domain_cluster': 'Authentication',
        'complexity_score': 75,
        'change_velocity': 12,
        'is_dead_code_candidate': False,
        'has_documentation_drift': False,
        'last_modified': '2024-03-13T10:30:00',
        'imports': ['src/db/users.py', 'src/utils/crypto.py'],
        'exports': ['login', 'logout', 'verify_session'],
        'import_count': 2,
        'imported_by_count': 2,
        'imported_by': ['src/api/endpoints.py', 'src/admin/panel.py'],
        'provenance': {
            'evidence_type': 'tree_sitter',
            'source_file': 'src/auth/login.py',
            'line_range': (1, 100),
            'confidence': 1.0,
            'resolution_status': 'resolved'
        }
    },
    'provenance_chain': [
        {
            'evidence_type': 'tree_sitter',
            'source_file': 'src/auth/login.py',
            'confidence': 1.0,
            'resolution_status': 'resolved'
        },
        {
            'source': 'purpose_statement',
            'evidence_type': 'llm',
            'confidence': 0.7,
            'resolution_status': 'inferred',
            'note': 'Purpose statement generated by LLM'
        },
        {
            'source': 'domain_cluster',
            'evidence_type': 'heuristic',
            'confidence': 0.8,
            'resolution_status': 'inferred',
            'note': 'Domain cluster assigned by k-means clustering'
        }
    ],
    'summary': 'Module: src/auth/login.py\nLanguage: python\n...'
}
```

**Provenance Chain:**
The tool builds a provenance chain showing:
1. Module extraction (tree_sitter, confidence: 1.0)
2. Purpose statement generation (llm, confidence: 0.7)
3. Domain clustering (heuristic, confidence: 0.8)

---

## Provenance Model

All tools follow the systematic provenance model:

### Evidence Types

- **tree_sitter**: AST-based static analysis (high confidence)
- **sqlglot**: SQL parsing (high confidence)
- **yaml_parse**: YAML configuration parsing (high confidence)
- **heuristic**: Algorithm-based inference (medium confidence)
- **llm**: LLM-generated content (lower confidence)

### Confidence Levels

- **1.0**: Directly observed, deterministic (e.g., AST parsing)
- **0.9**: Deterministic algorithm (e.g., graph traversal)
- **0.8**: Heuristic with high reliability (e.g., embeddings)
- **0.7**: LLM-generated with validation
- **0.5**: Dynamic or partially resolved
- **0.0**: Failed or not found

### Resolution Status

- **resolved**: Directly observed in source code
- **partial**: Partially resolved (e.g., relative imports)
- **dynamic**: Computed at runtime (e.g., dynamic imports)
- **inferred**: Derived through analysis (e.g., LLM, clustering)

---

## Usage Patterns

### Pattern 1: Semantic Code Search

```python
# Find all modules related to a concept
find_tool = FindImplementationTool(modules)
results = find_tool("payment processing", top_k=10)

for result in results['results']:
    if result['similarity_score'] > 0.7:
        print(f"High confidence match: {result['path']}")
        print(f"  Confidence: {result['similarity_score']:.2f}")
```

### Pattern 2: Impact Analysis

```python
# Analyze impact of changing a module
blast_tool = BlastRadiusTool(module_graph, lineage_graph)
impact = blast_tool("src/core/engine.py")

print(f"Modules affected: {impact['affected_module_count']}")
print(f"Datasets affected: {impact['affected_dataset_count']}")

# Check confidence
if impact['provenance']['confidence'] > 0.8:
    print("High confidence in blast radius analysis")
```

### Pattern 3: Lineage Investigation

```python
# Trace data lineage
trace_tool = TraceLineageTool(lineage_graph)

# Find all upstream sources
upstream = trace_tool("analytics_users", direction="upstream")
print(f"Found {upstream['node_count']} upstream nodes")

# Find all downstream consumers
downstream = trace_tool("raw_events", direction="downstream")
print(f"Found {downstream['node_count']} downstream nodes")
```

### Pattern 4: Module Deep Dive

```python
# Get complete module information
explain_tool = ExplainModuleTool(modules, module_graph)
info = explain_tool("src/auth/login.py")

if info['found']:
    print(info['summary'])
    
    # Check provenance chain
    for prov in info['provenance_chain']:
        print(f"Evidence: {prov['evidence_type']} "
              f"(confidence: {prov['confidence']:.2f})")
```

---

## Testing

Run the test suite:

```bash
pytest tests/unit/test_navigator_tools.py -v
```

Run the example demonstration:

```bash
python examples/navigator_tools_example.py
```

---

## Integration with NavigatorAgent

These tools are designed to be used by the NavigatorAgent (task 8.11) via LangGraph:

```python
from agents.navigator import (
    FindImplementationTool,
    TraceLineageTool,
    BlastRadiusTool,
    ExplainModuleTool
)

# NavigatorAgent will register these as LangGraph tools
tools = [
    FindImplementationTool(modules),
    TraceLineageTool(lineage_graph),
    BlastRadiusTool(module_graph, lineage_graph),
    ExplainModuleTool(modules, module_graph)
]
```

The agent will automatically:
- Parse natural language queries
- Select appropriate tools
- Combine results from multiple tools
- Present evidence with provenance chains

---

## Performance Considerations

### FindImplementationTool
- Embeddings are computed lazily and cached
- First query may be slower (model loading)
- Subsequent queries are fast (cached embeddings)

### TraceLineageTool
- Graph traversal is O(V + E) where V=nodes, E=edges
- Use `max_depth` to limit traversal for large graphs
- Upstream/downstream traversal have similar performance

### BlastRadiusTool
- Combines module and lineage graph traversal
- Set `include_data_lineage=False` for faster results
- Performance scales with graph size

### ExplainModuleTool
- O(1) lookup for module information
- Graph context adds minimal overhead
- Very fast for single module queries

---

## Error Handling

All tools handle errors gracefully:

```python
# Non-existent module
result = explain_tool("nonexistent/module.py")
assert result['found'] == False
assert result['provenance']['confidence'] == 0.0

# Non-existent dataset
result = trace_tool("nonexistent_dataset")
assert result['nodes'] == []
assert result['provenance']['confidence'] == 0.0
```

Errors are logged but don't raise exceptions, allowing analysis to continue.

---

## Future Enhancements

Potential improvements for future versions:

1. **Caching**: Cache query results for repeated queries
2. **Batch Queries**: Support batch processing for multiple queries
3. **Query Optimization**: Optimize graph traversal for large graphs
4. **Natural Language**: Better natural language query parsing
5. **Visualization**: Generate visual representations of results
6. **Export**: Export results to various formats (JSON, CSV, Markdown)

---

## See Also

- [Example Usage](../examples/navigator_tools_example.py)
- [Test Suite](../tests/unit/test_navigator_tools.py)
