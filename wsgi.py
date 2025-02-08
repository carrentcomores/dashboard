import sys
import os

# Add the project directory to the Python path
project_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_dir)

# Ensure the virtual environment's site-packages is in the path
venv_path = os.path.join(project_dir, 'venv', 'lib', 'python3.10', 'site-packages')
if os.path.exists(venv_path):
    sys.path.insert(0, venv_path)

# Import the configuration and create_app function
from config import config
from app import create_app

# Determine the configuration environment
config_name = os.environ.get('FLASK_ENV', 'production')

# Create the Flask application
application = create_app(config[config_name])

if __name__ == "__main__":
    application.run()
