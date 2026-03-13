"""Documentation drift detector using LLM to compare docstrings with actual purpose."""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

from models import ModuleNode, ProvenanceMetadata
from utils.llm_factory import get_llm, get_llm_config

logger = logging.getLogger(__name__)


class DocumentationDriftDetector:
    """Detects contradictions between docstrings and actual module purpose."""
    
    def __init__(self, budget_tracker=None):
        """
        Initialize documentation drift detector.
        
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
                    f"Initialized LLM for drift detection: {self.llm_config['provider']} "
                    f"with model {self.llm_config['model']}"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize LLM: {e}")
                logger.warning("Drift detection will be disabled")
        else:
            logger.warning(
                f"LLM provider '{self.llm_config['provider']}' not available. "
                "Drift detection will be disabled"
            )
    
    def compare_docstring_to_purpose(
        self,
        module: ModuleNode,
        source_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare module docstring to generated purpose statement to detect contradictions.
        
        Args:
            module: Module node with purpose_statement and docstring
            source_code: Optional source code content (if not provided, will read from file)
        
        Returns:
            Dictionary with keys:
                - has_drift: bool indicating if drift was detected
                - confidence: float between 0.0 and 1.0
                - explanation: str describing the drift (if any)
                - provenance: ProvenanceMetadata for the drift detection
        """
        # Check if module has both docstring and purpose statement
        if not module.docstring:
            logger.debug(f"No docstring found for {module.path}, skipping drift detection")
            return {
                "has_drift": False,
                "confidence": 1.0,
                "explanation": "No docstring to compare",
                "provenance": self._create_provenance(module, 1.0)
            }
        
        if not module.purpose_statement:
            logger.debug(f"No purpose statement for {module.path}, skipping drift detection")
            return {
                "has_drift": False,
                "confidence": 1.0,
                "explanation": "No purpose statement to compare",
                "provenance": self._create_provenance(module, 1.0)
            }
        
        # Read source code if not provided (for line range extraction)
        if source_code is None:
            try:
                with open(module.path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
            except Exception as e:
                logger.error(f"Failed to read {module.path}: {e}")
                return {
                    "has_drift": False,
                    "confidence": 0.0,
                    "explanation": f"Failed to read source: {e}",
                    "provenance": self._create_provenance(module, 0.0)
                }
        
        # Extract docstring line range
        docstring_line_range = self._extract_docstring_line_range(source_code, module.docstring)
        
        # Call LLM to compare docstring and purpose
        drift_result = self._call_llm_for_drift_detection(module, docstring_line_range)
        
        return drift_result
    
    def flag_drift(
        self,
        module: ModuleNode,
        drift_result: Dict[str, Any]
    ) -> ModuleNode:
        """
        Mark module with drift flag and store provenance metadata.
        
        Args:
            module: Module node to flag
            drift_result: Result from compare_docstring_to_purpose()
        
        Returns:
            Updated module node with drift flag
        """
        if drift_result["has_drift"]:
            module.has_documentation_drift = True
            logger.info(
                f"Flagged drift in {module.path}: {drift_result['explanation']} "
                f"(confidence: {drift_result['confidence']:.2f})"
            )
        else:
            module.has_documentation_drift = False
            logger.debug(f"No drift detected in {module.path}")
        
        return module
    
    def detect_all_drift(
        self,
        modules: list[ModuleNode]
    ) -> list[ModuleNode]:
        """
        Detect documentation drift across all modules.
        
        Args:
            modules: List of module nodes with purpose statements and docstrings
        
        Returns:
            List of modules with drift flags updated
        """
        logger.info(f"Detecting drift across {len(modules)} modules")
        
        drift_count = 0
        
        for module in modules:
            # Compare docstring to purpose
            drift_result = self.compare_docstring_to_purpose(module)
            
            # Flag module if drift detected
            self.flag_drift(module, drift_result)
            
            if drift_result["has_drift"]:
                drift_count += 1
        
        logger.info(f"Detected drift in {drift_count} modules")
        
        return modules
    
    def _extract_docstring_line_range(
        self,
        source_code: str,
        docstring: str
    ) -> Optional[tuple[int, int]]:
        """
        Extract line range for docstring in source code.
        
        Args:
            source_code: Full source code content
            docstring: Docstring text to find
        
        Returns:
            Tuple of (start_line, end_line) or None if not found
        """
        lines = source_code.split('\n')
        
        # Clean docstring for comparison (remove quotes and whitespace)
        clean_docstring = docstring.strip().strip('"""').strip("'''").strip()
        
        # Search for docstring in source
        for i, line in enumerate(lines):
            if clean_docstring[:50] in line:  # Match first 50 chars
                # Found start, now find end
                start_line = i + 1  # 1-indexed
                
                # Count lines in docstring
                docstring_lines = clean_docstring.count('\n') + 1
                end_line = start_line + docstring_lines
                
                return (start_line, end_line)
        
        # Fallback: return first few lines (common docstring location)
        return (1, min(10, len(lines)))
    
    def _call_llm_for_drift_detection(
        self,
        module: ModuleNode,
        docstring_line_range: Optional[tuple[int, int]]
    ) -> Dict[str, Any]:
        """
        Call LLM to detect drift between docstring and purpose.
        
        Args:
            module: Module node with docstring and purpose_statement
            docstring_line_range: Line range of docstring in source
        
        Returns:
            Dictionary with drift detection results and provenance
        """
        # Prepare prompt
        prompt = self._build_drift_detection_prompt(module)
        
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
                result_text = response.content.strip()
                
                # Track actual output tokens
                if self.budget_tracker:
                    output_tokens = self.budget_tracker.estimate_tokens(result_text)
                    model_name = self.budget_tracker.select_model("bulk")
                    self.budget_tracker.track_usage(model_name, input_tokens, output_tokens)
                
                # Parse LLM response
                drift_info = self._parse_drift_response(result_text)
                
                # Add provenance
                drift_info["provenance"] = self._create_provenance(
                    module,
                    drift_info["confidence"],
                    docstring_line_range
                )
                
                return drift_info
                
            except Exception as e:
                logger.error(f"LLM call failed for drift detection on {module.path}: {e}")
                # Return no drift on error
                return {
                    "has_drift": False,
                    "confidence": 0.0,
                    "explanation": f"LLM error: {e}",
                    "provenance": self._create_provenance(module, 0.0, docstring_line_range)
                }
        else:
            # No LLM available, cannot detect drift
            logger.debug(f"No LLM available for drift detection on {module.path}")
            return {
                "has_drift": False,
                "confidence": 0.0,
                "explanation": "LLM not available",
                "provenance": self._create_provenance(module, 0.0, docstring_line_range)
            }
    
    def _build_drift_detection_prompt(self, module: ModuleNode) -> str:
        """
        Build prompt for LLM drift detection.
        
        Args:
            module: Module node with docstring and purpose_statement
        
        Returns:
            Formatted prompt string
        """
        prompt = f"""Compare the following docstring and purpose statement for contradictions or drift.

Module: {module.path}

Docstring:
{module.docstring}

Purpose Statement:
{module.purpose_statement}

Analyze if there are any contradictions, inconsistencies, or significant drift between what the docstring claims and what the purpose statement describes.

Respond in the following format:
DRIFT: [YES/NO]
CONFIDENCE: [0.0-1.0]
EXPLANATION: [Brief explanation of drift or confirmation of alignment]

Response:"""
        
        return prompt
    
    def _parse_drift_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse LLM response for drift detection.
        
        Args:
            response_text: Raw LLM response
        
        Returns:
            Dictionary with has_drift, confidence, and explanation
        """
        lines = response_text.strip().split('\n')
        
        has_drift = False
        confidence = 0.5  # Default
        explanation = "Unable to parse response"
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("DRIFT:"):
                drift_value = line.split(":", 1)[1].strip().upper()
                has_drift = drift_value == "YES"
            
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence_str = line.split(":", 1)[1].strip()
                    confidence = float(confidence_str)
                    # Clamp to valid range
                    confidence = max(0.0, min(1.0, confidence))
                except (ValueError, IndexError):
                    logger.warning(f"Failed to parse confidence: {line}")
            
            elif line.startswith("EXPLANATION:"):
                explanation = line.split(":", 1)[1].strip()
        
        return {
            "has_drift": has_drift,
            "confidence": confidence,
            "explanation": explanation
        }
    
    def _create_provenance(
        self,
        module: ModuleNode,
        confidence: float,
        docstring_line_range: Optional[tuple[int, int]] = None
    ) -> ProvenanceMetadata:
        """
        Create provenance metadata for drift detection.
        
        Args:
            module: Module node
            confidence: Confidence score from LLM
            docstring_line_range: Optional line range of docstring
        
        Returns:
            ProvenanceMetadata instance
        """
        return ProvenanceMetadata(
            evidence_type="llm",
            source_file=module.path,
            line_range=docstring_line_range,
            confidence=confidence,
            resolution_status="inferred"
        )
