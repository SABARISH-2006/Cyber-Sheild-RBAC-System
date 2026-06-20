import os
import sys
import json
from datetime import datetime, timedelta

# Ensure parent directory is in search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend_flask.app import db, create_app
from backend_flask.app.models import User, Role, Permission, OTP, UserSession, AuditLog, RiskScore, BehaviorAlert
from backend_flask.app.utils import hash_password, hash_string

# Import our new security services
from backend_flask.app.services.audit_service import log_audit_event, get_filtered_audit_logs
from backend_flask.app.services.risk_service import evaluate_login_risk
from backend_flask.app.services.behavior_service import (
    check_brute_force_activity, detect_impossible_travel, evaluate_behavioral_anomalies
)

class TestConfig:
    """In-memory SQLite config for running services integration tests."""
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "services-verification-secret-key-at-least-32-chars-long"
    TESTING = True

def get_auth_token(client, username):
    """Helper to log in a user and retrieve their access token (bypassing OTP)."""
    login_res = client.post("/api/auth/login", json={
        "username": username,
        "password": "P@ssw0rd123!"
    })
    temp_token = login_res.get_json()["temp_token"]
    
    # Capture OTP and set it to a known mock value in DB
    latest_otp = OTP.query.order_by(OTP.id.desc()).first()
    latest_otp.otp_code_hash = hash_string("123456")
    db.session.commit()
    
    # Verify OTP
    verify_res = client.post(
        "/api/auth/verify-otp",
        headers={"Authorization": f"Bearer {temp_token}"},
        json={"otp_code": "123456"}
    )
    return verify_res.get_json()["access_token"]

