from datetime import datetime, timedelta
from backend_flask.app import db
from backend_flask.app.models import UserSession, AuditLog, RiskScore

def evaluate_login_risk(user, ip_address, login_time=None):
    """
    Evaluates risk factors for a login event and calculates a numerical score (0.0 to 100.0).
    Saves a RiskScore entry in the database.
    
    :param user: The User database model instance.
    :param ip_address: The incoming IP address of the login attempt.
    :param login_time: The datetime of the login attempt (defaults to utcnow).
    :return: A tuple of (score, factors_dictionary).
    """
    if login_time is None:
        login_time = datetime.utcnow()
        
    score = 10.0  # Base security baseline risk
    factors = {}
    
    # 1. Unusual Time Check (11:00 PM to 5:00 AM)
    # Checking hour value in range [23, 0, 1, 2, 3, 4]
    if login_time.hour >= 23 or login_time.hour < 5:
        score += 25.0
        factors["unusual_login_hours"] = {
            "triggered": True,
            "hour": login_time.hour,
            "description": "Login attempt during anomalous hours (11PM - 5AM)"
        }
        
    # 2. IP Subnet/Context Shift Check
    # Find the user's last successful login audit log to match IPs
    last_success = AuditLog.query.filter_by(
        user_id=user.id, 
        action="USER_LOGIN", 
        status="success"
    ).order_by(AuditLog.id.desc()).first()
    
    if last_success and last_success.ip_address != ip_address:
        score += 35.0
        factors["ip_context_shift"] = {
            "triggered": True,
            "current_ip": ip_address,
            "last_login_ip": last_success.ip_address,
            "description": "IP address context differs from last successful session"
        }
        
    # 3. Recent Failed Login Attempts Check (Last 10 minutes)
    ten_mins_ago = login_time - timedelta(minutes=10)
    failed_attempts = AuditLog.query.filter(
        AuditLog.user_id == user.id,
        AuditLog.action == "USER_LOGIN_ATTEMPT",
        AuditLog.status == "failure",
        AuditLog.created_at >= ten_mins_ago
    ).count()
    
    if failed_attempts > 0:
        increment = failed_attempts * 15.0
        score += increment
        factors["recent_login_failures"] = {
            "triggered": True,
            "failure_count": failed_attempts,
            "risk_increment": increment,
            "description": f"Multiple failed login attempts ({failed_attempts}) detected in last 10 minutes"
        }
        
    # Clamp score to maximum of 100.0
    final_score = min(score, 100.0)
    
    try:
        # Save RiskScore entry to database
        risk_entry = RiskScore(
            user=user,
            score=final_score,
            factors=factors,
            calculated_at=datetime.utcnow()
        )
        db.session.add(risk_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[CRITICAL RISK LOGGER ERROR] Failed to record risk score: {str(e)}")
        
    return final_score, factors
