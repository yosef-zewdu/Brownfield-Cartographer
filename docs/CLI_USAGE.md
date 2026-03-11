# Brownfield Cartographer - CLI Usage Guide

## Overview

The Brownfield Cartographer provides a command-line interface for analyzing codebases and extracting data lineage. The CLI orchestrates the Surveyor and Hydrologist agents in sequence and saves all outputs to a `.cartography/` directory.

## Installation

```bash
# Install dependencies using uv
uv sync

# Or using pip
pip install -r requirements.txt
```

## Basic Usage

### Analyze a Repository

```bash
# Full analysis (Surveyor + Hydrologist)
uv run python -m src.cli analyze /path/to/repository

# Or with python directly
python -m src.cli analyze /path/to/repository
```

This will:
1. Run the Surveyor Agent to analyze module structure
2. Run the Hydrologist Agent to extract data lineage
3. Save all outputs to `/path/to/repository/.cartography/`

### Custom Output Directory

```bash
uv run python -m src.cli analyze /path/to/repository --output-dir .analysis
```

Outputs will be saved to `/path/to/repository/.analysis/` instead of `.cartography/`

### Skip Surveyor Phase

If you've already run the Surveyor and want to re-run only the Hydrologist:

```bash
uv run python -m src.cli analyze /path/to/repository --skip-surveyor
```

This loads the existing `module_graph.json` and runs only the Hydrologist.

### Skip Hydrologist Phase

To run only the Surveyor (module structure analysis):

```bash
uv run python -m src.cli analyze /path/to/repository --skip-hydrologist
```

## Output Artifacts

All outputs are saved to `<repository>/.cartography/` (or custom output directory):

### 1. module_graph.json
Complete module dependency graph with:
- All Python, SQL, YAML, JavaScript files
- Import relationships
- Module metadata (complexity, change velocity, etc.)
- PageRank scores for architectural hubs

### 2. lineage_graph.json
Data lineage graph with:
- Dataset nodes (tables, files, streams)
- Transformation nodes (dbt models, Airflow tasks, SQL queries, etc.)
- CONSUMES and PRODUCES edges
- Full provenance metadata

### 3. surveyor_report.txt
Human-readable summary of Surveyor analysis:
- Module count and language breakdown
- Complexity analysis
- Circular dependencies
- Dead code candidates

### 4. hydrologist_report.txt
Human-readable summary of Hydrologist analysis:
- Dataset and transformation counts
- Transformation type breakdown
- Storage type distribution
- Data flow analysis (sources and sinks)

## Examples

### Example 1: Analyze dbt Project

```bash
uv run python -m src.cli analyze ~/projects/jaffle-shop
```

Output:
```
================================================================================
BROWNFIELD CARTOGRAPHER - ANALYSIS PIPELINE
================================================================================

Repository: /home/user/projects/jaffle-shop
Output directory: /home/user/projects/jaffle-shop/.cartography
Started at: 2026-03-11 23:09:18
--------------------------------------------------------------------------------

[PHASE 1] Running Surveyor Agent...
Analyzing module structure and dependencies...
✓ Surveyor complete:
  - Modules analyzed: 37
  - Graph nodes: 37
  - Graph edges: 0
  - Module graph saved: .../module_graph.json

[PHASE 2] Running Hydrologist Agent...
Analyzing data lineage and transformations...
✓ Hydrologist complete:
  - Datasets discovered: 19
  - Transformations discovered: 15
  - Lineage graph nodes: 34
  - Lineage graph edges: 30
  - Lineage graph saved: .../lineage_graph.json

================================================================================
ANALYSIS COMPLETE
================================================================================

✓ All phases completed successfully
```

### Example 2: Analyze Apache Airflow

```bash
uv run python -m src.cli analyze ~/projects/airflow
```

For large codebases like Airflow (7,500+ modules), the analysis takes ~7-10 minutes.

### Example 3: Re-run Hydrologist Only

```bash
# First run (full analysis)
uv run python -m src.cli analyze ~/projects/my-repo

# Later, re-run only Hydrologist (faster)
uv run python -m src.cli analyze ~/projects/my-repo --skip-surveyor
```

This is useful when:
- You've modified data transformation code
- You want to re-analyze lineage without re-scanning all modules
- You're iterating on lineage extraction logic

## Command Reference

