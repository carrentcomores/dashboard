import sys
import os

# Add the project directory to the Python path
project_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_dir)

# Import the create_app function
from app import create_app
from config import config

# Determine the configuration environment
config_name = os.environ.get('FLASK_ENV', 'production')

# Create the Flask application
application = create_app(config[config_name])

if __name__ == "__main__":
    application.run()
