import os
import sys
import importlib.util

# Get the absolute path of the project directory
project_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_dir)

# Add parent directory to Python path
parent_dir = os.path.dirname(project_dir)
sys.path.insert(0, parent_dir)

# Debugging: print Python path
print("Python path:", sys.path)

# Dynamic import function
def dynamic_import(module_path):
    module_name = os.path.splitext(os.path.basename(module_path))[0]
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Try to import config
try:
    import config
except ImportError:
    # Try alternative import methods
    config_paths = [
        os.path.join(project_dir, 'config.py'),
        os.path.join(parent_dir, 'config.py'),
        os.path.join(project_dir, 'Car Rent System', 'config.py')
    ]
    
    for path in config_paths:
        if os.path.exists(path):
            config = dynamic_import(path)
            break
    else:
        raise ImportError("Could not find config module")

# Import create_app
from app import create_app

# Determine the configuration environment
config_name = os.environ.get('FLASK_ENV', 'production')

# Create the Flask application
application = create_app(config.config[config_name])

if __name__ == "__main__":
    application.run()
