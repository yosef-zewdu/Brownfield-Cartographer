"""Command-line interface for Brownfield Cartographer."""

import argparse
import sys
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

  # Skip Surveyor phase (use existing module graph)
  python -m src.cli analyze /path/to/repository --skip-surveyor

  # Run only Surveyor phase
  python -m src.cli analyze /path/to/repository --skip-hydrologist
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze a repository and extract lineage'
    )
    analyze_parser.add_argument(
        'repo_path',
        type=str,
        help='Path to repository to analyze'
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
        '--semanticist-max-modules',
        type=int,
        default=None,
        help='Maximum modules for Semanticist analysis (default: all, recommended: 100 for large codebases)'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Show help if no command specified
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Handle analyze command
    if args.command == 'analyze':
        return analyze_command(args)
    
    return 0


def analyze_command(args):
    """
    Execute the analyze command.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    repo_path = Path(args.repo_path).resolve()
    
    # Validate repository path
    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repo_path}", file=sys.stderr)
        return 1
    
    if not repo_path.is_dir():
        print(f"Error: Path is not a directory: {repo_path}", file=sys.stderr)
        return 1
    
    # Create orchestrator
    orchestrator = CartographerOrchestrator(output_dir=args.output_dir)
    
    # Run analysis
    try:
        module_graph, lineage_graph = orchestrator.analyze_repository(
            str(repo_path),
            skip_surveyor=args.skip_surveyor,
            skip_hydrologist=args.skip_hydrologist,
            semanticist_max_modules=getattr(args, 'semanticist_max_modules', None)
        )
        
        # Check for errors
        if orchestrator.errors:
            print(f"\n⚠ Analysis completed with {len(orchestrator.errors)} errors", file=sys.stderr)
            return 1
        
        # Success
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


if __name__ == '__main__':
    sys.exit(main())
