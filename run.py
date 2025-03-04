from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError
import logging
import os

# Ensure log directory exists
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, 'app.log'))
    ]
)

app = create_app()

# Optionally, configure Flask's logger
app.logger.setLevel(logging.INFO)

if __name__ == '__main__':
    print("Starting Car Rent System...")
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Ensure admin user exists
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

    # Run the app with debug mode and logging
    print("Application starting on http://0.0.0.0:5003")
    app.run(debug=True, host='0.0.0.0', port=5003)