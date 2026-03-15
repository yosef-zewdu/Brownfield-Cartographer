"""Command-line interface for Brownfield Cartographer."""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from orchestrator import CartographerOrchestrator


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Brownfield Cartographer - Analyze codebases and extract data lineage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a repository
  python -m src.cli analyze /path/to/repository

  # Analyze with custom output directory
  python -m src.cli analyze /path/to/repository --output-dir .analysis

  # Incremental analysis (only re-analyze changed modules)
  python -m src.cli analyze /path/to/repository --incremental

  # Skip Surveyor phase (use existing module graph)
  python -m src.cli analyze /path/to/repository --skip-surveyor

  # Skip Semanticist phase
  python -m src.cli analyze /path/to/repository --skip-semanticist

  # Skip Archivist phase
  python -m src.cli analyze /path/to/repository --skip-archivist

  # Analyze a GitHub repository
  python -m src.cli analyze https://github.com/owner/repo

  # Query an analyzed repository interactively
  python -m src.cli query /path/to/repository
  python -m src.cli query /path/to/repository --output-dir .analysis
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # ------------------------------------------------------------------ #
    # analyze subcommand                                                   #
    # ------------------------------------------------------------------ #
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze a repository and extract lineage'
    )
    analyze_parser.add_argument(
        'repo_path',
        type=str,
        help='Path to repository to analyze (or a GitHub URL)'
    )
    analyze_parser.add_argument(
        '--output-dir',
        type=str,
        default='.cartography',
        help='Output directory name (default: .cartography)'
    )
    analyze_parser.add_argument(
        '--skip-surveyor',
        action='store_true',
        help='Skip Surveyor phase (use existing module graph)'
    )
    analyze_parser.add_argument(
        '--skip-hydrologist',
        action='store_true',
        help='Skip Hydrologist phase (only run Surveyor)'
    )
    analyze_parser.add_argument(
        '--skip-semanticist',
        action='store_true',
        help='Skip Semanticist phase'
    )
    analyze_parser.add_argument(
        '--skip-archivist',
        action='store_true',
        help='Skip Archivist phase (no living documentation generated)'
    )
    analyze_parser.add_argument(
        '--incremental',
        action='store_true',
        help='Only re-analyze modules changed since last run'
    )
    analyze_parser.add_argument(
        '--semanticist-max-modules',
        type=int,
        default=None,
        help='Maximum modules for Semanticist analysis (default: all, recommended: 100 for large codebases)'
    )

    # ------------------------------------------------------------------ #
    # query subcommand                                                     #
    # ------------------------------------------------------------------ #
    query_parser = subparsers.add_parser(
        'query',
        help='Interactively query an analyzed repository'
    )
    query_parser.add_argument(
        'repo_path',
        type=str,
        help='Path to the analyzed repository'
    )
    query_parser.add_argument(
        '--output-dir',
        type=str,
        default='.cartography',
        help='Output directory containing analysis artifacts (default: .cartography)'
    )

    # ------------------------------------------------------------------ #
    # visualize subcommand                                                 #
    # ------------------------------------------------------------------ #
    viz_parser = subparsers.add_parser(
        'visualize',
        help='Visualize module or lineage graph (Graphviz SVG/PNG + PyVis HTML)'
    )
    viz_parser.add_argument(
        'repo_path',
        type=str,
        help='Path to the analyzed repository'
    )
    viz_parser.add_argument(
        '--graph', choices=['lineage', 'module', 'both'], default='both',
        help='Which graph to visualize (default: both)'
    )
    viz_parser.add_argument(
        '--output-dir',
        type=str,
        default='.cartography',
        help='Output directory containing analysis artifacts (default: .cartography)'
    )
    viz_parser.add_argument(
        '--formats', nargs='+', default=['svg', 'html'],
        choices=['svg', 'png', 'html'],
        help='Output formats (default: svg html)'
    )
    viz_parser.add_argument(
        '--no-collapse',
        action='store_true',
        help='Show raw consumes/produces edges with transformation nodes (default: collapsed)'
    )
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'analyze':
        return analyze_command(args)

    if args.command == 'query':
        return query_command(args)

    if args.command == 'visualize':
        return visualize_command(args)

    return 0


# --------------------------------------------------------------------------- #
# analyze_command                                                              #
# --------------------------------------------------------------------------- #

