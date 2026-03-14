"""Example usage of NavigatorAgent for interactive querying."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import networkx as nx
from datetime import datetime

from agents.navigator import NavigatorAgent
from models.models import ModuleNode, ProvenanceMetadata


def create_sample_data():
    """Create sample data for demonstration."""
    
    # Create provenance metadata
    provenance = ProvenanceMetadata(
        evidence_type="tree_sitter",
        source_file="example.py",
        line_range=(1, 100),
        confidence=1.0,
        resolution_status="resolved"
    )
    
    # Create sample modules
    modules = [
        ModuleNode(
            path="src/auth/login.py",
            language="python",
            purpose_statement="Handles user authentication and session management for the application",
            domain_cluster="Authentication",
            complexity_score=75,
            change_velocity=12,
            is_dead_code_candidate=False,
            last_modified=datetime.now(),
            imports=["src/db/users.py", "src/utils/crypto.py"],
            exports=["login", "logout", "verify_session"],
            provenance=provenance
        ),
        ModuleNode(
            path="src/db/users.py",
            language="python",
            purpose_statement="Manages user data persistence and retrieval from PostgreSQL database",
            domain_cluster="Database",
            complexity_score=120,
            change_velocity=8,
            is_dead_code_candidate=False,
            last_modified=datetime.now(),
            imports=["src/db/connection.py"],
            exports=["get_user", "create_user", "update_user", "delete_user"],
            provenance=provenance
        ),
        ModuleNode(
            path="src/api/endpoints.py",
            language="python",
            purpose_statement="Defines REST API endpoints for user management and authentication",
            domain_cluster="API",
            complexity_score=95,
            change_velocity=20,
            is_dead_code_candidate=False,
            last_modified=datetime.now(),
            imports=["src/auth/login.py", "src/db/users.py"],
            exports=["app", "register_routes"],
            provenance=provenance
        ),
        ModuleNode(
            path="src/utils/crypto.py",
            language="python",
            purpose_statement="Provides cryptographic utilities for password hashing and token generation",
            domain_cluster="Security",
            complexity_score=45,
            change_velocity=2,
            is_dead_code_candidate=False,
            last_modified=datetime.now(),
            imports=[],
            exports=["hash_password", "verify_password", "generate_token"],
            provenance=provenance
        )
    ]
    
    # Create module graph
    module_graph = nx.DiGraph()
    for module in modules:
        module_graph.add_node(module.path, **module.model_dump())
    
    module_graph.add_edge("src/auth/login.py", "src/db/users.py", edge_type="imports")
    module_graph.add_edge("src/auth/login.py", "src/utils/crypto.py", edge_type="imports")
    module_graph.add_edge("src/api/endpoints.py", "src/auth/login.py", edge_type="imports")
    module_graph.add_edge("src/api/endpoints.py", "src/db/users.py", edge_type="imports")
    module_graph.add_edge("src/db/users.py", "src/db/connection.py", edge_type="imports")
    
    # Create lineage graph
    lineage_graph = nx.DiGraph()
    
    lineage_provenance = ProvenanceMetadata(
        evidence_type="sqlglot",
        source_file="etl/transform.sql",
        line_range=(1, 50),
        confidence=1.0,
        resolution_status="resolved"
    )
    
    # Add dataset nodes
    lineage_graph.add_node(
        "raw_events",
        node_type="dataset",
        storage_type="table",
        discovered_in="etl/extract.py",
        provenance=lineage_provenance.model_dump()
    )
    lineage_graph.add_node(
        "staging_events",
        node_type="dataset",
        storage_type="table",
        discovered_in="etl/transform.sql",
        provenance=lineage_provenance.model_dump()
    )
    lineage_graph.add_node(
        "analytics_events",
        node_type="dataset",
        storage_type="table",
        discovered_in="etl/load.py",
        provenance=lineage_provenance.model_dump()
    )
    
    # Add transformation nodes
    lineage_graph.add_node(
        "extract_events",
        node_type="transformation",
        transformation_type="python",
        source_file="etl/extract.py",
        line_range=(10, 50),
        provenance=lineage_provenance.model_dump()
    )
    lineage_graph.add_node(
        "transform_events",
        node_type="transformation",
        transformation_type="sql",
        source_file="etl/transform.sql",
        line_range=(1, 100),
        provenance=lineage_provenance.model_dump()
    )
    
    # Add edges
    lineage_graph.add_edge("extract_events", "raw_events", edge_type="produces", confidence=1.0)
    lineage_graph.add_edge("transform_events", "raw_events", edge_type="consumes", confidence=1.0)
    lineage_graph.add_edge("transform_events", "staging_events", edge_type="produces", confidence=1.0)
    
    return modules, module_graph, lineage_graph


def demo_single_queries():
    """Demonstrate single query execution."""
    print("\n" + "=" * 80)
    print("NavigatorAgent - Single Query Demonstration")
    print("=" * 80)
    
    # Create sample data
    modules, module_graph, lineage_graph = create_sample_data()
    
    # Initialize agent
    agent = NavigatorAgent(modules, module_graph, lineage_graph)
    
    # Example 1: Semantic search (auto-detected)
    print("\n1. Semantic Search (auto-detected)")
    print("-" * 80)
    result = agent.run_query("user authentication")
    print(f"Tool used: {result['query_metadata']['tool_used']}")
    print(f"Results found: {len(result.get('results', []))}")
    if result.get('results'):
        print(f"Top match: {result['results'][0]['path']}")
    
    # Example 2: Explicit tool selection
    print("\n2. Blast Radius (explicit tool)")
    print("-" * 80)
    result = agent.run_query("src/db/users.py", tool_name="blast_radius")
    print(f"Module: {result['module']}")
    print(f"Affected modules: {result['affected_module_count']}")
    
    # Example 3: Lineage traversal
    print("\n3. Lineage Traversal")
    print("-" * 80)
    result = agent.run_query("raw_events", tool_name="trace_lineage", direction="downstream")
    print(f"Dataset: {result['dataset']}")
    print(f"Direction: {result['direction']}")
    print(f"Nodes found: {result['node_count']}")
    
    # Example 4: Module explanation
    print("\n4. Module Explanation")
    print("-" * 80)
    result = agent.run_query("src/auth/login.py", tool_name="explain_module")
    if result.get('found'):
        print(result['summary'])
    
    print("\n" + "=" * 80)


def demo_interactive_mode():
    """Demonstrate interactive mode."""
    print("\n" + "=" * 80)
    print("NavigatorAgent - Interactive Mode Demonstration")
    print("=" * 80)
    print("\nStarting interactive mode...")
    print("Try queries like:")
    print("  - user authentication")
    print("  - blast_radius: src/db/users.py")
    print("  - trace_lineage: raw_events")
    print("  - explain_module: src/auth/login.py")
    print("\nType 'exit' to quit interactive mode.")
    
    # Create sample data
    modules, module_graph, lineage_graph = create_sample_data()
    
    # Initialize agent
    agent = NavigatorAgent(modules, module_graph, lineage_graph)
    
    # Launch interactive mode
    agent.interactive_mode()


def main():
    """Run demonstrations."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        demo_interactive_mode()
    else:
        demo_single_queries()
        print("\nTo try interactive mode, run:")
        print("  python examples/navigator_agent_example.py --interactive")


if __name__ == "__main__":
    main()
