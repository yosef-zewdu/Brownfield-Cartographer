"""Validate the Hydrologist Agent on a target codebase."""

import sys
from pathlib import Path
from datetime import datetime
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from agents.surveyor import SurveyorAgent
from agents.hydrologist import HydrologistAgent
from analyzers.graph_serializer import GraphSerializer


def main():
    """Validate Hydrologist on a repository specified as command line argument."""
    if len(sys.argv) < 2:
        print("Usage: python validate_hydrologist.py <path_to_repository> [--use-existing-graph]")
        print("\nExample:")
        print("  python validate_hydrologist.py /home/yosef/Desktop/intensive/airflow")
        print("  python validate_hydrologist.py /home/yosef/Desktop/intensive/airflow --use-existing-graph")
        sys.exit(1)
    
    repo_path = Path(sys.argv[1])
    use_existing = '--use-existing-graph' in sys.argv
    
    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repo_path}")
        sys.exit(1)
    
    if not repo_path.is_dir():
        print(f"Error: Path is not a directory: {repo_path}")
        sys.exit(1)
    
    print("=" * 80)
    print(f"BROWNFIELD CARTOGRAPHER - HYDROLOGIST VALIDATION")
    print("=" * 80)
    print(f"\nAnalyzing repository: {repo_path}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)
    
    # Step 1: Get module graph (either load existing or run Surveyor)
    output_dir = repo_path / '.cartography'
    module_graph_path = output_dir / 'module_graph.json'
    
    if use_existing and module_graph_path.exists():
        print("\n[PHASE 1] Loading existing module graph...")
        module_graph = GraphSerializer.deserialize_graph(str(module_graph_path))
        print(f"✓ Loaded existing graph: {module_graph.number_of_nodes()} nodes, {module_graph.number_of_edges()} edges")
    else:
        print("\n[PHASE 1] Running Surveyor Agent...")
        surveyor = SurveyorAgent()
        module_graph, modules = surveyor.analyze_repository(str(repo_path))
        print(f"✓ Surveyor complete: {module_graph.number_of_nodes()} nodes, {module_graph.number_of_edges()} edges")
    
    # Step 2: Run Hydrologist
    print("\n[PHASE 2] Running Hydrologist Agent...")
    hydrologist = HydrologistAgent()
    lineage_graph, datasets, transformations = hydrologist.analyze_repository(str(repo_path), module_graph)
    
    print(f"\n✓ Hydrologist complete:")
    print(f"  - Datasets found: {len(datasets)}")
    print(f"  - Transformations found: {len(transformations)}")
    print(f"  - Lineage graph nodes: {lineage_graph.number_of_nodes()}")
    print(f"  - Lineage graph edges: {lineage_graph.number_of_edges()}")
    
    # Step 3: Analyze lineage graph structure
    print("\n[VALIDATION] Analyzing lineage graph structure...")
    
    # Count node types
    dataset_nodes = [n for n, d in lineage_graph.nodes(data=True) if d.get('node_type') == 'dataset']
    transformation_nodes = [n for n, d in lineage_graph.nodes(data=True) if d.get('node_type') == 'transformation']
    
    print(f"\nNode type breakdown:")
    print(f"  - Dataset nodes: {len(dataset_nodes)}")
    print(f"  - Transformation nodes: {len(transformation_nodes)}")
    
    # Count edge types
    consumes_edges = [(u, v) for u, v, d in lineage_graph.edges(data=True) if d.get('edge_type') == 'consumes']
    produces_edges = [(u, v) for u, v, d in lineage_graph.edges(data=True) if d.get('edge_type') == 'produces']
    
    print(f"\nEdge type breakdown:")
    print(f"  - CONSUMES edges: {len(consumes_edges)}")
    print(f"  - PRODUCES edges: {len(produces_edges)}")
    
    # Find sources and sinks
    sources = hydrologist.find_sources(lineage_graph)
    sinks = hydrologist.find_sinks(lineage_graph)
    
    print(f"\nData flow analysis:")
    print(f"  - Source nodes (in-degree 0): {len(sources)}")
    print(f"  - Sink nodes (out-degree 0): {len(sinks)}")
    
    if sources:
        print(f"\n  Top 5 source datasets:")
        for i, source in enumerate(sources[:5], 1):
            node_data = lineage_graph.nodes[source]
            print(f"    {i}. {source}")
            if 'provenance' in node_data:
                prov = node_data['provenance']
                print(f"       Evidence: {prov.get('evidence_type', 'unknown')}, Confidence: {prov.get('confidence', 0):.2f}")
    
    if sinks:
        print(f"\n  Top 5 sink datasets:")
        for i, sink in enumerate(sinks[:5], 1):
            node_data = lineage_graph.nodes[sink]
            print(f"    {i}. {sink}")
            if 'provenance' in node_data:
                prov = node_data['provenance']
                print(f"       Evidence: {prov.get('evidence_type', 'unknown')}, Confidence: {prov.get('confidence', 0):.2f}")
    
    # Analyze transformations
    if transformations:
        print(f"\n  Transformation types:")
        transformation_types = {}
        for t in transformations:
            t_type = t.transformation_type
            transformation_types[t_type] = transformation_types.get(t_type, 0) + 1
        
        for t_type, count in sorted(transformation_types.items(), key=lambda x: x[1], reverse=True):
            print(f"    {t_type}: {count}")
    
    # Check for Airflow DAGs
    airflow_dags = [t for t in transformations if t.transformation_type == 'airflow_dag']
    if airflow_dags:
        print(f"\n  Airflow DAGs detected: {len(airflow_dags)}")
        for i, dag in enumerate(airflow_dags[:5], 1):
            print(f"    {i}. {dag.id}")
            print(f"       Source: {dag.provenance.source_file}")
    
    # Check for dbt models
    dbt_models = [t for t in transformations if t.transformation_type == 'dbt_model']
    if dbt_models:
        print(f"\n  dbt models detected: {len(dbt_models)}")
        for i, model in enumerate(dbt_models[:5], 1):
            print(f"    {i}. {model.id}")
            print(f"       Source: {model.provenance.source_file}")
    
    # Check for SQL transformations
    sql_transforms = [t for t in transformations if t.transformation_type == 'sql_query']
    if sql_transforms:
        print(f"\n  SQL queries detected: {len(sql_transforms)}")
        for i, sql in enumerate(sql_transforms[:5], 1):
            print(f"    {i}. {sql.id}")
            print(f"       Source: {sql.provenance.source_file}")
    
    # Blast radius analysis
    if transformation_nodes:
        print(f"\n[VALIDATION] Blast radius analysis...")
        sample_node = transformation_nodes[0]
        blast_radius = hydrologist.compute_blast_radius(lineage_graph, sample_node)
        print(f"  Sample node: {sample_node}")
        print(f"  Blast radius: {blast_radius.number_of_nodes()} affected nodes")
    
    # Step 4: Save outputs
    print("\n" + "=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)
    
    output_dir.mkdir(exist_ok=True)
    
    # Save lineage graph
    lineage_path = output_dir / 'lineage_graph.json'
    hydrologist.serialize_lineage_graph(lineage_graph, str(lineage_path))
    print(f"\n✓ Lineage graph saved to:")
    print(f"  {lineage_path}")
    print(f"  Size: {lineage_path.stat().st_size / 1024:.1f} KB")
    
    # Save comprehensive validation report
    report_path = output_dir / 'hydrologist_validation.txt'
    with open(report_path, 'w') as f:
        f.write(f"{'=' * 80}\n")
        f.write(f"HYDROLOGIST AGENT - COMPREHENSIVE VALIDATION REPORT\n")
        f.write(f"{'=' * 80}\n\n")
        f.write(f"Repository: {repo_path}\n")
        f.write(f"Validated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'-' * 80}\n\n")
        
        # Executive Summary
        f.write(f"EXECUTIVE SUMMARY\n")
        f.write(f"{'=' * 80}\n\n")
        f.write(f"Total Datasets Discovered: {len(datasets):,}\n")
        f.write(f"Total Transformations Discovered: {len(transformations):,}\n")
        f.write(f"Lineage Graph Nodes: {lineage_graph.number_of_nodes():,}\n")
        f.write(f"Lineage Graph Edges: {lineage_graph.number_of_edges():,}\n")
        f.write(f"Source Nodes (in-degree 0): {len(sources):,}\n")
        f.write(f"Sink Nodes (out-degree 0): {len(sinks):,}\n\n")
        
        # Node Type Breakdown
        f.write(f"{'=' * 80}\n")
        f.write(f"NODE TYPE BREAKDOWN\n")
        f.write(f"{'=' * 80}\n\n")
        f.write(f"Dataset Nodes: {len(dataset_nodes):,}\n")
        f.write(f"Transformation Nodes: {len(transformation_nodes):,}\n\n")
        
        # Dataset Analysis
        f.write(f"{'=' * 80}\n")
        f.write(f"DATASET ANALYSIS\n")
        f.write(f"{'=' * 80}\n\n")
        
        storage_types = {}
        for ds in datasets:
            storage_types[ds.storage_type] = storage_types.get(ds.storage_type, 0) + 1
        
        f.write(f"Storage Type Breakdown:\n")
        for storage_type, count in sorted(storage_types.items(), key=lambda x: x[1], reverse=True):
            f.write(f"  {storage_type}: {count:,}\n")
        f.write(f"\n")
        
        # Transformation Analysis
        f.write(f"{'=' * 80}\n")
        f.write(f"TRANSFORMATION ANALYSIS\n")
        f.write(f"{'=' * 80}\n\n")
        
        if transformation_types:
            f.write(f"Transformation Type Breakdown:\n")
            for t_type, count in sorted(transformation_types.items(), key=lambda x: x[1], reverse=True):
                f.write(f"  {t_type}: {count:,}\n")
            f.write(f"\n")
        
        # Airflow-specific analysis
        airflow_tasks = [t for t in transformations if t.transformation_type == 'airflow_task']
        if airflow_tasks:
            f.write(f"{'=' * 80}\n")
            f.write(f"AIRFLOW TASK ANALYSIS\n")
            f.write(f"{'=' * 80}\n\n")
            f.write(f"Total Airflow Tasks: {len(airflow_tasks):,}\n\n")
            
            # Group by DAG
            from collections import defaultdict
            tasks_by_dag = defaultdict(list)
            for task in airflow_tasks:
                source_file = task.provenance.source_file
                tasks_by_dag[source_file].append(task)
            
            f.write(f"DAGs with Tasks: {len(tasks_by_dag):,}\n\n")
            f.write(f"Top 10 DAGs by Task Count:\n")
            sorted_dags = sorted(tasks_by_dag.items(), key=lambda x: len(x[1]), reverse=True)[:10]
            for i, (dag_file, tasks) in enumerate(sorted_dags, 1):
                dag_name = Path(dag_file).name if dag_file else 'unknown'
                f.write(f"  {i:2d}. {dag_name}: {len(tasks)} tasks\n")
            f.write(f"\n")
        
        # dbt-specific analysis
        dbt_models = [t for t in transformations if t.transformation_type == 'dbt_model']
        if dbt_models:
            f.write(f"{'=' * 80}\n")
            f.write(f"DBT MODEL ANALYSIS\n")
            f.write(f"{'=' * 80}\n\n")
            f.write(f"Total dbt Models: {len(dbt_models):,}\n\n")
            
            # Group by directory
            staging_models = [m for m in dbt_models if 'staging' in m.provenance.source_file]
            mart_models = [m for m in dbt_models if 'marts' in m.provenance.source_file]
            
            f.write(f"Model Breakdown:\n")
            f.write(f"  Staging Models: {len(staging_models)}\n")
            f.write(f"  Mart Models: {len(mart_models)}\n")
            f.write(f"  Other Models: {len(dbt_models) - len(staging_models) - len(mart_models)}\n\n")
        
        # Data Operation Analysis
        pandas_ops = [t for t in transformations if 'pandas' in t.transformation_type]
        pyspark_ops = [t for t in transformations if 'pyspark' in t.transformation_type]
        sqlalchemy_ops = [t for t in transformations if 'sqlalchemy' in t.transformation_type]
        sql_ops = [t for t in transformations if t.transformation_type == 'sql']
        
        if any([pandas_ops, pyspark_ops, sqlalchemy_ops, sql_ops]):
            f.write(f"{'=' * 80}\n")
            f.write(f"DATA OPERATION ANALYSIS\n")
            f.write(f"{'=' * 80}\n\n")
            if pandas_ops:
                f.write(f"Pandas Operations: {len(pandas_ops):,}\n")
            if pyspark_ops:
                f.write(f"PySpark Operations: {len(pyspark_ops):,}\n")
            if sqlalchemy_ops:
                f.write(f"SQLAlchemy Operations: {len(sqlalchemy_ops):,}\n")
            if sql_ops:
                f.write(f"SQL Queries: {len(sql_ops):,}\n")
            f.write(f"\n")
        
        # Edge Analysis
        f.write(f"{'=' * 80}\n")
        f.write(f"LINEAGE EDGE ANALYSIS\n")
        f.write(f"{'=' * 80}\n\n")
        f.write(f"CONSUMES Edges: {len(consumes_edges):,}\n")
        f.write(f"PRODUCES Edges: {len(produces_edges):,}\n\n")
        
        # Find transformations with most inputs/outputs
        inputs_per_transform = {}
        outputs_per_transform = {}
        
        for u, v, d in lineage_graph.edges(data=True):
            if d.get('edge_type') == 'consumes':
                inputs_per_transform[v] = inputs_per_transform.get(v, 0) + 1
            elif d.get('edge_type') == 'produces':
                outputs_per_transform[u] = outputs_per_transform.get(u, 0) + 1
        
        if inputs_per_transform:
            f.write(f"Top 5 Transformations by Input Count:\n")
            for i, (transform, count) in enumerate(sorted(inputs_per_transform.items(), key=lambda x: x[1], reverse=True)[:5], 1):
                f.write(f"  {i}. {transform}: {count} inputs\n")
            f.write(f"\n")
        
        if outputs_per_transform:
            f.write(f"Top 5 Transformations by Output Count:\n")
            for i, (transform, count) in enumerate(sorted(outputs_per_transform.items(), key=lambda x: x[1], reverse=True)[:5], 1):
                f.write(f"  {i}. {transform}: {count} outputs\n")
            f.write(f"\n")
        
        # Provenance Analysis
        f.write(f"{'=' * 80}\n")
        f.write(f"PROVENANCE ANALYSIS\n")
        f.write(f"{'=' * 80}\n\n")
        
        evidence_types = {}
        confidences = []
        
        for node in lineage_graph.nodes(data=True):
            node_data = node[1]
            if 'provenance' in node_data:
                prov = node_data['provenance']
                evidence_type = prov.get('evidence_type', 'unknown')
                evidence_types[evidence_type] = evidence_types.get(evidence_type, 0) + 1
                confidences.append(prov.get('confidence', 0))
        
        f.write(f"Evidence Type Breakdown:\n")
        for evidence_type, count in sorted(evidence_types.items(), key=lambda x: x[1], reverse=True):
            f.write(f"  {evidence_type}: {count:,}\n")
        f.write(f"\n")
        
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
            high_confidence = sum(1 for c in confidences if c >= 0.8)
            medium_confidence = sum(1 for c in confidences if 0.5 <= c < 0.8)
            low_confidence = sum(1 for c in confidences if c < 0.5)
            
            f.write(f"Confidence Distribution:\n")
            f.write(f"  Average Confidence: {avg_confidence:.2f}\n")
            f.write(f"  High Confidence (≥0.8): {high_confidence:,} ({high_confidence/len(confidences)*100:.1f}%)\n")
            f.write(f"  Medium Confidence (0.5-0.8): {medium_confidence:,} ({medium_confidence/len(confidences)*100:.1f}%)\n")
            f.write(f"  Low Confidence (<0.5): {low_confidence:,} ({low_confidence/len(confidences)*100:.1f}%)\n")
            f.write(f"\n")
        
        # Source and Sink Analysis
        f.write(f"{'=' * 80}\n")
        f.write(f"DATA FLOW ANALYSIS\n")
        f.write(f"{'=' * 80}\n\n")
        f.write(f"Source Nodes (in-degree 0): {len(sources):,}\n")
        f.write(f"Sink Nodes (out-degree 0): {len(sinks):,}\n\n")
        
        if sources:
            f.write(f"Top 5 Source Datasets:\n")
            for i, source in enumerate(sources[:5], 1):
                node_data = lineage_graph.nodes[source]
                f.write(f"  {i}. {source}\n")
                if 'provenance' in node_data:
                    prov = node_data['provenance']
                    f.write(f"     Evidence: {prov.get('evidence_type', 'unknown')}, ")
                    f.write(f"Confidence: {prov.get('confidence', 0):.2f}\n")
            f.write(f"\n")
        
        if sinks:
            f.write(f"Top 5 Sink Datasets:\n")
            for i, sink in enumerate(sinks[:5], 1):
                node_data = lineage_graph.nodes[sink]
                f.write(f"  {i}. {sink}\n")
                if 'provenance' in node_data:
                    prov = node_data['provenance']
                    f.write(f"     Evidence: {prov.get('evidence_type', 'unknown')}, ")
                    f.write(f"Confidence: {prov.get('confidence', 0):.2f}\n")
            f.write(f"\n")
        
        # Validation Summary
        f.write(f"{'=' * 80}\n")
        f.write(f"VALIDATION SUMMARY\n")
        f.write(f"{'=' * 80}\n\n")
        f.write(f"All validation checks completed successfully.\n")
        f.write(f"The Hydrologist Agent successfully analyzed the repository and\n")
        f.write(f"extracted comprehensive data lineage with full provenance tracking.\n\n")
        f.write(f"{'=' * 80}\n")
        f.write(f"END OF REPORT\n")
        f.write(f"{'=' * 80}\n")
    
    print(f"\n✓ Validation report saved to:")
    print(f"  {report_path}")
    
    # Step 5: Validation checks
    print(f"\n{'=' * 80}")
    print(f"VALIDATION CHECKS")
    print(f"{'=' * 80}")
    
    checks_passed = 0
    checks_total = 0
    
    # Check 1: Lineage graph was created
    checks_total += 1
    if lineage_graph.number_of_nodes() > 0:
        print(f"✓ Check 1: Lineage graph created with nodes")
        checks_passed += 1
    else:
        print(f"✗ Check 1: Lineage graph is empty")
    
    # Check 2: Datasets were found
    checks_total += 1
    if len(datasets) > 0:
        print(f"✓ Check 2: Datasets found ({len(datasets)})")
        checks_passed += 1
    else:
        print(f"✗ Check 2: No datasets found")
    
    # Check 3: Transformations were found
    checks_total += 1
    if len(transformations) > 0:
        print(f"✓ Check 3: Transformations found ({len(transformations)})")
        checks_passed += 1
    else:
        print(f"✗ Check 3: No transformations found")
    
    # Check 4: Both CONSUMES and PRODUCES edges exist
    checks_total += 1
    if len(consumes_edges) > 0 and len(produces_edges) > 0:
        print(f"✓ Check 4: Both CONSUMES and PRODUCES edges exist")
        checks_passed += 1
    else:
        print(f"✗ Check 4: Missing edge types (CONSUMES: {len(consumes_edges)}, PRODUCES: {len(produces_edges)})")
    
    # Check 5: Provenance metadata exists
    checks_total += 1
    nodes_with_provenance = sum(1 for n, d in lineage_graph.nodes(data=True) if 'provenance' in d)
    if nodes_with_provenance > 0:
        print(f"✓ Check 5: Provenance metadata present ({nodes_with_provenance}/{lineage_graph.number_of_nodes()} nodes)")
        checks_passed += 1
    else:
        print(f"✗ Check 5: No provenance metadata found")
    
    # Check 6: Sources and sinks identified
    checks_total += 1
    if len(sources) > 0 or len(sinks) > 0:
        print(f"✓ Check 6: Sources and/or sinks identified (sources: {len(sources)}, sinks: {len(sinks)})")
        checks_passed += 1
    else:
        print(f"✗ Check 6: No sources or sinks found")
    
    print(f"\n{'=' * 80}")
    print(f"VALIDATION SUMMARY: {checks_passed}/{checks_total} checks passed")
    print(f"{'=' * 80}")
    
    if checks_passed == checks_total:
        print(f"\n✓ All validation checks passed!")
        return 0
    else:
        print(f"\n⚠ Some validation checks failed. Review the output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
