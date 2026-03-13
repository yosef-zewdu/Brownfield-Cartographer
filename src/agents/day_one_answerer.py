"""Day-One Question Answerer for synthesizing insights from repository analysis."""

import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import networkx as nx

from models import ModuleNode, DatasetNode, TransformationNode, ProvenanceMetadata
from utils.llm_factory import get_llm, get_llm_config

logger = logging.getLogger(__name__)


class DayOneQuestionAnswerer:
    """
    Answers the Five FDE Day-One Questions with evidence citations and provenance tracking.
    
    The Five Day-One Questions:
    1. Where does data come from? (Ingestion Path)
    2. What are the critical outputs? (Critical Outputs)
    3. What happens if X breaks? (Blast Radius)
    4. Where does business logic Y live? (Logic Distribution)
    5. What changes most often? (Change Velocity)
    """
    
    def __init__(self, budget_tracker=None):
        """
        Initialize Day-One Question Answerer.
        
        Args:
            budget_tracker: Optional ContextWindowBudget instance for tracking costs
        """
        self.budget_tracker = budget_tracker
        self.model = None
        self.llm_config = get_llm_config()
        
        # Initialize LLM for synthesis (use capable model like GPT-4/Claude)
        if self.llm_config["available"]:
            try:
                self.model = get_llm()
                logger.info(
                    f"Initialized LLM for Day-One synthesis: {self.llm_config['provider']} "
                    f"with model {self.llm_config['model']}"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize LLM: {e}")
                logger.warning("Day-One answers will use heuristics only")
        else:
            logger.warning(
                f"LLM provider '{self.llm_config['provider']}' not available. "
                "Day-One answers will use heuristics only"
            )
    
    def answer_ingestion_path(
        self,
        lineage_graph: nx.DiGraph,
        datasets: List[DatasetNode],
        transformations: List[TransformationNode]
    ) -> Dict[str, Any]:
        """
        Answer: Where does data come from?
        
        Identifies data sources (nodes with in-degree zero) and traces ingestion paths.
        Provides file and line citations with provenance tracking.
        
        Args:
            lineage_graph: Data lineage graph from Hydrologist
            datasets: List of dataset nodes
            transformations: List of transformation nodes
        
        Returns:
            Dictionary with:
                - answer: str - synthesized answer
                - evidence: List[Dict] - evidence with file:line citations
                - provenance: ProvenanceMetadata - tracking for this answer
        """
        logger.info("Answering: Where does data come from?")
        
        # Find source nodes (in-degree zero)
        sources = []
        for node in lineage_graph.nodes():
            if lineage_graph.in_degree(node) == 0:
                node_data = lineage_graph.nodes[node]
                if node_data.get('node_type') == 'dataset':
                    sources.append(node)
        
        # Collect evidence with file and line citations
        evidence = []
        for source_name in sources:
            # Find the dataset node
            dataset = next((ds for ds in datasets if ds.name == source_name), None)
            if dataset:
                evidence.append({
                    'type': 'data_source',
                    'name': source_name,
                    'storage_type': dataset.storage_type,
                    'file': dataset.discovered_in,
                    'line_range': dataset.provenance.line_range if dataset.provenance else None,
                    'confidence': dataset.provenance.confidence if dataset.provenance else 0.5,
                    'evidence_type': dataset.provenance.evidence_type if dataset.provenance else 'heuristic'
                })
        
        # Find transformations that read from these sources
        ingestion_transformations = []
        for transformation in transformations:
            if any(source in transformation.source_datasets for source in sources):
                ingestion_transformations.append({
                    'id': transformation.id,
                    'type': transformation.transformation_type,
                    'file': transformation.source_file,
                    'line_range': transformation.line_range,
                    'sources': [s for s in transformation.source_datasets if s in sources],
                    'confidence': transformation.provenance.confidence,
                    'evidence_type': transformation.provenance.evidence_type
                })
                evidence.append({
                    'type': 'ingestion_transformation',
                    'transformation_id': transformation.id,
                    'transformation_type': transformation.transformation_type,
                    'file': transformation.source_file,
                    'line_range': transformation.line_range,
                    'sources': [s for s in transformation.source_datasets if s in sources],
                    'confidence': transformation.provenance.confidence,
                    'evidence_type': transformation.provenance.evidence_type
                })
        
        # Synthesize answer with LLM
        answer = self.synthesize_with_llm(
            question="Where does data come from?",
            evidence=evidence,
            context={
                'num_sources': len(sources),
                'num_ingestion_points': len(ingestion_transformations)
            }
        )
        
        # Create provenance for this answer
        provenance = ProvenanceMetadata(
            evidence_type="heuristic",  # Base evidence is heuristic (graph analysis)
            source_file="lineage_graph",
            confidence=0.8 if evidence else 0.3,
            resolution_status="resolved" if evidence else "inferred"
        )
        
        return {
            'answer': answer,
            'evidence': evidence,
            'provenance': provenance
        }

    def answer_critical_outputs(
        self,
        lineage_graph: nx.DiGraph,
        module_graph: nx.DiGraph,
        datasets: List[DatasetNode],
        modules: List[ModuleNode]
    ) -> Dict[str, Any]:
        """
        Answer: What are the critical outputs?
        
        Uses PageRank and sink analysis to identify critical outputs.
        Provides file and line citations with provenance tracking.
        
        Args:
            lineage_graph: Data lineage graph from Hydrologist
            module_graph: Module dependency graph from Surveyor
            datasets: List of dataset nodes
            modules: List of module nodes
        
        Returns:
            Dictionary with:
                - answer: str - synthesized answer
                - evidence: List[Dict] - evidence with file:line citations
                - provenance: ProvenanceMetadata - tracking for this answer
        """
        logger.info("Answering: What are the critical outputs?")
        
        # Find sink nodes (out-degree zero) in lineage graph
        sinks = []
        for node in lineage_graph.nodes():
            if lineage_graph.out_degree(node) == 0:
                node_data = lineage_graph.nodes[node]
                if node_data.get('node_type') == 'dataset':
                    sinks.append(node)
        
        # Compute PageRank on module graph to find architectural hubs
        pagerank_scores = {}
        if len(module_graph.nodes) > 0:
            try:
                pagerank_scores = nx.pagerank(module_graph, weight='import_count')
            except:
                pagerank_scores = nx.pagerank(module_graph)
        
        # Get top 5 modules by PageRank
        top_modules = sorted(
            pagerank_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Collect evidence
        evidence = []
        
        # Evidence from sink datasets
        for sink_name in sinks:
            dataset = next((ds for ds in datasets if ds.name == sink_name), None)
            if dataset:
                evidence.append({
                    'type': 'critical_output_dataset',
                    'name': sink_name,
                    'storage_type': dataset.storage_type,
                    'file': dataset.discovered_in,
                    'line_range': dataset.provenance.line_range if dataset.provenance else None,
                    'confidence': dataset.provenance.confidence if dataset.provenance else 0.5,
                    'evidence_type': dataset.provenance.evidence_type if dataset.provenance else 'heuristic'
                })
        
        # Evidence from high PageRank modules
        for module_path, pagerank_score in top_modules:
            module = next((m for m in modules if m.path == module_path), None)
            if module:
                evidence.append({
                    'type': 'critical_module',
                    'path': module_path,
                    'pagerank': pagerank_score,
                    'file': module_path,
                    'line_range': None,
                    'exports': module.exports[:5],  # Top 5 exports
                    'confidence': 0.9,  # High confidence from PageRank
                    'evidence_type': 'heuristic'
                })
        
        # Synthesize answer with LLM
        answer = self.synthesize_with_llm(
            question="What are the critical outputs?",
            evidence=evidence,
            context={
                'num_sinks': len(sinks),
                'num_critical_modules': len(top_modules)
            }
        )
        
        # Create provenance for this answer
        provenance = ProvenanceMetadata(
            evidence_type="heuristic",  # PageRank and graph analysis
            source_file="module_graph,lineage_graph",
            confidence=0.85 if evidence else 0.3,
            resolution_status="resolved" if evidence else "inferred"
        )
        
        return {
            'answer': answer,
            'evidence': evidence,
            'provenance': provenance
        }
    
    def answer_blast_radius(
        self,
        lineage_graph: nx.DiGraph,
        module_graph: nx.DiGraph,
        target_node: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer: What happens if X breaks?
        
        Uses dependency graph to compute blast radius for a given node.
        Provides file and line citations with provenance tracking.
        
        Args:
            lineage_graph: Data lineage graph from Hydrologist
            module_graph: Module dependency graph from Surveyor
            target_node: Optional specific node to analyze (if None, analyzes top critical nodes)
        
        Returns:
            Dictionary with:
                - answer: str - synthesized answer
                - evidence: List[Dict] - evidence with file:line citations
                - provenance: ProvenanceMetadata - tracking for this answer
        """
        logger.info(f"Answering: What happens if {target_node or 'critical nodes'} break?")
        
        evidence = []
        
        # If no target specified, analyze top PageRank modules
        if target_node is None:
            pagerank_scores = {}
            if len(module_graph.nodes) > 0:
                try:
                    pagerank_scores = nx.pagerank(module_graph, weight='import_count')
                except:
                    pagerank_scores = nx.pagerank(module_graph)
            
            # Get top 3 modules by PageRank
            top_modules = sorted(
                pagerank_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            # Compute blast radius for each
            for module_path, pagerank_score in top_modules:
                if module_graph.has_node(module_path):
                    try:
                        descendants = nx.descendants(module_graph, module_path)
                        evidence.append({
                            'type': 'module_blast_radius',
                            'node': module_path,
                            'pagerank': pagerank_score,
                            'affected_modules': len(descendants),
                            'affected_list': list(descendants)[:10],  # Top 10 affected
                            'file': module_path,
                            'confidence': 0.9,
                            'evidence_type': 'heuristic'
                        })
                    except nx.NetworkXError as e:
                        logger.warning(f"Failed to compute descendants for {module_path}: {e}")
        else:
            # Analyze specific target node
            # Check both graphs
            for graph, graph_name in [(module_graph, 'module'), (lineage_graph, 'lineage')]:
                if graph.has_node(target_node):
                    try:
                        descendants = nx.descendants(graph, target_node)
                        evidence.append({
                            'type': f'{graph_name}_blast_radius',
                            'node': target_node,
                            'affected_count': len(descendants),
                            'affected_list': list(descendants)[:10],  # Top 10 affected
                            'file': target_node,
                            'confidence': 0.95,
                            'evidence_type': 'heuristic'
                        })
                    except nx.NetworkXError as e:
                        logger.warning(f"Failed to compute descendants for {target_node} in {graph_name} graph: {e}")
        
        # Synthesize answer with LLM
        answer = self.synthesize_with_llm(
            question=f"What happens if {target_node or 'critical components'} break?",
            evidence=evidence,
            context={
                'target_node': target_node,
                'num_analyses': len(evidence)
            }
        )
        
        # Create provenance for this answer
        provenance = ProvenanceMetadata(
            evidence_type="heuristic",  # Graph traversal
            source_file="module_graph,lineage_graph",
            confidence=0.9 if evidence else 0.3,
            resolution_status="resolved" if evidence else "inferred"
        )
        
        return {
            'answer': answer,
            'evidence': evidence,
            'provenance': provenance
        }

    def answer_logic_distribution(
        self,
        modules: List[ModuleNode],
        business_logic_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer: Where does business logic Y live?
        
        Uses domain clustering to organize modules semantically.
        Provides file and line citations with provenance tracking.
        
        Args:
            modules: List of module nodes with domain clusters assigned
            business_logic_query: Optional specific business logic to search for
        
        Returns:
            Dictionary with:
                - answer: str - synthesized answer
                - evidence: List[Dict] - evidence with file:line citations
                - provenance: ProvenanceMetadata - tracking for this answer
        """
        logger.info(f"Answering: Where does business logic {business_logic_query or 'live'}?")
        
        # Group modules by domain cluster
        domain_groups: Dict[str, List[ModuleNode]] = {}
        for module in modules:
            if module.domain_cluster:
                if module.domain_cluster not in domain_groups:
                    domain_groups[module.domain_cluster] = []
                domain_groups[module.domain_cluster].append(module)
        
        # Collect evidence
        evidence = []
        
        if business_logic_query:
            # Search for specific business logic
            query_lower = business_logic_query.lower()
            
            # Search in purpose statements
            for module in modules:
                if module.purpose_statement and query_lower in module.purpose_statement.lower():
                    evidence.append({
                        'type': 'matching_module',
                        'path': module.path,
                        'purpose': module.purpose_statement,
                        'domain_cluster': module.domain_cluster,
                        'file': module.path,
                        'line_range': None,
                        'confidence': 0.8,
                        'evidence_type': 'llm'  # Purpose statements are LLM-generated
                    })
            
            # Search in exports
            for module in modules:
                for export in module.exports:
                    if query_lower in export.lower():
                        evidence.append({
                            'type': 'matching_export',
                            'path': module.path,
                            'export': export,
                            'domain_cluster': module.domain_cluster,
                            'file': module.path,
                            'line_range': None,
                            'confidence': 0.7,
                            'evidence_type': 'tree_sitter'
                        })
        else:
            # Provide overview of logic distribution by domain
            for domain, domain_modules in domain_groups.items():
                # Get representative modules (top 5 by complexity)
                top_modules = sorted(
                    domain_modules,
                    key=lambda m: m.complexity_score,
                    reverse=True
                )[:5]
                
                evidence.append({
                    'type': 'domain_cluster',
                    'domain': domain,
                    'module_count': len(domain_modules),
                    'representative_modules': [
                        {
                            'path': m.path,
                            'purpose': m.purpose_statement,
                            'complexity': m.complexity_score
                        }
                        for m in top_modules
                    ],
                    'confidence': 0.75,
                    'evidence_type': 'heuristic'  # Clustering is heuristic
                })
        
        # Synthesize answer with LLM
        answer = self.synthesize_with_llm(
            question=f"Where does business logic {business_logic_query or ''} live?",
            evidence=evidence,
            context={
                'query': business_logic_query,
                'num_domains': len(domain_groups),
                'total_modules': len(modules)
            }
        )
        
        # Create provenance for this answer
        provenance = ProvenanceMetadata(
            evidence_type="heuristic",  # Domain clustering
            source_file="module_graph",
            confidence=0.75 if evidence else 0.3,
            resolution_status="inferred"  # Clustering is inferred
        )
        
        return {
            'answer': answer,
            'evidence': evidence,
            'provenance': provenance
        }
    
    def answer_change_velocity(
        self,
        modules: List[ModuleNode],
        top_n: int = 10
    ) -> Dict[str, Any]:
        """
        Answer: What changes most often?
        
        Uses git velocity evidence to identify high-change files.
        Provides file and line citations with provenance tracking.
        
        Args:
            modules: List of module nodes with change velocity data
            top_n: Number of top changing files to report
        
        Returns:
            Dictionary with:
                - answer: str - synthesized answer
                - evidence: List[Dict] - evidence with file:line citations
                - provenance: ProvenanceMetadata - tracking for this answer
        """
        logger.info("Answering: What changes most often?")
        
        # Filter modules with velocity data
        modules_with_velocity = [
            m for m in modules
            if m.change_velocity_30d is not None and m.change_velocity_30d > 0
        ]
        
        # Sort by velocity
        high_velocity_modules = sorted(
            modules_with_velocity,
            key=lambda m: m.change_velocity_30d,
            reverse=True
        )[:top_n]
        
        # Collect evidence
        evidence = []
        for module in high_velocity_modules:
            evidence.append({
                'type': 'high_velocity_module',
                'path': module.path,
                'change_velocity': module.change_velocity_30d,
                'purpose': module.purpose_statement,
                'domain_cluster': module.domain_cluster,
                'file': module.path,
                'line_range': None,
                'confidence': 1.0,  # Git data is highly reliable
                'evidence_type': 'heuristic'  # Git log analysis
            })
        
        # Compute Pareto analysis (80/20 rule)
        if modules_with_velocity:
            total_changes = sum(m.change_velocity_30d for m in modules_with_velocity)
            cumulative_changes = 0
            pareto_threshold = 0.8 * total_changes
            pareto_files = []
            
            for module in high_velocity_modules:
                cumulative_changes += module.change_velocity_30d
                pareto_files.append(module.path)
                if cumulative_changes >= pareto_threshold:
                    break
            
            evidence.append({
                'type': 'pareto_analysis',
                'pareto_files': pareto_files,
                'pareto_percentage': len(pareto_files) / len(modules_with_velocity) * 100,
                'total_changes': total_changes,
                'confidence': 1.0,
                'evidence_type': 'heuristic'
            })
        
        # Synthesize answer with LLM
        answer = self.synthesize_with_llm(
            question="What changes most often?",
            evidence=evidence,
            context={
                'top_n': top_n,
                'total_modules_with_velocity': len(modules_with_velocity)
            }
        )
        
        # Create provenance for this answer
        provenance = ProvenanceMetadata(
            evidence_type="heuristic",  # Git velocity analysis
            source_file="git_log",
            confidence=1.0 if evidence else 0.3,
            resolution_status="resolved"  # Git data is direct evidence
        )
        
        return {
            'answer': answer,
            'evidence': evidence,
            'provenance': provenance
        }

    def synthesize_with_llm(
        self,
        question: str,
        evidence: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> str:
        """
        Synthesize answer using capable LLM model (GPT-4/Claude) with provenance.
        
        Provenance: evidence_type=llm, confidence from model response
        
        Args:
            question: The Day-One question being answered
            evidence: List of evidence dictionaries with file:line citations
            context: Additional context for synthesis
        
        Returns:
            Synthesized answer string with evidence citations
        """
        # Build prompt with evidence
        prompt = self._build_synthesis_prompt(question, evidence, context)
        
        # Track token usage
        if self.budget_tracker:
            input_tokens = self.budget_tracker.estimate_tokens(prompt)
        else:
            input_tokens = 0
        
        # Use LLM if available
        if self.model:
            try:
                response = self.model.invoke(prompt)
                answer = response.content.strip()
                
                # Track output tokens
                if self.budget_tracker:
                    output_tokens = self.budget_tracker.estimate_tokens(answer)
                    model = self.budget_tracker.select_model("synthesis")
                    self.budget_tracker.track_usage(model, input_tokens, output_tokens)
                
                logger.info(f"Synthesized answer for: {question}")
                return answer
                
            except Exception as e:
                logger.error(f"LLM synthesis failed for '{question}': {e}")
                # Fall back to heuristic answer
                return self._generate_heuristic_answer(question, evidence, context)
        else:
            # No LLM available, use heuristic
            if self.budget_tracker:
                # Still track estimated usage for budgeting
                estimated_output = 200
                model = self.budget_tracker.select_model("synthesis")
                self.budget_tracker.track_usage(model, input_tokens, estimated_output)
            
            return self._generate_heuristic_answer(question, evidence, context)
    
    def _build_synthesis_prompt(
        self,
        question: str,
        evidence: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> str:
        """
        Build prompt for LLM synthesis.
        
        Args:
            question: The Day-One question
            evidence: List of evidence dictionaries
            context: Additional context
        
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are analyzing a codebase to answer Day-One questions for new developers.

Question: {question}

Context:
"""
        
        # Add context information
        for key, value in context.items():
            prompt += f"- {key}: {value}\n"
        
        prompt += "\nEvidence:\n"
        
        # Add evidence with citations
        for i, ev in enumerate(evidence, 1):
            prompt += f"\n{i}. "
            
            if ev.get('type') == 'data_source':
                prompt += f"Data Source: {ev['name']} ({ev['storage_type']})\n"
                prompt += f"   File: {ev['file']}"
                if ev.get('line_range'):
                    prompt += f" (lines {ev['line_range'][0]}-{ev['line_range'][1]})"
                prompt += f"\n   Confidence: {ev['confidence']:.2f}\n"
            
            elif ev.get('type') == 'ingestion_transformation':
                prompt += f"Ingestion: {ev['transformation_type']} transformation\n"
                prompt += f"   File: {ev['file']} (lines {ev['line_range'][0]}-{ev['line_range'][1]})\n"
                prompt += f"   Sources: {', '.join(ev['sources'])}\n"
                prompt += f"   Confidence: {ev['confidence']:.2f}\n"
            
            elif ev.get('type') == 'critical_output_dataset':
                prompt += f"Critical Output: {ev['name']} ({ev['storage_type']})\n"
                prompt += f"   File: {ev['file']}"
                if ev.get('line_range'):
                    prompt += f" (lines {ev['line_range'][0]}-{ev['line_range'][1]})"
                prompt += f"\n   Confidence: {ev['confidence']:.2f}\n"
            
            elif ev.get('type') == 'critical_module':
                prompt += f"Critical Module: {ev['path']}\n"
                prompt += f"   PageRank: {ev['pagerank']:.4f}\n"
                prompt += f"   Key Exports: {', '.join(ev['exports'])}\n"
            
            elif ev.get('type') in ['module_blast_radius', 'lineage_blast_radius']:
                prompt += f"Blast Radius for {ev['node']}:\n"
                prompt += f"   Affected: {ev.get('affected_count', ev.get('affected_modules', 0))} components\n"
                if ev.get('affected_list'):
                    prompt += f"   Examples: {', '.join(ev['affected_list'][:5])}\n"
            
            elif ev.get('type') == 'matching_module':
                prompt += f"Matching Module: {ev['path']}\n"
                prompt += f"   Purpose: {ev['purpose']}\n"
                prompt += f"   Domain: {ev.get('domain_cluster', 'Unknown')}\n"
            
            elif ev.get('type') == 'domain_cluster':
                prompt += f"Domain: {ev['domain']}\n"
                prompt += f"   Modules: {ev['module_count']}\n"
                if ev.get('representative_modules'):
                    prompt += f"   Key Modules:\n"
                    for mod in ev['representative_modules'][:3]:
                        prompt += f"     - {mod['path']}: {mod.get('purpose', 'N/A')}\n"
            
            elif ev.get('type') == 'high_velocity_module':
                prompt += f"High Change File: {ev['path']}\n"
                prompt += f"   Changes: {ev['change_velocity']} commits\n"
                if ev.get('purpose'):
                    prompt += f"   Purpose: {ev['purpose']}\n"
            
            elif ev.get('type') == 'pareto_analysis':
                prompt += f"Pareto Analysis:\n"
                prompt += f"   {ev['pareto_percentage']:.1f}% of files account for 80% of changes\n"
                prompt += f"   High-change files: {', '.join(ev['pareto_files'][:5])}\n"
        
        prompt += """
Based on the evidence above, provide a clear, concise answer to the question.

IMPORTANT:
- Cite specific files and line numbers from the evidence
- Use the format: `file.py:10-20` for citations
- Keep the answer focused and actionable for new developers
- Highlight the most critical information first
- If confidence is low, acknowledge uncertainty

Answer:"""
        
        return prompt
    
    def _generate_heuristic_answer(
        self,
        question: str,
        evidence: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> str:
        """
        Generate heuristic answer when LLM is not available.
        
        Args:
            question: The Day-One question
            evidence: List of evidence dictionaries
            context: Additional context
        
        Returns:
            Heuristic answer string
        """
        if not evidence:
            return f"Unable to answer '{question}' - insufficient evidence collected."
        
        # Build answer based on question type
        if "data come from" in question.lower():
            sources = [ev for ev in evidence if ev.get('type') == 'data_source']
            if sources:
                answer = f"Data comes from {len(sources)} primary sources:\n"
                for source in sources[:5]:
                    answer += f"- {source['name']} ({source['storage_type']}) in {source['file']}\n"
                return answer
        
        elif "critical outputs" in question.lower():
            outputs = [ev for ev in evidence if ev.get('type') == 'critical_output_dataset']
            modules = [ev for ev in evidence if ev.get('type') == 'critical_module']
            answer = f"Critical outputs include {len(outputs)} datasets and {len(modules)} key modules:\n"
            for output in outputs[:3]:
                answer += f"- {output['name']} in {output['file']}\n"
            for module in modules[:3]:
                answer += f"- {module['path']} (PageRank: {module['pagerank']:.4f})\n"
            return answer
        
        elif "break" in question.lower():
            blast_radii = [ev for ev in evidence if 'blast_radius' in ev.get('type', '')]
            if blast_radii:
                answer = "Breaking critical components would affect:\n"
                for br in blast_radii[:3]:
                    affected = br.get('affected_count', br.get('affected_modules', 0))
                    answer += f"- {br['node']}: {affected} downstream components\n"
                return answer
        
        elif "logic" in question.lower():
            domains = [ev for ev in evidence if ev.get('type') == 'domain_cluster']
            matches = [ev for ev in evidence if ev.get('type') == 'matching_module']
            if matches:
                answer = f"Found {len(matches)} modules matching the query:\n"
                for match in matches[:5]:
                    answer += f"- {match['path']}: {match.get('purpose', 'N/A')}\n"
                return answer
            elif domains:
                answer = f"Business logic is distributed across {len(domains)} domains:\n"
                for domain in domains[:5]:
                    answer += f"- {domain['domain']}: {domain['module_count']} modules\n"
                return answer
        
        elif "changes" in question.lower():
            high_velocity = [ev for ev in evidence if ev.get('type') == 'high_velocity_module']
            if high_velocity:
                answer = f"Top {len(high_velocity)} most frequently changed files:\n"
                for hv in high_velocity:
                    answer += f"- {hv['path']}: {hv['change_velocity']} commits\n"
                return answer
        
        return f"Analysis complete for '{question}' with {len(evidence)} pieces of evidence."
    
    def answer_all_questions(
        self,
        module_graph: nx.DiGraph,
        lineage_graph: nx.DiGraph,
        modules: List[ModuleNode],
        datasets: List[DatasetNode],
        transformations: List[TransformationNode]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Answer all five Day-One questions.
        
        Args:
            module_graph: Module dependency graph from Surveyor
            lineage_graph: Data lineage graph from Hydrologist
            modules: List of module nodes
            datasets: List of dataset nodes
            transformations: List of transformation nodes
        
        Returns:
            Dictionary mapping question names to answer dictionaries
        """
        logger.info("Answering all five Day-One questions")
        
        answers = {}
        
        # Question 1: Where does data come from?
        try:
            answers['ingestion_path'] = self.answer_ingestion_path(
                lineage_graph, datasets, transformations
            )
        except Exception as e:
            logger.error(f"Failed to answer ingestion_path: {e}")
            answers['ingestion_path'] = {
                'answer': f"Error: {e}",
                'evidence': [],
                'provenance': ProvenanceMetadata(
                    evidence_type="heuristic",
                    source_file="error",
                    confidence=0.0,
                    resolution_status="inferred"
                )
            }
        
        # Question 2: What are the critical outputs?
        try:
            answers['critical_outputs'] = self.answer_critical_outputs(
                lineage_graph, module_graph, datasets, modules
            )
        except Exception as e:
            logger.error(f"Failed to answer critical_outputs: {e}")
            answers['critical_outputs'] = {
                'answer': f"Error: {e}",
                'evidence': [],
                'provenance': ProvenanceMetadata(
                    evidence_type="heuristic",
                    source_file="error",
                    confidence=0.0,
                    resolution_status="inferred"
                )
            }
        
        # Question 3: What happens if X breaks?
        try:
            answers['blast_radius'] = self.answer_blast_radius(
                lineage_graph, module_graph
            )
        except Exception as e:
            logger.error(f"Failed to answer blast_radius: {e}")
            answers['blast_radius'] = {
                'answer': f"Error: {e}",
                'evidence': [],
                'provenance': ProvenanceMetadata(
                    evidence_type="heuristic",
                    source_file="error",
                    confidence=0.0,
                    resolution_status="inferred"
                )
            }
        
        # Question 4: Where does business logic Y live?
        try:
            answers['logic_distribution'] = self.answer_logic_distribution(modules)
        except Exception as e:
            logger.error(f"Failed to answer logic_distribution: {e}")
            answers['logic_distribution'] = {
                'answer': f"Error: {e}",
                'evidence': [],
                'provenance': ProvenanceMetadata(
                    evidence_type="heuristic",
                    source_file="error",
                    confidence=0.0,
                    resolution_status="inferred"
                )
            }
        
        # Question 5: What changes most often?
        try:
            answers['change_velocity'] = self.answer_change_velocity(modules)
        except Exception as e:
            logger.error(f"Failed to answer change_velocity: {e}")
            answers['change_velocity'] = {
                'answer': f"Error: {e}",
                'evidence': [],
                'provenance': ProvenanceMetadata(
                    evidence_type="heuristic",
                    source_file="error",
                    confidence=0.0,
                    resolution_status="inferred"
                )
            }
        
        logger.info("Completed answering all Day-One questions")
        
        return answers
