"""Language router for mapping file extensions to tree-sitter parsers."""

from typing import Optional
from tree_sitter import Language, Parser
import tree_sitter_python
import tree_sitter_javascript


class LanguageRouter:
    """Routes files to appropriate tree-sitter grammar based on extension."""
    
    def __init__(self):
        """Initialize language router with supported parsers."""
        self._parsers = {}
        self._languages = {}
        self._setup_parsers()
    
    def _setup_parsers(self):
        """Set up tree-sitter parsers for supported languages."""
        # Python language and parser
        python_lang = Language(tree_sitter_python.language())
        python_parser = Parser(python_lang)
        self._parsers['.py'] = python_parser
        self._languages['.py'] = python_lang
        
        # JavaScript/TypeScript language and parser
        js_lang = Language(tree_sitter_javascript.language())
        js_parser = Parser(js_lang)
        self._parsers['.js'] = js_parser
        self._parsers['.ts'] = js_parser  # TypeScript uses same parser
        self._languages['.js'] = js_lang
        self._languages['.ts'] = js_lang
        
        # SQL and YAML are handled by sqlglot and PyYAML respectively
        # We mark them as supported but don't create tree-sitter parsers
        self._parsers['.sql'] = None  # Handled by sqlglot
        self._parsers['.yaml'] = None  # Handled by PyYAML
        self._parsers['.yml'] = None  # Handled by PyYAML
    
    def get_parser(self, file_extension: str) -> Optional[Parser]:
        """
        Get the appropriate parser for a file extension.
        
        Args:
            file_extension: File extension including the dot (e.g., '.py')
        
        Returns:
            Parser instance for the language, or None if SQL/YAML (handled separately)
        
        Raises:
            ValueError: If the file extension is not supported
        """
        if file_extension not in self._parsers:
            raise ValueError(f"Unsupported file extension: {file_extension}")
        
        return self._parsers[file_extension]
    
    def is_supported(self, file_extension: str) -> bool:
        """
        Check if a file extension is supported.
        
        Args:
            file_extension: File extension including the dot (e.g., '.py')
        
        Returns:
            True if the extension is supported, False otherwise
        """
        return file_extension in self._parsers
    
    def get_language_name(self, file_extension: str) -> str:
        """
        Get the language name for a file extension.
        
        Args:
            file_extension: File extension including the dot (e.g., '.py')
        
        Returns:
            Language name (e.g., 'python', 'javascript', 'sql', 'yaml')
        
        Raises:
            ValueError: If the file extension is not supported
        """
        if not self.is_supported(file_extension):
            raise ValueError(f"Unsupported file extension: {file_extension}")
        
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.sql': 'sql',
            '.yaml': 'yaml',
            '.yml': 'yaml',
        }
        
        return language_map[file_extension]
