from datetime import datetime, timedelta
from backend_flask.app import db
from backend_flask.app.models import AuditLog, BehaviorAlert, User

def check_brute_force_activity(user, ip_address):
    """
    Analyzes failed login attempts. If failed attempts exceed 5 in the last 10 minutes,
    automatically suspends the account and triggers a critical BehaviorAlert.
    
    :param user: The User database model instance.
    :param ip_address: The originating IP address of the failed login.
    :return: True if brute force was detected and account was suspended, False otherwise.
    """
    ten_mins_ago = datetime.utcnow() - timedelta(minutes=10)
    
    # Count failed logins in the last 10 minutes
    failed_count = AuditLog.query.filter(
        AuditLog.user_id == user.id,
        AuditLog.action == "USER_LOGIN_ATTEMPT",
        AuditLog.status == "failure",
        AuditLog.created_at >= ten_mins_ago
    ).count()
    
    if failed_count >= 5:
        # Suspend user account
        user.status = "suspended"
        user.updated_at = datetime.utcnow()
        
        # Trigger BehaviorAlert
        alert = BehaviorAlert(
            user=user,
            alert_type="BRUTE_FORCE",
            severity="critical",
            description=(
                f"Account automatically suspended due to {failed_count} failed login attempts "
                f"within 10 minutes from IP {ip_address}."
            ),
            status="open",
            triggered_at=datetime.utcnow()
        )
        db.session.add(alert)
        
        # Log auto-suspension to AuditLog
        from backend_flask.app.services.audit_service import log_audit_event
        log_audit_event(
            user_id=None,  # Logged as system action
            action="ACCOUNT_AUTO_SUSPEND",
            resource=f"user:{user.username}",
            details={"reason": "brute_force_detected", "failures": failed_count, "ip_address": ip_address},
            ip_address=ip_address,
            status="success"
        )
        db.session.commit()
        return True
        
    return False

def detect_impossible_travel(user, current_ip):
    """
    Compares the current login session IP and timestamp with the user's last successful login.
    If the IP address changed across different subnets in a short timeframe, triggers an alert.
    
    :param user: The User database model instance.
    :param current_ip: The incoming session IP.
    :return: True if impossible travel was detected, False otherwise.
    """
    # Retrieve the last successful login event
    last_success = AuditLog.query.filter_by(
        user_id=user.id,
        action="USER_LOGIN",
        status="success"
    ).order_by(AuditLog.id.desc()).first()
    
    if last_success and last_success.ip_address != current_ip:
        time_diff = datetime.utcnow() - last_success.created_at
        
        # Threshold: Less than 15 minutes (900 seconds)
        if time_diff.total_seconds() < 900:
            # Check subnet octets to verify if they are on different network contexts (class B comparison)
            last_octets = last_success.ip_address.split('.')
            curr_octets = current_ip.split('.')
            
            if len(last_octets) >= 2 and len(curr_octets) >= 2 and (last_octets[0] != curr_octets[0] or last_octets[1] != curr_octets[1]):
                # Impossible travel confirmed
                alert = BehaviorAlert(
                    user=user,
                    alert_type="IMPOSSIBLE_TRAVEL",
                    severity="high",
                    description=(
                        f"Geographically impossible travel detected. Session IP changed from "
                        f"{last_success.ip_address} to {current_ip} in {int(time_diff.total_seconds())} seconds."
                    ),
                    status="open",
                    triggered_at=datetime.utcnow()
                )
                db.session.add(alert)
                db.session.commit()
                return True
                
    return False

def evaluate_behavioral_anomalies(user, ip_address):
    """
    Orchestrates behavioral analysis checks on successful or failed events.
    """
    anomalies = {
        "brute_force_suspended": False,
        "impossible_travel_triggered": False
    }
    
    if user.status == "active":
        # Check impossible travel first
        anomalies["impossible_travel_triggered"] = detect_impossible_travel(user, ip_address)
        # Check brute force next
        anomalies["brute_force_suspended"] = check_brute_force_activity(user, ip_address)
        
    return anomalies
