from app import create_app
import os

# Determine the configuration environment
config_name = os.environ.get('FLASK_ENV', 'production')

# Import the configuration
from config import config

# Create the Flask application
app = create_app(config[config_name])

if __name__ == "__main__":
    app.run()
