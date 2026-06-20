import datetime
from smart_rbac.models import User, BehaviorAlert, AuditLog, db

def check_and_apply_lockout(user, ip_address):
    """
    Check if user exceeded maximum failed login attempts (5).
    If so, suspend the account, trigger a BRUTE_FORCE behavior alert, and log the security event.
    Returns True if account is suspended/locked, False otherwise.
    """
    if user.failed_login_attempts >= 5:
        if user.status != 'suspended':
            user.status = 'suspended'
            
            # Create a security behavior alert
            alert = BehaviorAlert(
                user_id=user.id,
                alert_type="BRUTE_FORCE",
                description=f"Account suspended due to 5 consecutive failed login attempts from IP: {ip_address}"
            )
            alert.save()
            
            # Create a security audit log
            audit = AuditLog(
                username=user.username,
                action="ACCOUNT_LOCKED_BRUTE_FORCE",
                ip_address=ip_address
            )
            audit.save()
            
            # Save the user status
            user.save()
        return True
    return False

def record_failed_attempt(user, ip_address):
    """
    Increment failed login count, check for lockout, and log the attempt.
    """
    user.failed_login_attempts += 1
    user.save()
    
    is_locked = check_and_apply_lockout(user, ip_address)
    
    # Log the failed login attempt
    audit = AuditLog(
        username=user.username,
        action="FAILED_LOGIN_ATTEMPT",
        ip_address=ip_address
    )
    audit.save()
    
    return is_locked

def trigger_time_anomaly_alert(user, ip_address):
    """
    Raise an alert if a user logs in during off-peak/irregular hours (10 PM - 6 AM).
    """
    current_hour = datetime.datetime.now().hour
    if current_hour >= 22 or current_hour < 6:
        # Check if an alert was already generated in the last 12 hours to avoid spamming
        all_alerts = BehaviorAlert.find_by_field('user_id', user.id)
        recent_alert = None
        for a in all_alerts:
            if a.alert_type == "TIME_ANOMALY":
                # Convert triggered_at if it's not a datetime object
                trig_time = a.triggered_at
                if isinstance(trig_time, str):
                    try:
                        trig_time = datetime.datetime.fromisoformat(trig_time.replace('Z', ''))
                    except Exception:
                        trig_time = datetime.datetime.utcnow()
                
                # Check 12 hours window
                if trig_time >= datetime.datetime.utcnow() - datetime.timedelta(hours=12):
                    recent_alert = a
                    break
        
        if not recent_alert:
            alert = BehaviorAlert(
                user_id=user.id,
                alert_type="TIME_ANOMALY",
                description=f"User logged in at an off-peak hour ({current_hour}:00) from IP: {ip_address}"
            )
            alert.save()
            return True
    return False
