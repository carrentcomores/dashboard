import os
import sys

# Get the absolute path of the project directory
project_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_dir)

# Print sys.path for debugging
print("Python path:", sys.path)

# Modify Python path to include parent directory
parent_dir = os.path.dirname(project_dir)
sys.path.insert(0, parent_dir)

# Absolute imports
from config import config
from app import create_app

# Determine the configuration environment
config_name = os.environ.get('FLASK_ENV', 'production')

# Create the Flask application
application = create_app(config[config_name])

if __name__ == "__main__":
    application.run()
