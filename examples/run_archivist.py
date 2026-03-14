"""Run Archivist agent to generate living documentation artifacts."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import networkx as nx
from datetime import datetime

from agents.archivist import ArchivistAgent
from agents.trace_logger import CartographyTraceLogger
from analyzers.graph_serializer import GraphSerializer
from models import ModuleNode, DatasetNode, TransformationNode, ProvenanceMetadata


def load_graphs(analysis_dir: Path):
    """Load module and lineage graphs from analysis directory."""
    module_graph_path = analysis_dir / 'module_graph.json'
    lineage_graph_path = analysis_dir / 'lineage_graph.json'
    
    if not module_graph_path.exists():
        raise FileNotFoundError(f"Module graph not found: {module_graph_path}")
    
    if not lineage_graph_path.exists():
        raise FileNotFoundError(f"Lineage graph not found: {lineage_graph_path}")
    
    print(f"Loading module graph from {module_graph_path}")
    module_graph = GraphSerializer.deserialize_graph(str(module_graph_path))
    
    print(f"Loading lineage graph from {lineage_graph_path}")
    lineage_graph = GraphSerializer.deserialize_graph(str(lineage_graph_path))
    
    return module_graph, lineage_graph


def reconstruct_objects_from_graphs(module_graph: nx.DiGraph, lineage_graph: nx.DiGraph):
    """Reconstruct ModuleNode, DatasetNode, and TransformationNode objects from graphs."""
    modules = []
    datasets = []
    transformations = []
    
    # Reconstruct modules
    for node_id in module_graph.nodes():
        node_data = module_graph.nodes[node_id]
        
        provenance_data = node_data.get('provenance', {})
        provenance = ProvenanceMetadata(**provenance_data) if provenance_data else None
        
        if provenance:
            # Parse last_modified if it exists
            last_modified = None
            if node_data.get('last_modified'):
                try:
                    last_modified = datetime.fromisoformat(node_data['last_modified'])
                except:
                    pass
            
            module = ModuleNode(
                path=node_data['path'],
                language=node_data['language'],
                complexity_score=node_data['complexity_score'],
                imports=node_data.get('imports', []),
                exports=node_data.get('exports', []),
                provenance=provenance,
                purpose_statement=node_data.get('purpose_statement'),
                domain_cluster=node_data.get('domain_cluster'),
                change_velocity=node_data.get('change_velocity'),
                is_dead_code_candidate=node_data.get('is_dead_code_candidate', False),
                docstring=node_data.get('docstring'),
                has_documentation_drift=node_data.get('has_documentation_drift', False),
                last_modified=last_modified
            )
            modules.append(module)
    
    # Reconstruct datasets and transformations
    for node_id in lineage_graph.nodes():
        node_data = lineage_graph.nodes[node_id]
        node_type = node_data.get('node_type')
        
        provenance_data = node_data.get('provenance', {})
        provenance = ProvenanceMetadata(**provenance_data) if provenance_data else None
        
        if not provenance:
            continue
        
        if node_type == 'dataset':
            dataset = DatasetNode(
                name=node_data['name'],
                storage_type=node_data['storage_type'],
                discovered_in=node_data['discovered_in'],
                provenance=provenance,
                schema_snapshot=node_data.get('schema_snapshot'),
                freshness_sla=node_data.get('freshness_sla'),
                owner=node_data.get('owner'),
                is_source_of_truth=node_data.get('is_source_of_truth', False),
            )
            datasets.append(dataset)
        
        elif node_type == 'transformation':
            transformation = TransformationNode(
                id=node_data.get('id', node_id),  # Use node_id if 'id' not in data
                source_datasets=node_data.get('source_datasets', []),
                target_datasets=node_data.get('target_datasets', []),
                transformation_type=node_data['transformation_type'],
                source_file=node_data['source_file'],
                line_range=tuple(node_data['line_range']),
                provenance=provenance,
                sql_query=node_data.get('sql_query'),
            )
            transformations.append(transformation)
    
    return modules, datasets, transformations


def load_day_one_answers(analysis_dir: Path):
    """Load Day-One answers from JSON file."""
    import json
    
    answers_path = analysis_dir / 'day_one_answers.json'
    
    if not answers_path.exists():
        print(f"Warning: Day-One answers not found at {answers_path}")
        return {}
    
    with open(answers_path, 'r') as f:
        return json.load(f)


def main():
    """Run Archivist agent on existing analysis."""
    if len(sys.argv) < 2:
        print("Usage: python run_archivist.py <analysis_directory>")
        print("\nExample:")
        print("  python examples/run_archivist.py .cartography/.cartography-jaffle-shop")
        sys.exit(1)
    
    analysis_dir = Path(sys.argv[1])
    
    if not analysis_dir.exists():
        print(f"Error: Analysis directory does not exist: {analysis_dir}")
        sys.exit(1)
    
    print("=" * 80)
    print("ARCHIVIST AGENT - ARTIFACT GENERATION")
    print("=" * 80)
    print(f"\nAnalysis directory: {analysis_dir}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)
    
    # Load graphs
    print("\n[1/5] Loading graphs...")
    module_graph, lineage_graph = load_graphs(analysis_dir)
    print(f"  ✓ Module graph: {module_graph.number_of_nodes()} nodes, {module_graph.number_of_edges()} edges")
    print(f"  ✓ Lineage graph: {lineage_graph.number_of_nodes()} nodes, {lineage_graph.number_of_edges()} edges")
    
    # Reconstruct objects
    print("\n[2/5] Reconstructing objects from graphs...")
    modules, datasets, transformations = reconstruct_objects_from_graphs(module_graph, lineage_graph)
    print(f"  ✓ Modules: {len(modules)}")
    print(f"  ✓ Datasets: {len(datasets)}")
    print(f"  ✓ Transformations: {len(transformations)}")
    
    # Load Day-One answers
    print("\n[3/5] Loading Day-One answers...")
    day_one_answers = load_day_one_answers(analysis_dir)
    print(f"  ✓ Loaded {len(day_one_answers)} answers")
    
    # Compute PageRank scores
    print("\n[4/5] Computing PageRank scores...")
    pagerank_scores = nx.pagerank(module_graph) if module_graph.number_of_nodes() > 0 else {}
    print(f"  ✓ Computed PageRank for {len(pagerank_scores)} modules")
    
    # Detect circular dependencies
    print("\n[5/5] Detecting circular dependencies...")
    try:
        cycles = list(nx.simple_cycles(module_graph))
        circular_dependencies = cycles
    except:
        circular_dependencies = []
    print(f"  ✓ Found {len(circular_dependencies)} circular dependency groups")
    
    # Initialize Archivist
    print("\n" + "-" * 80)
    print("Generating artifacts...")
    print("-" * 80)
    
    archivist = ArchivistAgent(output_dir=analysis_dir)
    
    # Create trace logger
    trace_logger = CartographyTraceLogger()
    trace_logger.log_action(
        agent="archivist",
        action="generate_artifacts",
        evidence_source="module_graph + lineage_graph",
        evidence_type="heuristic",
        confidence=1.0,
        resolution_status="resolved"
    )
    
    # Analysis metadata
    analysis_metadata = {
        'timestamp': datetime.now().isoformat(),
        'module_count': len(modules),
        'dataset_count': len(datasets),
        'transformation_count': len(transformations),
        'analysis_directory': str(analysis_dir)
    }
    
    # Generate artifacts
    artifact_paths = archivist.generate_artifacts(
        modules=modules,
        datasets=datasets,
        transformations=transformations,
        module_graph=module_graph,
        lineage_graph=lineage_graph,
        pagerank_scores=pagerank_scores,
        circular_dependencies=circular_dependencies,
        day_one_answers=day_one_answers,
        analysis_metadata=analysis_metadata,
        trace_logger=trace_logger
    )
    
    # Summary
    print("\n" + "=" * 80)
    print("ARTIFACT GENERATION COMPLETE")
    print("=" * 80)
    print(f"\nGenerated {len(artifact_paths)} artifacts:")
    for name, path in artifact_paths.items():
        file_size = path.stat().st_size / 1024
        print(f"  ✓ {name}: {path.name} ({file_size:.1f} KB)")
    
    print(f"\nOutput directory: {analysis_dir}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    main()
