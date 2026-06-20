import os
from dotenv import load_dotenv

# Load variables from environment
load_dotenv()

class Config:
    """Base configurations for the Flask SQLAlchemy app."""
    SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET") or "dev-cyber-shield-key-secret"
    
    # Database connections
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "rbac_security_db")
    
    # Constructing database connection URI (using PyMySQL driver for MySQL compatibility)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL"
    ) or f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
