from datetime import datetime
from backend_flask.app import db
from backend_flask.app.models import AuditLog

def log_audit_event(user_id=None, action=None, resource=None, details=None, ip_address="0.0.0.0", status="success"):
    """
    Utility function to write a security compliance event into the AuditLog table.
    
    :param user_id: ID of the user triggering the action (None if system or pre-auth).
    :param action: String event identifier (e.g. 'USER_LOGIN', 'UNAUTHORIZED_ACCESS').
    :param resource: Target resource (e.g. 'network', 'user:secadmin').
    :param details: Dictionary containing contextual metadata (diffs, error details).
    :param ip_address: Originating IP.
    :param status: 'success' or 'failure'.
    """
    try:
        # If user_id is passed as a User object, extract its id
        from backend_flask.app.models import User
        if isinstance(user_id, User):
            user_id = user_id.id
            
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            details=details,
            ip_address=ip_address,
            status=status,
            created_at=datetime.utcnow()
        )
        db.session.add(audit_entry)
        db.session.commit()
        return audit_entry
    except Exception as e:
        db.session.rollback()
        # Fallback print log for critical system errors
        print(f"[CRITICAL AUDIT ERROR] Failed to write audit event. Error: {str(e)}")
        return None

def get_filtered_audit_logs(user_id=None, action=None, status=None, start_date=None, end_date=None, limit=100):
    """
    Retrieve and filter audit logs based on query parameters.
    """
    query = AuditLog.query
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    if action:
        query = query.filter(AuditLog.action.like(f"%{action}%"))
    if status:
        query = query.filter_by(status=status)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)
        
    return query.order_by(AuditLog.created_at.desc()).limit(limit).all()
