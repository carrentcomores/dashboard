from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from os import path
import os
import secrets
import logging
import traceback
import sys

db = SQLAlchemy()
migrate = Migrate()
DB_NAME = "car_rental.db"

def configure_logging(app):
    # Remove all existing handlers
    del app.logger.handlers[:]
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Create file handler for errors
    log_dir = path.join(path.dirname(path.abspath(__file__)), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(path.join(log_dir, 'app.log'))
    file_handler.setLevel(logging.ERROR)
    
    # Create formatters
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    
    # Set formatters
    console_handler.setFormatter(console_formatter)
    file_handler.setFormatter(file_formatter)
    
    # Add handlers to the app logger
    app.logger.addHandler(console_handler)
    app.logger.addHandler(file_handler)
    
    # Set logging level
    app.logger.setLevel(logging.DEBUG)

def create_app(config_object=None):
    app = Flask(__name__)
    
    # Apply configuration
    if config_object:
        app.config.from_object(config_object)
    
    # Configure logging early
    configure_logging(app)
    
    # Ensure a valid SECRET_KEY
    if not app.config.get('SECRET_KEY'):
        # Generate a secure random secret key
        app.config['SECRET_KEY'] = secrets.token_hex(32)
    
    # Ensure SECRET_KEY is a string
    app.config['SECRET_KEY'] = str(app.config['SECRET_KEY'])
    
    # Use an absolute path for the database
    base_dir = path.abspath(path.dirname(__file__))
    db_path = path.join(base_dir, DB_NAME)
    
    # Set database URI if not already set
    if 'SQLALCHEMY_DATABASE_URI' not in app.config:
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    migrate.init_app(app, db)

    from .auth import auth
    from .routes import main
    from .models import User, Customer, Car, Booking, Maintenance, Expense

    # Add error handling
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Log the full traceback
        app.logger.error(f"Unhandled Exception: {str(e)}")
        app.logger.error(traceback.format_exc())
        
        # For production, return a generic error message
        return "An internal server error occurred", 500

    with app.app_context():
        # Ensure database is created
        try:
            db.create_all()
            
            # Check if admin user exists, if not create one
            admin_email = os.environ.get('ADMIN_EMAIL', 'admin@carrent.com')
            admin_password = os.environ.get('ADMIN_PASSWORD', 'default_admin_password')
            
            existing_admin = User.query.filter_by(email=admin_email).first()
            if not existing_admin:
                from werkzeug.security import generate_password_hash
                new_admin = User(
                    email=admin_email, 
                    password=generate_password_hash(admin_password, method='pbkdf2:sha256'),
                    is_admin=True,
                    role='admin',
                    name='System Administrator',
                    employee_id='ADMIN001',
                    is_active=True
                )
                db.session.add(new_admin)
                db.session.commit()
                app.logger.info(f"Created admin user: {admin_email}")
        except Exception as e:
            app.logger.error(f"Error during database initialization: {str(e)}")
            app.logger.error(traceback.format_exc())

    app.register_blueprint(auth)
    app.register_blueprint(main)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
