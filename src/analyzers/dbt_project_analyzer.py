"""dbt project analyzer for extracting models, sources, and lineage with provenance tracking."""

import logging
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from models import DatasetNode, TransformationNode, ProvenanceMetadata
from analyzers.sql_lineage import SQLLineageAnalyzer


class DBTProjectAnalyzer:
    """Analyzes dbt projects to extract models, sources, and lineage with provenance tracking."""
    
    def __init__(self):
        """Initialize analyzer with SQL lineage analyzer."""
        self.sql_analyzer = SQLLineageAnalyzer()
        self.logger = logging.getLogger(__name__)
        self.dbt_project_root: Optional[Path] = None
        self.models_dir: Optional[Path] = None
        self.sources: Dict[str, Dict[str, DatasetNode]] = {}  # source_name -> table_name -> DatasetNode
        self.models: Dict[str, DatasetNode] = {}  # model_name -> DatasetNode
    
    def detect_dbt_project(self, repo_path: str) -> bool:
        """
        Detect if the repository is a dbt project by checking for dbt_project.yml.
        
        Args:
            repo_path: Path to repository root
            
        Returns:
            True if dbt_project.yml exists, False otherwise
        """
        repo = Path(repo_path)
        dbt_project_file = repo / "dbt_project.yml"
        
        if dbt_project_file.exists():
            self.dbt_project_root = repo
            self.logger.info(f"Detected dbt project at {repo_path}")
            return True
        
        return False
    
    def analyze_project(self, repo_path: str) -> Tuple[List[DatasetNode], List[TransformationNode]]:
        """
        Analyze complete dbt project.
        
        Args:
            repo_path: Path to repository root
            
        Returns:
            Tuple of (dataset_nodes, transformation_nodes)
        """
        if not self.detect_dbt_project(repo_path):
            self.logger.warning(f"No dbt project detected at {repo_path}")
            return [], []
        
        # Find models directory
        self.models_dir = self.dbt_project_root / "models"
        if not self.models_dir.exists():
            self.logger.warning(f"No models directory found at {self.models_dir}")
            return [], []
        
        # Parse schema.yml files first to get metadata
        self._parse_all_schema_files()
        
        # Parse dbt models
        transformations = self.parse_dbt_models(str(self.models_dir))
        
        # Collect all dataset nodes
        datasets = []
        for source_dict in self.sources.values():
            datasets.extend(source_dict.values())
        datasets.extend(self.models.values())
        
        return datasets, transformations
    
    def parse_dbt_models(self, models_dir: str) -> List[TransformationNode]:
        """
        Parse dbt model files (.sql) in the models directory with provenance.
        
        Args:
            models_dir: Path to models directory
            
        Returns:
            List of TransformationNode instances for dbt models
        """
        transformations = []
        models_path = Path(models_dir)
        
        if not models_path.exists():
            self.logger.warning(f"Models directory does not exist: {models_dir}")
            return []
        
        # Find all .sql files recursively
        for sql_file in models_path.rglob("*.sql"):
            try:
                with open(sql_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract model name from file name
                model_name = sql_file.stem
                
                # Extract ref() and source() calls
                ref_calls = self.extract_ref_calls(content)
                source_calls = self.extract_source_calls(content)
                
                # Parse SQL to get additional table dependencies
                sql_transformations = self.sql_analyzer.parse_sql(
                    content, 
                    str(sql_file.relative_to(self.dbt_project_root)),
                    dialect='postgres'  # Default dialect, could be configurable
                )
                
                # Combine dependencies from ref/source calls and SQL parsing
                source_datasets = []
                
                # Add ref() dependencies
                source_datasets.extend(ref_calls)
                
                # Add source() dependencies
                for source_name, table_name in source_calls:
                    source_datasets.append(f"{source_name}.{table_name}")
                
                # Add SQL table dependencies (excluding dbt refs/sources)
                for sql_trans in sql_transformations:
                    for table in sql_trans.source_datasets:
                        # Skip if it's a dbt ref or source
                        if table not in ref_calls and not any(
                            table == f"{s}.{t}" for s, t in source_calls
                        ):
                            source_datasets.append(table)
                
                # Create transformation node for this model
                transformation_id = f"dbt_model:{model_name}"
                
                # Calculate line range
                line_count = content.count('\n') + 1
                
                transformation = TransformationNode(
                    id=transformation_id,
                    source_datasets=source_datasets,
                    target_datasets=[model_name],
                    transformation_type="dbt_model",
                    source_file=str(sql_file.relative_to(self.dbt_project_root)),
                    line_range=(1, line_count),
                    sql_query=content,
                    provenance=ProvenanceMetadata(
                        evidence_type="sqlglot",  # Combined sqlglot + yaml_parse
                        source_file=str(sql_file.relative_to(self.dbt_project_root)),
                        line_range=(1, line_count),
                        confidence=1.0,  # High confidence for explicit dbt refs/sources
                        resolution_status="resolved"
                    )
                )
                
                transformations.append(transformation)
                
                # Create DatasetNode for this model if not already exists
                if model_name not in self.models:
                    self.models[model_name] = DatasetNode(
                        name=model_name,
                        storage_type="table",
                        discovered_in=str(sql_file.relative_to(self.dbt_project_root)),
                        provenance=ProvenanceMetadata(
                            evidence_type="sqlglot",
                            source_file=str(sql_file.relative_to(self.dbt_project_root)),
                            line_range=(1, line_count),
                            confidence=1.0,
                            resolution_status="resolved"
                        )
                    )
                
            except Exception as e:
                self.logger.error(f"Failed to parse dbt model {sql_file}: {e}")
                continue
        
        return transformations
    
    def extract_ref_calls(self, sql_content: str) -> List[str]:
        """
        Extract dbt ref() macro calls with confidence=1.0 (resolved).
        
        Args:
            sql_content: SQL content containing dbt macros
            
        Returns:
            List of referenced model names
        """
        # Pattern to match {{ ref('model_name') }} or {{ ref("model_name") }}
        ref_pattern = r"{{\s*ref\s*\(\s*['\"]([^'\"]+)['\"]\s*\)\s*}}"
        
        matches = re.findall(ref_pattern, sql_content)
        return matches
    
    def extract_source_calls(self, sql_content: str) -> List[Tuple[str, str]]:
        """
        Extract dbt source() macro calls with confidence=1.0 (resolved).
        
        Args:
            sql_content: SQL content containing dbt macros
            
        Returns:
            List of tuples (source_name, table_name)
        """
        # Pattern to match {{ source('source_name', 'table_name') }}
        source_pattern = r"{{\s*source\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)\s*}}"
        
        matches = re.findall(source_pattern, sql_content)
        return matches
    
    def parse_schema_yml(self, schema_path: str) -> List[DatasetNode]:
        """
        Parse schema.yml for table and column metadata with provenance.
        
        Args:
            schema_path: Path to schema.yml file
            
        Returns:
            List of DatasetNode instances with metadata
        """
        datasets = []
        
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_data = yaml.safe_load(f)
            
            if not schema_data:
                return []
            
            # Parse sources
            if 'sources' in schema_data:
                for source in schema_data['sources']:
                    source_name = source.get('name')
                    if not source_name:
                        continue
                    
                    if source_name not in self.sources:
                        self.sources[source_name] = {}
                    
                    # Parse tables in this source
                    for table in source.get('tables', []):
                        table_name = table.get('name')
                        if not table_name:
                            continue
                        
                        # Extract column metadata
                        schema_snapshot = {}
                        for column in table.get('columns', []):
                            col_name = column.get('name')
                            col_type = column.get('data_type', 'unknown')
                            if col_name:
                                schema_snapshot[col_name] = col_type
                        
                        # Create DatasetNode for source table
                        dataset = DatasetNode(
                            name=f"{source_name}.{table_name}",
                            storage_type="table",
                            schema_snapshot=schema_snapshot if schema_snapshot else None,
                            owner=source.get('owner'),
                            is_source_of_truth=True,  # Sources are typically source of truth
                            discovered_in=schema_path,
                            provenance=ProvenanceMetadata(
                                evidence_type="yaml_parse",
                                source_file=schema_path,
                                line_range=None,  # YAML doesn't have easy line tracking
                                confidence=1.0,
                                resolution_status="resolved"
                            )
                        )
                        
                        self.sources[source_name][table_name] = dataset
                        datasets.append(dataset)
            
            # Parse models
            if 'models' in schema_data:
                for model in schema_data['models']:
                    model_name = model.get('name')
                    if not model_name:
                        continue
                    
                    # Extract column metadata
                    schema_snapshot = {}
                    for column in model.get('columns', []):
                        col_name = column.get('name')
                        col_type = column.get('data_type', 'unknown')
                        if col_name:
                            schema_snapshot[col_name] = col_type
                    
                    # Update or create DatasetNode for model
                    if model_name in self.models:
                        # Update existing model with schema metadata
                        self.models[model_name].schema_snapshot = schema_snapshot if schema_snapshot else None
                    else:
                        # Create new DatasetNode
                        dataset = DatasetNode(
                            name=model_name,
                            storage_type="table",
                            schema_snapshot=schema_snapshot if schema_snapshot else None,
                            discovered_in=schema_path,
                            provenance=ProvenanceMetadata(
                                evidence_type="yaml_parse",
                                source_file=schema_path,
                                line_range=None,
                                confidence=1.0,
                                resolution_status="resolved"
                            )
                        )
                        
                        self.models[model_name] = dataset
                        datasets.append(dataset)
        
        except Exception as e:
            self.logger.error(f"Failed to parse schema file {schema_path}: {e}")
        
        return datasets
    
    def _parse_all_schema_files(self):
        """Parse all schema/sources YAML files in the models directory."""
        if not self.models_dir or not self.models_dir.exists():
            return

        for schema_file in self.models_dir.rglob("*.yml"):
            self.parse_schema_yml(str(schema_file))

        for schema_file in self.models_dir.rglob("*.yaml"):
            self.parse_schema_yml(str(schema_file))
