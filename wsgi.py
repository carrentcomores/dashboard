import os
import sys

# Get the absolute path of the project directory
project_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_dir)

# Add parent directory to Python path
parent_dir = os.path.dirname(project_dir)
sys.path.insert(0, parent_dir)

# Debugging: print Python path
print("Python path:", sys.path)

# Try multiple import strategies
try:
    from config import config
except ImportError:
    try:
        from "Car Rent System".config import config
    except ImportError:
        # Last resort: manually add the directory
        sys.path.insert(0, os.path.join(project_dir, 'Car Rent System'))
        from config import config

# Import create_app
from app import create_app

# Determine the configuration environment
config_name = os.environ.get('FLASK_ENV', 'production')

# Create the Flask application
application = create_app(config[config_name])

if __name__ == "__main__":
    application.run()
