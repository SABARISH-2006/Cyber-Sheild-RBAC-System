import jwt
from functools import wraps
from datetime import datetime
from flask import request, jsonify, g
from backend_flask.app import db
from backend_flask.app.models import UserSession, AuditLog
from backend_flask.app.utils import decode_jwt, hash_string

def jwt_required(permissions=None):
    """
    Decorator to verify JWT access tokens, ensure database sessions exist, 
    and authorize based on fine-grained permissions.
    
    :param permissions: String or List of strings specifying required permission names.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Parse Authorization Header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return jsonify({"error": "Authorization header is missing"}), 401
                
            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                return jsonify({"error": "Authorization header must be formatted as Bearer <token>"}), 401
                
            token = parts[1]
            
            try:
                # Decode and validate signature/expiry
                payload = decode_jwt(token)
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token has expired"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Invalid token"}), 401
                
            # Verify token type (only 'access' tokens are valid for general routes)
            if payload.get("type") != "access":
                return jsonify({"error": "Invalid token type for this endpoint"}), 401
                
            # Compute token hash to find matching session (Token Revocation Check)
            token_hash = hash_string(token)
            session = UserSession.query.filter_by(token_hash=token_hash).first()
            
            if not session:
                return jsonify({"error": "Session has been revoked or does not exist"}), 401
                
            if session.expires_at < datetime.utcnow():
                # Clean up expired session
                db.session.delete(session)
                db.session.commit()
                return jsonify({"error": "Session has expired"}), 401
                
            user = session.user
            if not user:
                return jsonify({"error": "User associated with this session not found"}), 401
                
            # Check user status
            if user.status != "active":
                return jsonify({"error": f"User account is {user.status}"}), 403
                
            # Register in Flask context
            g.current_user = user
            g.current_session = session
            
            # Verify Permissions
            if permissions:
                required_perms = [permissions] if isinstance(permissions, str) else list(permissions)
                
                # Retrieve user's set of permission names
                user_perms = {p.name for r in user.roles for p in r.permissions}
                
                # Verify that all required permissions are present
                missing_perms = [p for p in required_perms if p not in user_perms]
                if missing_perms:
                    # Log unauthorized access attempt in AuditLogs
                    ip_address = request.remote_addr or "0.0.0.0"
                    audit_entry = AuditLog(
                        user_id=user.id,
                        action="UNAUTHORIZED_ACCESS_ATTEMPT",
                        resource=request.path,
                        details={
                            "required_permissions": required_perms,
                            "missing_permissions": missing_perms,
                            "user_roles": [r.name for r in user.roles]
                        },
                        ip_address=ip_address,
                        status="failure"
                    )
                    db.session.add(audit_entry)
                    db.session.commit()
                    
                    return jsonify({
                        "error": "Forbidden: Insufficient privileges",
                        "missing_permissions": missing_perms
                    }), 403
                    
            return f(*args, **kwargs)
        return decorated_function
    return decorator
