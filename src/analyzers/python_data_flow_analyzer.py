"""Python data flow analyzer for extracting pandas, SQLAlchemy, and PySpark operations."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from tree_sitter import Node, Parser

from models import TransformationNode, ProvenanceMetadata
from analyzers.language_router import LanguageRouter


class PythonDataFlowAnalyzer:
    """Analyzes Python files to extract data flow operations with provenance tracking."""
    
    def __init__(self):
        """Initialize analyzer with language router."""
        self.router = LanguageRouter()
    
    def analyze_file(self, file_path: str) -> List[TransformationNode]:
        """
        Analyze a Python file for data flow operations.
        
        Args:
            file_path: Path to Python file to analyze
            
        Returns:
            List of TransformationNode instances for detected operations
        """
        if not file_path.endswith('.py'):
            return []
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return []
        
        # Parse with tree-sitter
        parser = self.router.get_parser('.py')
        if parser is None:
            return []
            
        tree = parser.parse(bytes(content, 'utf8'))
        root = tree.root_node
        
        transformations = []
        
        # Extract different types of operations
        transformations.extend(self.extract_pandas_operations(root, file_path))
        transformations.extend(self.extract_sqlalchemy_operations(root, file_path))
        transformations.extend(self.extract_pyspark_operations(root, file_path))
        
        return transformations
    def extract_pandas_operations(self, ast: Node, source_file: str) -> List[TransformationNode]:
        """
        Extract pandas read/write operations with provenance tracking.
        
        Args:
            ast: Tree-sitter AST root node
            source_file: Path to source file for provenance
            
        Returns:
            List of TransformationNode instances for pandas operations
        """
        operations = []
        
        # Pandas operations to detect
        read_ops = ['read_csv', 'read_sql', 'read_parquet', 'read_json', 'read_excel']
        write_ops = ['to_csv', 'to_sql', 'to_parquet', 'to_json', 'to_excel']
        
        def visit_node(node: Node):
            if node.type == 'call':
                # Check if this is a pandas operation
                func_node = node.child_by_field_name('function')
                if func_node:
                    func_text = self._get_node_text(func_node)
                    
                    # Check for pandas read operations (pd.read_csv, pandas.read_csv)
                    for read_op in read_ops:
                        if func_text.endswith(f'.{read_op}') or func_text == read_op:
                            dataset_name, confidence, resolution_status = self._extract_dataset_from_args(node)
                            if dataset_name:
                                operations.append(self._create_transformation_node(
                                    operation_type='pandas_read',
                                    source_datasets=[],
                                    target_datasets=[dataset_name],
                                    source_file=source_file,
                                    line_range=(node.start_point[0], node.end_point[0]),
                                    confidence=confidence,
                                    resolution_status=resolution_status
                                ))
                    
                    # Check for pandas write operations (df.to_csv, df.to_sql)
                    for write_op in write_ops:
                        if func_text.endswith(f'.{write_op}'):
                            dataset_name, confidence, resolution_status = self._extract_dataset_from_args(node)
                            if dataset_name:
                                operations.append(self._create_transformation_node(
                                    operation_type='pandas_write',
                                    source_datasets=[dataset_name],
                                    target_datasets=[],
                                    source_file=source_file,
                                    line_range=(node.start_point[0], node.end_point[0]),
                                    confidence=confidence,
                                    resolution_status=resolution_status
                                ))
            
            # Recursively visit children
            for child in node.children:
                visit_node(child)
        
        visit_node(ast)
        return operations
    def extract_sqlalchemy_operations(self, ast: Node, source_file: str) -> List[TransformationNode]:
        """
        Extract SQLAlchemy execute() and query() operations with provenance tracking.
        
        Args:
            ast: Tree-sitter AST root node
            source_file: Path to source file for provenance
            
        Returns:
            List of TransformationNode instances for SQLAlchemy operations
        """
        operations = []
        
        def visit_node(node: Node):
            if node.type == 'call':
                func_node = node.child_by_field_name('function')
                if func_node:
                    func_text = self._get_node_text(func_node)
                    
                    # Check for SQLAlchemy operations
                    if func_text.endswith('.execute') or func_text.endswith('.query'):
                        # Extract SQL query from arguments
                        sql_query, confidence, resolution_status = self._extract_sql_from_args(node)
                        
                        # Try to extract table names from SQL if available
                        source_datasets, target_datasets = self._parse_sql_for_tables(sql_query)
                        
                        operations.append(self._create_transformation_node(
                            operation_type='sqlalchemy',
                            source_datasets=source_datasets,
                            target_datasets=target_datasets,
                            source_file=source_file,
                            line_range=(node.start_point[0], node.end_point[0]),
                            confidence=confidence,
                            resolution_status=resolution_status,
                            sql_query=sql_query
                        ))
            
            # Recursively visit children
            for child in node.children:
                visit_node(child)
        
        visit_node(ast)
        return operations
    def extract_pyspark_operations(self, ast: Node, source_file: str) -> List[TransformationNode]:
        """
        Extract PySpark read/write operations with provenance tracking.
        
        Args:
            ast: Tree-sitter AST root node
            source_file: Path to source file for provenance
            
        Returns:
            List of TransformationNode instances for PySpark operations
        """
        operations = []
        
        # PySpark operations to detect
        read_ops = ['read', 'load', 'csv', 'parquet', 'json', 'table']
        write_ops = ['write', 'save', 'saveAsTable']
        
        def visit_node(node: Node):
            if node.type == 'call':
                func_node = node.child_by_field_name('function')
                if func_node:
                    func_text = self._get_node_text(func_node)
                    
                    # Check for Spark read operations (spark.read.csv, spark.read.table)
                    for read_op in read_ops:
                        if f'.read.{read_op}' in func_text or func_text.endswith(f'.{read_op}'):
                            dataset_name, confidence, resolution_status = self._extract_dataset_from_args(node)
                            if dataset_name:
                                operations.append(self._create_transformation_node(
                                    operation_type='pyspark_read',
                                    source_datasets=[],
                                    target_datasets=[dataset_name],
                                    source_file=source_file,
                                    line_range=(node.start_point[0], node.end_point[0]),
                                    confidence=confidence,
                                    resolution_status=resolution_status
                                ))
                    
                    # Check for Spark write operations (df.write.csv, df.write.saveAsTable)
                    for write_op in write_ops:
                        if f'.write.{write_op}' in func_text or func_text.endswith(f'.{write_op}'):
                            dataset_name, confidence, resolution_status = self._extract_dataset_from_args(node)
                            if dataset_name:
                                operations.append(self._create_transformation_node(
                                    operation_type='pyspark_write',
                                    source_datasets=[dataset_name],
                                    target_datasets=[],
                                    source_file=source_file,
                                    line_range=(node.start_point[0], node.end_point[0]),
                                    confidence=confidence,
                                    resolution_status=resolution_status
                                ))
            
            # Recursively visit children
            for child in node.children:
                visit_node(child)
        
        visit_node(ast)
        return operations
    def resolve_dataset_name(self, arg_node: Node) -> Tuple[Optional[str], float, str]:
        """
        Resolve dataset name from function argument with confidence scoring.
        
        Args:
            arg_node: Tree-sitter node representing the argument
            
        Returns:
            Tuple of (dataset_name, confidence, resolution_status)
        """
        if not arg_node:
            return None, 0.0, "dynamic"
        
        arg_text = self._get_node_text(arg_node).strip()
        
        # String literal - high confidence
        if arg_node.type == 'string':
            # Remove quotes
            dataset_name = arg_text.strip('"\'')
            return dataset_name, 1.0, "resolved"
        
        # Variable reference - medium confidence
        elif arg_node.type == 'identifier':
            return arg_text, 0.5, "dynamic"
        
        # Attribute access (e.g., config.table_name) - medium confidence
        elif arg_node.type == 'attribute':
            return arg_text, 0.5, "dynamic"
        
        # Function call or complex expression - low confidence
        else:
            return arg_text, 0.3, "dynamic"
    def _extract_dataset_from_args(self, call_node: Node) -> Tuple[Optional[str], float, str]:
        """Extract dataset name from function call arguments."""
        args_node = call_node.child_by_field_name('arguments')
        if not args_node:
            return None, 0.0, "dynamic"
        
        # Look for first argument (usually the dataset name/path)
        for child in args_node.children:
            if child.type in ['string', 'identifier', 'attribute']:
                return self.resolve_dataset_name(child)
        
        return None, 0.0, "dynamic"
    
    def _extract_sql_from_args(self, call_node: Node) -> Tuple[Optional[str], float, str]:
        """Extract SQL query from function call arguments."""
        args_node = call_node.child_by_field_name('arguments')
        if not args_node:
            return None, 0.0, "dynamic"
        
        # Look for SQL string in arguments
        for child in args_node.children:
            if child.type == 'string':
                sql_text = self._get_node_text(child).strip('"\'')
                return sql_text, 1.0, "resolved"
            elif child.type in ['identifier', 'attribute']:
                # Variable containing SQL
                return self._get_node_text(child), 0.5, "dynamic"
        
        return None, 0.0, "dynamic"
    
    def _parse_sql_for_tables(self, sql_query: Optional[str]) -> Tuple[List[str], List[str]]:
        """Parse SQL query to extract source and target tables."""
        if not sql_query:
            return [], []
        
        # Simple regex-based parsing for basic table extraction
        # This is a simplified approach - full SQL parsing would use sqlglot
        source_tables = []
        target_tables = []
        
        # Extract FROM clauses
        from_matches = re.findall(r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)', sql_query, re.IGNORECASE)
        source_tables.extend(from_matches)
        
        # Extract JOIN clauses
        join_matches = re.findall(r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)', sql_query, re.IGNORECASE)
        source_tables.extend(join_matches)
        
        # Extract INSERT INTO clauses
        insert_matches = re.findall(r'INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)', sql_query, re.IGNORECASE)
        target_tables.extend(insert_matches)
        
        return source_tables, target_tables
    def _create_transformation_node(
        self, 
        operation_type: str,
        source_datasets: List[str],
        target_datasets: List[str],
        source_file: str,
        line_range: Tuple[int, int],
        confidence: float,
        resolution_status: str,
        sql_query: Optional[str] = None
    ) -> TransformationNode:
        """Create a TransformationNode with provenance metadata."""
        # Generate unique ID for transformation
        transformation_id = f"{source_file}:{line_range[0]}:{operation_type}"
        
        return TransformationNode(
            id=transformation_id,
            source_datasets=source_datasets,
            target_datasets=target_datasets,
            transformation_type=operation_type,
            source_file=source_file,
            line_range=line_range,
            sql_query=sql_query,
            provenance=ProvenanceMetadata(
                evidence_type="tree_sitter",
                source_file=source_file,
                line_range=line_range,
                confidence=confidence,
                resolution_status=resolution_status
            )
        )
    
    def _get_node_text(self, node: Node) -> str:
        """Get text content of a node."""
        return node.text.decode('utf8') if node.text else ""