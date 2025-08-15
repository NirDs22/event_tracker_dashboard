#!/usr/bin/env python3

import os
import ast
import sys

def extract_imports_from_file(filename):
    """Extract all imports from a Python file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split('.')[0]
                    imports.add(module_name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split('.')[0]
                    imports.add(module_name)
        
        return imports
    except Exception as e:
        print(f"Error parsing {filename}: {e}")
        return set()

def get_all_imports():
    """Get all imports from all Python files in the project."""
    all_imports = set()
    
    for root, dirs, files in os.walk('.'):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', '.streamlit']]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                file_imports = extract_imports_from_file(filepath)
                all_imports.update(file_imports)
    
    return sorted(all_imports)

if __name__ == "__main__":
    imports = get_all_imports()
    print("All third-party imports found in the project:")
    
    # Filter out standard library imports
    stdlib_modules = {
        'os', 'sys', 'datetime', 'time', 'json', 'logging', 'typing',
        'random', 'html', 're', 'textwrap', 'difflib', 'urllib', 'ast'
    }
    
    third_party = [imp for imp in imports if imp not in stdlib_modules]
    
    for imp in third_party:
        print(f"  {imp}")
