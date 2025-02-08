from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from os import path
import os

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
DB_NAME = "car_rental.db"

def create_app(config_object=None):
    app = Flask(__name__)
    
    # Load configuration
    if config_object:
        app.config.from_object(config_object)
    
    # Use environment variable or default configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key')
    
    # Database configuration
    if 'SQLALCHEMY_DATABASE_URI' not in app.config:
        # Use an absolute path for the database
        base_dir = path.abspath(path.dirname(__file__))
        db_path = path.join(base_dir, DB_NAME)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
            'DATABASE_URL', 
            f'sqlite:///{db_path}'
        )
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Import and register blueprints
    from .auth import auth
    from .routes import main
    
    app.register_blueprint(auth)
    app.register_blueprint(main)
    
    # Login Manager Configuration
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    
    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))
    
    # Ensure database is created
    with app.app_context():
        db.create_all()
        
        # Optional: Create admin user
        try:
            from .models import User
            from werkzeug.security import generate_password_hash
            
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
    
    return app

# Create the app instance
app = create_app()
