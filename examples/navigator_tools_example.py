"""Example usage of Navigator query tools with provenance tracking."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import networkx as nx
from datetime import datetime

from agents.navigator import (
    FindImplementationTool,
    TraceLineageTool,
    BlastRadiusTool,
    ExplainModuleTool
)
from models.models import ModuleNode, DatasetNode, TransformationNode, ProvenanceMetadata


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
    lineage_graph.add_node(
        "user_metrics",
        node_type="dataset",
        storage_type="table",
        discovered_in="analytics/metrics.sql",
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
    lineage_graph.add_node(
        "load_analytics",
        node_type="transformation",
        transformation_type="python",
        source_file="etl/load.py",
        line_range=(20, 80),
        provenance=lineage_provenance.model_dump()
    )
    lineage_graph.add_node(
        "compute_metrics",
        node_type="transformation",
        transformation_type="sql",
        source_file="analytics/metrics.sql",
        line_range=(1, 150),
        provenance=lineage_provenance.model_dump()
    )
    
    # Add edges
    lineage_graph.add_edge("extract_events", "raw_events", edge_type="produces", confidence=1.0)
    lineage_graph.add_edge("transform_events", "raw_events", edge_type="consumes", confidence=1.0)
    lineage_graph.add_edge("transform_events", "staging_events", edge_type="produces", confidence=1.0)
    lineage_graph.add_edge("load_analytics", "staging_events", edge_type="consumes", confidence=1.0)
    lineage_graph.add_edge("load_analytics", "analytics_events", edge_type="produces", confidence=1.0)
    lineage_graph.add_edge("compute_metrics", "analytics_events", edge_type="consumes", confidence=1.0)
    lineage_graph.add_edge("compute_metrics", "user_metrics", edge_type="produces", confidence=1.0)
    
    return modules, module_graph, lineage_graph


def demo_find_implementation_tool(modules):
    """Demonstrate FindImplementationTool."""
    print("=" * 80)
    print("1. FindImplementationTool - Semantic Search")
    print("=" * 80)
    
    tool = FindImplementationTool(modules)
    
    # Search for authentication
    print("\n🔍 Searching for: 'user authentication'")
    result = tool("user authentication", top_k=2)
    
    print(f"\nQuery: {result['query']}")
    print(f"Provenance: {result['provenance']['evidence_type']} "
          f"(confidence: {result['provenance']['confidence']})")
    
    print(f"\nTop {len(result['results'])} results:")
    for i, res in enumerate(result['results'], 1):
        print(f"\n  {i}. {res['path']}")
        print(f"     Similarity: {res['similarity_score']:.3f}")
        print(f"     Purpose: {res['purpose']}")
        print(f"     Domain: {res['domain_cluster']}")
        print(f"     Provenance chain: {len(res['provenance_chain'])} sources")


def demo_trace_lineage_tool(lineage_graph):
    """Demonstrate TraceLineageTool."""
    print("\n\n" + "=" * 80)
    print("2. TraceLineageTool - Lineage Traversal")
    print("=" * 80)
    
    tool = TraceLineageTool(lineage_graph)
    
    # Trace downstream from raw_events
    print("\n🔍 Tracing downstream lineage from: 'raw_events'")
    result = tool("raw_events", direction="downstream")
    
    print(f"\nDataset: {result['dataset']}")
    print(f"Direction: {result['direction']}")
    print(f"Nodes found: {result['node_count']}")
    print(f"Edges found: {result['edge_count']}")
    print(f"Provenance: {result['provenance']['method']} "
          f"(confidence: {result['provenance']['confidence']})")
    
    print("\nDownstream nodes:")
    for node in result['nodes']:
        print(f"  - {node['id']} ({node['type']})")
        if 'provenance' in node:
            print(f"    Evidence: {node['provenance']['evidence_type']}")
    
    # Trace upstream from user_metrics
    print("\n\n🔍 Tracing upstream lineage from: 'user_metrics'")
    result = tool("user_metrics", direction="upstream")
    
    print(f"\nDataset: {result['dataset']}")
    print(f"Direction: {result['direction']}")
    print(f"Nodes found: {result['node_count']}")
    
    print("\nUpstream nodes:")
    for node in result['nodes']:
        print(f"  - {node['id']} ({node['type']})")


def demo_blast_radius_tool(module_graph, lineage_graph):
    """Demonstrate BlastRadiusTool."""
    print("\n\n" + "=" * 80)
    print("3. BlastRadiusTool - Dependency Analysis")
    print("=" * 80)
    
    tool = BlastRadiusTool(module_graph, lineage_graph)
    
    # Compute blast radius for db/users.py
    print("\n🔍 Computing blast radius for: 'src/db/users.py'")
    result = tool("src/db/users.py", include_data_lineage=True)
    
    print(f"\nModule: {result['module']}")
    print(f"Affected modules: {result['affected_module_count']}")
    print(f"Affected datasets: {result['affected_dataset_count']}")
    print(f"Provenance: {result['provenance']['method']} "
          f"(confidence: {result['provenance']['confidence']})")
    
    if result['affected_modules']:
        print("\nAffected modules:")
        for module in result['affected_modules']:
            print(f"  - {module}")
    
    if result['affected_datasets']:
        print("\nAffected datasets:")
        for dataset in result['affected_datasets']:
            print(f"  - {dataset['name']} ({dataset['storage_type']})")


def demo_explain_module_tool(modules, module_graph):
    """Demonstrate ExplainModuleTool."""
    print("\n\n" + "=" * 80)
    print("4. ExplainModuleTool - Module Information")
    print("=" * 80)
    
    tool = ExplainModuleTool(modules, module_graph)
    
    # Explain auth/login.py
    print("\n🔍 Explaining module: 'src/auth/login.py'")
    result = tool("src/auth/login.py")
    
    if result['found']:
        print(f"\n{result['summary']}")
        
        print(f"\nProvenance chain ({len(result['provenance_chain'])} sources):")
        for i, prov in enumerate(result['provenance_chain'], 1):
            print(f"  {i}. {prov.get('source', 'module')}: "
                  f"{prov['evidence_type']} "
                  f"(confidence: {prov['confidence']:.2f})")
        
        module = result['module']
        print(f"\nImports ({len(module['imports'])}):")
        for imp in module['imports']:
            print(f"  - {imp}")
        
        print(f"\nExports ({len(module['exports'])}):")
        for exp in module['exports']:
            print(f"  - {exp}")
        
        if module.get('imported_by'):
            print(f"\nImported by ({len(module['imported_by'])}):")
            for imp_by in module['imported_by']:
                print(f"  - {imp_by}")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 80)
    print("Navigator Query Tools - Demonstration with Provenance Tracking")
    print("=" * 80)
    
    # Create sample data
    modules, module_graph, lineage_graph = create_sample_data()
    
    # Run demonstrations
    demo_find_implementation_tool(modules)
    demo_trace_lineage_tool(lineage_graph)
    demo_blast_radius_tool(module_graph, lineage_graph)
    demo_explain_module_tool(modules, module_graph)
    
    print("\n\n" + "=" * 80)
    print("Demonstration Complete")
    print("=" * 80)
    print("\nAll tools provide:")
    print("  ✓ Provenance tracking (evidence_type, confidence, resolution_status)")
    print("  ✓ Evidence citations (source_file, line_range)")
    print("  ✓ Confidence scores for all inferences")
    print("  ✓ Full provenance chains for query results")
    print()


if __name__ == "__main__":
    main()
