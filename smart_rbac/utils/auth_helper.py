import datetime
from functools import wraps
import jwt
from flask import request, redirect, url_for, g, render_template, jsonify, current_app
from smart_rbac.config import Config
from smart_rbac.models import User, Role, Permission, db

def generate_token(user_id):
    """
    Generate a JWT token for the given user ID.
    Enforces string subject mapping per RFC/PyJWT rules.
    """
    try:
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=Config.JWT_ACCESS_TOKEN_EXPIRES_MINUTES),
            'iat': datetime.datetime.utcnow(),
            'sub': str(user_id)  # Cast to string to comply with PyJWT
        }
        return jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')
    except Exception as e:
        current_app.logger.error(f"Error generating token: {str(e)}")
        return None

def verify_token(token):
    """
    Verify the JWT token and return the decoded payload if valid.
    """
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        current_app.logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError:
        current_app.logger.warning("Invalid token")
        return None

def get_current_user():
    """
    Retrieve the current logged-in user from the JWT token in cookies.
    """
    if hasattr(g, 'current_user') and g.current_user is not None:
        return g.current_user

    token = request.cookies.get('access_token')
    if not token:
        return None

    payload = verify_token(token)
    if not payload:
        return None

    try:
        user_id = str(payload['sub'])  # Keep as string for Firestore ID lookup
        user = User.get(user_id)
        if user and user.status == 'active':
            g.current_user = user
            return user
    except Exception as e:
        current_app.logger.error(f"Error resolving user from token: {str(e)}")
    
    return None

def login_required(f):
    """
    Decorator to restrict access to authenticated users.
    Redirects to login page or returns JSON 401 if it's an API route.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('auth.login', next=request.full_path))
        return f(*args, **kwargs)
    return decorated

def permission_required(permission_name):
    """
    Decorator to restrict access to users with a specific permission.
    Returns 403 Forbidden page or JSON 403 if it's an API route.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()
            if not user:
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect(url_for('auth.login', next=request.full_path))
            
            # Admins have master bypass
            has_perm = False
            if user.role and user.role.lower() == 'admin':
                has_perm = True
            else:
                role_obj = Role.find_by_name(user.role)
                if role_obj:
                    has_perm = permission_name in role_obj._permissions_list
            
            if not has_perm:
                # Log unauthorized access attempt
                from smart_rbac.models import AuditLog
                log_entry = AuditLog(
                    username=user.username,
                    action=f"UNAUTHORIZED_ACCESS_ATTEMPT: Tried to access {request.path} requiring {permission_name}",
                    ip_address=request.remote_addr or '127.0.0.1'
                )
                log_entry.save()

                if request.path.startswith('/api/'):
                    return jsonify({'error': f'Permission denied: {permission_name} required'}), 403
                return render_template('errors/403.html', permission=permission_name), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator
