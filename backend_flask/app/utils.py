import bcrypt
import jwt
import secrets
import hashlib
from datetime import datetime, timedelta
from flask import current_app

def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt with a work factor of 12."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def check_password(password: str, hashed: str) -> bool:
    """Checks a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def generate_otp_code() -> str:
    """Generates a cryptographically secure 6-digit OTP code."""
    # secrets.randbelow(900000) generates an integer from 0 to 899999. Adding 100000 guarantees a 6-digit range.
    return str(secrets.randbelow(900000) + 100000)

def hash_string(value: str) -> str:
    """Hashes a string using SHA-256 and returns a 64-character hex string."""
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def generate_jwt(payload: dict, expiry_minutes: int) -> str:
    """Generates a JWT token signed with the application secret key."""
    secret_key = current_app.config.get("SECRET_KEY", "dev-cyber-shield-key-secret")
    
    # Avoid mutating the passed-in payload dict
    token_payload = payload.copy()
    
    now = datetime.utcnow()
    token_payload.update({
        'iat': now,
        'exp': now + timedelta(minutes=expiry_minutes)
    })
    
    return jwt.encode(token_payload, secret_key, algorithm='HS256')

def decode_jwt(token: str) -> dict:
    """Decodes a JWT token. Returns payload dict or raises exceptions on invalid/expired tokens."""
    secret_key = current_app.config.get("SECRET_KEY", "dev-cyber-shield-key-secret")
    # Will raise jwt.ExpiredSignatureError or jwt.InvalidTokenError if token is invalid
    return jwt.decode(token, secret_key, algorithms=['HS256'])
