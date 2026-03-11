"""Simple example demonstrating the Surveyor Agent."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from agents.surveyor import SurveyorAgent
from analyzers.graph_serializer import GraphSerializer


def main():
    """Run a simple example of the Surveyor Agent."""
    # Analyze the current repository
    repo_path = Path(__file__).parent.parent
    
    print(f"Analyzing repository: {repo_path}")
    print("-" * 60)
    
    # Create surveyor agent
    surveyor = SurveyorAgent()
    
    # Analyze repository
    graph, modules = surveyor.analyze_repository(str(repo_path))
    
    print(f"\nFound {len(modules)} modules")
    print(f"Graph has {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
    
    # Show some statistics
    if modules:
        print("\nTop 5 modules by complexity:")
        sorted_modules = sorted(modules, key=lambda m: m.complexity_score, reverse=True)[:5]
        for module in sorted_modules:
            print(f"  {module.path}: {module.complexity_score} nodes")
    
    # Show PageRank scores
    print("\nTop 5 modules by PageRank (architectural hubs):")
    pagerank_scores = [(node, data.get('pagerank', 0)) 
                       for node, data in graph.nodes(data=True)]
    pagerank_scores.sort(key=lambda x: x[1], reverse=True)
    for node, score in pagerank_scores[:5]:
        print(f"  {Path(node).name}: {score:.4f}")
    
    # Show circular dependencies
    circular = surveyor.detect_circular_dependencies(graph)
    if circular:
        print(f"\nFound {len(circular)} circular dependency groups:")
        for cycle in circular[:3]:  # Show first 3
            print(f"  {' -> '.join([Path(p).name for p in cycle])}")
    else:
        print("\nNo circular dependencies found!")
    
    # Show dead code candidates
    dead_code = [m for m in modules if m.is_dead_code_candidate]
    if dead_code:
        print(f"\nFound {len(dead_code)} dead code candidates:")
        for module in dead_code[:5]:  # Show first 5
            print(f"  {module.path}")
    else:
        print("\nNo dead code candidates found!")
    
    # Serialize graph
    output_dir = repo_path / '.cartography'
    output_dir.mkdir(exist_ok=True)
    
    output_path = output_dir / 'module_graph.json'
    GraphSerializer.serialize_module_graph(graph, str(output_path))
    print(f"\nModule graph saved to: {output_path}")
    
    # Show errors if any
    if surveyor.errors:
        print(f"\nEncountered {len(surveyor.errors)} errors during analysis:")
        for error in surveyor.errors[:5]:  # Show first 5
            print(f"  {error['file']}: {error['error']}")


if __name__ == '__main__':
    main()
