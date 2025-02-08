from . import create_app
import os
from config import config

# Determine the configuration environment
config_name = os.environ.get('FLASK_ENV', 'production')

# Create the Flask application
app = create_app(config[config_name])

# This ensures the app is directly importable by Gunicorn
if __name__ == "__main__":
    app.run()
