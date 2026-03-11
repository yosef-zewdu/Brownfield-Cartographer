"""Unit tests for DBTProjectAnalyzer."""

import pytest
import tempfile
import shutil
from pathlib import Path

from src.analyzers.dbt_project_analyzer import DBTProjectAnalyzer


class TestDBTProjectAnalyzer:
    """Test suite for DBTProjectAnalyzer."""
    
    @pytest.fixture
    def temp_dbt_project(self):
        """Create a temporary dbt project structure for testing."""
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)
        
        # Create dbt_project.yml
        dbt_project_yml = project_path / "dbt_project.yml"
        dbt_project_yml.write_text("""
name: 'test_project'
version: '1.0.0'
profile: 'test'
""")
        
        # Create models directory
        models_dir = project_path / "models"
        models_dir.mkdir()
        
        # Create a simple model
        model_file = models_dir / "customers.sql"
        model_file.write_text("""
SELECT
    customer_id,
    customer_name
FROM {{ ref('raw_customers') }}
WHERE active = true
""")
        
        # Create a model with source
        orders_file = models_dir / "orders.sql"
        orders_file.write_text("""
SELECT
    order_id,
    customer_id,
    order_date
FROM {{ source('raw_data', 'orders') }}
""")
        
        # Create schema.yml
        schema_file = models_dir / "schema.yml"
        schema_file.write_text("""
version: 2

sources:
  - name: raw_data
    tables:
      - name: orders
        columns:
          - name: order_id
            data_type: integer
          - name: customer_id
            data_type: integer

models:
  - name: customers
    columns:
      - name: customer_id
        data_type: integer
      - name: customer_name
        data_type: varchar
""")
        
        yield str(project_path)
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_detect_dbt_project(self, temp_dbt_project):
        """Test detection of dbt project."""
        analyzer = DBTProjectAnalyzer()
        
        assert analyzer.detect_dbt_project(temp_dbt_project) is True
        assert analyzer.dbt_project_root == Path(temp_dbt_project)
    
    def test_detect_non_dbt_project(self):
        """Test detection fails for non-dbt directory."""
        analyzer = DBTProjectAnalyzer()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            assert analyzer.detect_dbt_project(temp_dir) is False
    
    def test_extract_ref_calls(self):
        """Test extraction of dbt ref() calls."""
        analyzer = DBTProjectAnalyzer()
        
        sql_content = """
        SELECT * FROM {{ ref('model_a') }}
        JOIN {{ ref("model_b") }} ON a.id = b.id
        """
        
        refs = analyzer.extract_ref_calls(sql_content)
        
        assert len(refs) == 2
        assert 'model_a' in refs
        assert 'model_b' in refs
    
    def test_extract_source_calls(self):
        """Test extraction of dbt source() calls."""
        analyzer = DBTProjectAnalyzer()
        
        sql_content = """
        SELECT * FROM {{ source('raw_data', 'users') }}
        JOIN {{ source("raw_data", "orders") }} ON u.id = o.user_id
        """
        
        sources = analyzer.extract_source_calls(sql_content)
        
        assert len(sources) == 2
        assert ('raw_data', 'users') in sources
        assert ('raw_data', 'orders') in sources
    
    def test_parse_schema_yml(self, temp_dbt_project):
        """Test parsing of schema.yml file."""
        analyzer = DBTProjectAnalyzer()
        analyzer.dbt_project_root = Path(temp_dbt_project)
        
        schema_path = Path(temp_dbt_project) / "models" / "schema.yml"
        datasets = analyzer.parse_schema_yml(str(schema_path))
        
        # Should have at least one source and one model
        assert len(datasets) >= 1
        
        # Check source was parsed
        assert 'raw_data' in analyzer.sources
        assert 'orders' in analyzer.sources['raw_data']
        
        # Check model was parsed
        assert 'customers' in analyzer.models
    
    def test_parse_dbt_models(self, temp_dbt_project):
        """Test parsing of dbt model files."""
        analyzer = DBTProjectAnalyzer()
        analyzer.dbt_project_root = Path(temp_dbt_project)
        analyzer.models_dir = Path(temp_dbt_project) / "models"
        
        # Parse schema first
        analyzer._parse_all_schema_files()
        
        # Parse models
        transformations = analyzer.parse_dbt_models(str(analyzer.models_dir))
        
        # Should have transformations for both models
        assert len(transformations) >= 2
        
        # Check transformation properties
        for trans in transformations:
            assert trans.transformation_type == "dbt_model"
            assert trans.provenance.evidence_type == "sqlglot"
            assert trans.provenance.confidence == 1.0
            assert trans.provenance.resolution_status == "resolved"
    
    def test_analyze_project(self, temp_dbt_project):
        """Test complete project analysis."""
        analyzer = DBTProjectAnalyzer()
        
        datasets, transformations = analyzer.analyze_project(temp_dbt_project)
        
        # Should have datasets and transformations
        assert len(datasets) > 0
        assert len(transformations) > 0
        
        # Check dataset provenance
        for dataset in datasets:
            assert dataset.provenance is not None
            assert dataset.provenance.confidence > 0
        
        # Check transformation provenance
        for trans in transformations:
            assert trans.provenance is not None
            assert trans.provenance.confidence == 1.0
