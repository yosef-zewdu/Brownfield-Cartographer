"""Airflow DAG analyzer for extracting task dependencies and data sources with provenance tracking."""

import logging
from pathlib import Path
from typing import List, Optional, Tuple
from tree_sitter import Node

from models import TransformationNode, DatasetNode, ProvenanceMetadata
from analyzers.language_router import LanguageRouter


class AirflowDAGAnalyzer:
    """Analyzes Airflow DAG files to extract task dependencies and data sources with provenance tracking."""
    
    def __init__(self):
        """Initialize analyzer with language router for Python parsing."""
        self.router = LanguageRouter()
        self.logger = logging.getLogger(__name__)
    
    def detect_airflow_dag(self, file_path: str) -> bool:
        """Detect if a Python file contains an Airflow DAG by searching for DAG class instantiation."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            parser = self.router.get_parser('.py')
            if parser is None:
                self.logger.warning(f"Python parser not available for {file_path}")
                return False
            
            tree = parser.parse(bytes(content, 'utf8'))
            root = tree.root_node
            
            return self._find_dag_instantiation(root) is not None
            
        except Exception as e:
            self.logger.error(f"Failed to detect Airflow DAG in {file_path}: {e}")
            return False
    
    def analyze_dag_file(self, file_path: str) -> Tuple[List[TransformationNode], List[DatasetNode]]:
        """Analyze an Airflow DAG file to extract tasks and dependencies."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            parser = self.router.get_parser('.py')
            if parser is None:
                self.logger.warning(f"Python parser not available for {file_path}")
                return [], []

            tree = parser.parse(bytes(content, 'utf8'))
            root = tree.root_node

            dag_node = self._find_dag_instantiation(root)
            if dag_node is None:
                self.logger.warning(f"No DAG instantiation found in {file_path}")
                return [], []

            tasks = self._extract_tasks(root, file_path, content)
            dependencies = self.extract_task_dependencies(root, file_path, content)

            # Create mapping from variable names to task IDs
            var_to_task_id = {}
            for task in tasks:
                # Extract variable name from the AST (stored during task extraction)
                # For now, we'll extract it again by looking at assignments
                pass

            # Build variable name to task ID mapping
            var_to_task_id = self._build_var_to_task_map(root)

            # Map dependencies using variable names to task IDs
            task_map = {task.id: task for task in tasks}
            for source_var, target_var, resolution_status in dependencies:
                # Map variable names to task IDs
                source_task_id = var_to_task_id.get(source_var, source_var)
                target_task_id = var_to_task_id.get(target_var, target_var)

                # Add airflow_task: prefix if not present
                if not source_task_id.startswith('airflow_task:'):
                    source_task_id = f'airflow_task:{source_task_id}'
                if not target_task_id.startswith('airflow_task:'):
                    target_task_id = f'airflow_task:{target_task_id}'

                if source_task_id in task_map and target_task_id in task_map:
                    if target_task_id not in task_map[source_task_id].target_datasets:
                        task_map[source_task_id].target_datasets.append(target_task_id)
                    if source_task_id not in task_map[target_task_id].source_datasets:
                        task_map[target_task_id].source_datasets.append(source_task_id)

            datasets = []
            for task in tasks:
                task_datasets = self.extract_data_sources_from_operators(
                    root, task.id.split(':')[1], file_path, content
                )
                datasets.extend(task_datasets)

            return tasks, datasets

        except Exception as e:
            self.logger.error(f"Failed to analyze Airflow DAG file {file_path}: {e}")
            return [], []
    
    def _find_dag_instantiation(self, root: Node) -> Optional[Node]:
        """Find DAG class instantiation in the AST."""
        def visit_node(node: Node) -> Optional[Node]:
            if node.type == 'assignment':
                right_side = node.child_by_field_name('right')
                if right_side and self._is_dag_call(right_side):
                    return node
            
            if node.type == 'with_statement':
                for child in node.children:
                    if child.type == 'with_clause':
                        for item in child.children:
                            if item.type == 'with_item':
                                # Check direct children for call or as_pattern
                                for subchild in item.children:
                                    if self._is_dag_call(subchild):
                                        return node
                                    # Handle as_pattern: with DAG(...) as dag:
                                    if subchild.type == 'as_pattern':
                                        for pattern_child in subchild.children:
                                            if self._is_dag_call(pattern_child):
                                                return node
            
            for child in node.children:
                result = visit_node(child)
                if result:
                    return result
            
            return None
        
        return visit_node(root)
    
    def _is_dag_call(self, node: Node) -> bool:
        """Check if a node represents a DAG() call."""
        if node.type == 'call':
            func = node.child_by_field_name('function')
            if func:
                func_text = self._get_node_text(func)
                return func_text == 'DAG' or func_text.endswith('.DAG')
        return False
    
    def _extract_tasks(self, root: Node, file_path: str, content: str) -> List[TransformationNode]:
        """Extract task definitions from Airflow DAG."""
        tasks = []
        
        def visit_node(node: Node):
            if node.type == 'assignment':
                right_side = node.child_by_field_name('right')
                if right_side and right_side.type == 'call':
                    func = right_side.child_by_field_name('function')
                    if func:
                        func_text = self._get_node_text(func)
                        if 'Operator' in func_text or 'Sensor' in func_text:
                            task_id = self._extract_task_id(right_side)
                            if task_id:
                                line_range = (node.start_point[0] + 1, node.end_point[0] + 1)
                                transformation = TransformationNode(
                                    id=f"airflow_task:{task_id}",
                                    source_datasets=[],
                                    target_datasets=[],
                                    transformation_type="airflow_task",
                                    source_file=file_path,
                                    line_range=line_range,
                                    provenance=ProvenanceMetadata(
                                        evidence_type="tree_sitter",
                                        source_file=file_path,
                                        line_range=line_range,
                                        confidence=1.0,
                                        resolution_status="resolved"
                                    )
                                )
                                tasks.append(transformation)
            
            for child in node.children:
                visit_node(child)
        
        visit_node(root)
        return tasks
    
    def _extract_task_id(self, call_node: Node) -> Optional[str]:
        """Extract task_id from operator call arguments."""
        args = call_node.child_by_field_name('arguments')
        if not args:
            return None
        
        for child in args.children:
            if child.type == 'keyword_argument':
                name_node = child.child_by_field_name('name')
                if name_node and self._get_node_text(name_node) == 'task_id':
                    value_node = child.child_by_field_name('value')
                    if value_node and value_node.type == 'string':
                        task_id = self._get_node_text(value_node).strip('"\'')
                        return task_id
        
        return None

    def _build_var_to_task_map(self, root: Node) -> dict:
        """Build mapping from variable names to task IDs."""
        var_to_task = {}

        def visit_node(node: Node):
            if node.type == 'assignment':
                left_side = node.child_by_field_name('left')
                right_side = node.child_by_field_name('right')

                if left_side and right_side and right_side.type == 'call':
                    func = right_side.child_by_field_name('function')
                    if func:
                        func_text = self._get_node_text(func)
                        if 'Operator' in func_text or 'Sensor' in func_text:
                            var_name = self._get_node_text(left_side)
                            task_id = self._extract_task_id(right_side)
                            if var_name and task_id:
                                var_to_task[var_name] = task_id

            for child in node.children:
                visit_node(child)

        visit_node(root)
        return var_to_task

    
    def extract_task_dependencies(self, root: Node, file_path: str, content: str) -> List[Tuple[str, str, str]]:
        """Extract task dependencies for set_upstream, set_downstream, >>, << operators."""
        dependencies = []

        def visit_node(node: Node):
            # Look for method calls: task1.set_downstream(task2)
            if node.type == 'call':
                func = node.child_by_field_name('function')
                if func and func.type == 'attribute':
                    method_name = self._get_node_text(func.child_by_field_name('attribute'))

                    if method_name in ['set_downstream', 'set_upstream']:
                        obj = func.child_by_field_name('object')
                        source_task = self._get_node_text(obj) if obj else None

                        args = node.child_by_field_name('arguments')
                        if args and args.children:
                            for arg in args.children:
                                if arg.type == 'identifier':
                                    target_task = self._get_node_text(arg)

                                    if method_name == 'set_downstream':
                                        dependencies.append((source_task, target_task, "resolved"))
                                    else:
                                        dependencies.append((target_task, source_task, "resolved"))

            # Look for binary operators: task1 >> task2 or task1 << task2
            elif node.type == 'binary_operator':
                # Check if this is inside a conditional (if/else)
                resolution_status = "resolved"
                parent = node.parent
                while parent:
                    if parent.type in ['if_statement', 'conditional_expression']:
                        resolution_status = "partial"
                        break
                    parent = parent.parent

                # Extract left and right operands using field names
                left_node = node.child_by_field_name('left')
                right_node = node.child_by_field_name('right')
                operator_node = node.child_by_field_name('operator')

                if left_node and right_node and operator_node:
                    left = self._get_node_text(left_node)
                    right = self._get_node_text(right_node)
                    operator = self._get_node_text(operator_node)

                    if operator == '>>':
                        dependencies.append((left, right, resolution_status))
                    elif operator == '<<':
                        dependencies.append((right, left, resolution_status))

            # Recursively visit children
            for child in node.children:
                visit_node(child)

        visit_node(root)
        return dependencies
    
    def extract_data_sources_from_operators(self, root: Node, task_id: str, file_path: str, content: str) -> List[DatasetNode]:
        """Extract data sources from operator parameters."""
        datasets = []
        
        def visit_node(node: Node):
            if node.type == 'assignment':
                right_side = node.child_by_field_name('right')
                if right_side and right_side.type == 'call':
                    extracted_task_id = self._extract_task_id(right_side)
                    if extracted_task_id == task_id:
                        args = right_side.child_by_field_name('arguments')
                        if args:
                            datasets.extend(self._extract_datasets_from_args(
                                args, file_path, node.start_point[0] + 1, node.end_point[0] + 1
                            ))
            
            for child in node.children:
                visit_node(child)
        
        visit_node(root)
        return datasets
    
    def _extract_datasets_from_args(self, args_node: Node, file_path: str, start_line: int, end_line: int) -> List[DatasetNode]:
        """Extract dataset references from operator arguments."""
        datasets = []
        
        data_params = [
            'sql', 'query', 'table', 'table_name', 'source_table', 'target_table',
            'bucket', 's3_key', 'filename', 'filepath', 'path', 'dataset_id',
            'postgres_conn_id', 'mysql_conn_id', 'bigquery_table'
        ]
        
        for child in args_node.children:
            if child.type == 'keyword_argument':
                name_node = child.child_by_field_name('name')
                value_node = child.child_by_field_name('value')
                
                if name_node and value_node:
                    param_name = self._get_node_text(name_node)
                    
                    if param_name in data_params:
                        confidence = 1.0
                        resolution_status = "resolved"
                        storage_type = "table"
                        
                        if value_node.type == 'string':
                            dataset_name = self._get_node_text(value_node).strip('"\'')
                            confidence = 1.0
                            resolution_status = "resolved"
                        elif value_node.type == 'identifier':
                            dataset_name = self._get_node_text(value_node)
                            confidence = 0.5
                            resolution_status = "dynamic"
                        elif value_node.type == 'call':
                            dataset_name = self._get_node_text(value_node)
                            confidence = 0.3
                            resolution_status = "dynamic"
                        else:
                            dataset_name = self._get_node_text(value_node)
                            confidence = 0.3
                            resolution_status = "dynamic"
                        
                        if 's3' in param_name or 'bucket' in param_name:
                            storage_type = "file"
                        elif 'api' in param_name or 'endpoint' in param_name:
                            storage_type = "api"
                        
                        dataset = DatasetNode(
                            name=dataset_name,
                            storage_type=storage_type,
                            discovered_in=file_path,
                            provenance=ProvenanceMetadata(
                                evidence_type="tree_sitter",
                                source_file=file_path,
                                line_range=(start_line, end_line),
                                confidence=confidence,
                                resolution_status=resolution_status
                            )
                        )
                        datasets.append(dataset)
        
        return datasets
    
    def _get_node_text(self, node: Node) -> str:
        """Get text content of a node."""
        return node.text.decode('utf8') if node and node.text else ""
