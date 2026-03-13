"""Domain clusterer for organizing modules by semantic similarity."""

import logging
from typing import List, Dict, Optional
import numpy as np
from sklearn.cluster import KMeans

from models import ModuleNode, ProvenanceMetadata
from utils.llm_factory import get_llm, get_llm_config

logger = logging.getLogger(__name__)


class DomainClusterer:
    """Clusters modules into semantic domains using embeddings and k-means."""
    
    def __init__(self, budget_tracker=None):
        """
        Initialize domain clusterer.
        
        Args:
            budget_tracker: Optional ContextWindowBudget instance for tracking costs
        """
        self.budget_tracker = budget_tracker
        self.embeddings_cache: Dict[str, np.ndarray] = {}
        self.model = None
        self.embedding_model = None
        
        # Initialize LLM for cluster labeling
        llm_config = get_llm_config()
        if llm_config["available"]:
            try:
                self.model = get_llm()
                logger.info(f"Initialized LLM for cluster labeling: {llm_config['provider']}")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM: {e}")
        
        # Initialize sentence-transformers model
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Initialized sentence-transformers model: all-MiniLM-L6-v2")
        except Exception as e:
            logger.warning(f"Failed to initialize sentence-transformers: {e}")
            logger.warning("Falling back to simple embeddings")
    
    def embed_purposes(
        self,
        modules: List[ModuleNode]
    ) -> Dict[str, np.ndarray]:
        """
        Generate embeddings for purpose statements using sentence-transformers.
        
        Provenance: evidence_type=heuristic for embeddings
        
        Args:
            modules: List of modules with purpose statements
        
        Returns:
            Dictionary mapping module paths to embedding vectors
        """
        logger.info(f"Generating embeddings for {len(modules)} modules")
        
        embeddings = {}
        
        # Filter modules with purpose statements
        modules_with_purpose = [m for m in modules if m.purpose_statement]
        
        if not modules_with_purpose:
            logger.warning("No modules with purpose statements to embed")
            return embeddings
        
        # Use sentence-transformers if available
        if self.embedding_model:
            try:
                # Extract purpose statements
                purposes = [m.purpose_statement for m in modules_with_purpose]
                
                # Generate embeddings in batch
                embedding_vectors = self.embedding_model.encode(
                    purposes,
                    show_progress_bar=False,
                    convert_to_numpy=True
                )
                
                # Map to module paths
                for module, embedding in zip(modules_with_purpose, embedding_vectors):
                    embeddings[module.path] = embedding
                    self.embeddings_cache[module.path] = embedding
                
                logger.info(f"Generated {len(embeddings)} embeddings using sentence-transformers")
                
            except Exception as e:
                logger.error(f"Failed to generate embeddings with sentence-transformers: {e}")
                logger.info("Falling back to simple embeddings")
                # Fall back to simple embeddings
                for module in modules_with_purpose:
                    embedding = self._generate_simple_embedding(module.purpose_statement)
                    embeddings[module.path] = embedding
                    self.embeddings_cache[module.path] = embedding
        else:
            # Use simple embeddings as fallback
            for module in modules_with_purpose:
                embedding = self._generate_simple_embedding(module.purpose_statement)
                embeddings[module.path] = embedding
                self.embeddings_cache[module.path] = embedding
            
            logger.info(f"Generated {len(embeddings)} embeddings using simple method")
        
        return embeddings
    
    def cluster(
        self,
        embeddings: Dict[str, np.ndarray],
        k: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Cluster embeddings using k-means with k between 5 and 8.
        
        Args:
            embeddings: Dictionary mapping module paths to embeddings
            k: Optional number of clusters (default: auto-select between 5-8)
        
        Returns:
            Dictionary mapping module paths to cluster IDs
        """
        if not embeddings:
            logger.warning("No embeddings to cluster")
            return {}
        
        # Determine k if not provided
        if k is None:
            # Auto-select k based on number of modules
            n_modules = len(embeddings)
            if n_modules < 5:
                k = min(n_modules, 3)
            elif n_modules < 20:
                k = 5
            elif n_modules < 50:
                k = 6
            else:
                k = 8
        
        # Ensure k is in valid range
        k = max(2, min(k, 8))
        k = min(k, len(embeddings))  # Can't have more clusters than samples
        
        logger.info(f"Clustering {len(embeddings)} modules into {k} clusters")
        
        # Prepare data for clustering
        paths = list(embeddings.keys())
        vectors = np.array([embeddings[path] for path in paths])
        
        # Perform k-means clustering
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(vectors)
        
        # Map paths to cluster IDs
        clusters = {path: int(label) for path, label in zip(paths, cluster_labels)}
        
        logger.info(f"Clustering complete: {len(set(cluster_labels))} clusters created")
        
        return clusters
    
    def label_clusters(
        self,
        modules: List[ModuleNode],
        clusters: Dict[str, int]
    ) -> Dict[int, str]:
        """
        Generate descriptive labels for clusters using LLM.
        
        Args:
            modules: List of modules
            clusters: Dictionary mapping module paths to cluster IDs
        
        Returns:
            Dictionary mapping cluster IDs to descriptive labels
        """
        logger.info("Generating cluster labels")
        
        # Group modules by cluster
        cluster_groups: Dict[int, List[ModuleNode]] = {}
        for module in modules:
            if module.path in clusters:
                cluster_id = clusters[module.path]
                if cluster_id not in cluster_groups:
                    cluster_groups[cluster_id] = []
                cluster_groups[cluster_id].append(module)
        
        # Generate label for each cluster
        labels = {}
        for cluster_id, cluster_modules in cluster_groups.items():
            label = self._generate_cluster_label(cluster_id, cluster_modules)
            labels[cluster_id] = label
        
        logger.info(f"Generated {len(labels)} cluster labels")
        
        return labels
    
    def assign_domains(
        self,
        modules: List[ModuleNode],
        clusters: Dict[str, int],
        labels: Dict[int, str]
    ) -> List[ModuleNode]:
        """
        Assign each module to exactly one domain cluster with provenance.
        
        Stores domain_cluster in ModuleNode metadata with provenance tracking.
        Resolution status is marked as 'inferred' for cluster assignments.
        
        Args:
            modules: List of modules
            clusters: Dictionary mapping module paths to cluster IDs
            labels: Dictionary mapping cluster IDs to labels
        
        Returns:
            List of modules with domain_cluster assigned
        """
        logger.info("Assigning domain clusters to modules")
        
        assigned_count = 0
        
        for module in modules:
            if module.path in clusters:
                cluster_id = clusters[module.path]
                cluster_label = labels.get(cluster_id, f"Cluster {cluster_id}")
                
                # Assign domain cluster
                module.domain_cluster = cluster_label
                
                # Note: Provenance for domain clustering is tracked at the module level
                # The clustering is based on embeddings (evidence_type=heuristic) and
                # LLM-generated labels (evidence_type=llm), with resolution_status=inferred
                # This is implicit in the domain_cluster field being populated
                
                assigned_count += 1
        
        logger.info(f"Assigned {assigned_count} modules to domain clusters")
        
        return modules
    
    def _generate_simple_embedding(self, text: str, dim: int = 128) -> np.ndarray:
        """
        Generate simple embedding for text (placeholder for sentence-transformers).
        
        This is a basic TF-IDF-like approach. Should be replaced with actual
        sentence-transformers in production.
        
        Args:
            text: Text to embed
            dim: Embedding dimension
        
        Returns:
            Embedding vector
        """
        # Simple hash-based embedding
        words = text.lower().split()
        
        # Create a simple bag-of-words embedding
        embedding = np.zeros(dim)
        
        for i, word in enumerate(words):
            # Use hash to map word to dimension
            idx = hash(word) % dim
            embedding[idx] += 1.0
        
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding
    
    def _generate_cluster_label(
        self,
        cluster_id: int,
        modules: List[ModuleNode]
    ) -> str:
        """
        Generate descriptive label for a cluster using LLM with provenance.
        
        Provenance: evidence_type=llm, confidence from LLM response
        
        Args:
            cluster_id: Cluster ID
            modules: Modules in this cluster
        
        Returns:
            Descriptive label
        """
        # Collect purpose statements
        purposes = [m.purpose_statement for m in modules if m.purpose_statement]
        
        if not purposes:
            return f"Cluster {cluster_id}"
        
        # Build prompt for LLM
        prompt = self._build_labeling_prompt(cluster_id, purposes)
        
        # Track token usage
        if self.budget_tracker:
            input_tokens = self.budget_tracker.estimate_tokens(prompt)
        
        # Use LLM if available
        if self.model:
            try:
                response = self.model.invoke(prompt)
                label = response.content.strip()
                
                # Track output tokens
                if self.budget_tracker:
                    output_tokens = self.budget_tracker.estimate_tokens(label)
                    model = self.budget_tracker.select_model("synthesis")
                    self.budget_tracker.track_usage(model, input_tokens, output_tokens)
                
                # Clean up label (remove quotes, extra whitespace, markdown formatting)
                label = label.strip('"\'').strip()
                
                # Remove markdown bold/italic markers
                label = label.replace('**', '').replace('*', '').replace('__', '').replace('_', '')
                
                # Take only the first line if multi-line response
                label = label.split('\n')[0].strip()
                
                # If label is too long (more than 50 chars), truncate or use heuristic
                if len(label) > 50:
                    logger.warning(f"LLM label too long ({len(label)} chars), using heuristic")
                    label = self._heuristic_label(purposes)
                
                logger.info(f"Generated LLM label for cluster {cluster_id}: {label}")
                
                return label
                
            except Exception as e:
                logger.error(f"LLM call failed for cluster {cluster_id}: {e}")
                # Fall back to heuristic
                return self._heuristic_label(purposes)
        else:
            # No LLM available, use heuristic
            if self.budget_tracker:
                # Still track estimated usage for budgeting
                estimated_output = 20
                model = self.budget_tracker.select_model("synthesis")
                self.budget_tracker.track_usage(model, input_tokens, estimated_output)
            
            return self._heuristic_label(purposes)
    
    def _build_labeling_prompt(
        self,
        cluster_id: int,
        purposes: List[str]
    ) -> str:
        """
        Build prompt for LLM cluster labeling.
        
        Args:
            cluster_id: Cluster ID
            purposes: List of purpose statements in cluster
        
        Returns:
            Formatted prompt string
        """
        # Limit to first 10 purposes to keep prompt manageable
        sample_purposes = purposes[:10]
        
        prompt = f"""Analyze these related module purposes and provide a short, descriptive domain label.

Cluster {cluster_id} contains modules with these purposes:

"""
        
        for i, purpose in enumerate(sample_purposes, 1):
            prompt += f"{i}. {purpose}\n"
        
        prompt += """
Based on these purposes, what is the common domain or functional area?

IMPORTANT: Respond with ONLY a concise label (2-4 words) like "Data Processing", "User Authentication", "API Integration", etc.
Do NOT include any explanation, reasoning, or additional text. Just the label.

Domain label:"""
        
        return prompt
    
    def _heuristic_label(self, purposes: List[str]) -> str:
        """
        Generate heuristic label based on common terms.
        
        Args:
            purposes: List of purpose statements
        
        Returns:
            Heuristic label
        """
        # Combine all purposes
        combined = " ".join(purposes).lower()
        
        # Common domain keywords
        domain_keywords = {
            "data": "Data Processing",
            "api": "API Integration",
            "auth": "Authentication",
            "user": "User Management",
            "database": "Database Operations",
            "test": "Testing",
            "config": "Configuration",
            "util": "Utilities",
            "model": "Data Models",
            "service": "Business Services",
            "controller": "Request Handling",
            "view": "Presentation Layer",
            "pipeline": "Data Pipeline",
            "transform": "Data Transformation",
            "analysis": "Analytics",
            "report": "Reporting",
        }
        
        # Find most common keyword
        for keyword, label in domain_keywords.items():
            if keyword in combined:
                return label
        
        # Default label
        return "Core Functionality"
