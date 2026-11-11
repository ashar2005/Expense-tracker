"""Configuration settings for ExpenseMate application environments."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "expensemate-dev-secret-key")
    DB_PATH = os.environ.get("EXPENSEMATE_DB", os.path.join(BASE_DIR, "expensemate.db"))
    TESTING = False

class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True

class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    DB_PATH = os.path.join(BASE_DIR, "test_expensemate.db")

config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}