import os
import sys
import json
from datetime import datetime, timedelta

# Ensure parent directory is in search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend_flask.app import db, create_app
from backend_flask.app.models import User, Role, Permission, OTP, UserSession, AuditLog
from backend_flask.app.utils import hash_password, hash_string

class TestConfig:
    """In-memory SQLite config for running auth integration tests."""
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "auth-verification-secret-key-at-least-32-chars-long"
    TESTING = True

def run_auth_tests():
    print("=" * 70)
    print("RUNNING AUTHENTICATION & SESSION VERIFICATION TESTS")
    print("=" * 70)
    
    app = create_app(config_class=TestConfig)
    client = app.test_client()
    
    with app.app_context():
        # Setup tables
        db.create_all()
        
        # Seed permissions
        p_scan = Permission(name="network:scan", resource="network", action="scan", description="Scan networks")
        p_read_logs = Permission(name="logs:view", resource="logs", action="view", description="View logs")
        db.session.add_all([p_scan, p_read_logs])
        
        # Seed roles
        role_analyst = Role(name="Analyst", description="Security analyst")
        role_analyst.permissions.append(p_scan)
        role_analyst.permissions.append(p_read_logs)
        db.session.add(role_analyst)
        
        # Hash user password
        raw_password = "P@ssw0rd123!"
        hashed = hash_password(raw_password)
        
        # Seed user
        user = User(
            username="sec_analyst_01",
            email="analyst@shield.local",
            password_hash=hashed,
            status="active"
        )
        user.roles.append(role_analyst)
        db.session.add(user)
        db.session.commit()
        
        print("[SUCCESS] Initial seed complete. Testing auth endpoints...")
        
        # --- TEST 1: Login with Invalid Password ---
        print("\nTEST 1: Logging in with incorrect password...")
        login_res = client.post("/api/auth/login", json={
            "username": "sec_analyst_01",
            "password": "wrong_password"
        })
        assert login_res.status_code == 401, f"Expected 401, got {login_res.status_code}"
        print(f"[SUCCESS] Login rejected with 401. Response: {login_res.get_json()}")
        
        # Check audit log contains failure entry
        failed_log = AuditLog.query.filter_by(action="USER_LOGIN_ATTEMPT", status="failure").first()
        assert failed_log is not None
        print(f"[SUCCESS] Audit entry created for login failure: {failed_log.details}")
        
        # --- TEST 2: Login Stage 1 (Credentials check) ---
        print("\nTEST 2: Logging in with valid credentials...")
        login_res = client.post("/api/auth/login", json={
            "username": "sec_analyst_01",
            "password": raw_password
        })
        assert login_res.status_code == 200, f"Expected 200, got {login_res.status_code}"
        login_data = login_res.get_json()
        assert login_data.get("status") == "otp_required"
        temp_token = login_data.get("temp_token")
        assert temp_token is not None
        print(f"[SUCCESS] Credential validation succeeded. Temp token issued.")
        
        # --- TEST 3: OTP Verification with Invalid OTP ---
        print("\nTEST 3: Verifying OTP with incorrect code...")
        otp_res = client.post(
            "/api/auth/verify-otp",
            headers={"Authorization": f"Bearer {temp_token}"},
            json={"otp_code": "000000"}
        )
        assert otp_res.status_code == 401, f"Expected 401, got {otp_res.status_code}"
        print(f"[SUCCESS] OTP verification rejected with 401. Response: {otp_res.get_json()}")
        
        # Check audit log contains OTP verification failure
        otp_fail_log = AuditLog.query.filter_by(action="USER_LOGIN_OTP_FAIL").first()
        assert otp_fail_log is not None
        
        # --- TEST 4: OTP Verification with Correct OTP ---
        print("\nTEST 4: Verifying OTP with correct code...")
        # Retrieve latest OTP code from database (simulating fetching it from SMS/Email)
        latest_otp_entry = OTP.query.order_by(OTP.id.desc()).first()
        # Find the raw OTP code matching this hash. For testing, we mock retrieve code from print logs.
        # But wait, since we generated a random code in routes, how do we get it?
        # In our script, since we can't capture printed stdout directly, we can read the database's 
        # otp_code_hash. Let's see: we know we can fetch the active OTP from DB, but we need the raw code.
        # Let's inspect the code hash. Oh! Since we cannot decrypt a hash, how do we verify it?
        # For testing purposes, we can temporarily retrieve the printed OTP by mocking generate_otp_code 
        # or we can inspect the generated OTP record. Wait! How do we know the code?
        # Ah! We can intercept generate_otp_code in the test!
        # Let's patch `generate_otp_code` to return a fixed code "123456" during login test, 
        # or we can update the database directly to set a known code's hash!
        # Yes! We can query the latest OTP entry in the DB, and rewrite its code hash to matches "123456" 
        # so that when verify-otp is called with "123456", it validates perfectly!
        # That is extremely clever and clean!
        
        # Let's modify the OTP code hash in DB to match "123456"
        test_otp_code = "123456"
        latest_otp_entry.otp_code_hash = hash_string(test_otp_code)
        db.session.commit()
        
        otp_res = client.post(
            "/api/auth/verify-otp",
            headers={"Authorization": f"Bearer {temp_token}"},
            json={"otp_code": test_otp_code}
        )
        assert otp_res.status_code == 200, f"Expected 200, got {otp_res.status_code}"
        otp_data = otp_res.get_json()
        access_token = otp_data.get("access_token")
        assert access_token is not None
        print(f"[SUCCESS] OTP verification passed. Access Token issued.")
        
        # Assert database marked OTP as used
        assert db.session.get(OTP, latest_otp_entry.id).is_used == True
        print(f"[SUCCESS] OTP code was successfully marked as consumed.")
        
        # Assert session was created in DB
        active_sessions = UserSession.query.all()
        assert len(active_sessions) == 1
        print(f"[SUCCESS] Database active session registered: IP={active_sessions[0].ip_address}")
        
        # --- TEST 5: Access Protected Route ---
        print("\nTEST 5: Accessing protected profile route '/api/auth/me'...")
        me_res = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert me_res.status_code == 200, f"Expected 200, got {me_res.status_code}"
        me_data = me_res.get_json()
        assert me_data.get("user", {}).get("username") == "sec_analyst_01"
        print(f"[SUCCESS] Profile retrieved successfully: {me_data}")
        
        # --- TEST 6: Logout Revocation ---
        print("\nTEST 6: Logging out (session revocation)...")
        logout_res = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert logout_res.status_code == 200, f"Expected 200, got {logout_res.status_code}"
        print(f"[SUCCESS] Logout completed. Response: {logout_res.get_json()}")
        
        # Verify session is deleted from database
        assert len(UserSession.query.all()) == 0
        print("[SUCCESS] Session record deleted from active session table.")
        
        # --- TEST 7: Accessing Protected Route Post-Logout ---
        print("\nTEST 7: Accessing '/api/auth/me' after logout...")
        me_revoked_res = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert me_revoked_res.status_code == 401, f"Expected 401, got {me_revoked_res.status_code}"
        print(f"[SUCCESS] Access denied. Token was successfully blacklisted: {me_revoked_res.get_json()}")
        
        print("\n" + "=" * 70)
        print("ALL AUTHENTICATION INTEGRATION TESTS PASSED COMPLETELY!")
        print("=" * 70)

if __name__ == "__main__":
    run_auth_tests()
