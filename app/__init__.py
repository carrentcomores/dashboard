from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from os import path
import os
import secrets
import logging
import traceback

db = SQLAlchemy()
migrate = Migrate()
DB_NAME = "car_rental.db"

def create_app(config_object=None):
    app = Flask(__name__)
    
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Apply configuration
    if config_object:
        app.config.from_object(config_object)
    
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
                    is_admin=True
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
