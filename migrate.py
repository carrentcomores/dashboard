from flask_migrate import Migrate, upgrade
from app import create_app, db
from config import config
import os
import logging
from werkzeug.security import generate_password_hash

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Determine the configuration environment
config_name = os.environ.get('FLASK_ENV', 'production')

# Create the Flask application
app = create_app(config[config_name])

# Initialize Flask-Migrate
migrate = Migrate(app, db)

def run_migrations():
    with app.app_context():
        try:
            # Upgrade the database to the latest version
            upgrade()
            logger.info("Database migrations completed successfully.")

            # Check and create admin user if not exists
            from app.models import User
            admin_email = os.environ.get('ADMIN_EMAIL', 'admin@carrent.com')
            admin_password = os.environ.get('ADMIN_PASSWORD', 'default_admin_password')
            
            existing_admin = User.query.filter_by(email=admin_email).first()
            if not existing_admin:
                new_admin = User(
                    email=admin_email, 
                    password=generate_password_hash(admin_password, method='pbkdf2:sha256'),
                    is_admin=True,
                    role='admin',
                    name='System Administrator',
                    employee_id='ADMIN001',  # Specific employee ID
                    is_active=True
                )
                db.session.add(new_admin)
                db.session.commit()
                logger.info(f"Created admin user: {admin_email}")
            else:
                logger.info("Admin user already exists.")
        
        except Exception as e:
            logger.error(f"Error during migration: {str(e)}")
            raise

if __name__ == '__main__':
    run_migrations()
