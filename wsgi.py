from app.wsgi_app import app

# Determine the configuration environment
config_name = os.environ.get('FLASK_ENV', 'production')

# Import the configuration
from config import config

if __name__ == "__main__":
    app.run()
