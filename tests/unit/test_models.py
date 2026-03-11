"""Unit tests for Pydantic models."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

import pytest
from pydantic import ValidationError
from models import (
    ProvenanceMetadata,
    ModuleNode,
    DatasetNode,
    FunctionNode,
    TransformationNode,
    ImportEdge,
    ProducesEdge,
    ConsumesEdge,
)


class TestProvenanceMetadata:
    """Test suite for ProvenanceMetadata."""
    
    def test_valid_provenance(self):
        """Test creating valid provenance metadata."""
        prov = ProvenanceMetadata(
            evidence_type="tree_sitter",
            source_file="test.py",
            line_range=(1, 10),
            confidence=0.95,
            resolution_status="resolved"
        )
        assert prov.confidence == 0.95
        assert prov.evidence_type == "tree_sitter"
    
    def test_confidence_validation(self):
        """Test confidence must be between 0 and 1."""
        with pytest.raises(ValidationError):
            ProvenanceMetadata(
                evidence_type="tree_sitter",
                source_file="test.py",
                confidence=1.5,
                resolution_status="resolved"
            )
        
        with pytest.raises(ValidationError):
            ProvenanceMetadata(
                evidence_type="tree_sitter",
                source_file="test.py",
                confidence=-0.1,
                resolution_status="resolved"
            )


class TestModuleNode:
    """Test suite for ModuleNode."""
    
    def test_valid_module_node(self):
        """Test creating valid module node."""
        prov = ProvenanceMetadata(
            evidence_type="tree_sitter",
            source_file="src/test.py",
            confidence=1.0,
            resolution_status="resolved"
        )
        node = ModuleNode(
            path="src/test.py",
            language="python",
            complexity_score=100,
            imports=["os", "sys"],
            exports=["main", "helper"],
            provenance=prov
        )
        assert node.path == "src/test.py"
        assert len(node.imports) == 2
        assert len(node.exports) == 2
    
    def test_negative_complexity_fails(self):
        """Test that negative complexity score fails validation."""
        prov = ProvenanceMetadata(
            evidence_type="tree_sitter",
            source_file="test.py",
            confidence=1.0,
            resolution_status="resolved"
        )
        with pytest.raises(ValidationError):
            ModuleNode(
                path="test.py",
                language="python",
                complexity_score=-1,
                provenance=prov
            )


class TestImportEdge:
    """Test suite for ImportEdge."""
    
    def test_valid_import_edge(self):
        """Test creating valid import edge."""
        prov = ProvenanceMetadata(
            evidence_type="tree_sitter",
            source_file="a.py",
            confidence=1.0,
            resolution_status="resolved"
        )
        edge = ImportEdge(
            source="a.py",
            target="b.py",
            import_count=3,
            import_type="absolute",
            provenance=prov
        )
        assert edge.import_count == 3
        assert edge.import_type == "absolute"
    
    def test_import_count_must_be_positive(self):
        """Test that import count must be at least 1."""
        prov = ProvenanceMetadata(
            evidence_type="tree_sitter",
            source_file="a.py",
            confidence=1.0,
            resolution_status="resolved"
        )
        with pytest.raises(ValidationError):
            ImportEdge(
                source="a.py",
                target="b.py",
                import_count=0,
                import_type="absolute",
                provenance=prov
            )


class TestDatasetNode:
    """Test suite for DatasetNode."""
    
    def test_valid_dataset_node(self):
        """Test creating valid dataset node."""
        prov = ProvenanceMetadata(
            evidence_type="sqlglot",
            source_file="etl.py",
            confidence=1.0,
            resolution_status="resolved"
        )
        node = DatasetNode(
            name="users_table",
            storage_type="table",
            discovered_in="etl.py",
            is_source_of_truth=True,
            provenance=prov
        )
        assert node.name == "users_table"
        assert node.storage_type == "table"
        assert node.is_source_of_truth is True