def analyze_command(args):
    """
    Execute the analyze command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    repo_path_str = args.repo_path
    temp_dir = None

    # GitHub URL support
    if repo_path_str.startswith("https://github.com") or repo_path_str.startswith("git@github.com"):
        temp_dir = tempfile.mkdtemp()
        print(f"Cloning {repo_path_str} into {temp_dir} ...")
        result = subprocess.run(["git", "clone", repo_path_str, temp_dir])
        if result.returncode != 0:
            print(f"Error: git clone failed for {repo_path_str}", file=sys.stderr)
            return 1
        repo_path_str = temp_dir

    repo_path = Path(repo_path_str).resolve()

    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repo_path}", file=sys.stderr)
        return 1

    if not repo_path.is_dir():
        print(f"Error: Path is not a directory: {repo_path}", file=sys.stderr)
        return 1

    orchestrator = CartographerOrchestrator(output_dir=args.output_dir)

    try:
        module_graph, lineage_graph = orchestrator.analyze_repository(
            str(repo_path),
            skip_surveyor=args.skip_surveyor,
            skip_hydrologist=args.skip_hydrologist,
            skip_semanticist=getattr(args, 'skip_semanticist', False),
            skip_archivist=getattr(args, 'skip_archivist', False),
            semanticist_max_modules=getattr(args, 'semanticist_max_modules', None),
            incremental=getattr(args, 'incremental', False),
        )

        if orchestrator.errors:
            print(f"\n⚠ Analysis completed with {len(orchestrator.errors)} errors", file=sys.stderr)
            return 1

        print("\n✓ Analysis completed successfully")
        return 0

    except KeyboardInterrupt:
        print("\n\nAnalysis interrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\nError: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


# --------------------------------------------------------------------------- #
# query_command                                                                #
# --------------------------------------------------------------------------- #

def query_command(args):
    """
    Launch the Navigator interactive query mode.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    from analyzers.graph_serializer import GraphSerializer
    from agents.navigator import NavigatorAgent
    from models import ModuleNode, ProvenanceMetadata

    repo_path = Path(args.repo_path).resolve()
    output_dir = repo_path / args.output_dir

    module_graph_path = output_dir / "module_graph.json"
    lineage_graph_path = output_dir / "lineage_graph.json"

    # Validate graph files exist
    missing = [p for p in (module_graph_path, lineage_graph_path) if not p.exists()]
    if missing:
        for p in missing:
            print(f"Error: graph file not found: {p}", file=sys.stderr)
        print(
            "Run 'analyze' first to generate the required graph files.",
            file=sys.stderr,
        )
        return 1

    try:
        module_graph = GraphSerializer.deserialize_graph(str(module_graph_path))
        lineage_graph = GraphSerializer.deserialize_graph(str(lineage_graph_path))
    except Exception as e:
        print(f"Error loading graph files: {e}", file=sys.stderr)
        return 1

    # Reconstruct ModuleNode list from module graph nodes
    modules = []
    for node_id in module_graph.nodes():
        node_data = module_graph.nodes[node_id]
        provenance_data = node_data.get('provenance', {})
        if not provenance_data:
            continue
        try:
            provenance = ProvenanceMetadata(**provenance_data)
            module = ModuleNode(
                path=node_data['path'],
                language=node_data['language'],
                complexity_score=node_data.get('complexity_score', 0),
                imports=node_data.get('imports', []),
                exports=node_data.get('exports', []),
                provenance=provenance,
                purpose_statement=node_data.get('purpose_statement'),
                domain_cluster=node_data.get('domain_cluster'),
                change_velocity=node_data.get('change_velocity'),
                is_dead_code_candidate=node_data.get('is_dead_code_candidate', False),
                docstring=node_data.get('docstring'),
                has_documentation_drift=node_data.get('has_documentation_drift', False),
            )
            modules.append(module)
        except Exception:
            continue

    navigator = NavigatorAgent(
        modules=modules,
        module_graph=module_graph,
        lineage_graph=lineage_graph,
    )
    navigator.interactive_mode()
    return 0


# --------------------------------------------------------------------------- #
# visualize_command                                                            #
# --------------------------------------------------------------------------- #

def visualize_command(args):
    """Render module and/or lineage graphs to SVG, PNG, and/or HTML."""
    from utils.visualizer import visualize

    repo_path = Path(args.repo_path).resolve()
    output_dir = repo_path / args.output_dir

    graphs = []
    if args.graph in ('lineage', 'both'):
        graphs.append(('lineage', output_dir / 'lineage_graph.json'))
    if args.graph in ('module', 'both'):
        graphs.append(('module', output_dir / 'module_graph.json'))

    for graph_type, graph_path in graphs:
        if not graph_path.exists():
            print(f"Error: {graph_path} not found. Run 'analyze' first.", file=sys.stderr)
            return 1
        print(f"\nRendering {graph_type} graph...")
        collapse = not getattr(args, 'no_collapse', False)
        visualize(str(graph_path), graph_type, str(output_dir), args.formats, collapse_transforms=collapse)

    print("\n✓ Visualization complete")
    return 0


if __name__ == '__main__':
    sys.exit(main())
