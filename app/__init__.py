from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from os import path

db = SQLAlchemy()
migrate = Migrate()
DB_NAME = "car_rental.db"

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'  # Change this in production
    
    # Use an absolute path for the database
    base_dir = path.abspath(path.dirname(__file__))
    db_path = path.join(base_dir, DB_NAME)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    migrate.init_app(app, db)

    from .auth import auth
    from .routes import main
    from .models import User, Customer, Car, Booking, Maintenance, Expense

    with app.app_context():
        # Create database if it doesn't exist
        if not path.exists(db_path):
            db.create_all()

    app.register_blueprint(auth)
    app.register_blueprint(main)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
