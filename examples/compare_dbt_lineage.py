"""Compare Hydrologist lineage against expected dbt lineage."""

import sys
import json
from pathlib import Path
from collections import defaultdict

def main():
    """Compare lineage graph against expected dbt dependencies."""
    
    lineage_file = Path("/home/yosef/Desktop/intensive/jaffle-shop/.cartography/lineage_graph.json")
    
    if not lineage_file.exists():
        print("Error: Run validate_hydrologist.py first to generate lineage_graph.json")
        sys.exit(1)
    
    with open(lineage_file) as f:
        graph_data = json.load(f)
    
    print("=" * 80)
    print("DBT JAFFLE-SHOP LINEAGE COMPARISON")
    print("=" * 80)
    
    # Extract nodes and edges
    nodes = {n['id']: n for n in graph_data['nodes']}
    edges = graph_data['edges']
    
    # Build dependency map
    dependencies = defaultdict(list)
    for edge in edges:
        if edge['edge_type'] == 'consumes':
            # transformation consumes dataset
            dependencies[edge['target']].append(edge['source'])
    
    print(f"\nTotal nodes: {len(nodes)}")
    print(f"Total edges: {len(edges)}")
    
    # Expected dbt lineage based on ref() calls
    expected_lineage = {
        'dbt_model:customers': ['stg_customers', 'orders'],
        'dbt_model:orders': ['stg_orders', 'order_items'],
        'dbt_model:order_items': ['stg_order_items', 'stg_orders', 'stg_products', 'stg_supplies'],
        'dbt_model:products': ['stg_products'],
        'dbt_model:locations': ['stg_locations'],
        'dbt_model:supplies': ['stg_supplies'],
        'dbt_model:stg_customers': ['ecom.raw_customers'],
        'dbt_model:stg_orders': ['ecom.raw_orders'],
        'dbt_model:stg_products': ['ecom.raw_products'],
        'dbt_model:stg_supplies': ['ecom.raw_supplies'],
        'dbt_model:stg_order_items': ['ecom.raw_items'],
        'dbt_model:stg_locations': ['ecom.raw_stores'],
    }
    
    print("\n" + "=" * 80)
    print("LINEAGE VERIFICATION")
    print("=" * 80)
    
    all_correct = True
    
    for model, expected_deps in expected_lineage.items():
        if model not in dependencies:
            print(f"\n✗ {model}")
            print(f"  Expected dependencies: {expected_deps}")
            print(f"  Found: NONE")
            all_correct = False
            continue
        
        actual_deps = set(dependencies[model])
        expected_deps_set = set(expected_deps)
        
        if actual_deps == expected_deps_set:
            print(f"\n✓ {model}")
            print(f"  Dependencies: {sorted(actual_deps)}")
        else:
            print(f"\n⚠ {model}")
            print(f"  Expected: {sorted(expected_deps_set)}")
            print(f"  Found: {sorted(actual_deps)}")
            
            missing = expected_deps_set - actual_deps
            extra = actual_deps - expected_deps_set
            
            if missing:
                print(f"  Missing: {sorted(missing)}")
            if extra:
                print(f"  Extra: {sorted(extra)}")
            
            all_correct = False
    
    # Check for source datasets
    print("\n" + "=" * 80)
    print("SOURCE DATASETS (raw tables)")
    print("=" * 80)
    
    source_datasets = [n for n in nodes.values() if n['node_type'] == 'dataset' and 'raw_' in n['id']]
    print(f"\nFound {len(source_datasets)} source datasets:")
    for ds in sorted(source_datasets, key=lambda x: x['id']):
        print(f"  - {ds['id']} (discovered in: {ds['discovered_in']})")
    
    # Check for final mart models
    print("\n" + "=" * 80)
    print("FINAL MART MODELS (outputs)")
    print("=" * 80)
    
    mart_models = [n for n in nodes.values() if n['node_type'] == 'transformation' and 'marts/' in n.get('source_file', '')]
    print(f"\nFound {len(mart_models)} mart models:")
    for model in sorted(mart_models, key=lambda x: x['id']):
        print(f"  - {model['id']}")
        print(f"    Source: {model['source_file']}")
    
    print("\n" + "=" * 80)
    if all_correct:
        print("✓ ALL LINEAGE CHECKS PASSED")
    else:
        print("⚠ SOME LINEAGE CHECKS FAILED - Review output above")
    print("=" * 80)
    
    return 0 if all_correct else 1


if __name__ == '__main__':
    sys.exit(main())
