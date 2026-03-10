"""Unit tests for LanguageRouter."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

import pytest
from analyzers.language_router import LanguageRouter


class TestLanguageRouter:
    """Test suite for LanguageRouter."""
    
    def test_supported_extensions(self):
        """Test that all required extensions are supported."""
        router = LanguageRouter()
        
        supported = ['.py', '.sql', '.yaml', '.yml', '.js', '.ts']
        for ext in supported:
            assert router.is_supported(ext), f"Extension {ext} should be supported"
    
    def test_unsupported_extension(self):
        """Test that unsupported extensions raise ValueError."""
        router = LanguageRouter()
        
        with pytest.raises(ValueError):
            router.get_parser('.txt')
    
    def test_python_parser(self):
        """Test that Python files get a parser."""
        router = LanguageRouter()
        parser = router.get_parser('.py')
        assert parser is not None
    
    def test_sql_yaml_no_parser(self):
        """Test that SQL and YAML return None (handled separately)."""
        router = LanguageRouter()
        
        assert router.get_parser('.sql') is None
        assert router.get_parser('.yaml') is None
        assert router.get_parser('.yml') is None
    
    def test_language_names(self):
        """Test language name mapping."""
        router = LanguageRouter()
        
        assert router.get_language_name('.py') == 'python'
        assert router.get_language_name('.js') == 'javascript'
        assert router.get_language_name('.ts') == 'typescript'
        assert router.get_language_name('.sql') == 'sql'
        assert router.get_language_name('.yaml') == 'yaml'
        assert router.get_language_name('.yml') == 'yaml'
