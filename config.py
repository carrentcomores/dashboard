import os
from datetime import timedelta

class Config:
    # Secret key for sessions and CSRF protection
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-hard-to-guess-secret-key'
    
    # SQLAlchemy database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///carrent.db')
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
    
    # Environment configuration
    ENV = os.environ.get('FLASK_ENV', 'production')
    DEBUG = ENV == 'development'

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
    'default': ProductionConfig
}
