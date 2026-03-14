# NavigatorAgent

The NavigatorAgent provides a unified interface for querying the Brownfield Cartographer knowledge graph. It orchestrates four specialized query tools and supports both single-query execution and interactive REPL-style exploration.

## Overview

The NavigatorAgent wraps the four Navigator query tools:
1. **FindImplementationTool** - Semantic search over purpose statements
2. **TraceLineageTool** - Data lineage traversal
3. **BlastRadiusTool** - Dependency impact analysis
4. **ExplainModuleTool** - Module information and metadata

All queries return results with full provenance tracking, including evidence types, confidence scores, and resolution status.

## Features

- **Unified Query Interface**: Single entry point for all query types
- **Auto-Detection**: Automatically selects appropriate tool based on query keywords
- **Explicit Tool Selection**: Override auto-detection with explicit tool names
- **Interactive Mode**: REPL-style interface for continuous exploration
- **Provenance Tracking**: All results include evidence chains and confidence scores
- **Error Handling**: Graceful degradation with informative error messages

## Usage

### Basic Usage

```python
from agents.navigator import NavigatorAgent
import networkx as nx

# Initialize with knowledge graphs
agent = NavigatorAgent(
    modules=module_list,
    module_graph=module_graph,
    lineage_graph=lineage_graph
)

# Run a query (auto-detects tool)
result = agent.run_query("user authentication")

# Run a query with explicit tool
result = agent.run_query(
    "src/auth/login.py",
    tool_name="explain_module"
)

# Run a query with parameters
result = agent.run_query(
    "authentication",
    tool_name="find_implementation",
    top_k=10
)
```

### Interactive Mode

```python
# Launch interactive REPL
agent.interactive_mode()
```

Interactive mode provides a command-line interface:

```
🔍 Query> user authentication
Tool: find_implementation
Provenance: heuristic (confidence: 0.80)

Found 4 results:

  1. src/auth/login.py
     Similarity: 0.856
     Purpose: Handles user authentication...

🔍 Query> explain_module: src/auth/login.py
Tool: explain_module
Query: src/auth/login.py

Module: src/auth/login.py
Language: python

Purpose: Handles user authentication and session management
Domain: Authentication

Complexity: 75
Change Velocity: 12 commits
Imports: 2 modules
Imported by: 3 modules

🔍 Query> exit
Exiting interactive mode...
```

## Query Formats

### Auto-Detection

The agent automatically detects the appropriate tool based on keywords:

```python
# Semantic search (default)
agent.run_query("payment processing")
agent.run_query("where is authentication")

# Lineage traversal
agent.run_query("show lineage for raw_events")
agent.run_query("trace upstream from analytics_users")

# Blast radius
agent.run_query("what breaks if I change src/db/users.py")
agent.run_query("show impact of src/auth/login.py")

# Module explanation
agent.run_query("explain src/api/endpoints.py")
agent.run_query("what does src/utils/crypto.py do")
```

### Explicit Tool Selection

Override auto-detection by specifying the tool name:

```python
# Format: run_query(query, tool_name="tool_name", **params)

agent.run_query(
    "authentication",
    tool_name="find_implementation",
    top_k=5
)

agent.run_query(
    "raw_events",
    tool_name="trace_lineage",
    direction="downstream",
    max_depth=3
)

agent.run_query(
    "src/db/users.py",
    tool_name="blast_radius",
    include_data_lineage=True
)

agent.run_query(
    "src/auth/login.py",
    tool_name="explain_module"
)
```

### Interactive Mode Syntax

In interactive mode, use either format:

```
# Auto-detection
Query> user authentication

# Explicit tool selection
Query> find_implementation: payment processing
Query> trace_lineage: raw_events
Query> blast_radius: src/db/users.py
Query> explain_module: src/auth/login.py
```

## Tool Detection Keywords

The agent uses keyword matching to auto-detect tools:

| Tool | Keywords |
|------|----------|
| trace_lineage | lineage, upstream, downstream, trace, flow |
| blast_radius | blast, impact, affect, break, change, dependency |
| explain_module | explain, what is, what does, module, info, metadata |
| find_implementation | (default for all other queries) |

## Result Structure

All queries return a dictionary with:

```python
{
    'query_metadata': {
        'original_query': str,
        'tool_used': str,
        'parameters': dict
    },
    'provenance': {
        'evidence_type': str,  # tree_sitter, sqlglot, heuristic, llm
        'confidence': float,   # 0.0 to 1.0
        'resolution_status': str,  # resolved, partial, dynamic, inferred
        'method': str  # Optional: algorithm/method used
    },
    # Tool-specific results...
}
```

### FindImplementationTool Results

```python
{
    'query': str,
    'results': [
        {
            'path': str,
            'purpose': str,
            'similarity_score': float,
            'domain_cluster': str,
            'complexity_score': int,
            'provenance_chain': [...]
        }
    ],
    'provenance': {...},
    'query_metadata': {...}
}
```

### TraceLineageTool Results

```python
{
    'dataset': str,
    'direction': str,
    'node_count': int,
    'edge_count': int,
    'nodes': [...],
    'edges': [...],
    'provenance': {...},
    'query_metadata': {...}
}
```

### BlastRadiusTool Results

```python
{
    'module': str,
    'affected_module_count': int,
    'affected_modules': [str],
    'affected_dataset_count': int,
    'affected_datasets': [...],
    'provenance': {...},
    'query_metadata': {...}
}
```

### ExplainModuleTool Results

```python
{
    'found': bool,
    'module': {
        'path': str,
        'language': str,
        'purpose_statement': str,
        'domain_cluster': str,
        'complexity_score': int,
        'change_velocity': int,
        'imports': [str],
        'exports': [str],
        'imported_by': [str],
        ...
    },
    'provenance_chain': [...],
    'summary': str,
    'query_metadata': {...}
}
```

## Error Handling

The agent handles errors gracefully:

```python
# Invalid tool name
result = agent.run_query("test", tool_name="invalid_tool")
# Returns: {'error': '...', 'available_tools': [...]}

# Module not found
result = agent.run_query("nonexistent.py", tool_name="explain_module")
# Returns: {'found': False, 'provenance': {'confidence': 0.0}}

# Query execution error
# Returns: {'error': '...', 'provenance': {'confidence': 0.0}}
```

All errors include:
- Error message
- Provenance with confidence 0.0
- Context information (available tools, query, etc.)

## Interactive Mode Commands

| Command | Description |
|---------|-------------|
| `help` | Show help message with examples |
| `tools` | List all available tools |
| `exit` or `quit` | Exit interactive mode |
| `<query>` | Run query with auto-detection |
| `<tool>: <query>` | Run query with explicit tool |

## Examples

### Example 1: Finding Implementation

```python
# Find modules related to authentication
result = agent.run_query("user authentication")

for res in result['results'][:3]:
    print(f"{res['path']}: {res['similarity_score']:.2f}")
    print(f"  {res['purpose']}")
```

### Example 2: Analyzing Impact

```python
# Check what breaks if we change a module
result = agent.run_query(
    "src/db/users.py",
    tool_name="blast_radius"
)

print(f"Affected modules: {result['affected_module_count']}")
for module in result['affected_modules']:
    print(f"  - {module}")
```

### Example 3: Tracing Lineage

```python
# Trace data lineage downstream
result = agent.run_query(
    "raw_events",
    tool_name="trace_lineage",
    direction="downstream"
)

print(f"Found {result['node_count']} nodes in lineage")
for node in result['nodes']:
    print(f"  {node['id']} ({node['type']})")
```

### Example 4: Module Deep Dive

```python
# Get complete module information
result = agent.run_query(
    "src/auth/login.py",
    tool_name="explain_module"
)

if result['found']:
    print(result['summary'])
    print(f"\nProvenance chain: {len(result['provenance_chain'])} sources")
```

### Example 5: Interactive Exploration

