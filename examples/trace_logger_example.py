"""Example demonstrating CartographyTraceLogger usage."""

from pathlib import Path
from agents.trace_logger import CartographyTraceLogger


def main():
    """Demonstrate CartographyTraceLogger functionality."""
    
    # Initialize logger
    logger = CartographyTraceLogger()
    
    print("=== CartographyTraceLogger Example ===\n")
    
    # Simulate Surveyor agent actions
    print("1. Surveyor analyzing module structure...")
    logger.log_action(
        agent="surveyor",
        action="Analyzed module structure for src/main.py",
        evidence_source="src/main.py",
        evidence_type="tree_sitter",
        confidence=0.95,
        resolution_status="resolved",
        details={
            "imports": ["os", "sys", "pathlib"],
            "exports": ["main", "run"],
            "complexity_score": 42
        }
    )
    
    logger.log_action(
        agent="surveyor",
        action="Extracted module dependencies",
        evidence_source="src/utils.py",
        evidence_type="tree_sitter",
        confidence=0.90,
        resolution_status="resolved"
    )
    
    # Simulate Hydrologist agent actions
    print("2. Hydrologist extracting data lineage...")
    logger.log_action(
        agent="hydrologist",
        action="Extracted SQL lineage from transformation",
        evidence_source="src/pipeline/transform.sql",
        evidence_type="sqlglot",
        confidence=0.88,
        resolution_status="partial",
        details={
            "source_tables": ["users", "orders"],
            "target_table": "user_orders_summary"
        }
    )
    
    logger.log_error(
        agent="hydrologist",
        severity="warning",
        message="Could not fully resolve dynamic table name",
        evidence_source="src/pipeline/dynamic_query.py",
        evidence_type="heuristic",
        context={
            "line_number": 45,
            "variable": "table_name",
            "reason": "Runtime-determined value"
        }
    )
    
    # Simulate Semanticist agent with LLM calls
    print("3. Semanticist generating purpose statements...")
    logger.log_llm_call(
        agent="semanticist",
        model="gpt-4",
        prompt_tokens=250,
        completion_tokens=75,
        confidence=0.85,
        purpose="Generate purpose statement for src/main.py",
        result_summary="Entry point module that orchestrates the data pipeline"
    )
    
    logger.log_action(
        agent="semanticist",
        action="Generated purpose statement",
        evidence_source="src/main.py",
        evidence_type="llm",
        confidence=0.85,
        resolution_status="inferred",
        details={
            "purpose": "Entry point module that orchestrates the data pipeline"
        }
    )
    
    # Simulate Archivist agent
    print("4. Archivist generating documentation...")
    logger.log_action(
        agent="archivist",
        action="Generated CODEBASE.md",
        evidence_source="knowledge_graph",
        evidence_type="heuristic",
        confidence=0.92,
        resolution_status="resolved",
        details={
            "modules_documented": 25,
            "critical_paths_identified": 5
        }
    )
    
    # Get statistics
    print("\n=== Statistics ===")
    stats = logger.get_statistics()
    print(f"Total entries: {stats['total_entries']}")
    print(f"By type: {stats['by_type']}")
    print(f"By agent: {stats['by_agent']}")
    print(f"By evidence type: {stats['by_evidence_type']}")
    print(f"Total LLM tokens: {stats['total_llm_tokens']}")
    print(f"Average confidence: {stats['average_confidence']:.2f}")
    
    # Flush to file
    output_path = Path(".cartography") / "example_trace.jsonl"
    logger.flush(output_path)
    
    print(f"\n=== Trace Log Written ===")
    print(f"Location: {output_path}")
    print(f"Entries: {len(logger.log_entries)}")
    
    # Display sample of JSONL content
    print(f"\n=== Sample JSONL Content ===")
    with open(output_path, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines[:2], 1):
            print(f"Entry {i}:")
            print(line)


if __name__ == "__main__":
    main()
