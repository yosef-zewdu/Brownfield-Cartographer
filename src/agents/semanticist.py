"""Semanticist agent for LLM-powered semantic analysis."""

import logging
import time
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import networkx as nx

from models import ModuleNode, DatasetNode, TransformationNode
from agents.context_budget import ContextWindowBudget
from agents.purpose_generator import PurposeStatementGenerator
from agents.drift_detector import DocumentationDriftDetector
from agents.domain_clusterer import DomainClusterer
from agents.day_one_answerer import DayOneQuestionAnswerer

logger = logging.getLogger(__name__)


class SemanticistAgent:
    """Orchestrates LLM-powered semantic analysis of the codebase."""
    
    def __init__(self):
        """Initialize semanticist agent with all components."""
        self.budget_tracker = ContextWindowBudget()
        self.purpose_generator = PurposeStatementGenerator(self.budget_tracker)
        self.drift_detector = DocumentationDriftDetector(self.budget_tracker)
        self.domain_clusterer = DomainClusterer(self.budget_tracker)
        self.question_answerer = DayOneQuestionAnswerer(self.budget_tracker)
        self.errors: List[Dict[str, str]] = []
    
    def analyze_repository(
        self,
        modules: List[ModuleNode],
        module_graph: nx.DiGraph,
        lineage_graph: nx.DiGraph,
        datasets: List[DatasetNode],
        transformations: List[TransformationNode]
    ) -> Tuple[List[ModuleNode], Dict[str, any]]:
        """
        Coordinate all semantic analysis.
        
        Args:
            modules: List of module nodes from Surveyor
            module_graph: Module dependency graph
            lineage_graph: Data lineage graph
            datasets: List of dataset nodes
            transformations: List of transformation nodes
        
        Returns:
            Tuple of (enriched modules, day-one answers)
        """
        logger.info("Starting semantic analysis")
        
        # Phase 1: Generate purpose statements
        modules = self.enrich_modules_with_purpose(modules)
        
        # Phase 2: Detect documentation drift
        modules = self.detect_all_drift(modules)
        
        # Phase 3: Cluster into domains
        modules = self.cluster_domains(modules)
        
        # Phase 4: Answer Day-One questions
        day_one_answers = self.answer_day_one_questions(
            modules,
            module_graph,
            lineage_graph,
            datasets,
            transformations
        )
        
        # Log usage summary
        usage_summary = self.budget_tracker.get_usage_summary()
        logger.info(f"Semantic analysis complete. Token usage: {usage_summary}")
        
        return modules, day_one_answers
    
    def enrich_modules_with_purpose(
        self,
        modules: List[ModuleNode]
    ) -> List[ModuleNode]:
        """
        Add purpose statements to modules.
        
        Args:
            modules: List of module nodes
        
        Returns:
            List of modules with purpose statements
        """
        print(f"  → Generating purpose statements for {len(modules)} modules...")
        logger.info(f"Generating purpose statements for {len(modules)} modules")
        
        try:
            modules = self.purpose_generator.batch_generate(modules, batch_size=10)
        except Exception as e:
            logger.error(f"Failed to generate purpose statements: {e}")
            self.errors.append({
                'component': 'purpose_generator',
                'error': str(e),
                'phase': 'purpose_generation'
            })
            # Continue with analysis even if purpose generation fails
        
        purpose_count = sum(1 for m in modules if m.purpose_statement)
        print(f"  ✓ Generated {purpose_count} purpose statements")
        logger.info(f"Generated {purpose_count} purpose statements")
        
        return modules
    
    def detect_all_drift(
        self,
        modules: List[ModuleNode]
    ) -> List[ModuleNode]:
        """
        Find documentation drift across all modules.
        
        Args:
            modules: List of modules with purpose statements
        
        Returns:
            List of modules with drift flags
        """
        print(f"  → Detecting documentation drift...")
        logger.info("Detecting documentation drift")
        
        try:
            modules = self.drift_detector.detect_all_drift(modules)
        except Exception as e:
            logger.error(f"Failed to detect drift: {e}")
            self.errors.append({
                'component': 'drift_detector',
                'error': str(e),
                'phase': 'drift_detection'
            })
            # Continue with analysis
        
        drift_count = sum(1 for m in modules if m.has_documentation_drift)
        print(f"  ✓ Found {drift_count} modules with documentation drift")
        logger.info(f"Found {drift_count} modules with documentation drift")
        
        return modules
    
    def cluster_domains(
        self,
        modules: List[ModuleNode]
    ) -> List[ModuleNode]:
        """
        Organize modules semantically into domain clusters.
        
        Args:
            modules: List of modules with purpose statements
        
        Returns:
            List of modules with domain clusters assigned
        """
        print(f"  → Clustering modules into semantic domains...")
        logger.info("Clustering modules into semantic domains")
        
        try:
            # Generate embeddings
            embeddings = self.domain_clusterer.embed_purposes(modules)
            
            if not embeddings:
                logger.warning("No embeddings generated, skipping clustering")
                return modules
            
            # Cluster embeddings
            clusters = self.domain_clusterer.cluster(embeddings)
            
            # Generate cluster labels
            labels = self.domain_clusterer.label_clusters(modules, clusters)
            
            # Assign domains to modules
            modules = self.domain_clusterer.assign_domains(modules, clusters, labels)
            
        except Exception as e:
            logger.error(f"Failed to cluster domains: {e}")
            self.errors.append({
                'component': 'domain_clusterer',
                'error': str(e),
                'phase': 'domain_clustering'
            })
            # Continue with analysis
        
        clustered_count = sum(1 for m in modules if m.domain_cluster)
        cluster_count = len(set(m.domain_cluster for m in modules if m.domain_cluster))
        print(f"  ✓ Assigned {clustered_count} modules to {cluster_count} domain clusters")
        logger.info(f"Assigned {clustered_count} modules to domain clusters")
        
        return modules
    
    def answer_day_one_questions(
        self,
        modules: List[ModuleNode],
        module_graph: nx.DiGraph,
        lineage_graph: nx.DiGraph,
        datasets: List[DatasetNode],
        transformations: List[TransformationNode]
    ) -> Dict[str, any]:
        """
        Synthesize insights by answering Day-One questions.
        
        Args:
            modules: List of enriched modules
            module_graph: Module dependency graph
            lineage_graph: Data lineage graph
            datasets: List of dataset nodes
            transformations: List of transformation nodes
        
        Returns:
            Dictionary with answers to all five questions
        """
        print(f"  → Answering Day-One questions...")
        logger.info("Answering Day-One questions")
        
        answers = {}
        
        try:
            # Question 1: Where does data enter?
            print(f"    • Question 1/5: Primary ingestion path...")
            answers['ingestion_path'] = self._retry_with_backoff(
                lambda: self.question_answerer.answer_ingestion_path(
                    lineage_graph, datasets, transformations
                )
            )
            
            # Question 2: What are critical outputs?
            print(f"    • Question 2/5: Critical outputs...")
            answers['critical_outputs'] = self._retry_with_backoff(
                lambda: self.question_answerer.answer_critical_outputs(
                    lineage_graph, module_graph, datasets, modules
                )
            )
            
            # Question 3: What is blast radius?
            print(f"    • Question 3/5: Blast radius...")
            answers['blast_radius'] = self._retry_with_backoff(
                lambda: self.question_answerer.answer_blast_radius(
                    lineage_graph, module_graph
                )
            )
            
            # Question 4: How is logic distributed?
            print(f"    • Question 4/5: Logic distribution...")
            answers['logic_distribution'] = self._retry_with_backoff(
                lambda: self.question_answerer.answer_logic_distribution(modules)
            )
            
            # Question 5: Where is code changing?
            print(f"    • Question 5/5: Change velocity...")
            answers['change_velocity'] = self._retry_with_backoff(
                lambda: self.question_answerer.answer_change_velocity(modules)
            )
            
        except Exception as e:
            logger.error(f"Failed to answer Day-One questions: {e}")
            self.errors.append({
                'component': 'question_answerer',
                'error': str(e),
                'phase': 'question_answering'
            })
        
        print(f"  ✓ Answered {len(answers)} Day-One questions")
        logger.info("Day-One questions answered")
        
        return answers
    
    def _retry_with_backoff(
        self,
        func,
        max_retries: int = 3,
        initial_delay: float = 1.0
    ) -> any:
        """
        Retry function with exponential backoff for LLM API calls.
        
        Args:
            func: Function to retry
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
        
        Returns:
            Function result
        
        Raises:
            Exception: If all retries fail
        """
        delay = initial_delay
        
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if attempt == max_retries - 1:
                    # Last attempt, re-raise
                    raise
                
                logger.warning(
                    f"Attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                
                time.sleep(delay)
                delay *= 2  # Exponential backoff
        
        # Should not reach here
        raise Exception("Max retries exceeded")
    
    def get_analysis_summary(self) -> Dict[str, any]:
        """
        Get summary of semantic analysis.
        
        Returns:
            Dictionary with analysis statistics
        """
        usage_summary = self.budget_tracker.get_usage_summary()
        
        return {
            'token_usage': usage_summary,
            'errors': self.errors,
            'error_count': len(self.errors),
        }
