"""Orchestrator that wires Surveyor + Hydrologist in sequence."""

from pathlib import Path
from typing import Optional, Tuple
import networkx as nx
from datetime import datetime

from agents.surveyor import SurveyorAgent
from agents.hydrologist import HydrologistAgent
from agents.semanticist import SemanticistAgent
from agents.trace_logger import CartographyTraceLogger
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
        self.semanticist = SemanticistAgent()
        self.errors = []
        self.trace_logger = CartographyTraceLogger()
    
    def analyze_repository(
        self,
        repo_path: str,
        skip_surveyor: bool = False,
        skip_hydrologist: bool = False,
        skip_semanticist: bool = False,
        semanticist_max_modules: Optional[int] = None
    ) -> Tuple[Optional[nx.DiGraph], Optional[nx.DiGraph]]:
        """
        Run complete analysis pipeline on a repository.
        
        Args:
            repo_path: Path to repository to analyze
            skip_surveyor: Skip Surveyor phase (use existing module graph)
            skip_hydrologist: Skip Hydrologist phase
            skip_semanticist: Skip Semanticist phase
            semanticist_max_modules: Maximum modules for Semanticist (None = all)
            
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
        
        # Reset trace logger for this run
        self.trace_logger.clear()
        self.trace_logger.log_action(
            agent="surveyor",
            action="pipeline_start",
            evidence_source=str(repo_path),
            evidence_type="heuristic",
            confidence=1.0,
            resolution_status="resolved",
            details={"repo_path": str(repo_path), "output_dir": str(output_dir)}
        )
        
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
                
                self.trace_logger.log_action(
                    agent="surveyor",
                    action="analyze_repository:module_graph_built",
                    evidence_source=str(repo_path),
                    evidence_type="tree_sitter",
                    confidence=1.0,
                    resolution_status="resolved",
                    details={
                        "modules_analyzed": len(modules),
                        "graph_nodes": module_graph.number_of_nodes(),
                        "graph_edges": module_graph.number_of_edges(),
                        "parse_errors": len(self.surveyor.errors)
                    }
                )
                if self.surveyor.errors:
                    for err in self.surveyor.errors:
                        self.trace_logger.log_error(
                            agent="surveyor",
                            severity="warning",
                            message=f"Failed to parse {err['file']}: {err['error']}",
                            evidence_source=err['file'],
                            evidence_type="tree_sitter"
                        )
                
                # Serialize module graph
                module_graph_path = output_dir / 'module_graph.json'
                GraphSerializer.serialize_module_graph(module_graph, str(module_graph_path))
                print(f"  - Module graph saved: {module_graph_path}")
                
                # Save analysis report
                self._save_surveyor_report(output_dir, modules, module_graph)
                
            except Exception as e:
                error_msg = f"Surveyor failed: {str(e)}"
                self.errors.append(error_msg)
                self.trace_logger.log_error(
                    agent="surveyor", severity="error", message=error_msg,
                    evidence_source=str(repo_path), evidence_type="tree_sitter"
                )
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
                self.trace_logger.log_action(
                    agent="surveyor",
                    action="load_existing_module_graph",
                    evidence_source=str(module_graph_path),
                    evidence_type="heuristic",
                    confidence=1.0,
                    resolution_status="resolved",
                    details={"nodes": module_graph.number_of_nodes(), "edges": module_graph.number_of_edges()}
                )
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
                
                self.trace_logger.log_action(
                    agent="hydrologist",
                    action="analyze_repository:lineage_graph_built",
                    evidence_source=str(repo_path),
                    evidence_type="sqlglot",
                    confidence=0.9,
                    resolution_status="resolved",
                    details={
                        "datasets": len(datasets),
                        "transformations": len(transformations),
                        "graph_nodes": lineage_graph.number_of_nodes(),
                        "graph_edges": lineage_graph.number_of_edges(),
                        "parse_errors": len(self.hydrologist.errors)
                    }
                )
                if self.hydrologist.errors:
                    for err in self.hydrologist.errors:
                        self.trace_logger.log_error(
                            agent="hydrologist",
                            severity="warning",
                            message=f"Analysis error in {err.get('file', err.get('component', 'unknown'))}: {err['error']}",
                            evidence_source=err.get('file', err.get('component')),
                            evidence_type="sqlglot"
                        )
                
                # Serialize lineage graph
                lineage_graph_path = output_dir / 'lineage_graph.json'
                self.hydrologist.serialize_lineage_graph(lineage_graph, str(lineage_graph_path))
                print(f"  - Lineage graph saved: {lineage_graph_path}")
                
                # Save analysis report
                self._save_hydrologist_report(output_dir, datasets, transformations, lineage_graph)
                
            except Exception as e:
                error_msg = f"Hydrologist failed: {str(e)}"
                self.errors.append(error_msg)
                self.trace_logger.log_error(
                    agent="hydrologist", severity="error", message=error_msg,
                    evidence_source=str(repo_path), evidence_type="sqlglot"
                )
                print(f"✗ {error_msg}")
        else:
            print("\n[PHASE 2] Skipping Hydrologist")
        
        # Phase 3: Semanticist Agent
        if not skip_semanticist and module_graph is not None:
            print("\n[PHASE 3] Running Semanticist Agent...")
            print("Performing LLM-powered semantic analysis...")
            
            try:
                # Get modules from module graph
                modules = []
                for node_id in module_graph.nodes():
                    node_data = module_graph.nodes[node_id]
                    # Reconstruct ModuleNode from graph data
                    from models import ModuleNode, ProvenanceMetadata
                    
                    provenance_data = node_data.get('provenance', {})
                    provenance = ProvenanceMetadata(**provenance_data) if provenance_data else None
                    
                    if provenance:
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
                        )
                        modules.append(module)
                
                # Apply module limit if specified
                if semanticist_max_modules and len(modules) > semanticist_max_modules:
                    print(f"  ⚠ Large codebase detected: {len(modules)} modules")
                    print(f"  → Sampling {semanticist_max_modules} most important modules for analysis")
                    
                    # Sort by PageRank (if available) or complexity
                    modules_with_rank = []
                    for module in modules:
                        pagerank = module_graph.nodes[module.path].get('pagerank', 0)
                        modules_with_rank.append((module, pagerank, module.complexity_score))
                    
                    # Sort by PageRank desc, then complexity desc
                    modules_with_rank.sort(key=lambda x: (x[1], x[2]), reverse=True)
                    modules = [m[0] for m in modules_with_rank[:semanticist_max_modules]]
                    
                    print(f"  → Selected {len(modules)} modules (top by PageRank and complexity)")
                
                # Get datasets and transformations if lineage graph exists
                datasets = []
                transformations = []
                if lineage_graph is not None:
                    from models import DatasetNode, TransformationNode
                    
                    for node_id in lineage_graph.nodes():
                        node_data = lineage_graph.nodes[node_id]
                        node_type = node_data.get('node_type')
                        
                        if node_type == 'dataset':
                            provenance_data = node_data.get('provenance', {})
                            provenance = ProvenanceMetadata(**provenance_data) if provenance_data else None
                            
                            if provenance:
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
                            provenance_data = node_data.get('provenance', {})
                            provenance = ProvenanceMetadata(**provenance_data) if provenance_data else None
                            
                            if provenance:
                                transformation = TransformationNode(
                                    id=node_data['id'],
                                    source_datasets=node_data.get('source_datasets', []),
                                    target_datasets=node_data.get('target_datasets', []),
                                    transformation_type=node_data['transformation_type'],
                                    source_file=node_data['source_file'],
                                    line_range=tuple(node_data['line_range']),
                                    provenance=provenance,
                                    sql_query=node_data.get('sql_query'),
                                )
                                transformations.append(transformation)
                
                # Run semantic analysis
                enriched_modules, day_one_answers = self.semanticist.analyze_repository(
                    modules,
                    module_graph,
                    lineage_graph if lineage_graph is not None else nx.DiGraph(),
                    datasets,
                    transformations
                )
                
                print(f"✓ Semanticist complete:")
                print(f"  - Modules with purpose statements: {sum(1 for m in enriched_modules if m.purpose_statement)}")
                print(f"  - Modules with drift detected: {sum(1 for m in enriched_modules if m.has_documentation_drift)}")
                print(f"  - Domain clusters created: {len(set(m.domain_cluster for m in enriched_modules if m.domain_cluster))}")
                print(f"  - Day-One questions answered: {len(day_one_answers)}")
                
                self.trace_logger.log_action(
                    agent="semanticist",
                    action="analyze_repository:semantic_enrichment_complete",
                    evidence_source="module_graph + llm",
                    evidence_type="llm",
                    confidence=0.8,
                    resolution_status="inferred",
                    details={
                        "modules_with_purpose": sum(1 for m in enriched_modules if m.purpose_statement),
                        "modules_with_drift": sum(1 for m in enriched_modules if m.has_documentation_drift),
                        "domain_clusters": len(set(m.domain_cluster for m in enriched_modules if m.domain_cluster)),
                        "day_one_questions_answered": len(day_one_answers)
                    }
                )
                
                # Update module graph with enriched data
                for module in enriched_modules:
                    if module_graph.has_node(module.path):
                        module_graph.nodes[module.path]['purpose_statement'] = module.purpose_statement
                        module_graph.nodes[module.path]['domain_cluster'] = module.domain_cluster
                        module_graph.nodes[module.path]['has_documentation_drift'] = module.has_documentation_drift
                
                # Save updated module graph
                module_graph_path = output_dir / 'module_graph.json'
                GraphSerializer.serialize_module_graph(module_graph, str(module_graph_path))
                
                # Save analysis report
                self._save_semanticist_report(output_dir, enriched_modules, day_one_answers)
                
                # Save Day-One answers
                import json
                
                # Convert Pydantic models to dicts for JSON serialization
                def serialize_answer(obj):
                    """Recursively serialize Pydantic models and other objects."""
                    if hasattr(obj, 'model_dump'):
                        return obj.model_dump()
                    elif isinstance(obj, dict):
                        return {k: serialize_answer(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [serialize_answer(item) for item in obj]
                    else:
                        return obj
                
                serializable_answers = serialize_answer(day_one_answers)
                
                answers_path = output_dir / 'day_one_answers.json'
                with open(answers_path, 'w') as f:
                    json.dump(serializable_answers, f, indent=2)
                print(f"  - Day-One answers saved: {answers_path}")
                
            except Exception as e:
                error_msg = f"Semanticist failed: {str(e)}"
                self.errors.append(error_msg)
                self.trace_logger.log_error(
                    agent="semanticist", severity="error", message=error_msg,
                    evidence_source=str(repo_path), evidence_type="llm"
                )
                print(f"✗ {error_msg}")
                import traceback
                traceback.print_exc()
        else:
            if skip_semanticist:
                print("\n[PHASE 3] Skipping Semanticist")
            else:
                print("\n[PHASE 3] Skipping Semanticist (module graph not available)")
        
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
        
        # Flush trace log
        trace_path = output_dir / 'cartography_trace.jsonl'
        self.trace_logger.flush(output_path=trace_path)
        stats = self.trace_logger.get_statistics()
        print(f"\nTrace log: {trace_path} ({stats['total_entries']} entries)")
        
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
    
    def _save_semanticist_report(self, output_dir: Path, modules, day_one_answers) -> None:
        """Save Semanticist analysis report."""
        report_path = output_dir / 'semanticist_report.txt'
        
        with open(report_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("SEMANTICIST AGENT - ANALYSIS REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("SUMMARY\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total modules analyzed: {len(modules)}\n")
            
            modules_with_purpose = sum(1 for m in modules if m.purpose_statement)
            f.write(f"Modules with purpose statements: {modules_with_purpose}\n")
            
            modules_with_drift = sum(1 for m in modules if m.has_documentation_drift)
            f.write(f"Modules with documentation drift: {modules_with_drift}\n")
            
            domain_clusters = set(m.domain_cluster for m in modules if m.domain_cluster)
            f.write(f"Domain clusters identified: {len(domain_clusters)}\n\n")
            
            # Domain distribution
            if domain_clusters:
                f.write("DOMAIN DISTRIBUTION\n")
                f.write("-" * 80 + "\n")
                
                domain_counts = {}
                for module in modules:
                    if module.domain_cluster:
                        domain_counts[module.domain_cluster] = domain_counts.get(module.domain_cluster, 0) + 1
                
                for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"{domain}: {count} modules\n")
                f.write("\n")
            
            # Day-One Questions
            f.write("DAY-ONE QUESTIONS\n")
            f.write("-" * 80 + "\n\n")
            
            for key, answer_data in day_one_answers.items():
                question = answer_data.get('question', key)
                answer = answer_data.get('answer', 'No answer available')
                
                f.write(f"Q: {question}\n")
                f.write(f"A: {answer}\n\n")
            
            # Token usage
            if hasattr(self.semanticist, 'budget_tracker'):
                usage_summary = self.semanticist.budget_tracker.get_usage_summary()
                
                f.write("TOKEN USAGE\n")
                f.write("-" * 80 + "\n")
                
                if 'total' in usage_summary:
                    total = usage_summary['total']
                    f.write(f"Total tokens: {total.get('total_tokens', 0):,}\n")
                    f.write(f"Input tokens: {total.get('input_tokens', 0):,}\n")
                    f.write(f"Output tokens: {total.get('output_tokens', 0):,}\n")
                    f.write(f"Estimated cost: ${total.get('cost_usd', 0):.4f}\n\n")
            
            f.write("=" * 80 + "\n")
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
