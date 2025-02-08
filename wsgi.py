import os
import sys

# Get the absolute path of the project directory
project_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_dir)

# Debugging: print Python path
print("Python path:", sys.path)

# Import config
import config

# Import create_app
from app import create_app

# Determine the configuration environment
config_name = os.environ.get('FLASK_ENV', 'production')

# Create the Flask application
application = create_app(config.config[config_name])

if __name__ == "__main__":
    application.run()
