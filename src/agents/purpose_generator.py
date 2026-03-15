"""Purpose statement generator using LLM for semantic understanding."""

import logging
import os
import time
from typing import List, Optional
from pathlib import Path

from models import ModuleNode, ProvenanceMetadata
from utils.llm_factory import get_llm, get_llm_config

logger = logging.getLogger(__name__)


class PurposeStatementGenerator:
    """Generates business-focused purpose statements for code modules using LLM."""
    
    # Modules that typically don't need purpose statements
    SKIP_PATTERNS = [
        "__init__.py",
        "conftest.py",
        "setup.py",
        "config.py",
        "constants.py",
        "__pycache__",
    ]
    
    def __init__(self, budget_tracker=None):
        """
        Initialize purpose statement generator.
        
        Args:
            budget_tracker: Optional ContextWindowBudget instance for tracking costs
        """
        self.budget_tracker = budget_tracker
        self.model = None
        self.llm_config = get_llm_config()
        
        # Initialize LLM using factory
        if self.llm_config["available"]:
            try:
                self.model = get_llm()
                logger.info(
                    f"Initialized LLM: {self.llm_config['provider']} "
                    f"with model {self.llm_config['model']}"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize LLM: {e}")
                logger.warning("Using placeholder purposes")
        else:
            logger.warning(
                f"LLM provider '{self.llm_config['provider']}' not available. "
                "Using placeholder purposes"
            )
    
    def generate_purpose(
        self,
        module: ModuleNode,
        source_code: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate 2-3 sentence purpose statement with provenance.
        
        Focuses on business function, not implementation details.
        
        Args:
            module: Module node to generate purpose for
            source_code: Optional source code content (if not provided, will read from file)
        
        Returns:
            Purpose statement string, or None if module should be skipped
        """
        # Check if module should be skipped
        if self._should_skip_module(module):
            logger.debug(f"Skipping purpose generation for {module.path}")
            return None
        
        # Read source code if not provided
        if source_code is None:
            try:
                with open(module.path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
            except Exception as e:
                logger.error(f"Failed to read {module.path}: {e}")
                return None
        
        # Generate purpose using LLM
        purpose = self._call_llm_for_purpose(module, source_code)
        
        if purpose:
            # Update module with purpose statement
            module.purpose_statement = purpose
            
            # Note: Provenance is tracked at the module level
            # The module already has provenance from static analysis
            # Purpose statement is LLM-inferred, so we don't override the base provenance
            # but the fact that purpose_statement is populated indicates LLM enrichment
            
            logger.info(f"Generated purpose for {module.path}")
        
        return purpose
    
    def batch_generate(
        self,
        modules: List[ModuleNode],
        batch_size: int = 10
    ) -> List[ModuleNode]:
        """
        Efficiently generate purposes for multiple modules in batches.
        
        Args:
            modules: List of module nodes
            batch_size: Number of modules to process in each batch
        
        Returns:
            List of modules with purpose statements added
        """
        logger.info(f"Batch generating purposes for {len(modules)} modules")
        
        enriched_modules = []
        total_batches = (len(modules) + batch_size - 1) // batch_size
        
        for i in range(0, len(modules), batch_size):
            batch = modules[i:i + batch_size]
            batch_num = i // batch_size + 1
            print(f"    • Processing batch {batch_num}/{total_batches} ({len(batch)} modules)...")
            logger.debug(f"Processing batch {batch_num}/{total_batches}")
            
            for module in batch:
                # Skip if already has a purpose statement (e.g. from previous run)
                if module.purpose_statement:
                    enriched_modules.append(module)
                    continue
                purpose = self.generate_purpose(module)
                if purpose:
                    module.purpose_statement = purpose
                enriched_modules.append(module)
        
        logger.info(
            f"Generated {sum(1 for m in enriched_modules if m.purpose_statement)} "
            f"purpose statements"
        )
        
        return enriched_modules
    
    def _should_skip_module(self, module: ModuleNode) -> bool:
        """
        Check if module should be skipped for purpose generation.
        
        Args:
            module: Module node to check
        
        Returns:
            True if module should be skipped
        """
        path = Path(module.path)
        
        # Check against skip patterns
        for pattern in self.SKIP_PATTERNS:
            if pattern in path.name:
                return True
        
        # Skip test files
        if path.name.startswith("test_") or "tests" in path.parts:
            return True
        
        # Skip very small files (likely config or constants)
        if module.complexity_score < 10:
            return True
        
        return False
    
    def _call_llm_for_purpose(
        self,
        module: ModuleNode,
        source_code: str
    ) -> Optional[str]:
        """
        Call LLM to generate purpose statement.
        
        Uses configured LLM provider (fast, cheap model preferred like Gemini Flash).
        
        Args:
            module: Module node
            source_code: Source code content
        
        Returns:
            Generated purpose statement with provenance tracking
        """
        # Prepare prompt
        prompt = self._build_purpose_prompt(module, source_code)
        
        # Track token usage
        if self.budget_tracker:
            input_tokens = self.budget_tracker.estimate_tokens(prompt)
        else:
            input_tokens = 0
        
        # Call LLM if available
        if self.model:
            try:
                # Use LangChain invoke method
                response = self.model.invoke(prompt)
                purpose = response.content.strip()
                
                # Track actual output tokens
                if self.budget_tracker:
                    output_tokens = self.budget_tracker.estimate_tokens(purpose)
                    model_name = self.budget_tracker.select_model("bulk")
                    self.budget_tracker.track_usage(model_name, input_tokens, output_tokens)
                
                # Default confidence for LLM-generated content
                confidence = 0.8
                
                return purpose
                
            except Exception as e:
                logger.error(f"LLM call failed for {module.path}: {e}")
                # Fall back to placeholder
                return self._generate_placeholder_purpose(module)
        else:
            # No LLM available, use placeholder
            if self.budget_tracker:
                # Still track estimated usage for budgeting
                estimated_output = 75
                model_name = self.budget_tracker.select_model("bulk")
                self.budget_tracker.track_usage(model_name, input_tokens, estimated_output)
            
            return self._generate_placeholder_purpose(module)
    
    def _build_purpose_prompt(self, module: ModuleNode, source_code: str) -> str:
        """
        Build prompt for LLM purpose generation.
        
        Args:
            module: Module node
            source_code: Source code content
        
        Returns:
            Formatted prompt string
        """
        # Truncate source code if too long (keep first 2000 chars)
        truncated_code = source_code[:2000]
        if len(source_code) > 2000:
            truncated_code += "\n... (truncated)"
        
        prompt = f"""Analyze this code module and provide a 2-3 sentence purpose statement.

CRITICAL: Ignore any docstrings or comments. Analyze the actual code implementation to determine what it does.
Focus on WHAT the module does from a business/functional perspective, not HOW it's implemented.

Module: {module.path}
Language: {module.language}
Exports: {', '.join(module.exports[:5]) if module.exports else 'None'}

Code:
```{module.language}
{truncated_code}
```

Provide a concise purpose statement (2-3 sentences) that describes:
1. The primary business function or responsibility (based on actual code, not docstrings)
2. Key capabilities or features (inferred from implementation)
3. How it fits into the larger system

Purpose statement:"""
        
        return prompt
    
    def _generate_placeholder_purpose(self, module: ModuleNode) -> str:
        """
        Generate placeholder purpose statement based on module metadata.
        
        This is used when LLM is not available. Should be replaced with actual LLM calls.
        
        Args:
            module: Module node
        
        Returns:
            Placeholder purpose statement
        """
        path = Path(module.path)
        name = path.stem
        
        # Generate basic purpose based on file name and exports
        if module.exports:
            exports_str = ", ".join(module.exports[:3])
            if len(module.exports) > 3:
                exports_str += f" and {len(module.exports) - 3} more"
            
            purpose = (
                f"This module provides {exports_str}. "
                f"It serves as a {name} component in the system. "
                f"The module contains {module.complexity_score} complexity units."
            )
        else:
            purpose = (
                f"This module implements {name} functionality. "
                f"It is a {module.language} module with {module.complexity_score} complexity units."
            )
        
        return purpose
