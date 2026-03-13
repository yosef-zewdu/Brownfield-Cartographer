"""Unit tests for DocumentationDriftDetector."""

import pytest
from datetime import datetime

from agents.drift_detector import DocumentationDriftDetector
from models import ModuleNode, ProvenanceMetadata


class TestDocumentationDriftDetector:
    """Test suite for DocumentationDriftDetector."""
    
    def test_initialization(self):
        """Test that DocumentationDriftDetector initializes correctly."""
        detector = DocumentationDriftDetector()
        
        assert detector.budget_tracker is None
        assert detector.llm_config is not None
    
    def test_compare_no_docstring(self):
        """Test drift detection when module has no docstring."""
        detector = DocumentationDriftDetector()
        
        module = ModuleNode(
            path="test.py",
            language="python",
            complexity_score=50,
            purpose_statement="This module handles user authentication.",
            docstring=None,
            provenance=ProvenanceMetadata(
                evidence_type="tree_sitter",
                source_file="test.py",
                confidence=1.0,
                resolution_status="resolved"
            )
        )
        
        result = detector.compare_docstring_to_purpose(module)
        
        assert result["has_drift"] is False
        assert result["confidence"] == 1.0
        assert "No docstring" in result["explanation"]
        assert result["provenance"].evidence_type == "llm"
        assert result["provenance"].resolution_status == "inferred"
    
    def test_compare_no_purpose(self):
        """Test drift detection when module has no purpose statement."""
        detector = DocumentationDriftDetector()
        
        module = ModuleNode(
            path="test.py",
            language="python",
            complexity_score=50,
            purpose_statement=None,
            docstring="This module handles user authentication.",
            provenance=ProvenanceMetadata(
                evidence_type="tree_sitter",
                source_file="test.py",
                confidence=1.0,
                resolution_status="resolved"
            )
        )
        
        result = detector.compare_docstring_to_purpose(module)
        
        assert result["has_drift"] is False
        assert result["confidence"] == 1.0
        assert "No purpose statement" in result["explanation"]
    
    def test_flag_drift_true(self):
        """Test flagging module with drift."""
        detector = DocumentationDriftDetector()
        
        module = ModuleNode(
            path="test.py",
            language="python",
            complexity_score=50,
            has_documentation_drift=False,
            provenance=ProvenanceMetadata(
                evidence_type="tree_sitter",
                source_file="test.py",
                confidence=1.0,
                resolution_status="resolved"
            )
        )
        
        drift_result = {
            "has_drift": True,
            "confidence": 0.85,
            "explanation": "Docstring claims authentication but code handles authorization",
            "provenance": ProvenanceMetadata(
                evidence_type="llm",
                source_file="test.py",
                confidence=0.85,
                resolution_status="inferred"
            )
        }
        
        updated_module = detector.flag_drift(module, drift_result)
        
        assert updated_module.has_documentation_drift is True
    
    def test_flag_drift_false(self):
        """Test flagging module without drift."""
        detector = DocumentationDriftDetector()
        
        module = ModuleNode(
            path="test.py",
            language="python",
            complexity_score=50,
            has_documentation_drift=False,
            provenance=ProvenanceMetadata(
                evidence_type="tree_sitter",
                source_file="test.py",
                confidence=1.0,
                resolution_status="resolved"
            )
        )
        
        drift_result = {
            "has_drift": False,
            "confidence": 0.95,
            "explanation": "Docstring and purpose are aligned",
            "provenance": ProvenanceMetadata(
                evidence_type="llm",
                source_file="test.py",
                confidence=0.95,
                resolution_status="inferred"
            )
        }
        
        updated_module = detector.flag_drift(module, drift_result)
        
        assert updated_module.has_documentation_drift is False
    
    def test_extract_docstring_line_range(self):
        """Test extracting line range for docstring."""
        detector = DocumentationDriftDetector()
        
        source_code = '''"""This is a module docstring.
It spans multiple lines.
"""

def foo():
    pass
'''
        
        docstring = "This is a module docstring.\nIt spans multiple lines."
        
        line_range = detector._extract_docstring_line_range(source_code, docstring)
        
        assert line_range is not None
        assert line_range[0] == 1  # 1-indexed
        assert line_range[1] >= 1
    
    def test_parse_drift_response_yes(self):
        """Test parsing LLM response indicating drift."""
        detector = DocumentationDriftDetector()
        
        response = """DRIFT: YES
CONFIDENCE: 0.85
EXPLANATION: The docstring claims this module handles authentication, but the purpose statement indicates it handles authorization."""
        
        result = detector._parse_drift_response(response)
        
        assert result["has_drift"] is True
        assert result["confidence"] == 0.85
        assert "authentication" in result["explanation"].lower()
    
    def test_parse_drift_response_no(self):
        """Test parsing LLM response indicating no drift."""
        detector = DocumentationDriftDetector()
        
        response = """DRIFT: NO
CONFIDENCE: 0.95
EXPLANATION: The docstring and purpose statement are well-aligned."""
        
        result = detector._parse_drift_response(response)
        
        assert result["has_drift"] is False
        assert result["confidence"] == 0.95
        assert "aligned" in result["explanation"].lower()
    
    def test_parse_drift_response_malformed(self):
        """Test parsing malformed LLM response."""
        detector = DocumentationDriftDetector()
        
        response = "This is not a properly formatted response."
        
        result = detector._parse_drift_response(response)
        
        # Should have defaults
        assert result["has_drift"] is False
        assert result["confidence"] == 0.5
        assert "Unable to parse" in result["explanation"]
    
    def test_create_provenance(self):
        """Test creating provenance metadata."""
        detector = DocumentationDriftDetector()
        
        module = ModuleNode(
            path="test.py",
            language="python",
            complexity_score=50,
            provenance=ProvenanceMetadata(
                evidence_type="tree_sitter",
                source_file="test.py",
                confidence=1.0,
                resolution_status="resolved"
            )
        )
        
        provenance = detector._create_provenance(module, 0.85, (1, 10))
        
        assert provenance.evidence_type == "llm"
        assert provenance.source_file == "test.py"
        assert provenance.line_range == (1, 10)
        assert provenance.confidence == 0.85
        assert provenance.resolution_status == "inferred"
    
    def test_build_drift_detection_prompt(self):
        """Test building drift detection prompt."""
        detector = DocumentationDriftDetector()
        
        module = ModuleNode(
            path="test.py",
            language="python",
            complexity_score=50,
            docstring="This module handles user authentication.",
            purpose_statement="This module provides user login and session management.",
            provenance=ProvenanceMetadata(
                evidence_type="tree_sitter",
                source_file="test.py",
                confidence=1.0,
                resolution_status="resolved"
            )
        )
        
        prompt = detector._build_drift_detection_prompt(module)
        
        assert "test.py" in prompt
        assert "user authentication" in prompt
        assert "user login" in prompt
        assert "DRIFT:" in prompt
        assert "CONFIDENCE:" in prompt
    
    def test_detect_all_drift(self):
        """Test detecting drift across multiple modules."""
        detector = DocumentationDriftDetector()
        
        modules = [
            ModuleNode(
                path="test1.py",
                language="python",
                complexity_score=50,
                docstring="Module 1 docstring",
                purpose_statement="Module 1 purpose",
                provenance=ProvenanceMetadata(
                    evidence_type="tree_sitter",
                    source_file="test1.py",
                    confidence=1.0,
                    resolution_status="resolved"
                )
            ),
            ModuleNode(
                path="test2.py",
                language="python",
                complexity_score=50,
                docstring=None,  # No docstring
                purpose_statement="Module 2 purpose",
                provenance=ProvenanceMetadata(
                    evidence_type="tree_sitter",
                    source_file="test2.py",
                    confidence=1.0,
                    resolution_status="resolved"
                )
            ),
            ModuleNode(
                path="test3.py",
                language="python",
                complexity_score=50,
                docstring="Module 3 docstring",
                purpose_statement=None,  # No purpose
                provenance=ProvenanceMetadata(
                    evidence_type="tree_sitter",
                    source_file="test3.py",
                    confidence=1.0,
                    resolution_status="resolved"
                )
            )
        ]
        
        result_modules = detector.detect_all_drift(modules)
        
        # Should return same number of modules
        assert len(result_modules) == 3
        
        # All modules should have has_documentation_drift set (even if False)
        for module in result_modules:
            assert isinstance(module.has_documentation_drift, bool)
