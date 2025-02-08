from app import create_app, db
from config import config
import os

# Determine the configuration environment
config_name = os.environ.get('FLASK_ENV', 'production')

# Create the Flask application
app = create_app(config[config_name])

# Ensure admin user exists (optional, can be moved to a separate script)
def create_admin_user():
    from app.models import User
    from werkzeug.security import generate_password_hash
    
    with app.app_context():
        try:
            from sqlalchemy.exc import IntegrityError
            
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

# Create admin user when the module is imported
create_admin_user()
