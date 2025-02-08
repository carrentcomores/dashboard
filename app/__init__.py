from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from os import path
import os

db = SQLAlchemy()
migrate = Migrate()
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

    from .auth import auth
    from .routes import main
    from .models import User, Customer, Car, Booking, Maintenance, Expense

    with app.app_context():
        # Ensure database is created
        db.create_all()

    app.register_blueprint(auth)
    app.register_blueprint(main)

    # Login Manager Configuration
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
