"""Analyze any repository with the Surveyor Agent."""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from agents.surveyor import SurveyorAgent
from analyzers.graph_serializer import GraphSerializer


def main():
    """Analyze a repository specified as command line argument."""
    if len(sys.argv) < 2:
        print("Usage: python analyze_repo.py <path_to_repository>")
        print("\nExample:")
        print("  python analyze_repo.py /home/yosef/Desktop/intensive/airflow")
        sys.exit(1)
    
    repo_path = Path(sys.argv[1])
    
    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repo_path}")
        sys.exit(1)
    
    if not repo_path.is_dir():
        print(f"Error: Path is not a directory: {repo_path}")
        sys.exit(1)
    
    print("=" * 80)
    print(f"BROWNFIELD CARTOGRAPHER - SURVEYOR AGENT")
    print("=" * 80)
    print(f"\nAnalyzing repository: {repo_path}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)
    
    # Create surveyor agent
    surveyor = SurveyorAgent()
    
    # Analyze repository
    print("\n[1/6] Scanning repository for supported files...")
    graph, modules = surveyor.analyze_repository(str(repo_path))
    
    print(f"[2/6] Analyzing module structure...")
    print(f"      ✓ Found {len(modules)} modules")
    print(f"      ✓ Built graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
    
    # Language breakdown
    print(f"\n[3/6] Language breakdown:")
    language_counts = {}
    for module in modules:
        lang = module.language
        language_counts[lang] = language_counts.get(lang, 0) + 1
    
    for lang, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"      {lang}: {count} files")
    
    # Complexity analysis
    print(f"\n[4/6] Complexity analysis:")
    if modules:
        total_complexity = sum(m.complexity_score for m in modules)
        avg_complexity = total_complexity / len(modules)
        print(f"      Total complexity: {total_complexity:,} AST nodes")
        print(f"      Average complexity: {avg_complexity:.0f} nodes per file")
        
        print(f"\n      Top 10 most complex modules:")
        sorted_modules = sorted(modules, key=lambda m: m.complexity_score, reverse=True)[:10]
        for i, module in enumerate(sorted_modules, 1):
            rel_path = Path(module.path).relative_to(repo_path)
            print(f"      {i:2d}. {rel_path} ({module.complexity_score:,} nodes)")
    
    # PageRank analysis
    print(f"\n[5/6] Architectural hub analysis (PageRank):")
    pagerank_scores = [(node, data.get('pagerank', 0)) 
                       for node, data in graph.nodes(data=True)]
    pagerank_scores.sort(key=lambda x: x[1], reverse=True)
    
    print(f"      Top 10 architectural hubs (most imported modules):")
    for i, (node, score) in enumerate(pagerank_scores[:10], 1):
        rel_path = Path(node).relative_to(repo_path)
        in_degree = graph.in_degree(node)
        print(f"      {i:2d}. {rel_path}")
        print(f"          PageRank: {score:.4f} | Imported by: {in_degree} modules")
    
    # Circular dependencies
    print(f"\n[6/6] Code quality analysis:")
    circular = surveyor.detect_circular_dependencies(graph)
    if circular:
        print(f"      ⚠ Found {len(circular)} circular dependency groups:")
        for i, cycle in enumerate(circular[:5], 1):  # Show first 5
            cycle_names = [Path(p).relative_to(repo_path).name for p in cycle]
            print(f"      {i}. {' ↔ '.join(cycle_names)}")
        if len(circular) > 5:
            print(f"      ... and {len(circular) - 5} more")
    else:
        print(f"      ✓ No circular dependencies found!")
    
    # Dead code candidates
    dead_code = [m for m in modules if m.is_dead_code_candidate]
    if dead_code:
        print(f"\n      ⚠ Found {len(dead_code)} dead code candidates:")
        for i, module in enumerate(dead_code[:5], 1):  # Show first 5
            rel_path = Path(module.path).relative_to(repo_path)
            print(f"      {i}. {rel_path} (has exports but no imports)")
        if len(dead_code) > 5:
            print(f"      ... and {len(dead_code) - 5} more")
    else:
        print(f"      ✓ No dead code candidates found!")
    
    # Git velocity analysis
    print(f"\n      Git velocity (last 90 days):")
    modules_with_velocity = [m for m in modules if m.change_velocity is not None and m.change_velocity > 0]
    if modules_with_velocity:
        print(f"      {len(modules_with_velocity)} files changed in last 90 days")
        
        sorted_by_velocity = sorted(modules_with_velocity, key=lambda m: m.change_velocity, reverse=True)[:5]
        print(f"\n      Top 5 most frequently changed files:")
        for i, module in enumerate(sorted_by_velocity, 1):
            rel_path = Path(module.path).relative_to(repo_path)
            print(f"      {i}. {rel_path} ({module.change_velocity} commits)")
    else:
        print(f"      No files changed in last 90 days")
    
    # Errors
    if surveyor.errors:
        print(f"\n      ⚠ Encountered {len(surveyor.errors)} errors during analysis:")
        for i, error in enumerate(surveyor.errors[:5], 1):  # Show first 5
            rel_path = Path(error['file']).relative_to(repo_path)
            print(f"      {i}. {rel_path}: {error['error'][:60]}...")
        if len(surveyor.errors) > 5:
            print(f"      ... and {len(surveyor.errors) - 5} more errors")
    
    # Save output
    print("\n" + "=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)
    
    # Create output directory in the analyzed repository
    output_dir = repo_path / '.cartography'
    output_dir.mkdir(exist_ok=True)
    
    # Save module graph
    graph_path = output_dir / 'module_graph.json'
    GraphSerializer.serialize_module_graph(graph, str(graph_path))
    print(f"\n✓ Module graph saved to:")
    print(f"  {graph_path}")
    print(f"  Size: {graph_path.stat().st_size / 1024:.1f} KB")
    
    # Save detailed report
    report_path = output_dir / 'analysis_report.txt'
    with open(report_path, 'w') as f:
        f.write(f"{'=' * 80}\n")
        f.write(f"BROWNFIELD CARTOGRAPHER - SURVEYOR AGENT\n")
        f.write(f"{'=' * 80}\n\n")
        f.write(f"Repository: {repo_path}\n")
        f.write(f"Analyzed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'-' * 80}\n\n")
        
        # Summary
        f.write(f"SUMMARY\n")
        f.write(f"{'-' * 80}\n")
        f.write(f"Total modules analyzed: {len(modules)}\n")
        f.write(f"Graph nodes: {graph.number_of_nodes()}\n")
        f.write(f"Graph edges: {graph.number_of_edges()}\n")
        f.write(f"Circular dependencies: {len(circular)}\n")
        f.write(f"Dead code candidates: {len(dead_code)}\n")
        f.write(f"Analysis errors: {len(surveyor.errors)}\n\n")
        
        # Language breakdown
        f.write(f"LANGUAGE BREAKDOWN\n")
        f.write(f"{'-' * 80}\n")
        for lang, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(modules) * 100) if modules else 0
            f.write(f"{lang}: {count} files ({percentage:.1f}%)\n")
        f.write(f"\n")
        
        # Complexity analysis
        f.write(f"COMPLEXITY ANALYSIS\n")
        f.write(f"{'-' * 80}\n")
        if modules:
            total_complexity = sum(m.complexity_score for m in modules)
            avg_complexity = total_complexity / len(modules)
            f.write(f"Total complexity: {total_complexity:,} AST nodes\n")
            f.write(f"Average complexity: {avg_complexity:.0f} nodes per file\n\n")
            
            f.write(f"Top 10 most complex modules:\n")
            sorted_modules = sorted(modules, key=lambda m: m.complexity_score, reverse=True)[:10]
            for i, module in enumerate(sorted_modules, 1):
                rel_path = Path(module.path).relative_to(repo_path)
                f.write(f"  {i:2d}. {rel_path}\n")
                f.write(f"      Complexity: {module.complexity_score:,} AST nodes\n")
        f.write(f"\n")
        
        # PageRank analysis
        f.write(f"ARCHITECTURAL HUB ANALYSIS (PageRank)\n")
        f.write(f"{'-' * 80}\n")
        pagerank_scores = [(node, data.get('pagerank', 0)) 
                           for node, data in graph.nodes(data=True)]
        pagerank_scores.sort(key=lambda x: x[1], reverse=True)
        
        f.write(f"Top 10 architectural hubs (most imported modules):\n")
        for i, (node, score) in enumerate(pagerank_scores[:10], 1):
            rel_path = Path(node).relative_to(repo_path)
            in_degree = graph.in_degree(node)
            f.write(f"  {i:2d}. {rel_path}\n")
            f.write(f"      PageRank: {score:.4f} | Imported by: {in_degree} modules\n")
        f.write(f"\n")
        
        # Code quality analysis
        f.write(f"CODE QUALITY ANALYSIS\n")
        f.write(f"{'-' * 80}\n")
        
        # Circular dependencies
        if circular:
            f.write(f"⚠ Found {len(circular)} circular dependency groups:\n")
            for i, cycle in enumerate(circular[:10], 1):  # Show first 10
                cycle_names = [Path(p).relative_to(repo_path).name for p in cycle]
                f.write(f"  {i}. {' ↔ '.join(cycle_names)}\n")
            if len(circular) > 10:
                f.write(f"  ... and {len(circular) - 10} more\n")
        else:
            f.write(f"✓ No circular dependencies found!\n")
        f.write(f"\n")
        
        # Dead code candidates
        if dead_code:
            f.write(f"⚠ Found {len(dead_code)} dead code candidates:\n")
            for i, module in enumerate(dead_code[:10], 1):  # Show first 10
                rel_path = Path(module.path).relative_to(repo_path)
                f.write(f"  {i}. {rel_path}\n")
                f.write(f"     Reason: Has exports but no imports\n")
            if len(dead_code) > 10:
                f.write(f"  ... and {len(dead_code) - 10} more\n")
        else:
            f.write(f"✓ No dead code candidates found!\n")
        f.write(f"\n")
        
        # Git velocity analysis
        f.write(f"GIT VELOCITY (Last 90 Days)\n")
        f.write(f"{'-' * 80}\n")
        modules_with_velocity = [m for m in modules if m.change_velocity is not None and m.change_velocity > 0]
        if modules_with_velocity:
            f.write(f"{len(modules_with_velocity)} files changed in last 90 days\n\n")
            
            sorted_by_velocity = sorted(modules_with_velocity, key=lambda m: m.change_velocity, reverse=True)[:10]
            f.write(f"Top 10 most frequently changed files:\n")
            for i, module in enumerate(sorted_by_velocity, 1):
                rel_path = Path(module.path).relative_to(repo_path)
                f.write(f"  {i:2d}. {rel_path}\n")
                f.write(f"      Commits: {module.change_velocity}\n")
        else:
            f.write(f"No files changed in last 90 days\n")
        f.write(f"\n")
        
        # Errors
        if surveyor.errors:
            f.write(f"ANALYSIS ERRORS\n")
            f.write(f"{'-' * 80}\n")
            f.write(f"⚠ Encountered {len(surveyor.errors)} errors during analysis:\n")
            for i, error in enumerate(surveyor.errors[:10], 1):  # Show first 10
                rel_path = Path(error['file']).relative_to(repo_path)
                f.write(f"  {i}. {rel_path}\n")
                f.write(f"     Error: {error['error']}\n")
            if len(surveyor.errors) > 10:
                f.write(f"  ... and {len(surveyor.errors) - 10} more errors\n")
            f.write(f"\n")
        
        # Footer
        f.write(f"{'=' * 80}\n")
        f.write(f"OUTPUT FILES\n")
        f.write(f"{'=' * 80}\n")
        f.write(f"1. module_graph.json - Complete graph with all metadata\n")
        f.write(f"2. analysis_report.txt - This human-readable summary\n\n")
        f.write(f"Next Steps:\n")
        f.write(f"  - Inspect the graph JSON for detailed analysis\n")
        f.write(f"  - Use the graph for further processing\n")
        f.write(f"  - Run incremental updates as the codebase changes\n")
    
    print(f"\n✓ Analysis report saved to:")
    print(f"  {report_path}")
    
    print(f"\n{'=' * 80}")
    print(f"ANALYSIS COMPLETE")
    print(f"{'=' * 80}")
    print(f"\nOutput directory: {output_dir}")
    print(f"\nFiles created:")
    print(f"  1. module_graph.json - Complete graph with all metadata")
    print(f"  2. analysis_report.txt - Human-readable summary")
    print(f"\nYou can now:")
    print(f"  - Inspect the graph JSON for detailed analysis")
    print(f"  - Use the graph for further processing")
    print(f"  - Run incremental updates as the codebase changes")


if __name__ == '__main__':
    main()
