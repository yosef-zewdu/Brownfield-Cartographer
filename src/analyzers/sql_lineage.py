"""SQL lineage analyzer for extracting table dependencies using sqlglot."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import sqlglot
from sqlglot import exp

from models import TransformationNode, ProvenanceMetadata


class SQLLineageAnalyzer:
    """Analyzes SQL files to extract table dependencies with provenance tracking."""
    
    def __init__(self):
        """Initialize analyzer with supported SQL dialects."""
        self.supported_dialects = {
            'postgres': 'postgres',
            'bigquery': 'bigquery',
            'snowflake': 'snowflake',
            'duckdb': 'duckdb'
        }
        self.logger = logging.getLogger(__name__)
    
    def analyze_file(self, file_path: str, dialect: str = 'postgres') -> List[TransformationNode]:
        """
        Analyze a SQL file for table dependencies.
        
        Args:
            file_path: Path to SQL file to analyze
            dialect: SQL dialect to use for parsing
            
        Returns:
            List of TransformationNode instances for detected operations
        """
        if not file_path.endswith('.sql'):
            return []
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.logger.error(f"Failed to read SQL file {file_path}: {e}")
            return []
        
        return self.parse_sql(content, file_path, dialect)
    
    def parse_sql(self, sql_content: str, source_file: str, dialect: str = 'postgres') -> List[TransformationNode]:
        """
        Parse SQL content using sqlglot with provenance tracking.
        
        Args:
            sql_content: SQL content to parse
            source_file: Path to source file for provenance
            dialect: SQL dialect to use for parsing
            
        Returns:
            List of TransformationNode instances for detected operations
        """
        transformations = []
        
        # Handle multi-statement SQL files
        statements = self._split_sql_statements(sql_content)
        
        for i, statement in enumerate(statements):
            if not statement.strip():
                continue
                
            try:
                # Parse the SQL statement
                parsed = sqlglot.parse_one(statement, dialect=dialect)
                if parsed is None:
                    continue
                
                # Extract table dependencies
                source_tables, target_tables, ctes = self.extract_table_dependencies(parsed)
                
                # Calculate line range for this statement
                line_start = self._get_statement_line_number(sql_content, statement, i)
                line_end = line_start + statement.count('\n')
                
                # Create transformation node
                transformation_id = f"{source_file}:{line_start}:sql_statement_{i}"
                
                transformations.append(TransformationNode(
                    id=transformation_id,
                    source_datasets=list(source_tables),
                    target_datasets=list(target_tables),
                    transformation_type="sql",
                    source_file=source_file,
                    line_range=(line_start, line_end),
                    sql_query=statement.strip(),
                    provenance=ProvenanceMetadata(
                        evidence_type="sqlglot",
                        source_file=source_file,
                        line_range=(line_start, line_end),
                        confidence=self._calculate_confidence(source_tables, target_tables, ctes),
                        resolution_status=self._determine_resolution_status(source_tables, target_tables, ctes)
                    )
                ))
                
            except Exception as e:
                # Log unparseable SQL with confidence=0.0
                self.logger.warning(f"Failed to parse SQL statement in {source_file}: {e}")
                line_start = self._get_statement_line_number(sql_content, statement, i)
                line_end = line_start + statement.count('\n')
                
                transformation_id = f"{source_file}:{line_start}:unparseable_sql_{i}"
                
                transformations.append(TransformationNode(
                    id=transformation_id,
                    source_datasets=[],
                    target_datasets=[],
                    transformation_type="sql",
                    source_file=source_file,
                    line_range=(line_start, line_end),
                    sql_query=statement.strip(),
                    provenance=ProvenanceMetadata(
                        evidence_type="sqlglot",
                        source_file=source_file,
                        line_range=(line_start, line_end),
                        confidence=0.0,
                        resolution_status="dynamic"
                    )
                ))
        
        return transformations
    
    def extract_table_dependencies(self, parsed_sql: exp.Expression) -> Tuple[Set[str], Set[str], Set[str]]:
        """
        Extract table dependencies from parsed SQL with confidence scores.
        
        Args:
            parsed_sql: Parsed SQL expression from sqlglot
            
        Returns:
            Tuple of (source_tables, target_tables, ctes)
        """
        source_tables = set()
        target_tables = set()
        ctes = set()
        
        # Extract CTEs first
        ctes = self.handle_cte(parsed_sql)
        if ctes is None:
            ctes = set()
        
        # Extract tables from different SQL operations
        if isinstance(parsed_sql, exp.Select):
            source_tables.update(self._extract_from_select(parsed_sql, ctes))
            
            # Also extract tables from CTE definitions
            for with_clause in parsed_sql.find_all(exp.With):
                for cte in with_clause.expressions:
                    if isinstance(cte, exp.CTE) and cte.this:
                        source_tables.update(self._extract_from_select(cte.this, set()))
        elif isinstance(parsed_sql, exp.Insert):
            table_name = self._get_table_name(parsed_sql.this)
            if table_name:
                target_tables.add(table_name)
            if parsed_sql.expression:
                source_tables.update(self._extract_from_select(parsed_sql.expression, ctes))
        elif isinstance(parsed_sql, exp.Update):
            table_name = self._get_table_name(parsed_sql.this)
            if table_name:
                target_tables.add(table_name)
            source_tables.update(self._extract_from_update(parsed_sql, ctes))
        elif isinstance(parsed_sql, exp.Delete):
            table_name = self._get_table_name(parsed_sql.this)
            if table_name:
                target_tables.add(table_name)
            source_tables.update(self._extract_from_delete(parsed_sql, ctes))
        elif isinstance(parsed_sql, exp.Create):
            if parsed_sql.this:
                table_name = self._get_table_name(parsed_sql.this)
                if table_name:
                    target_tables.add(table_name)
            if parsed_sql.expression:
                source_tables.update(self._extract_from_select(parsed_sql.expression, ctes))
        
        # Remove CTEs from source tables (they're not external dependencies)
        source_tables = source_tables - ctes
        
        return source_tables, target_tables, ctes
    
    def handle_cte(self, parsed_sql: exp.Expression) -> Set[str]:
        """
        Handle common table expressions (CTEs).
        
        Args:
            parsed_sql: Parsed SQL expression
            
        Returns:
            Set of CTE names
        """
        ctes = set()
        
        # Find WITH clauses
        for with_clause in parsed_sql.find_all(exp.With):
            for cte in with_clause.expressions:
                if isinstance(cte, exp.CTE) and cte.alias:
                    ctes.add(cte.alias)
                elif hasattr(cte, 'alias') and cte.alias:
                    # Handle different CTE structures
                    ctes.add(cte.alias)
        
        return ctes
    
    def _split_sql_statements(self, sql_content: str) -> List[str]:
        """Split SQL content into individual statements."""
        # Simple splitting on semicolons - could be enhanced for more complex cases
        statements = []
        current_statement = []
        in_string = False
        string_char = None
        
        lines = sql_content.split('\n')
        for line in lines:
            i = 0
            while i < len(line):
                char = line[i]
                
                if not in_string:
                    if char in ('"', "'"):
                        in_string = True
                        string_char = char
                    elif char == ';':
                        current_statement.append(line[:i])
                        statements.append('\n'.join(current_statement))
                        current_statement = []
                        line = line[i+1:]
                        i = -1
                else:
                    if char == string_char and (i == 0 or line[i-1] != '\\'):
                        in_string = False
                        string_char = None
                
                i += 1
            
            if line.strip():
                current_statement.append(line)
        
        # Add remaining statement if any
        if current_statement:
            statements.append('\n'.join(current_statement))
        
        return [stmt for stmt in statements if stmt.strip()]
    
    def _get_statement_line_number(self, full_content: str, statement: str, statement_index: int) -> int:
        """Calculate the line number where a statement starts."""
        lines_before = full_content[:full_content.find(statement)].count('\n')
        return lines_before + 1
    
    def _extract_from_select(self, select_expr: exp.Select, ctes: Set[str]) -> Set[str]:
        """Extract source tables from SELECT statement."""
        tables = set()
        
        # Use find_all to get all tables in the SELECT statement
        for table in select_expr.find_all(exp.Table):
            table_name = self._get_table_name(table)
            if table_name and table_name not in ctes:
                tables.add(table_name)
        
        return tables
    
    def _extract_from_update(self, update_expr: exp.Update, ctes: Set[str]) -> Set[str]:
        """Extract source tables from UPDATE statement."""
        tables = set()
        
        # Extract from JOIN clauses in UPDATE
        for join in update_expr.find_all(exp.Join):
            table_name = self._get_table_name(join.this)
            if table_name and table_name not in ctes:
                tables.add(table_name)
        
        # Extract from WHERE clause subqueries and all tables
        for table in update_expr.find_all(exp.Table):
            table_name = self._get_table_name(table)
            if table_name and table_name not in ctes:
                tables.add(table_name)
        
        return tables
    
    def _extract_from_delete(self, delete_expr: exp.Delete, ctes: Set[str]) -> Set[str]:
        """Extract source tables from DELETE statement."""
        tables = set()
        
        # Extract from WHERE clause subqueries
        if delete_expr.args.get('where'):
            for subquery in delete_expr.args['where'].find_all(exp.Subquery):
                if subquery.this:
                    tables.update(self._extract_from_select(subquery.this, ctes))
        
        return tables
    
    def _get_table_name(self, table_expr) -> Optional[str]:
        """Extract table name from table expression."""
        if table_expr is None:
            return None
        
        if isinstance(table_expr, exp.Table):
            # Handle schema.table format
            if table_expr.catalog and table_expr.db and table_expr.name:
                return f"{table_expr.catalog}.{table_expr.db}.{table_expr.name}"
            elif table_expr.db and table_expr.name:
                return f"{table_expr.db}.{table_expr.name}"
            elif table_expr.name:
                return table_expr.name
            else:
                return None
        elif isinstance(table_expr, exp.Schema):
            # Handle INSERT INTO table_name (columns) case
            if hasattr(table_expr, 'this') and table_expr.this:
                return self._get_table_name(table_expr.this)
            return None
        elif isinstance(table_expr, exp.Identifier):
            return table_expr.name if table_expr.name else None
        elif hasattr(table_expr, 'name') and table_expr.name:
            return table_expr.name
        
        return None
    
    def _calculate_confidence(self, source_tables: Set[str], target_tables: Set[str], ctes: Set[str]) -> float:
        """Calculate confidence score based on table resolution."""
        total_tables = len(source_tables) + len(target_tables)
        if total_tables == 0:
            return 0.5  # Neutral confidence for statements with no tables
        
        # Higher confidence for explicit table names, lower for dynamic references
        explicit_tables = sum(1 for table in source_tables | target_tables 
                            if '.' in table or table.isidentifier())
        
        return min(1.0, explicit_tables / total_tables)
    
    def _determine_resolution_status(self, source_tables: Set[str], target_tables: Set[str], ctes: Set[str]) -> str:
        """Determine resolution status based on table types."""
        all_tables = source_tables | target_tables
        
        if not all_tables:
            return "inferred"
        
        # Check if all tables are explicit names
        explicit_count = sum(1 for table in all_tables if table.isidentifier() or '.' in table)
        
        if explicit_count == len(all_tables):
            return "resolved"
        elif explicit_count > 0:
            return "partial"
        else:
            return "dynamic"