### Main Command

```bash
python -m src.cli [command] [options]
```

### Commands

#### analyze

Analyze a repository and extract lineage.

**Arguments:**
- `repo_path` (required): Path to repository to analyze

**Options:**
- `--output-dir DIR`: Output directory name (default: `.cartography`)
- `--skip-surveyor`: Skip Surveyor phase (use existing module graph)
- `--skip-hydrologist`: Skip Hydrologist phase (only run Surveyor)
- `-h, --help`: Show help message

## Supported Frameworks

The Cartographer automatically detects and analyzes:

### Data Transformation Frameworks
- **dbt**: Models, sources, refs, schema metadata
- **Apache Airflow**: DAGs, tasks, dependencies
- **SQL**: Raw SQL queries and table references

### Data Processing Libraries
- **Pandas**: read_csv, read_sql, to_csv, to_sql, etc.
- **PySpark**: read, write operations
- **SQLAlchemy**: execute, query operations

### Languages
- **Python**: .py files
- **SQL**: .sql files
- **YAML**: .yaml, .yml files
- **JavaScript/TypeScript**: .js, .ts files

## Troubleshooting

### Error: Repository path does not exist

Make sure the path is correct and the directory exists:

```bash
ls -la /path/to/repository
```

### Error: Module graph not found

If using `--skip-surveyor`, ensure you've run a full analysis first:

```bash
# Run full analysis first
uv run python -m src.cli analyze /path/to/repository

# Then you can skip surveyor
uv run python -m src.cli analyze /path/to/repository --skip-surveyor
```

### SQL Parse Errors

SQL files with Jinja templates (e.g., dbt models) may show parse warnings. This is expected and handled gracefully. The dbt-specific analyzer uses regex extraction for `ref()` and `source()` macros.

### Large Codebases

For repositories with 5,000+ files:
- Analysis may take 5-15 minutes
- Consider using `--skip-surveyor` for subsequent runs
- Monitor memory usage (typically <2GB)

## Integration with Other Tools

### Use with Git Hooks

```bash
# .git/hooks/post-merge
#!/bin/bash
uv run python -m src.cli analyze . --skip-surveyor
```

### Use in CI/CD

```yaml
# .github/workflows/analyze.yml
- name: Analyze Codebase
  run: |
    uv run python -m src.cli analyze .
    
- name: Upload Artifacts
  uses: actions/upload-artifact@v3
  with:
    name: cartography-analysis
    path: .cartography/
```

## Advanced Usage

### Programmatic Usage

You can also use the orchestrator directly in Python:

```python
from src.orchestrator import CartographerOrchestrator

orchestrator = CartographerOrchestrator(output_dir=".cartography")
module_graph, lineage_graph = orchestrator.analyze_repository(
    "/path/to/repository",
    skip_surveyor=False,
    skip_hydrologist=False
)
```

### Custom Analysis

For custom analysis workflows, use the agents directly:

```python
from src.agents.surveyor import SurveyorAgent
from src.agents.hydrologist import HydrologistAgent

# Run Surveyor
surveyor = SurveyorAgent()
module_graph, modules = surveyor.analyze_repository("/path/to/repo")

# Run Hydrologist
hydrologist = HydrologistAgent()
lineage_graph, datasets, transformations = hydrologist.analyze_repository(
    "/path/to/repo",
    module_graph
)
```

## Performance Tips

1. **Use --skip-surveyor**: After the first run, use this flag to skip module scanning
2. **Exclude large directories**: Move large data/build directories outside the repo
3. **Run incrementally**: Analyze specific subdirectories if possible
4. **Monitor resources**: Large repos may need 2-4GB RAM

## Getting Help

```bash
# Show main help
uv run python -m src.cli --help

# Show analyze command help
uv run python -m src.cli analyze --help
```

## Next Steps

After running the analysis:

1. **Explore the graphs**: Open `module_graph.json` and `lineage_graph.json`
2. **Read the reports**: Check `surveyor_report.txt` and `hydrologist_report.txt`
3. **Query the lineage**: Use the Navigator agent (Phase 4) for interactive queries
4. **Generate documentation**: Use the Archivist agent (Phase 4) to create CODEBASE.md

---

For more information, see the main [README.md](README.md) and [USAGE_GUIDE.md](USAGE_GUIDE.md).
