import os
import secrets
import logging

class Config:
    # Generate a secure random secret key if not set
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    
    # Ensure the secret key is always a string
    if not isinstance(SECRET_KEY, str):
        SECRET_KEY = str(SECRET_KEY)
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database configuration prioritizes environment variable
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:////' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')

    # Logging configuration
    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
        },
        'handlers': {
            'default': {
                'level': 'DEBUG',
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            '': {  # root logger
                'handlers': ['default'],
                'level': 'DEBUG',
                'propagate': True
            },
            'flask.app': {
                'handlers': ['default'],
                'level': 'DEBUG',
                'propagate': False
            },
            'sqlalchemy.engine': {
                'handlers': ['default'],
                'level': 'INFO',
                'propagate': False
            }
        }
    }

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True  # Log SQL queries

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_ECHO = False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
