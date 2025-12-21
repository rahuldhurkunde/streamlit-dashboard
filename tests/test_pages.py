import ast
import os
import pytest

def test_pages_syntax():
    """
    Parses all python files in the project root and pages/ directory 
    to ensure there are no syntax errors (including indentation errors).
    """
    # Define directories to check
    directories = ['.', 'pages']
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    for directory in directories:
        dir_path = os.path.join(project_root, directory)
        if not os.path.exists(dir_path):
            continue
            
        for filename in os.listdir(dir_path):
            if filename.endswith(".py"):
                file_path = os.path.join(dir_path, filename)
                
                # Skip virtual envs or other ignored folders if they happen to be scanned
                # (Though here we are strict about directories)
                
                with open(file_path, "r", encoding="utf-8") as f:
                    source = f.read()
                
                try:
                    ast.parse(source, filename=filename)
                except SyntaxError as e:
                    pytest.fail(f"SyntaxError in {file_path}: {e}")
                except Exception as e:
                    pytest.fail(f"Error parsing {file_path}: {e}")
