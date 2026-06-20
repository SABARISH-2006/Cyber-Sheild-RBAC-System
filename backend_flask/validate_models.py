import os
import sys
from datetime import datetime, timedelta

# Append parent directory to system path to allow importing backend_flask package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask
from backend_flask.app import db, create_app
from backend_flask.app.models import User, Role, Permission, UserSession, AuditLog, OTP, RiskScore, BehaviorAlert

class TestConfig:
    """In-memory testing configuration class."""
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "verification-test-secret"
    TESTING = True

def run_validation():
    print("=" * 60)
    print("STARTING FLASK SQLALCHEMY MODELS VERIFICATION")
    print("=" * 60)
    
    # Initialize application with local test configuration
    app = create_app(config_class=TestConfig)
    
    with app.app_context():
        print("1. Creating database tables in memory...")
        db.create_all()
        print("   Database schema generated successfully.")
        
        # Insert sample permissions
        print("\n2. Seeding test permissions...")
        p_view_logs = Permission(name="logs:view", resource="logs", action="view", description="View system logs")
        p_scan_net = Permission(name="network:scan", resource="network", action="scan", description="Scan network resources")
        p_user_create = Permission(name="user:create", resource="user", action="create", description="Create users")
        db.session.add_all([p_view_logs, p_scan_net, p_user_create])
        db.session.commit()
        
        # Insert sample roles
        print("\n3. Seeding test roles and mapping permissions...")
        role_analyst = Role(name="Analyst", description="Security analyst role")
        role_admin = Role(name="SecurityAdmin", description="Security administrator role")
        
        # Associate roles to permissions
        role_analyst.permissions.extend([p_view_logs, p_scan_net])
        role_admin.permissions.extend([p_view_logs, p_user_create])
        
        db.session.add_all([role_analyst, role_admin])
        db.session.commit()
        
        # Insert sample users
        print("\n4. Creating test user accounts...")
        user_alice = User(
            username="alice_analyst",
            email="alice@cybersecurity.local",
            password_hash="$2b$12$K1Hk7L2vPz293nJ2O3g8U.C43bfeG5l5hD8B1C8nC4v3O.D1i3R5e", # mock bcrypt
            status="active"
        )
        user_bob = User(
            username="bob_admin",
            email="bob@cybersecurity.local",
            password_hash="$2b$12$K1Hk7L2vPz293nJ2O3g8U.C43bfeG5l5hD8B1C8nC4v3O.D1i3R5e",
            status="active"
        )
        
        # Map users to roles
        user_alice.roles.append(role_analyst)
        user_bob.roles.append(role_admin)
        
        db.session.add_all([user_alice, user_bob])
        db.session.commit()
        
        # Create user session
        print("\n5. Registering user sessions...")
        session_alice = UserSession(
            user=user_alice,
            token_hash="5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8", # mock SHA256
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.session.add(session_alice)
        db.session.commit()
        
        # Log audit entry
        print("\n6. Logging events to audit log trail...")
        audit_entry = AuditLog(
            user=user_alice,
            action="network:scan",
            resource="network",
            details={"subnet": "192.168.1.0/24", "scanner_tool": "nmap"},
            ip_address="192.168.1.100",
            status="success"
        )
        db.session.add(audit_entry)
        db.session.commit()
        
        # Generate OTP
        print("\n7. Simulating OTP code generation...")
        otp_entry = OTP(
            user=user_alice,
            otp_code_hash="8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918", # mock SHA256
            purpose="2fa",
            expires_at=datetime.utcnow() + timedelta(minutes=5)
        )
        db.session.add(otp_entry)
        db.session.commit()
        
        # Record user risk score
        print("\n8. Recording computed risk scores...")
        risk_entry = RiskScore(
            user=user_alice,
            score=42.5,
            factors={"failed_logins_last_hour": 2, "unusual_isp": False}
        )
        db.session.add(risk_entry)
        db.session.commit()
        
        # Trigger behavior alert
        print("\n9. Triggering behavior alerts...")
        alert_entry = BehaviorAlert(
            user=user_alice,
            alert_type="IMPOSSIBLE_TRAVEL",
            severity="high",
            description="Geographically impossible travel detected between consecutive sessions.",
            status="open"
        )
        db.session.add(alert_entry)
        db.session.commit()
        
        # Check querying & assertions
        print("\n" + "=" * 60)
        print("VERIFYING DATABASE RELATIONS AND CONSTRAINTS")
        print("=" * 60)
        
        # Retrieve alice and test associations
        alice = User.query.filter_by(username="alice_analyst").first()
        assert alice is not None
        print(f"[SUCCESS] User: {alice.username}")
        print(f"          Status: {alice.status}")
        print(f"          Assigned Roles: {[role.name for role in alice.roles]}")
        print(f"          Effective Permissions: {[perm.name for role in alice.roles for perm in role.permissions]}")
        
        # Verify Session mapping
        assert len(alice.sessions) == 1
        print(f"[SUCCESS] Active sessions count: {len(alice.sessions)}")
        print(f"          Latest Session IP: {alice.sessions[0].ip_address}")
        
        # Verify Audit Log mapping
        assert len(alice.audit_logs) == 1
        print(f"[SUCCESS] Audit trail logs count: {len(alice.audit_logs)}")
        print(f"          Audit action: '{alice.audit_logs[0].action}' on '{alice.audit_logs[0].resource}'")
        print(f"          Audit meta factors: {alice.audit_logs[0].details}")
        
        # Verify OTP relationship
        assert len(alice.otps) == 1
        print(f"[SUCCESS] OTP purposes mapping: {[o.purpose for o in alice.otps]}")
        
        # Verify Risk score
        assert len(alice.risk_scores) == 1
        print(f"[SUCCESS] Risk assessment score: {alice.risk_scores[0].score}")
        print(f"          Risk assessment factors: {alice.risk_scores[0].factors}")
        
        # Verify Behavior Alerts and Resolvers workflow
        assert len(alice.behavior_alerts) == 1
        print(f"[SUCCESS] Behavior threat alerts count: {len(alice.behavior_alerts)}")
        print(f"          Triggered Alert: {alice.behavior_alerts[0].alert_type} ({alice.behavior_alerts[0].severity})")
        
        # Resolve alert by administrator
        print("\nSimulating administrator intervention and threat resolution...")
        retrieved_alert = BehaviorAlert.query.filter_by(alert_type="IMPOSSIBLE_TRAVEL").first()
        retrieved_alert.status = "resolved"
        retrieved_alert.resolved_by = user_bob.id
        retrieved_alert.resolved_at = datetime.utcnow()
        db.session.commit()
        
        # Re-fetch and assert resolve attributes
        updated_alert = BehaviorAlert.query.filter_by(alert_type="IMPOSSIBLE_TRAVEL").first()
        assert updated_alert.resolver is not None
        assert updated_alert.resolver.username == "bob_admin"
        print(f"[SUCCESS] Threat status changed to: {updated_alert.status}")
        print(f"          Mitigated & Resolved by: {updated_alert.resolver.username}")
        
        # Verify JSON dictionary serialization outputs
        print("\n10. Testing model JSON serialization dict...")
        print("    Alice User dict:")
        import json
        print(json.dumps(alice.to_dict(), indent=4))
        
        print("    Resolved Behavior Alert dict:")
        print(json.dumps(updated_alert.to_dict(), indent=4))
        
        print("\n" + "=" * 60)
        print("VERIFICATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)

if __name__ == "__main__":
    run_validation()
