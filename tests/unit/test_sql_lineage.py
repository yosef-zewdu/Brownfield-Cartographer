"""Unit tests for SQLLineageAnalyzer."""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from analyzers.sql_lineage import SQLLineageAnalyzer
from models import TransformationNode, ProvenanceMetadata


class TestSQLLineageAnalyzer:
    """Test cases for SQLLineageAnalyzer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = SQLLineageAnalyzer()
    
    def test_analyzer_initialization(self):
        """Test that SQLLineageAnalyzer initializes correctly."""
        assert self.analyzer is not None
        assert isinstance(self.analyzer.supported_dialects, dict)
        assert 'postgres' in self.analyzer.supported_dialects
        assert 'bigquery' in self.analyzer.supported_dialects
        assert 'snowflake' in self.analyzer.supported_dialects
        assert 'duckdb' in self.analyzer.supported_dialects
    
    def test_basic_select_parsing(self):
        """Test parsing of basic SELECT statement."""
        sql = "SELECT id, name FROM users WHERE active = true"
        transformations = self.analyzer.parse_sql(sql, "test.sql", "postgres")
        
        assert len(transformations) == 1
        t = transformations[0]
        
        assert isinstance(t, TransformationNode)
        assert 'users' in t.source_datasets
        assert len(t.target_datasets) == 0
        assert t.transformation_type == "sql"
        assert t.source_file == "test.sql"
        assert t.sql_query.strip() == sql
        
        # Check provenance
        assert t.provenance.evidence_type == "sqlglot"
        assert t.provenance.source_file == "test.sql"
        assert t.provenance.confidence > 0
        assert t.provenance.resolution_status in ["resolved", "partial", "dynamic", "inferred"]
    
    def test_join_parsing(self):
        """Test parsing of JOIN statements."""
        sql = """
        SELECT u.name, o.total 
        FROM users u 
        JOIN orders o ON u.id = o.user_id
        WHERE u.active = true
        """
        transformations = self.analyzer.parse_sql(sql, "test.sql", "postgres")
        
        assert len(transformations) == 1
        t = transformations[0]
        
        assert 'users' in t.source_datasets
        assert 'orders' in t.source_datasets
        assert len(t.target_datasets) == 0
        assert t.provenance.confidence == 1.0  # Both tables are explicit
        assert t.provenance.resolution_status == "resolved"
    
    def test_multiple_joins(self):
        """Test parsing of multiple JOIN statements."""
        sql = """
        SELECT u.name, o.total, p.name as product_name
        FROM users u 
        JOIN orders o ON u.id = o.user_id
        JOIN products p ON o.product_id = p.id
        LEFT JOIN categories c ON p.category_id = c.id
        """
        transformations = self.analyzer.parse_sql(sql, "test.sql", "postgres")
        
        assert len(transformations) == 1
        t = transformations[0]
        
        expected_tables = {'users', 'orders', 'products', 'categories'}
        assert set(t.source_datasets) == expected_tables
        assert len(t.target_datasets) == 0
    
    def test_cte_parsing(self):
        """Test parsing of Common Table Expressions (CTEs)."""
        sql = """
        WITH active_users AS (
            SELECT id, name FROM users WHERE active = true
        ),
        recent_orders AS (
            SELECT user_id, total FROM orders WHERE created_at > '2023-01-01'
        )
        SELECT au.name, ro.total
        FROM active_users au
        JOIN recent_orders ro ON au.id = ro.user_id
        """
        transformations = self.analyzer.parse_sql(sql, "test.sql", "postgres")
        
        assert len(transformations) == 1
        t = transformations[0]
        
        # Should find base tables from CTE definitions, not CTE names
        assert 'users' in t.source_datasets
        assert 'orders' in t.source_datasets
        assert 'active_users' not in t.source_datasets  # CTE name should be excluded
        assert 'recent_orders' not in t.source_datasets  # CTE name should be excluded
        assert len(t.target_datasets) == 0
    
    def test_insert_statement(self):
        """Test parsing of INSERT statements."""
        sql = """
        INSERT INTO user_summary (user_id, total_orders, total_amount)
        SELECT user_id, COUNT(*), SUM(total)
        FROM orders
        GROUP BY user_id
        """
        transformations = self.analyzer.parse_sql(sql, "test.sql", "postgres")
        
        assert len(transformations) == 1
        t = transformations[0]
        
        assert 'orders' in t.source_datasets
        assert 'user_summary' in t.target_datasets
    
    def test_create_table_as_select(self):
        """Test parsing of CREATE TABLE AS SELECT statements."""
        sql = """
        CREATE TABLE temp_users AS
        SELECT id, name, email
        FROM users
        WHERE active = true
        """
        transformations = self.analyzer.parse_sql(sql, "test.sql", "postgres")
        
        assert len(transformations) == 1
        t = transformations[0]
        
        assert 'users' in t.source_datasets
        assert 'temp_users' in t.target_datasets
    
    def test_update_statement(self):
        """Test parsing of UPDATE statements."""
        sql = """
        UPDATE customers 
        SET last_order_date = (
            SELECT MAX(order_date) 
            FROM orders 
            WHERE orders.customer_id = customers.id
        )
        WHERE customers.active = true
        """
        transformations = self.analyzer.parse_sql(sql, "test.sql", "postgres")
        
        assert len(transformations) == 1
        t = transformations[0]
        
        assert 'orders' in t.source_datasets
        assert 'customers' in t.target_datasets
    
    def test_multi_statement_sql(self):
        """Test parsing of multi-statement SQL files."""
        sql = """
        CREATE TABLE temp_orders AS
        SELECT * FROM orders WHERE order_date > '2023-01-01';
        
        UPDATE customers 
        SET last_order_date = (
            SELECT MAX(order_date) 
            FROM temp_orders 
            WHERE temp_orders.customer_id = customers.id
        );
        
        DROP TABLE temp_orders;
        """
        transformations = self.analyzer.parse_sql(sql, "test.sql", "postgres")
        
        # Should find multiple transformations for multiple statements
        assert len(transformations) >= 2  # At least CREATE and UPDATE
        
        # Check that we can find the expected tables across statements
        all_source_tables = set()
        all_target_tables = set()
        for t in transformations:
            all_source_tables.update(t.source_datasets)
            all_target_tables.update(t.target_datasets)
        
        assert 'orders' in all_source_tables
        assert 'temp_orders' in all_source_tables or 'temp_orders' in all_target_tables
        assert 'customers' in all_target_tables
    
    def test_schema_qualified_tables(self):
        """Test parsing of schema-qualified table names."""
        sql = """
        SELECT u.name, o.total
        FROM public.users u
        JOIN sales.orders o ON u.id = o.user_id
        """
        transformations = self.analyzer.parse_sql(sql, "test.sql", "postgres")
        
        assert len(transformations) == 1
        t = transformations[0]
        
        # Should handle schema-qualified names
        source_tables = set(t.source_datasets)
        assert any('users' in table for table in source_tables)
        assert any('orders' in table for table in source_tables)
    
    def test_confidence_scoring(self):
        """Test confidence scoring for different types of table references."""
        # Explicit table names should have high confidence
        sql_explicit = "SELECT * FROM users"
        transformations = self.analyzer.parse_sql(sql_explicit, "test.sql", "postgres")
        assert transformations[0].provenance.confidence == 1.0
        
        # Mixed explicit and potential dynamic references
        sql_mixed = "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
        transformations = self.analyzer.parse_sql(sql_mixed, "test.sql", "postgres")
        assert transformations[0].provenance.confidence >= 0.5
    
    def test_resolution_status(self):
        """Test resolution status determination."""
        # Explicit table names should be "resolved"
        sql = "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
        transformations = self.analyzer.parse_sql(sql, "test.sql", "postgres")
        assert transformations[0].provenance.resolution_status == "resolved"
    
    def test_unparseable_sql_handling(self):
        """Test handling of unparseable SQL."""
        # Intentionally malformed SQL
        sql = "SELCT * FORM users WHRE invalid syntax"
        transformations = self.analyzer.parse_sql(sql, "test.sql", "postgres")
        
        # Should still create a transformation node with confidence 0.0
        assert len(transformations) == 1
        t = transformations[0]
        assert t.provenance.confidence == 0.0
        assert t.provenance.resolution_status == "dynamic"
        assert len(t.source_datasets) == 0
        assert len(t.target_datasets) == 0
    
    def test_different_dialects(self):
        """Test parsing with different SQL dialects."""
        sql = "SELECT * FROM users"
        
        for dialect in self.analyzer.supported_dialects.keys():
            transformations = self.analyzer.parse_sql(sql, "test.sql", dialect)
            assert len(transformations) == 1
            assert 'users' in transformations[0].source_datasets
    
    def test_analyze_file_method(self):
        """Test the analyze_file method."""
        # Test with non-SQL file
        transformations = self.analyzer.analyze_file("test.py", "postgres")
        assert len(transformations) == 0
        
        # Test with SQL file (would need actual file, so we test the extension check)
        assert self.analyzer.analyze_file("test.txt") == []
    
    def test_empty_sql_handling(self):
        """Test handling of empty or whitespace-only SQL."""
        transformations = self.analyzer.parse_sql("", "test.sql", "postgres")
        assert len(transformations) == 0
        
        transformations = self.analyzer.parse_sql("   \n\t  ", "test.sql", "postgres")
        assert len(transformations) == 0
    
    def test_line_range_tracking(self):
        """Test that line ranges are correctly tracked."""
        sql = """
        SELECT * FROM users;
        
        SELECT * FROM orders;
        """
        transformations = self.analyzer.parse_sql(sql, "test.sql", "postgres")
        
        assert len(transformations) == 2
        
        # Line ranges should be different for each statement
        line_ranges = [t.line_range for t in transformations]
        assert len(set(line_ranges)) == 2  # Should have unique line ranges
        
        # Each transformation should have valid line range
        for t in transformations:
            assert isinstance(t.line_range, tuple)
            assert len(t.line_range) == 2
            assert t.line_range[0] >= 1  # Line numbers start at 1
            assert t.line_range[1] >= t.line_range[0]  # End >= start