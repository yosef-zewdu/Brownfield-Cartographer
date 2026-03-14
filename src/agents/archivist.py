"""Archivist agent for generating living documentation artifacts."""

import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import networkx as nx
from datetime import datetime

from models import ModuleNode, DatasetNode, TransformationNode
from agents.onboarding_brief_generator import OnboardingBriefGenerator
from agents.trace_logger import CartographyTraceLogger
from analyzers.graph_serializer import GraphSerializer

logger = logging.getLogger(__name__)


class CODEBASEGenerator:
    """Generates CODEBASE.md living context file for AI coding agents."""
    
    def __init__(self):
        """Initialize CODEBASE generator."""
        pass
    
    def generate(
        self,
        modules: List[ModuleNode],
        module_graph: nx.DiGraph,
        lineage_graph: nx.DiGraph,
        datasets: List[DatasetNode],
        transformations: List[TransformationNode],
        pagerank_scores: Dict[str, float],
        circular_dependencies: List[List[str]],
        day_one_answers: Dict[str, any]
    ) -> str:
        """
        Generate complete CODEBASE.md document.
        
        Args:
            modules: List of all module nodes
            module_graph: Module dependency graph
            lineage_graph: Data lineage graph
            datasets: List of dataset nodes
            transformations: List of transformation nodes
            pagerank_scores: PageRank scores for modules
            circular_dependencies: List of circular dependency cycles
            day_one_answers: Answers to Day-One questions
        
        Returns:
            Complete CODEBASE.md content as string
        """
        logger.info("Generating CODEBASE.md")
        
        sections = []
        
        # Header
        sections.append("# CODEBASE.md - Living Context Document")
        sections.append("")
        sections.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sections.append("")
        sections.append("This document provides architectural awareness for AI coding agents.")
        sections.append("")
        
        # Architecture Overview
        sections.append(self.write_architecture_overview(
            modules, module_graph, lineage_graph, day_one_answers
        ))
        sections.append("")
        
        # Critical Path
        sections.append(self.write_critical_path(pagerank_scores, modules))
        sections.append("")
        
        # Data Sources & Sinks
        sections.append(self.write_data_sources_sinks(lineage_graph, datasets))
        sections.append("")
        
        # Known Debt
        sections.append(self.write_known_debt(circular_dependencies, modules))
        sections.append("")
        
        # High-Velocity Files
        sections.append(self.write_high_velocity_files(modules))
        sections.append("")
        
        # Module Purpose Index
        sections.append(self.write_module_purpose_index(modules))
        
        content = "\n".join(sections)
        logger.info("CODEBASE.md generation complete")
        
        return content

    
    def write_architecture_overview(
        self,
        modules: List[ModuleNode],
        module_graph: nx.DiGraph,
        lineage_graph: nx.DiGraph,
        day_one_answers: Dict[str, any]
    ) -> str:
        """
        Write 1-paragraph architecture overview.
        
        Args:
            modules: List of all modules
            module_graph: Module dependency graph
            lineage_graph: Data lineage graph
            day_one_answers: Day-One question answers for context
        
        Returns:
            Architecture Overview section as string
        """
        # Gather statistics
        module_count = len(modules)
        dataset_count = sum(1 for node in lineage_graph.nodes() 
                          if lineage_graph.nodes[node].get('node_type') == 'dataset')
        transformation_count = sum(1 for node in lineage_graph.nodes() 
                                  if lineage_graph.nodes[node].get('node_type') == 'transformation')
        
        # Get domain distribution
        domains = {}
        for module in modules:
            if module.domain_cluster:
                domains[module.domain_cluster] = domains.get(module.domain_cluster, 0) + 1
        
        domain_summary = ", ".join([f"{count} {domain}" for domain, count in 
                                   sorted(domains.items(), key=lambda x: x[1], reverse=True)[:3]])
        
        # Build overview paragraph
        overview = f"## Architecture Overview\n\n"
        overview += (
            f"This codebase contains {module_count} modules organized into "
            f"{len(domains)} semantic domains ({domain_summary}). "
            f"The data pipeline processes {dataset_count} datasets through "
            f"{transformation_count} transformations. "
        )
        
        # Add ingestion summary if available
        if 'ingestion_path' in day_one_answers and day_one_answers['ingestion_path']:
            ingestion_summary = day_one_answers['ingestion_path'].get('summary', '')
            if ingestion_summary:
                overview += f"{ingestion_summary} "
        
        # Add logic distribution summary if available
        if 'logic_distribution' in day_one_answers and day_one_answers['logic_distribution']:
            logic_summary = day_one_answers['logic_distribution'].get('summary', '')
            if logic_summary:
                overview += f"{logic_summary}"
        
        return overview
    
    def write_critical_path(
        self,
        pagerank_scores: Dict[str, float],
        modules: List[ModuleNode]
    ) -> str:
        """
        Write Critical Path section with top 5 modules by PageRank.
        
        Args:
            pagerank_scores: PageRank scores for all modules
            modules: List of all modules for metadata lookup
        
        Returns:
            Critical Path section as string
        """
        section = "## Critical Path\n\n"
        section += "The following modules are architectural hubs (highest PageRank scores):\n\n"
        
        # Sort by PageRank score
        sorted_modules = sorted(pagerank_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Create module lookup
        module_dict = {m.path: m for m in modules}
        
        for rank, (module_path, score) in enumerate(sorted_modules, 1):
            module = module_dict.get(module_path)
            
            section += f"{rank}. **{module_path}** (PageRank: {score:.4f})\n"
            
            if module and module.purpose_statement:
                section += f"   - {module.purpose_statement}\n"
            
            if module and module.domain_cluster:
                section += f"   - Domain: {module.domain_cluster}\n"
            
            section += "\n"
        
        return section
    
    def write_data_sources_sinks(
        self,
        lineage_graph: nx.DiGraph,
        datasets: List[DatasetNode]
    ) -> str:
        """
        Write Data Sources & Sinks section.
        
        Args:
            lineage_graph: Data lineage graph
            datasets: List of all dataset nodes
        
        Returns:
            Data Sources & Sinks section as string
        """
        section = "## Data Sources & Sinks\n\n"
        
        # Find sources (in-degree = 0)
        sources = [node for node in lineage_graph.nodes() 
                  if lineage_graph.in_degree(node) == 0 
                  and lineage_graph.nodes[node].get('node_type') == 'dataset']
        
        # Find sinks (out-degree = 0)
        sinks = [node for node in lineage_graph.nodes() 
                if lineage_graph.out_degree(node) == 0 
                and lineage_graph.nodes[node].get('node_type') == 'dataset']
        
        # Create dataset lookup
        dataset_dict = {d.name: d for d in datasets}
        
        # Write sources
        section += f"### Data Sources ({len(sources)})\n\n"
        if sources:
            for source in sorted(sources)[:10]:  # Limit to top 10
                dataset = dataset_dict.get(source)
                section += f"- **{source}**"
                
                if dataset:
                    section += f" ({dataset.storage_type})"
                    if dataset.discovered_in:
                        section += f" - discovered in `{dataset.discovered_in}`"
                
                section += "\n"
        else:
            section += "No data sources identified.\n"
        
        section += "\n"
        
        # Write sinks
        section += f"### Data Sinks ({len(sinks)})\n\n"
        if sinks:
            for sink in sorted(sinks)[:10]:  # Limit to top 10
                dataset = dataset_dict.get(sink)
                section += f"- **{sink}**"
                
                if dataset:
                    section += f" ({dataset.storage_type})"
                    if dataset.discovered_in:
                        section += f" - discovered in `{dataset.discovered_in}`"
                
                section += "\n"
        else:
            section += "No data sinks identified.\n"
        
        return section

    
    def write_known_debt(
        self,
        circular_dependencies: List[List[str]],
        modules: List[ModuleNode]
    ) -> str:
        """
        Write Known Debt section with circular dependencies and drift flags.
        
        Args:
            circular_dependencies: List of circular dependency cycles
            modules: List of all modules
        
        Returns:
            Known Debt section as string
        """
        section = "## Known Debt\n\n"
        
        # Circular dependencies
        section += f"### Circular Dependencies ({len(circular_dependencies)})\n\n"
        if circular_dependencies:
            for idx, cycle in enumerate(circular_dependencies[:10], 1):  # Limit to top 10
                section += f"{idx}. Cycle of {len(cycle)} modules:\n"
                for module in cycle:
                    section += f"   - `{module}`\n"
                section += "\n"
        else:
            section += "No circular dependencies detected. ✓\n\n"
        
        # Documentation drift
        drift_modules = [m for m in modules if m.has_documentation_drift]
        section += f"### Documentation Drift ({len(drift_modules)})\n\n"
        
        if drift_modules:
            section += "The following modules have docstrings that contradict their implementation:\n\n"
            for module in sorted(drift_modules, key=lambda m: m.path)[:10]:  # Limit to top 10
                section += f"- **{module.path}**\n"
                if module.docstring:
                    # Show first line of docstring
                    first_line = module.docstring.split('\n')[0].strip()
                    section += f"  - Docstring: \"{first_line[:80]}...\"\n"
                if module.purpose_statement:
                    section += f"  - Actual purpose: {module.purpose_statement[:100]}...\n"
                section += "\n"
        else:
            section += "No documentation drift detected. ✓\n"
        
        return section
    
    def write_high_velocity_files(
        self,
        modules: List[ModuleNode]
    ) -> str:
        """
        Write High-Velocity Files section with change velocity data.
        
        Args:
            modules: List of all modules
        
        Returns:
            High-Velocity Files section as string
        """
        section = "## High-Velocity Files\n\n"
        section += "Files with the most frequent changes (potential pain points):\n\n"
        
        # Filter modules with change velocity data
        modules_with_velocity = [m for m in modules if m.change_velocity is not None and m.change_velocity > 0]
        
        if not modules_with_velocity:
            section += "No git history available or no changes detected.\n"
            return section
        
        # Sort by change velocity
        sorted_modules = sorted(modules_with_velocity, key=lambda m: m.change_velocity, reverse=True)[:10]
        
        for rank, module in enumerate(sorted_modules, 1):
            section += f"{rank}. **{module.path}** ({module.change_velocity} commits)\n"
            
            if module.purpose_statement:
                section += f"   - {module.purpose_statement}\n"
            
            if module.domain_cluster:
                section += f"   - Domain: {module.domain_cluster}\n"
            
            section += "\n"
        
        return section
    
    def write_module_purpose_index(
        self,
        modules: List[ModuleNode]
    ) -> str:
        """
        Write Module Purpose Index with all purpose statements.
        
        Args:
            modules: List of all modules
        
        Returns:
            Module Purpose Index section as string
        """
        section = "## Module Purpose Index\n\n"
        section += "Complete index of all modules with their purpose statements:\n\n"
        
        # Group modules by domain cluster
        domains = {}
        for module in modules:
            domain = module.domain_cluster or "Uncategorized"
            if domain not in domains:
                domains[domain] = []
            domains[domain].append(module)
        
        # Sort domains by size
        sorted_domains = sorted(domains.items(), key=lambda x: len(x[1]), reverse=True)
        
        for domain, domain_modules in sorted_domains:
            section += f"### {domain} ({len(domain_modules)} modules)\n\n"
            
            # Sort modules within domain by path
            for module in sorted(domain_modules, key=lambda m: m.path):
                section += f"- **{module.path}**"
                
                if module.language:
                    section += f" ({module.language})"
                
                section += "\n"
                
                if module.purpose_statement:
                    section += f"  - {module.purpose_statement}\n"
                else:
                    section += f"  - _No purpose statement available_\n"
                
                # Add metadata
                metadata = []
                if module.complexity_score:
                    metadata.append(f"complexity: {module.complexity_score}")
                if module.change_velocity:
                    metadata.append(f"changes: {module.change_velocity}")
                if module.is_dead_code_candidate:
                    metadata.append("⚠️ dead code candidate")
                if module.has_documentation_drift:
                    metadata.append("⚠️ documentation drift")
                
                if metadata:
                    section += f"  - {', '.join(metadata)}\n"
                
                section += "\n"
        
        return section



class ArchivistAgent:
    """
    Archivist Agent orchestrator for generating all living documentation artifacts.
    
    Coordinates:
    - CODEBASE.md generation (living context for AI agents)
    - onboarding_brief.md generation (Day-One questions)
    - Graph serialization (module_graph.json, lineage_graph.json)
    - Trace log writing (cartography_trace.jsonl)
    
    All artifacts are written to .cartography/ directory.
    """
    
    def __init__(self, output_dir: Path):
        """
        Initialize ArchivistAgent.
        
        Args:
            output_dir: Base output directory (typically .cartography/)
        """
        self.output_dir = Path(output_dir)
        self.codebase_generator = CODEBASEGenerator()
        self.onboarding_generator = OnboardingBriefGenerator()
        self.graph_serializer = GraphSerializer()
        
        logger.info(f"ArchivistAgent initialized with output directory: {self.output_dir}")
    
    def generate_artifacts(
        self,
        modules: List[ModuleNode],
        datasets: List[DatasetNode],
        transformations: List[TransformationNode],
        module_graph: nx.DiGraph,
        lineage_graph: nx.DiGraph,
        pagerank_scores: Dict[str, float],
        circular_dependencies: List[List[str]],
        day_one_answers: Dict[str, Dict[str, any]],
        analysis_metadata: Dict[str, any],
        trace_logger: CartographyTraceLogger
    ) -> Dict[str, Path]:
        """
        Generate all artifacts and write to output directory.
        
        Args:
            modules: List of all module nodes
            datasets: List of all dataset nodes
            transformations: List of all transformation nodes
            module_graph: Module dependency graph
            lineage_graph: Data lineage graph
            pagerank_scores: PageRank scores for modules
            circular_dependencies: List of circular dependency cycles
            day_one_answers: Answers to Day-One questions
            analysis_metadata: Metadata about the analysis run
            trace_logger: CartographyTraceLogger instance with accumulated logs
        
        Returns:
            Dictionary mapping artifact names to their file paths
        """
        logger.info("Starting artifact generation")
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        trace_logger.log_action(
            agent="archivist",
            action="start_artifact_generation",
            evidence_source=f"{len(modules)} modules, {len(datasets)} datasets, {len(transformations)} transformations",
            evidence_type="heuristic",
            confidence=1.0,
            resolution_status="resolved",
            details={"module_count": len(modules), "dataset_count": len(datasets), "transformation_count": len(transformations)}
        )
        
        artifact_paths = {}
        
        # Generate CODEBASE.md
        codebase_path = self.generate_codebase_md(
            modules=modules,
            datasets=datasets,
            transformations=transformations,
            module_graph=module_graph,
            lineage_graph=lineage_graph,
            pagerank_scores=pagerank_scores,
            circular_dependencies=circular_dependencies,
            day_one_answers=day_one_answers,
            trace_logger=trace_logger
        )
        artifact_paths['codebase_md'] = codebase_path
        
        # Generate onboarding_brief.md
        onboarding_path = self.generate_onboarding_brief(
            day_one_answers=day_one_answers,
            analysis_metadata=analysis_metadata,
            trace_logger=trace_logger
        )
        artifact_paths['onboarding_brief'] = onboarding_path
        
        # Serialize graphs
        graph_paths = self.serialize_graphs(
            module_graph=module_graph,
            lineage_graph=lineage_graph,
            trace_logger=trace_logger
        )
        artifact_paths.update(graph_paths)
        
        # Write trace log (flush after all other actions are recorded)
        trace_path = self.write_trace_log(trace_logger)
        artifact_paths['trace_log'] = trace_path
        
        logger.info(f"Artifact generation complete. Generated {len(artifact_paths)} artifacts.")
        
        return artifact_paths
    
    def generate_codebase_md(
        self,
        modules: List[ModuleNode],
        datasets: List[DatasetNode],
        transformations: List[TransformationNode],
        module_graph: nx.DiGraph,
        lineage_graph: nx.DiGraph,
        pagerank_scores: Dict[str, float],
        circular_dependencies: List[List[str]],
        day_one_answers: Dict[str, Dict[str, any]],
        trace_logger: Optional[CartographyTraceLogger] = None
    ) -> Path:
        """
        Generate CODEBASE.md living context document.
        
        Args:
            modules: List of all module nodes
            datasets: List of all dataset nodes
            transformations: List of all transformation nodes
            module_graph: Module dependency graph
            lineage_graph: Data lineage graph
            pagerank_scores: PageRank scores for modules
            circular_dependencies: List of circular dependency cycles
            day_one_answers: Answers to Day-One questions
            trace_logger: Optional trace logger for audit trail
        
        Returns:
            Path to generated CODEBASE.md file
        """
        logger.info("Generating CODEBASE.md")
        
        sections_to_log = [
            ("architecture_overview", "module_graph + lineage_graph + day_one_answers", "heuristic", 0.9),
            ("critical_path", "module_graph pagerank scores", "heuristic", 1.0),
            ("data_sources_sinks", "lineage_graph in/out-degree analysis", "heuristic", 1.0),
            ("known_debt", "circular_dependencies + documentation_drift flags", "heuristic", 1.0),
            ("high_velocity_files", "git_velocity_analyzer", "heuristic", 1.0),
            ("module_purpose_index", "semanticist purpose_statements + domain_clusters", "llm", 0.8),
        ]
        
        # Generate content
        content = self.codebase_generator.generate(
            modules=modules,
            module_graph=module_graph,
            lineage_graph=lineage_graph,
            datasets=datasets,
            transformations=transformations,
            pagerank_scores=pagerank_scores,
            circular_dependencies=circular_dependencies,
            day_one_answers=day_one_answers
        )
        
        # Log each section written
        if trace_logger:
            for section, source, ev_type, confidence in sections_to_log:
                trace_logger.log_action(
                    agent="archivist",
                    action=f"write_codebase_md_section:{section}",
                    evidence_source=source,
                    evidence_type=ev_type,
                    confidence=confidence,
                    resolution_status="resolved",
                )
        
        # Write to file
        output_path = self.output_dir / "CODEBASE.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        if trace_logger:
            trace_logger.log_action(
                agent="archivist",
                action="write_file:CODEBASE.md",
                evidence_source=str(output_path),
                evidence_type="heuristic",
                confidence=1.0,
                resolution_status="resolved",
                details={"size_bytes": output_path.stat().st_size, "sections": len(sections_to_log)}
            )
        
        logger.info(f"CODEBASE.md written to {output_path}")
        return output_path
    
    def generate_onboarding_brief(
        self,
        day_one_answers: Dict[str, Dict[str, any]],
        analysis_metadata: Dict[str, any],
        trace_logger: Optional[CartographyTraceLogger] = None
    ) -> Path:
        """
        Generate onboarding_brief.md with Day-One question answers.
        
        Args:
            day_one_answers: Answers to Day-One questions
            analysis_metadata: Metadata about the analysis run
            trace_logger: Optional trace logger for audit trail
        
        Returns:
            Path to generated onboarding_brief.md file
        """
        logger.info("Generating onboarding_brief.md")
        
        question_map = {
            'ingestion_path':    ("Q1: Where does data come from?",        "lineage_graph sources",              "heuristic", 0.8),
            'critical_outputs':  ("Q2: What are the critical outputs?",     "lineage_graph sinks + pagerank",     "heuristic", 0.85),
            'blast_radius':      ("Q3: What breaks if X changes?",          "lineage_graph blast radius BFS",     "heuristic", 0.9),
            'logic_distribution':("Q4: Where does business logic live?",    "semanticist domain_clusters",        "llm",       0.75),
            'change_velocity':   ("Q5: What changes most often?",           "git_velocity_analyzer pareto",       "heuristic", 0.8),
        }
        
        # Log each question being answered
        if trace_logger:
            for key, (action, source, ev_type, confidence) in question_map.items():
                if key in day_one_answers:
                    trace_logger.log_action(
                        agent="archivist",
                        action=f"write_onboarding_brief_section:{action}",
                        evidence_source=source,
                        evidence_type=ev_type,
                        confidence=confidence,
                        resolution_status="inferred" if ev_type == "llm" else "resolved",
                    )
        
        # Generate content
        content = self.onboarding_generator.generate(
            day_one_answers=day_one_answers,
            analysis_metadata=analysis_metadata
        )
        
        # Write to file
        output_path = self.output_dir / "onboarding_brief.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        if trace_logger:
            trace_logger.log_action(
                agent="archivist",
                action="write_file:onboarding_brief.md",
                evidence_source=str(output_path),
                evidence_type="heuristic",
                confidence=1.0,
                resolution_status="resolved",
                details={"questions_answered": len(day_one_answers), "size_bytes": output_path.stat().st_size}
            )
        
        logger.info(f"onboarding_brief.md written to {output_path}")
        return output_path
    
    def serialize_graphs(
        self,
        module_graph: nx.DiGraph,
        lineage_graph: nx.DiGraph,
        trace_logger: Optional[CartographyTraceLogger] = None
    ) -> Dict[str, Path]:
        """
        Serialize module and lineage graphs to JSON files.
        
        Args:
            module_graph: Module dependency graph
            lineage_graph: Data lineage graph
            trace_logger: Optional trace logger for audit trail
        
        Returns:
            Dictionary mapping graph names to their file paths
        """
        logger.info("Serializing graphs to JSON")
        
        graph_paths = {}
        
        # Serialize module graph
        module_graph_path = self.output_dir / "module_graph.json"
        self.graph_serializer.serialize_module_graph(
            graph=module_graph,
            output_path=str(module_graph_path)
        )
        graph_paths['module_graph'] = module_graph_path
        if trace_logger:
            trace_logger.log_action(
                agent="archivist",
                action="serialize_graph:module_graph.json",
                evidence_source="surveyor module_graph",
                evidence_type="tree_sitter",
                confidence=1.0,
                resolution_status="resolved",
                details={"nodes": module_graph.number_of_nodes(), "edges": module_graph.number_of_edges()}
            )
        logger.info(f"module_graph.json written to {module_graph_path}")
        
        # Serialize lineage graph
        lineage_graph_path = self.output_dir / "lineage_graph.json"
        self.graph_serializer.serialize_lineage_graph(
            graph=lineage_graph,
            output_path=str(lineage_graph_path)
        )
        graph_paths['lineage_graph'] = lineage_graph_path
        if trace_logger:
            trace_logger.log_action(
                agent="archivist",
                action="serialize_graph:lineage_graph.json",
                evidence_source="hydrologist lineage_graph",
                evidence_type="sqlglot",
                confidence=1.0,
                resolution_status="resolved",
                details={"nodes": lineage_graph.number_of_nodes(), "edges": lineage_graph.number_of_edges()}
            )
        logger.info(f"lineage_graph.json written to {lineage_graph_path}")
        
        return graph_paths
    
    def write_trace_log(
        self,
        trace_logger: CartographyTraceLogger
    ) -> Path:
        """
        Write cartography trace log to JSONL file.
        
        Args:
            trace_logger: CartographyTraceLogger instance with accumulated logs
        
        Returns:
            Path to written cartography_trace.jsonl file
        """
        logger.info("Writing cartography trace log")
        
        # Write trace log
        trace_path = self.output_dir / "cartography_trace.jsonl"
        trace_logger.flush(output_path=trace_path)
        
        # Log statistics
        stats = trace_logger.get_statistics()
        logger.info(
            f"Trace log written: {stats['total_entries']} entries, "
            f"{stats['total_llm_tokens']} LLM tokens, "
            f"avg confidence: {stats['average_confidence']:.2f}"
        )
        
        return trace_path
