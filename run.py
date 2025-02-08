import os
import logging
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError
from config import config

# Determine the configuration environment
config_name = os.environ.get('FLASK_ENV', 'production')

# Create the Flask application
app = create_app(config[config_name])

# Configure logging
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, 'app.log'))
    ]
)

# Optionally, configure Flask's logger
app.logger.setLevel(logging.INFO)

# Ensure admin user exists
def create_admin_user():
    with app.app_context():
        try:
            admin = User.query.filter_by(email='admin@carrent.com').first()
            if not admin:
                admin = User(
                    name='Admin',
                    email='admin@carrent.com',
                    employee_id='admin',
                    password=generate_password_hash('admin123'),
                    is_admin=True,
                    role='admin'
                )
                db.session.add(admin)
                db.session.commit()
                print("Admin user created successfully.")
            else:
                print("Admin user already exists.")
        except Exception as e:
            print(f"Error creating admin user: {e}")

# Create admin user when the script is run directly
if __name__ == '__main__':
    create_admin_user()
    print("Starting Car Rent System...")
    print("Application starting on http://0.0.0.0:5003")
    app.run(debug=True, host='0.0.0.0', port=5003)
else:
    # When imported, create admin user
    create_admin_user()