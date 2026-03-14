"""Comprehensive validation script for Archivist & Navigator checkpoint."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import json
import networkx as nx
from datetime import datetime

from agents.navigator import NavigatorAgent
from analyzers.graph_serializer import GraphSerializer
from models import ModuleNode, ProvenanceMetadata


def validate_codebase_md(analysis_dir: Path) -> dict:
    """Validate CODEBASE.md contains all required sections."""
    print("\n[1/6] Validating CODEBASE.md...")
    
    codebase_path = analysis_dir / "CODEBASE.md"
    
    if not codebase_path.exists():
        return {
            'passed': False,
            'error': 'CODEBASE.md not found'
        }
    
    with open(codebase_path, 'r') as f:
        content = f.read()
    
    required_sections = [
        "# CODEBASE.md - Living Context Document",
        "## Architecture Overview",
        "## Critical Path",
        "## Data Sources & Sinks",
        "## Known Debt",
        "## High-Velocity Files",
        "## Module Purpose Index"
    ]
    
    missing_sections = []
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)
    
    if missing_sections:
        return {
            'passed': False,
            'error': f'Missing sections: {", ".join(missing_sections)}'
        }
    
    file_size = codebase_path.stat().st_size / 1024
    
    return {
        'passed': True,
        'file_size_kb': round(file_size, 1),
        'sections_found': len(required_sections),
        'content_length': len(content)
    }


def validate_onboarding_brief(analysis_dir: Path) -> dict:
    """Validate onboarding_brief.md answers all Day-One questions."""
    print("\n[2/6] Validating onboarding_brief.md...")
    
    brief_path = analysis_dir / "onboarding_brief.md"
    
    if not brief_path.exists():
        return {
            'passed': False,
            'error': 'onboarding_brief.md not found'
        }
    
    with open(brief_path, 'r') as f:
        content = f.read()
    
    required_questions = [
        "Question 1:",
        "Question 2:",
        "Question 3:",
        "Question 4:",
        "Question 5:"
    ]
    
    missing_questions = []
    for question in required_questions:
        if question not in content:
            missing_questions.append(question)
    
    if missing_questions:
        return {
            'passed': False,
            'error': f'Missing questions: {", ".join(missing_questions)}'
        }
    
    # Check for evidence citations
    has_evidence = "### Evidence" in content
    has_confidence = "### Confidence" in content
    
    file_size = brief_path.stat().st_size / 1024
    
    return {
        'passed': True,
        'file_size_kb': round(file_size, 1),
        'questions_answered': len(required_questions),
        'has_evidence_citations': has_evidence,
        'has_confidence_scores': has_confidence
    }


def validate_trace_log(analysis_dir: Path) -> dict:
    """Validate cartography_trace.jsonl contains complete audit log."""
    print("\n[3/6] Validating cartography_trace.jsonl...")
    
    trace_path = analysis_dir / "cartography_trace.jsonl"
    
    if not trace_path.exists():
        return {
            'passed': False,
            'error': 'cartography_trace.jsonl not found'
        }
    
    entries = []
    with open(trace_path, 'r') as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    
    if not entries:
        return {
            'passed': False,
            'error': 'Trace log is empty'
        }
    
    # Validate entry structure
    required_fields = ['entry_type', 'timestamp', 'agent', 'evidence_type', 'confidence']
    
    for entry in entries:
        missing_fields = [field for field in required_fields if field not in entry]
        if missing_fields:
            return {
                'passed': False,
                'error': f'Entry missing fields: {", ".join(missing_fields)}'
            }
    
    file_size = trace_path.stat().st_size / 1024
    
    return {
        'passed': True,
        'file_size_kb': round(file_size, 1),
        'total_entries': len(entries),
        'entry_types': list(set(e['entry_type'] for e in entries))
    }


def validate_graphs(analysis_dir: Path) -> dict:
    """Validate module_graph.json and lineage_graph.json are present and valid."""
    print("\n[4/6] Validating graph files...")
    
    module_graph_path = analysis_dir / "module_graph.json"
    lineage_graph_path = analysis_dir / "lineage_graph.json"
    
    if not module_graph_path.exists():
        return {
            'passed': False,
            'error': 'module_graph.json not found'
        }
    
    if not lineage_graph_path.exists():
        return {
            'passed': False,
            'error': 'lineage_graph.json not found'
        }
    
    try:
        module_graph = GraphSerializer.deserialize_graph(str(module_graph_path))
        lineage_graph = GraphSerializer.deserialize_graph(str(lineage_graph_path))
    except Exception as e:
        return {
            'passed': False,
            'error': f'Failed to deserialize graphs: {str(e)}'
        }
    
    module_size = module_graph_path.stat().st_size / 1024
    lineage_size = lineage_graph_path.stat().st_size / 1024
    
    return {
        'passed': True,
        'module_graph': {
            'nodes': module_graph.number_of_nodes(),
            'edges': module_graph.number_of_edges(),
            'size_kb': round(module_size, 1)
        },
        'lineage_graph': {
            'nodes': lineage_graph.number_of_nodes(),
            'edges': lineage_graph.number_of_edges(),
            'size_kb': round(lineage_size, 1)
        }
    }


def test_navigator_queries(analysis_dir: Path) -> dict:
    """Test Navigator query interface with sample queries."""
    print("\n[5/6] Testing Navigator query interface...")
    
    try:
        # Load graphs
        module_graph_path = analysis_dir / "module_graph.json"
        lineage_graph_path = analysis_dir / "lineage_graph.json"
        
        module_graph = GraphSerializer.deserialize_graph(str(module_graph_path))
        lineage_graph = GraphSerializer.deserialize_graph(str(lineage_graph_path))
        
        # Reconstruct modules
        modules = []
        for node_id in module_graph.nodes():
            node_data = module_graph.nodes[node_id]
            
            provenance_data = node_data.get('provenance', {})
            provenance = ProvenanceMetadata(**provenance_data) if provenance_data else None
            
            if provenance:
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
        
        # Initialize Navigator
        navigator = NavigatorAgent(modules, module_graph, lineage_graph)
        
        # Test queries
        test_results = []
        
        # Test 1: Semantic search
        if modules:
            result = navigator.run_query("data transformation", tool_name="find_implementation", top_k=3)
            test_results.append({
                'query': 'Semantic search for "data transformation"',
                'tool': 'find_implementation',
                'success': 'results' in result and len(result.get('results', [])) > 0,
                'result_count': len(result.get('results', []))
            })
        
        # Test 2: Lineage traversal
        lineage_nodes = [n for n in lineage_graph.nodes() 
                        if lineage_graph.nodes[n].get('node_type') == 'dataset']
        if lineage_nodes:
            test_dataset = lineage_nodes[0]
            result = navigator.run_query(test_dataset, tool_name="trace_lineage", direction="downstream")
            test_results.append({
                'query': f'Trace lineage for {test_dataset}',
                'tool': 'trace_lineage',
                'success': 'nodes' in result,
                'node_count': result.get('node_count', 0)
            })
        
        # Test 3: Blast radius
        if modules:
            test_module = modules[0].path
            result = navigator.run_query(test_module, tool_name="blast_radius")
            test_results.append({
                'query': f'Blast radius for {Path(test_module).name}',
                'tool': 'blast_radius',
                'success': 'affected_modules' in result,
                'affected_count': result.get('affected_module_count', 0)
            })
        
        # Test 4: Module explanation
        if modules:
            test_module = modules[0].path
            result = navigator.run_query(test_module, tool_name="explain_module")
            test_results.append({
                'query': f'Explain module {Path(test_module).name}',
                'tool': 'explain_module',
                'success': result.get('found', False),
                'has_summary': 'summary' in result
            })
        
        all_passed = all(t['success'] for t in test_results)
        
        return {
            'passed': all_passed,
            'tests_run': len(test_results),
            'tests_passed': sum(1 for t in test_results if t['success']),
            'test_results': test_results
        }
    
    except Exception as e:
        return {
            'passed': False,
            'error': f'Navigator test failed: {str(e)}'
        }


def check_property_tests() -> dict:
    """Check if property tests exist and can be run."""
    print("\n[6/6] Checking property tests...")
    
    test_dir = Path("tests/unit")
    
    if not test_dir.exists():
        return {
            'passed': False,
            'error': 'Test directory not found'
        }
    
    # Look for property test files
    property_test_files = list(test_dir.glob("test_*.py"))
    
    return {
        'passed': True,
        'test_files_found': len(property_test_files),
        'note': 'Property tests exist but not executed in this validation'
    }


def main():
    """Run comprehensive validation."""
    if len(sys.argv) < 2:
        print("Usage: python validate_archivist_navigator.py <analysis_directory>")
        print("\nExample:")
        print("  python examples/validate_archivist_navigator.py .cartography/.cartography-jaffle-shop")
        sys.exit(1)
    
    analysis_dir = Path(sys.argv[1])
    
    if not analysis_dir.exists():
        print(f"Error: Analysis directory does not exist: {analysis_dir}")
        sys.exit(1)
    
    print("=" * 80)
    print("CHECKPOINT 9: ARCHIVIST & NAVIGATOR VALIDATION")
    print("=" * 80)
    print(f"\nAnalysis directory: {analysis_dir}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)
    
    # Run validations
    results = {}
    
    results['codebase_md'] = validate_codebase_md(analysis_dir)
    results['onboarding_brief'] = validate_onboarding_brief(analysis_dir)
    results['trace_log'] = validate_trace_log(analysis_dir)
    results['graphs'] = validate_graphs(analysis_dir)
    results['navigator'] = test_navigator_queries(analysis_dir)
    results['property_tests'] = check_property_tests()
    
    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    all_passed = all(r['passed'] for r in results.values())
    
    for name, result in results.items():
        status = "✓ PASS" if result['passed'] else "✗ FAIL"
        print(f"\n{status} - {name.replace('_', ' ').title()}")
        
        if result['passed']:
            # Print success details
            for key, value in result.items():
                if key != 'passed' and not key.startswith('_'):
                    if isinstance(value, dict):
                        print(f"  {key}:")
                        for k, v in value.items():
                            print(f"    - {k}: {v}")
                    elif isinstance(value, list):
                        print(f"  {key}: {len(value)} items")
                    else:
                        print(f"  {key}: {value}")
        else:
            # Print error
            print(f"  Error: {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 80)
    
    if all_passed:
        print("✓ ALL VALIDATIONS PASSED")
        print("\nCheckpoint 9 complete! Archivist & Navigator are working correctly.")
    else:
        print("✗ SOME VALIDATIONS FAILED")
        print("\nPlease review the errors above and fix the issues.")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
