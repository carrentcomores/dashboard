from flask_migrate import Migrate, upgrade
from app import create_app, db
from config import config
import os

# Determine the configuration environment
config_name = os.environ.get('FLASK_ENV', 'production')

# Create the Flask application
app = create_app(config[config_name])

# Initialize Flask-Migrate
migrate = Migrate(app, db)

def run_migrations():
    with app.app_context():
        # Upgrade the database to the latest version
        upgrade()
        print("Database migrations completed successfully.")

if __name__ == '__main__':
    run_migrations()