def run_services_tests():
    print("=" * 70)
    print("RUNNING SECURITY SERVICES & ANALYTICS INTEGRATION TESTS")
    print("=" * 70)
    
    app = create_app(config_class=TestConfig)
    client = app.test_client()
    
    with app.app_context():
        # Setup tables
        db.create_all()
        
        # 1. Seed Permissions and Roles
        p_view_logs = Permission(name="logs:view", resource="logs", action="view", description="View logs")
        p_read_audit = Permission(name="audit:read", resource="audit", action="read", description="Read audit trail")
        p_sys_config = Permission(name="system:configure", resource="system", action="configure", description="Configure firewalls")
        p_role_assign = Permission(name="role:assign", resource="role", action="assign", description="Assign roles")
        p_role_read = Permission(name="role:read", resource="role", action="read", description="Read roles")
        
        db.session.add_all([p_view_logs, p_read_audit, p_sys_config, p_role_assign, p_role_read])
        
        role_super = Role(name="SuperAdmin", description="Super administrator")
        role_super.permissions.extend([p_view_logs, p_read_audit, p_sys_config, p_role_assign, p_role_read])
        db.session.add(role_super)
        
        # 2. Seed Users
        pw_hash = hash_password("P@ssw0rd123!")
        admin_user = User(username="superadmin", email="superadmin@shield.local", password_hash=pw_hash, status="active")
        admin_user.roles.append(role_super)
        
        target_user = User(username="target_employee", email="employee@shield.local", password_hash=pw_hash, status="active")
        db.session.add_all([admin_user, target_user])
        db.session.commit()
        
        print("[SUCCESS] Initial seed complete. Logging in SuperAdmin...")
        super_token = get_auth_token(client, "superadmin")
        
        # --- TEST 1: Audit Service logging and filtering ---
        print("\nTEST 1: Logging events via Audit Logging service...")
        log1 = log_audit_event(
            user_id=target_user.id,
            action="FILE_ACCESS",
            resource="confidential_reports.pdf",
            details={"access_type": "download"},
            ip_address="192.168.1.110",
            status="success"
        )
        assert log1 is not None
        
        # Fetch and verify filtered log
        filtered_logs = get_filtered_audit_logs(action="FILE_ACCESS")
        assert len(filtered_logs) == 1
        assert filtered_logs[0].resource == "confidential_reports.pdf"
        assert filtered_logs[0].details["access_type"] == "download"
        print(f"[SUCCESS] Audit entry created and verified via service filters.")

        # --- TEST 2: Risk-Based Authentication Scoring ---
        print("\nTEST 2: Evaluating login risk scores...")
        
        # Test Case A: Safe Login
        # Log a successful login first to establish last known IP
        log_audit_event(user_id=target_user.id, action="USER_LOGIN", status="success", ip_address="192.168.1.100")
        
        # Same IP, standard business hour (e.g. 12:00 PM)
        normal_time = datetime(2026, 6, 18, 12, 0, 0)
        risk_score_normal, normal_factors = evaluate_login_risk(target_user, "192.168.1.100", normal_time)
        assert risk_score_normal == 10.0
        assert len(normal_factors) == 0
        print(f"[SUCCESS] Normal conditions risk score correctly evaluated: {risk_score_normal} (Safe)")
        
        # Test Case B: High Risk Anomaly
        # Subnet shift IP and unusual late hour (e.g. 1:00 AM)
        anomaly_time = datetime(2026, 6, 18, 1, 0, 0)
        risk_score_anom, anom_factors = evaluate_login_risk(target_user, "10.0.0.50", anomaly_time)
        # Expected score: 10 (base) + 25 (unusual hour) + 35 (IP shift) = 70.0
        assert risk_score_anom == 70.0
        assert "unusual_login_hours" in anom_factors
        assert "ip_context_shift" in anom_factors
        print(f"[SUCCESS] High-risk login anomalies correctly scored: {risk_score_anom} (High Risk)")
        
        # Verify RiskScore recorded in DB
        latest_risk = RiskScore.query.order_by(RiskScore.id.desc()).first()
        assert latest_risk.score == 70.0
        print("[SUCCESS] Risk evaluation context saved to database.")

        # --- TEST 3: User Behavior Analytics (Impossible Travel) ---
        print("\nTEST 3: Checking Impossible Travel anomaly triggers...")
        # Target user logged successful login from IP 192.168.1.100 in previous step.
        # Now we evaluate login from 10.0.0.50 (which was recorded in Test 2 as an audit/risk event).
        # We manually call detect_impossible_travel
        travel_triggered = detect_impossible_travel(target_user, "10.0.0.50")
        assert travel_triggered is True
        
        # Assert behavior alert of type IMPOSSIBLE_TRAVEL is generated
        travel_alert = BehaviorAlert.query.filter_by(alert_type="IMPOSSIBLE_TRAVEL").first()
        assert travel_alert is not None
        assert travel_alert.severity == "high"
        print(f"[SUCCESS] Impossible travel anomaly detected: {travel_alert.description}")

        # --- TEST 4: UBA Brute-Force & Account Auto-Suspension ---
        print("\nTEST 4: Simulating brute force login attack (5 failed attempts)...")
        # Log 5 failed attempts in the last minute
        for _ in range(5):
            log_audit_event(
                user_id=target_user.id,
                action="USER_LOGIN_ATTEMPT",
                ip_address="192.168.5.55",
                status="failure"
            )
            
        # Run UBA Brute Force check
        brute_force_active = check_brute_force_activity(target_user, "192.168.5.55")
        assert brute_force_active is True
        
        # Verify user is suspended
        db.session.expire(target_user)
        updated_target = db.session.get(User, target_user.id)
        assert updated_target.status == "suspended"
        print("[SUCCESS] Account status updated to: SUSPENDED.")
        
        # Verify BehaviorAlert created for BRUTE_FORCE
        brute_alert = BehaviorAlert.query.filter_by(alert_type="BRUTE_FORCE").first()
        assert brute_alert is not None
        assert brute_alert.severity == "critical"
        print(f"[SUCCESS] Critical Behavior Alert issued: {brute_alert.description}")
        
        # Verify auto suspension was logged in audit trail
        suspend_audit = AuditLog.query.filter_by(action="ACCOUNT_AUTO_SUSPEND").first()
        assert suspend_audit is not None
        print(f"[SUCCESS] Audit entry confirmed for auto suspension event: {suspend_audit.details}")

        # --- TEST 5: API Endpoints (GET /api/admin/audit-logs, GET /api/admin/behavior-alerts) ---
        print("\nTEST 5: Querying administrative API telemetry endpoints...")
        
        # Fetch audit logs
        res_audits = client.get(
            "/api/admin/audit-logs",
            headers={"Authorization": f"Bearer {super_token}"}
        )
        assert res_audits.status_code == 200
        logs_list = res_audits.get_json()
        assert len(logs_list) > 0
        print(f"[SUCCESS] Audit logs retrieved via API. Count: {len(logs_list)}")
        
        # Fetch behavior alerts
        res_alerts = client.get(
            "/api/admin/behavior-alerts",
            headers={"Authorization": f"Bearer {super_token}"}
        )
        assert res_alerts.status_code == 200
        alerts_list = res_alerts.get_json()
        assert len(alerts_list) >= 2  # Brute force and impossible travel
        print(f"[SUCCESS] Threat alerts retrieved via API. Count: {len(alerts_list)}")

        # --- TEST 6: Resolve Threat Alert ---
        print("\nTEST 6: Resolving triggered behavior alert via API...")
        open_alert = BehaviorAlert.query.filter_by(status="open", alert_type="IMPOSSIBLE_TRAVEL").first()
        assert open_alert is not None
        
        res_resolve = client.post(
            f"/api/admin/behavior-alerts/{open_alert.id}/resolve",
            headers={"Authorization": f"Bearer {super_token}"}
        )
        assert res_resolve.status_code == 200
        resolve_data = res_resolve.get_json()
        assert resolve_data["alert"]["status"] == "resolved"
        print(f"[SUCCESS] Threat status resolved. Response: {resolve_data['message']}")
        
        # Verify resolver is superadmin
        resolved_alert = db.session.get(BehaviorAlert, open_alert.id)
        assert resolved_alert.status == "resolved"
        assert resolved_alert.resolver.username == "superadmin"
        print(f"[SUCCESS] Threat resolved in DB by administrator: {resolved_alert.resolver.username}")
        
        print("\n" + "=" * 70)
        print("ALL SECURITY SERVICES & TELEMETRY INTEGRATION TESTS PASSED!")
        print("=" * 70)

if __name__ == "__main__":
    run_services_tests()
