import jwt
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g
from backend_flask.app import db
from backend_flask.app.models import User, OTP, UserSession, AuditLog
from backend_flask.app.utils import (
    check_password, generate_otp_code, hash_string, 
    generate_jwt, decode_jwt
)
from backend_flask.app.middleware import jwt_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Stage 1 Login: Check user credentials.
    If valid, generate an OTP, hash it, store it, and return a temporary token.
    """
    data = request.get_json() or {}
    identifier = data.get("username") or data.get("email")
    password = data.get("password")
    
    ip_address = request.remote_addr or "0.0.0.0"
    
    if not identifier or not password:
        return jsonify({"error": "Username/email and password are required"}), 400
        
    # Search for user by username or email
    user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()
    
    # Verify password hash
    if not user or not check_password(password, user.password_hash):
        # Log authentication failure
        audit_entry = AuditLog(
            user_id=user.id if user else None,
            action="USER_LOGIN_ATTEMPT",
            resource="/api/auth/login",
            details={"identifier": identifier, "reason": "invalid_credentials"},
            ip_address=ip_address,
            status="failure"
        )
        db.session.add(audit_entry)
        db.session.commit()
        return jsonify({"error": "Invalid username/email or password"}), 401
        
    # Check user account status
    if user.status != "active":
        return jsonify({"error": f"Account is {user.status}"}), 403
        
    # Generate OTP code (e.g. 6 digit string)
    otp_code = generate_otp_code()
    otp_hash = hash_string(otp_code)
    
    # Store OTP in database
    otp_expiry = datetime.utcnow() + timedelta(minutes=5)
    otp_entry = OTP(
        user=user,
        otp_code_hash=otp_hash,
        purpose="2fa",
        expires_at=otp_expiry
    )
    db.session.add(otp_entry)
    
    # Log OTP Generation to audit trail
    audit_entry = AuditLog(
        user=user,
        action="OTP_GENERATED",
        resource="/api/auth/login",
        details={"purpose": "2fa", "expiry": otp_expiry.isoformat()},
        ip_address=ip_address,
        status="success"
    )
    db.session.add(audit_entry)
    db.session.commit()
    
    # Simulate sending OTP (output to app logs/stdout for developer access)
    print(f"[OTP SECURITY LOGGER] MFA OTP generated for User '{user.username}': {otp_code} (expires in 5 minutes)")
    
    # Generate temporary OTP-verification JWT token
    temp_payload = {
        "sub": str(user.id),
        "type": "temp_otp"
    }
    temp_token = generate_jwt(temp_payload, expiry_minutes=5)
    
    return jsonify({
        "status": "otp_required",
        "temp_token": temp_token,
        "message": "OTP generated. Please verify with code."
    }), 200


@auth_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    """
    Stage 2 Login: Verify OTP.
    Expects Authorization Bearer Header to hold the temp_token, and JSON body to hold otp_code.
    If valid, register a session and issue a final access token.
    """
    # 1. Decode & Verify temp_token from Authorization Header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "Temporary verification token is missing"}), 401
        
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return jsonify({"error": "Authorization header must be formatted as Bearer <temp_token>"}), 401
        
    temp_token = parts[1]
    
    try:
        payload = decode_jwt(temp_token)
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Temporary token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid temporary token"}), 401
        
    if payload.get("type") != "temp_otp":
        return jsonify({"error": "Invalid token type for OTP verification"}), 401
        
    user_id = payload.get("sub")
    user = db.session.get(User, int(user_id)) if user_id else None
    if not user:
        return jsonify({"error": "User associated with token not found"}), 401
        
    # 2. Extract OTP code from Request
    data = request.get_json() or {}
    otp_code = data.get("otp_code")
    if not otp_code:
        return jsonify({"error": "OTP code is required"}), 400
        
    ip_address = request.remote_addr or "0.0.0.0"
    user_agent = request.headers.get("User-Agent", "Unknown")
    
    # 3. Retrieve matching valid OTP hash
    otp_hash = hash_string(otp_code)
    
    # Query unused 2FA OTP codes for this user
    active_otps = OTP.query.filter_by(user_id=user.id, is_used=False, purpose="2fa").all()
    
    valid_otp = None
    for otp_entry in active_otps:
        # Check matching hash and verify expiry
        if otp_entry.otp_code_hash == otp_hash:
            if otp_entry.expires_at > datetime.utcnow():
                valid_otp = otp_entry
                break
                
    if not valid_otp:
        # Audit log failed OTP verification
        audit_entry = AuditLog(
            user=user,
            action="USER_LOGIN_OTP_FAIL",
            resource="/api/auth/verify-otp",
            details={"reason": "invalid_or_expired_code"},
            ip_address=ip_address,
            status="failure"
        )
        db.session.add(audit_entry)
        db.session.commit()
        return jsonify({"error": "Invalid or expired OTP code"}), 401
        
    # Mark OTP as consumed
    valid_otp.is_used = True
    
    # Generate final Access Token (valid for 60 minutes)
    access_payload = {
        "sub": str(user.id),
        "type": "access",
        "username": user.username
    }
    access_token = generate_jwt(access_payload, expiry_minutes=60)
    token_hash = hash_string(access_token)
    
    # Save active session details to the database (Token Revocation List)
    session_expiry = datetime.utcnow() + timedelta(hours=1)
    session = UserSession(
        user=user,
        token_hash=token_hash,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=session_expiry
    )
    db.session.add(session)
    
    # Audit log successful auth
    audit_entry = AuditLog(
        user=user,
        action="USER_LOGIN",
        resource="/api/auth/verify-otp",
        details={"method": "credentials_and_2fa"},
        ip_address=ip_address,
        status="success"
    )
    db.session.add(audit_entry)
    db.session.commit()
    
    return jsonify({
        "access_token": access_token,
        "expires_in_seconds": 3600,
        "user": user.to_dict()
    }), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """
    Logout: Revoke current session.
    Removes session from DB session list and logs the audit event.
    """
    ip_address = request.remote_addr or "0.0.0.0"
    user = g.current_user
    session = g.current_session
    
    # Revoke session in database
    db.session.delete(session)
    
    # Audit log the logout
    audit_entry = AuditLog(
        user=user,
        action="USER_LOGOUT",
        resource="/api/auth/logout",
        details={"reason": "user_requested"},
        ip_address=ip_address,
        status="success"
    )
    db.session.add(audit_entry)
    db.session.commit()
    
    return jsonify({"message": "Logged out successfully and session revoked"}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """
    Protected endpoint: Get current authenticated user details.
    """
    return jsonify({
        "user": g.current_user.to_dict()
    }), 200
