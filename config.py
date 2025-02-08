import os
import urllib.parse
from datetime import timedelta

class Config:
    # Secret key for sessions and CSRF protection
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-hard-to-guess-secret-key'
    
    # SQLAlchemy database configuration
    # Support both Heroku PostgreSQL and local SQLite
    if os.environ.get('DATABASE_URL'):
        # Heroku PostgreSQL configuration
        uri = os.environ.get('DATABASE_URL')
        if uri and uri.startswith('postgres://'):
            uri = uri.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = uri
    else:
        # Fallback to SQLite for local development
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///carrent.db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask-Login configuration
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    
    # Security settings
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    
    # Upload configurations
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max file upload
    
    # Logging configuration
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT', 'true') == 'true'
    
    # Email configuration (if using email services)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    DEBUG = False
    
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
