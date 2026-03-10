"""Pydantic models for knowledge graph nodes and edges with provenance tracking."""

from datetime import datetime
from typing import Dict, List, Literal, Optional, Tuple, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict


class ProvenanceMetadata(BaseModel):
    """Metadata tracking the source and confidence of extracted information."""
    
    evidence_type: Literal["tree_sitter", "sqlglot", "yaml_parse", "heuristic", "llm"]
    source_file: str
    line_range: Optional[Tuple[int, int]] = None
    confidence: float = Field(ge=0.0, le=1.0)
    resolution_status: Literal["resolved", "partial", "dynamic", "inferred"]
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        """Ensure confidence is between 0.0 and 1.0."""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return v


class ModuleNode(BaseModel):
    """Node representing a code module/file with metadata."""
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )
    
    path: str
    language: str
    purpose_statement: Optional[str] = None
    domain_cluster: Optional[str] = None
    complexity_score: int = Field(ge=0)  # Must be non-negative
    change_velocity_30d: Optional[int] = None
    is_dead_code_candidate: bool = False
    last_modified: Optional[datetime] = None
    imports: List[str] = Field(default_factory=list)
    exports: List[str] = Field(default_factory=list)
    docstring: Optional[str] = None
    has_documentation_drift: bool = False
    provenance: ProvenanceMetadata


class DatasetNode(BaseModel):
    """Node representing a data source, table, file, or stream."""
    
    name: str
    storage_type: Literal["table", "file", "stream", "api"]
    schema_snapshot: Optional[Dict[str, str]] = None
    freshness_sla: Optional[str] = None
    owner: Optional[str] = None
    is_source_of_truth: bool = False
    discovered_in: str  # file path where discovered
    provenance: ProvenanceMetadata


class FunctionNode(BaseModel):
    """Node representing a function or method."""
    
    qualified_name: str
    parent_module: str
    signature: str
    purpose_statement: Optional[str] = None
    call_count_within_repo: int = 0
    is_public_api: bool = True
    line_range: Tuple[int, int]
    provenance: ProvenanceMetadata


class TransformationNode(BaseModel):
    """Node representing a data transformation operation."""
    
    id: str
    source_datasets: List[str] = Field(default_factory=list)
    target_datasets: List[str] = Field(default_factory=list)
    transformation_type: str  # "sql", "pandas", "pyspark", "airflow_task"
    source_file: str
    line_range: Tuple[int, int]
    sql_query: Optional[str] = None
    provenance: ProvenanceMetadata


# Edge Models

class ImportEdge(BaseModel):
    """Edge representing module import relationship."""
    
    source: str  # importing module
    target: str  # imported module
    import_count: int = Field(ge=1)  # Must be at least 1
    import_type: Literal["absolute", "relative"]
    provenance: ProvenanceMetadata


class ProducesEdge(BaseModel):
    """Edge representing transformation producing a dataset."""
    
    source: str  # transformation id
    target: str  # dataset name
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: ProvenanceMetadata
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        """Ensure confidence is between 0.0 and 1.0."""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return v


class ConsumesEdge(BaseModel):
    """Edge representing transformation consuming a dataset."""
    
    source: str  # transformation id
    target: str  # dataset name
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: ProvenanceMetadata
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        """Ensure confidence is between 0.0 and 1.0."""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return v


class CallsEdge(BaseModel):
    """Edge representing function call relationship."""
    
    source: str  # calling function
    target: str  # called function
    call_count: int = 1
    provenance: ProvenanceMetadata


class ConfiguresEdge(BaseModel):
    """Edge representing configuration relationship."""
    
    source: str  # config file
    target: str  # module/pipeline
    config_type: str  # "airflow_dag", "dbt_schema", "env"
    provenance: ProvenanceMetadata