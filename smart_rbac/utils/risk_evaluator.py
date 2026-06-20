import datetime
import json
from smart_rbac.models import User, RiskScore, db

def evaluate_login_risk(user, user_agent_info, ip_address):
    """
    Evaluate the risk score of a login attempt for a user.
    Risk is scored from 0 to 100 based on:
    - New Device (+30)
    - New Browser (+20)
    - Failed Login Attempts (+20 for 1, +40 for multiple)
    - Time Anomaly (10 PM - 6 AM) (+20)
    
    Categorization:
    - Low: 0 - 30
    - Medium: 31 - 60
    - High: 61 - 100 (triggers conditional OTP)
    """
    score = 0.0
    factors = []
    
    current_device = user_agent_info.get('device', 'Unknown Device')
    current_browser = user_agent_info.get('browser', 'Unknown Browser')
    
    # 1. Device check
    if user.last_login_device and user.last_login_device != current_device:
        score += 30.0
        factors.append("New login device detected (+30)")
    elif not user.last_login_device:
        score += 15.0  # First time device setup has moderate risk increment
        factors.append("First time device registration (+15)")
        
    # 2. Browser check
    if user.last_login_browser and user.last_login_browser != current_browser:
        score += 20.0
        factors.append("New web browser detected (+20)")
    elif not user.last_login_browser:
        score += 10.0
        factors.append("First time browser registration (+10)")
        
    # 3. Failed attempts check
    if user.failed_login_attempts == 1:
        score += 20.0
        factors.append("Recent failed login attempt (+20)")
    elif user.failed_login_attempts > 1:
        score += 40.0
        factors.append(f"Multiple consecutive failed login attempts ({user.failed_login_attempts}) (+40)")
        
    # 4. Time anomaly check (10 PM to 6 AM)
    current_hour = datetime.datetime.now().hour
    if current_hour >= 22 or current_hour < 6:
        score += 20.0
        factors.append("Login attempt at suspicious/off-peak hours (+20)")
        
    # Cap score at 100
    score = min(score, 100.0)
    
    # Determine risk level
    if score >= 61.0:
        risk_level = "High"
    elif score >= 31.0:
        risk_level = "Medium"
    else:
        risk_level = "Low"
        
    # Create RiskScore record
    risk_record = RiskScore(
        user_id=user.id,
        score=score,
        risk_level=risk_level,
        factors=json.dumps(factors)
    )
    risk_record.save()
    
    return risk_record
