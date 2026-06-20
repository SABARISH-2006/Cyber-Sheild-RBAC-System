import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """System configuration parameters."""
    SECRET_KEY = os.getenv("SECRET_KEY") or "cyber-shield-smart-rbac-secret-key-at-least-32-chars"
    
    # DB connection parameters
    DB_USER = os.getenv("DB_USER", "root")
    # For local test development, default password to empty
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "smart_rbac_db")
    
    # We support MySQL connection. Fallback to a local SQLite database file for out-of-the-box development setup.
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL"
    ) or f"sqlite:///{os.path.join(os.path.abspath(os.path.dirname(__file__)), 'cyber_shield.db')}"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT configuration
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES = 60
    OTP_EXPIRES_MINUTES = 5

    # SMTP configuration (deprecated - use Brevo API instead)
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587)) if os.getenv("SMTP_PORT") else 587
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_SENDER = os.getenv("SMTP_SENDER", "no-reply@cybersecurity.local")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "True").lower() == "true"
    
    # Brevo Email Service configuration
    BREVO_API_KEY = os.getenv("BREVO_API_KEY")
    BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "no-reply@cybersecurity.local")
    BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "CyberShield Smart RBAC")
