"""Orchestrator that wires Surveyor + Hydrologist in sequence."""

from pathlib import Path
from typing import Optional, Tuple
import networkx as nx
from datetime import datetime

from agents.surveyor import SurveyorAgent
from agents.hydrologist import HydrologistAgent
from analyzers.graph_serializer import GraphSerializer


class CartographerOrchestrator:
    """
    Orchestrates the Brownfield Cartographer analysis pipeline.
    
    Runs Surveyor and Hydrologist agents in sequence and serializes
    outputs to .cartography/ directory.
    """
    
    def __init__(self, output_dir: str = ".cartography"):
        """
        Initialize the orchestrator.
        
        Args:
            output_dir: Directory name for output artifacts (default: .cartography)
        """
        self.output_dir_name = output_dir
        self.surveyor = SurveyorAgent()
        self.hydrologist = HydrologistAgent()
        self.errors = []
    
    def analyze_repository(
        self,
        repo_path: str,
        skip_surveyor: bool = False,
        skip_hydrologist: bool = False
    ) -> Tuple[Optional[nx.DiGraph], Optional[nx.DiGraph]]:
        """
        Run complete analysis pipeline on a repository.
        
        Args:
            repo_path: Path to repository to analyze
            skip_surveyor: Skip Surveyor phase (use existing module graph)
            skip_hydrologist: Skip Hydrologist phase
            
        Returns:
            Tuple of (module_graph, lineage_graph)
        """
        repo_path = Path(repo_path).resolve()
        
        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")
        
        if not repo_path.is_dir():
            raise ValueError(f"Path is not a directory: {repo_path}")
        
        # Create output directory
        output_dir = repo_path / self.output_dir_name
        output_dir.mkdir(exist_ok=True)
        
        print("=" * 80)
        print("BROWNFIELD CARTOGRAPHER - ANALYSIS PIPELINE")
        print("=" * 80)
        print(f"\nRepository: {repo_path}")
        print(f"Output directory: {output_dir}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 80)
        
        module_graph = None
        lineage_graph = None
        
        # Phase 1: Surveyor Agent
        if not skip_surveyor:
            print("\n[PHASE 1] Running Surveyor Agent...")
            print("Analyzing module structure and dependencies...")
            
            try:
                module_graph, modules = self.surveyor.analyze_repository(str(repo_path))
                
                print(f"✓ Surveyor complete:")
                print(f"  - Modules analyzed: {len(modules)}")
                print(f"  - Graph nodes: {module_graph.number_of_nodes()}")
                print(f"  - Graph edges: {module_graph.number_of_edges()}")
                
                # Serialize module graph
                module_graph_path = output_dir / 'module_graph.json'
                GraphSerializer.serialize_module_graph(module_graph, str(module_graph_path))
                print(f"  - Module graph saved: {module_graph_path}")
                
                # Save analysis report
                self._save_surveyor_report(output_dir, modules, module_graph)
                
            except Exception as e:
                error_msg = f"Surveyor failed: {str(e)}"
                self.errors.append(error_msg)
                print(f"✗ {error_msg}")
                return None, None
        else:
            print("\n[PHASE 1] Skipping Surveyor (loading existing module graph)...")
            module_graph_path = output_dir / 'module_graph.json'
            
            if not module_graph_path.exists():
                error_msg = "Module graph not found. Run without skip_surveyor first."
                self.errors.append(error_msg)
                print(f"✗ {error_msg}")
                return None, None
            
            try:
                module_graph = GraphSerializer.deserialize_graph(str(module_graph_path))
                print(f"✓ Loaded existing module graph:")
                print(f"  - Graph nodes: {module_graph.number_of_nodes()}")
                print(f"  - Graph edges: {module_graph.number_of_edges()}")
            except Exception as e:
                error_msg = f"Failed to load module graph: {str(e)}"
                self.errors.append(error_msg)
                print(f"✗ {error_msg}")
                return None, None
        
        # Phase 2: Hydrologist Agent
        if not skip_hydrologist:
            print("\n[PHASE 2] Running Hydrologist Agent...")
            print("Analyzing data lineage and transformations...")
            
            try:
                lineage_graph, datasets, transformations = self.hydrologist.analyze_repository(
                    str(repo_path),
                    module_graph
                )
                
                print(f"✓ Hydrologist complete:")
                print(f"  - Datasets discovered: {len(datasets)}")
                print(f"  - Transformations discovered: {len(transformations)}")
                print(f"  - Lineage graph nodes: {lineage_graph.number_of_nodes()}")
                print(f"  - Lineage graph edges: {lineage_graph.number_of_edges()}")
                
                # Serialize lineage graph
                lineage_graph_path = output_dir / 'lineage_graph.json'
                self.hydrologist.serialize_lineage_graph(lineage_graph, str(lineage_graph_path))
                print(f"  - Lineage graph saved: {lineage_graph_path}")
                
                # Save analysis report
                self._save_hydrologist_report(output_dir, datasets, transformations, lineage_graph)
                
            except Exception as e:
                error_msg = f"Hydrologist failed: {str(e)}"
                self.errors.append(error_msg)
                print(f"✗ {error_msg}")
        else:
            print("\n[PHASE 2] Skipping Hydrologist")
        
        # Summary
        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)
        
        if self.errors:
            print(f"\n⚠ Completed with {len(self.errors)} errors:")
            for error in self.errors:
                print(f"  - {error}")
        else:
            print("\n✓ All phases completed successfully")
        
        print(f"\nOutput artifacts saved to: {output_dir}")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return module_graph, lineage_graph
    
    def _save_surveyor_report(self, output_dir: Path, modules, module_graph) -> None:
        """Save Surveyor analysis report."""
        report_path = output_dir / 'surveyor_report.txt'
        
        with open(report_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("SURVEYOR AGENT - ANALYSIS REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("SUMMARY\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total modules: {len(modules)}\n")
            f.write(f"Graph nodes: {module_graph.number_of_nodes()}\n")
            f.write(f"Graph edges: {module_graph.number_of_edges()}\n\n")
            
            # Language breakdown
            language_counts = {}
            for module in modules:
                lang = module.language
                language_counts[lang] = language_counts.get(lang, 0) + 1
            
            f.write("LANGUAGE BREAKDOWN\n")
            f.write("-" * 80 + "\n")
            for lang, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True):
                f.write(f"{lang}: {count} files\n")
            f.write("\n")
            
            # Complexity analysis
            if modules:
                total_complexity = sum(m.complexity_score for m in modules)
                avg_complexity = total_complexity / len(modules)
                
                f.write("COMPLEXITY ANALYSIS\n")
                f.write("-" * 80 + "\n")
                f.write(f"Total complexity: {total_complexity:,} AST nodes\n")
                f.write(f"Average complexity: {avg_complexity:.0f} nodes per file\n\n")
            
            # Circular dependencies
            circular = self.surveyor.detect_circular_dependencies(module_graph)
            f.write("CODE QUALITY\n")
            f.write("-" * 80 + "\n")
            f.write(f"Circular dependencies: {len(circular)}\n")
            
            dead_code = [m for m in modules if m.is_dead_code_candidate]
            f.write(f"Dead code candidates: {len(dead_code)}\n")
            
            if self.surveyor.errors:
                f.write(f"Analysis errors: {len(self.surveyor.errors)}\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("END OF REPORT\n")
            f.write("=" * 80 + "\n")
    
    def _save_hydrologist_report(self, output_dir: Path, datasets, transformations, lineage_graph) -> None:
        """Save Hydrologist analysis report."""
        report_path = output_dir / 'hydrologist_report.txt'
        
        with open(report_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("HYDROLOGIST AGENT - ANALYSIS REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("SUMMARY\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total datasets: {len(datasets)}\n")
            f.write(f"Total transformations: {len(transformations)}\n")
            f.write(f"Lineage graph nodes: {lineage_graph.number_of_nodes()}\n")
            f.write(f"Lineage graph edges: {lineage_graph.number_of_edges()}\n\n")
            
            # Transformation types
            transformation_types = {}
            for t in transformations:
                t_type = t.transformation_type
                transformation_types[t_type] = transformation_types.get(t_type, 0) + 1
            
            f.write("TRANSFORMATION TYPES\n")
            f.write("-" * 80 + "\n")
            for t_type, count in sorted(transformation_types.items(), key=lambda x: x[1], reverse=True):
                f.write(f"{t_type}: {count}\n")
            f.write("\n")
            
            # Dataset storage types
            storage_types = {}
            for ds in datasets:
                storage_types[ds.storage_type] = storage_types.get(ds.storage_type, 0) + 1
            
            f.write("DATASET STORAGE TYPES\n")
            f.write("-" * 80 + "\n")
            for storage_type, count in sorted(storage_types.items(), key=lambda x: x[1], reverse=True):
                f.write(f"{storage_type}: {count}\n")
            f.write("\n")
            
            # Data flow
            sources = self.hydrologist.find_sources(lineage_graph)
            sinks = self.hydrologist.find_sinks(lineage_graph)
            
            f.write("DATA FLOW\n")
            f.write("-" * 80 + "\n")
            f.write(f"Source nodes (in-degree 0): {len(sources)}\n")
            f.write(f"Sink nodes (out-degree 0): {len(sinks)}\n\n")
            
            f.write("=" * 80 + "\n")
            f.write("END OF REPORT\n")
            f.write("=" * 80 + "\n")
