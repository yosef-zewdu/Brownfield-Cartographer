"""Analyze Airflow lineage graph in detail."""

import sys
import json
from pathlib import Path
from collections import defaultdict, Counter

def main():
    """Analyze Airflow lineage graph."""
    
    lineage_file = Path("/home/yosef/Desktop/intensive/airflow/.cartography/lineage_graph.json")
    
    if not lineage_file.exists():
        print("Error: Run validate_hydrologist.py first to generate lineage_graph.json")
        sys.exit(1)
    
    with open(lineage_file) as f:
        graph_data = json.load(f)
    
    print("=" * 80)
    print("APACHE AIRFLOW LINEAGE ANALYSIS")
    print("=" * 80)
    
    # Extract nodes and edges
    nodes = {n['id']: n for n in graph_data['nodes']}
    edges = graph_data['edges']
    
    print(f"\nTotal nodes: {len(nodes):,}")
    print(f"Total edges: {len(edges):,}")
    
    # Analyze transformation types
    print("\n" + "=" * 80)
    print("TRANSFORMATION TYPE BREAKDOWN")
    print("=" * 80)
    
    transformation_nodes = [n for n in nodes.values() if n['node_type'] == 'transformation']
    transformation_types = Counter(n['transformation_type'] for n in transformation_nodes)
    
    print(f"\nTotal transformations: {len(transformation_nodes):,}")
    for t_type, count in transformation_types.most_common():
        print(f"  {t_type}: {count:,}")
    
    # Analyze Airflow tasks
    print("\n" + "=" * 80)
    print("AIRFLOW TASK ANALYSIS")
    print("=" * 80)
    
    airflow_tasks = [n for n in transformation_nodes if n['transformation_type'] == 'airflow_task']
    print(f"\nTotal Airflow tasks detected: {len(airflow_tasks):,}")
    
    # Group by source file (DAG)
    tasks_by_dag = defaultdict(list)
    for task in airflow_tasks:
        source_file = task.get('source_file', 'unknown')
        tasks_by_dag[source_file].append(task)
    
    print(f"\nDAGs with tasks: {len(tasks_by_dag):,}")
    print(f"\nTop 10 DAGs by task count:")
    sorted_dags = sorted(tasks_by_dag.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    for i, (dag_file, tasks) in enumerate(sorted_dags, 1):
        dag_name = Path(dag_file).name if dag_file != 'unknown' else 'unknown'
        print(f"  {i:2d}. {dag_name}: {len(tasks)} tasks")
    
    # Analyze data operations
    print("\n" + "=" * 80)
    print("DATA OPERATION ANALYSIS")
    print("=" * 80)
    
    pandas_ops = [n for n in transformation_nodes if 'pandas' in n['transformation_type']]
    pyspark_ops = [n for n in transformation_nodes if 'pyspark' in n['transformation_type']]
    sqlalchemy_ops = [n for n in transformation_nodes if 'sqlalchemy' in n['transformation_type']]
    sql_ops = [n for n in transformation_nodes if n['transformation_type'] == 'sql']
    
    print(f"\nPandas operations: {len(pandas_ops):,}")
    print(f"PySpark operations: {len(pyspark_ops):,}")
    print(f"SQLAlchemy operations: {len(sqlalchemy_ops):,}")
    print(f"SQL queries: {len(sql_ops):,}")
    
    # Analyze datasets
    print("\n" + "=" * 80)
    print("DATASET ANALYSIS")
    print("=" * 80)
    
    dataset_nodes = [n for n in nodes.values() if n['node_type'] == 'dataset']
    storage_types = Counter(n['storage_type'] for n in dataset_nodes)
    
    print(f"\nTotal datasets: {len(dataset_nodes):,}")
    print(f"\nStorage type breakdown:")
    for storage_type, count in storage_types.most_common():
        print(f"  {storage_type}: {count:,}")
    
    # Analyze evidence types
    print("\n" + "=" * 80)
    print("PROVENANCE ANALYSIS")
    print("=" * 80)
    
    evidence_types = Counter(n['provenance']['evidence_type'] for n in nodes.values())
    print(f"\nEvidence type breakdown:")
    for evidence_type, count in evidence_types.most_common():
        print(f"  {evidence_type}: {count:,}")
    
    # Confidence distribution
    confidences = [n['provenance']['confidence'] for n in nodes.values()]
    avg_confidence = sum(confidences) / len(confidences)
    high_confidence = sum(1 for c in confidences if c >= 0.8)
    medium_confidence = sum(1 for c in confidences if 0.5 <= c < 0.8)
    low_confidence = sum(1 for c in confidences if c < 0.5)
    
    print(f"\nConfidence distribution:")
    print(f"  Average confidence: {avg_confidence:.2f}")
    print(f"  High confidence (≥0.8): {high_confidence:,} ({high_confidence/len(confidences)*100:.1f}%)")
    print(f"  Medium confidence (0.5-0.8): {medium_confidence:,} ({medium_confidence/len(confidences)*100:.1f}%)")
    print(f"  Low confidence (<0.5): {low_confidence:,} ({low_confidence/len(confidences)*100:.1f}%)")
    
    # Analyze edge patterns
    print("\n" + "=" * 80)
    print("LINEAGE EDGE ANALYSIS")
    print("=" * 80)
    
    consumes_edges = [e for e in edges if e['edge_type'] == 'consumes']
    produces_edges = [e for e in edges if e['edge_type'] == 'produces']
    
    print(f"\nCONSUMES edges: {len(consumes_edges):,}")
    print(f"PRODUCES edges: {len(produces_edges):,}")
    
    # Find transformations with most inputs/outputs
    inputs_per_transform = defaultdict(int)
    outputs_per_transform = defaultdict(int)
    
    for edge in consumes_edges:
        inputs_per_transform[edge['target']] += 1
    
    for edge in produces_edges:
        outputs_per_transform[edge['source']] += 1
    
    if inputs_per_transform:
        print(f"\nTop 5 transformations by input count:")
        for i, (transform, count) in enumerate(sorted(inputs_per_transform.items(), key=lambda x: x[1], reverse=True)[:5], 1):
            print(f"  {i}. {transform}: {count} inputs")
    
    if outputs_per_transform:
        print(f"\nTop 5 transformations by output count:")
        for i, (transform, count) in enumerate(sorted(outputs_per_transform.items(), key=lambda x: x[1], reverse=True)[:5], 1):
            print(f"  {i}. {transform}: {count} outputs")
    
    # Sample some interesting DAG files
    print("\n" + "=" * 80)
    print("SAMPLE AIRFLOW DAG ANALYSIS")
    print("=" * 80)
    
    # Find example DAGs
    example_dags = [dag for dag in tasks_by_dag.keys() if 'example' in dag.lower()]
    if example_dags:
        print(f"\nFound {len(example_dags)} example DAGs")
        print(f"\nSample example DAG analysis:")
        sample_dag = example_dags[0]
        sample_tasks = tasks_by_dag[sample_dag]
        print(f"\nDAG: {Path(sample_dag).name}")
        print(f"Tasks: {len(sample_tasks)}")
        print(f"\nTask IDs:")
        for i, task in enumerate(sample_tasks[:10], 1):
            print(f"  {i}. {task['id']}")
        if len(sample_tasks) > 10:
            print(f"  ... and {len(sample_tasks) - 10} more tasks")
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