```python
agent = NavigatorAgent(modules, module_graph, lineage_graph)
agent.interactive_mode()

# User can now interactively explore:
# Query> authentication
# Query> blast_radius: src/auth/login.py
# Query> trace_lineage: raw_events
# Query> explain_module: src/db/users.py
# Query> exit
```

## API Reference

### NavigatorAgent

```python
class NavigatorAgent:
    def __init__(
        self,
        modules: List[ModuleNode],
        module_graph: nx.DiGraph,
        lineage_graph: nx.DiGraph
    )
```

Initialize the NavigatorAgent with knowledge graphs.

**Parameters:**
- `modules`: List of module nodes with purpose statements
- `module_graph`: Module dependency graph
- `lineage_graph`: Data lineage graph

### create_tools()

```python
def create_tools(self) -> Dict[str, Any]
```

Create and register all four query tools.

**Returns:** Dictionary mapping tool names to tool instances

### run_query()

```python
def run_query(
    self,
    query: str,
    tool_name: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]
```

Execute a single query using the appropriate tool.

**Parameters:**
- `query`: Natural language query or specific parameter
- `tool_name`: Specific tool to use (optional, auto-detected if not provided)
- `**kwargs`: Additional tool-specific parameters

**Returns:** Query results with provenance information

**Tool-Specific Parameters:**
- `find_implementation`: `top_k` (int, default: 5)
- `trace_lineage`: `direction` (str, default: "downstream"), `max_depth` (int, optional)
- `blast_radius`: `include_data_lineage` (bool, default: True)
- `explain_module`: (no additional parameters)

### interactive_mode()

```python
def interactive_mode(self)
```

Launch interactive query mode for continuous querying.

Provides a REPL-style interface for exploring the knowledge graph.

## Testing

Run the test suite:

```bash
# Test NavigatorAgent
pytest tests/unit/test_navigator_agent.py -v

# Test all Navigator components
pytest tests/unit/test_navigator_tools.py tests/unit/test_navigator_agent.py -v
```

Run the example:

```bash
# Single query demonstration
python examples/navigator_agent_example.py

# Interactive mode
python examples/navigator_agent_example.py --interactive
```

## Integration

The NavigatorAgent is designed to be used as the final query interface for the Brownfield Cartographer:

```python
from src.orchestrator import CartographerOrchestrator
from agents.navigator import NavigatorAgent

# Run full analysis
orchestrator = CartographerOrchestrator(repo_path)
orchestrator.analyze_repository()

# Create navigator from results
agent = NavigatorAgent(
    modules=orchestrator.surveyor.modules,
    module_graph=orchestrator.surveyor.module_graph,
    lineage_graph=orchestrator.hydrologist.lineage_graph
)

# Query the knowledge graph
agent.interactive_mode()
```

## Performance

- **Initialization**: O(n) where n = number of modules (embedding model loading)
- **Query Execution**: Varies by tool
  - FindImplementationTool: O(n) for similarity computation (cached after first query)
  - TraceLineageTool: O(V + E) for graph traversal
  - BlastRadiusTool: O(V + E) for both graphs
  - ExplainModuleTool: O(1) for lookup
- **Interactive Mode**: Minimal overhead per query

## Limitations

- Auto-detection is keyword-based and may not always select the optimal tool
- Semantic search quality depends on purpose statement quality
- Graph traversal performance degrades with very large graphs (>10k nodes)
- Interactive mode requires terminal with input support

## Future Enhancements

Potential improvements:
1. **LLM-Based Query Parsing**: Use LLM to better understand natural language queries
2. **Query Composition**: Combine multiple tools in a single query
3. **Result Caching**: Cache frequent queries for faster response
4. **Visualization**: Generate visual representations of results
5. **Export**: Export results to various formats (JSON, CSV, Markdown)
6. **History**: Track query history and support replay

## See Also

- [Navigator Tools Documentation](NAVIGATOR_TOOLS.md)
- [Example Usage](../examples/navigator_agent_example.py)
- [Test Suite](../tests/unit/test_navigator_agent.py)
