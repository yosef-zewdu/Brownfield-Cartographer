"""Setup script for tree-sitter grammars."""

import os
import subprocess
import sys
from pathlib import Path
from tree_sitter import Language

# Grammar repositories
GRAMMARS = {
    "python": "https://github.com/tree-sitter/tree-sitter-python",
    "javascript": "https://github.com/tree-sitter/tree-sitter-javascript", 
    "typescript": "https://github.com/tree-sitter/tree-sitter-typescript",
    "sql": "https://github.com/DerekStride/tree-sitter-sql",
    "yaml": "https://github.com/ikatyang/tree-sitter-yaml",
}


def check_pip_packages():
    """Check if tree-sitter grammar packages are installed via pip."""
    required_packages = [
        "tree-sitter-python",
        "tree-sitter-javascript",
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✓ {package} is installed")
        except ImportError:
            missing.append(package)
            print(f"✗ {package} is missing")
    
    return missing


def install_missing_packages(missing_packages):
    """Install missing tree-sitter packages via pip."""
    if not missing_packages:
        return
    
    print(f"\nInstalling missing packages: {', '.join(missing_packages)}")
    for package in missing_packages:
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", package
            ], check=True)
            print(f"✓ Installed {package}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install {package}: {e}")


def setup_grammars():
    """Set up tree-sitter grammars (check pip packages)."""
    print("Checking tree-sitter grammar setup...")
    print("=" * 50)
    
    # Check pip packages first (recommended approach)
    missing = check_pip_packages()
    
    if missing:
        print(f"\nFound {len(missing)} missing packages.")
        install_missing_packages(missing)
    else:
        print("\n✓ All required tree-sitter grammars are available!")
    
    print("\nNote: SQL parsing uses sqlglot, YAML parsing uses PyYAML")
    print("These are more reliable than tree-sitter for these languages.")


if __name__ == "__main__":
    setup_grammars()
