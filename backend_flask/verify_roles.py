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
    """In-memory SQLite config for running RBAC integration tests."""
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "rbac-verification-secret-key-at-least-32-chars-long"
    TESTING = True

def get_auth_token(client, username):
    """Helper function to log in a user and retrieve their access token (simulates the OTP flow)."""
    login_res = client.post("/api/auth/login", json={
        "username": username,
        "password": "P@ssw0rd123!"
    })
    if login_res.status_code != 200:
        raise RuntimeError(f"Login failed for {username}: {login_res.get_json()}")
        
    temp_token = login_res.get_json()["temp_token"]
    
    # Capture OTP and set it to a known mock value in DB
    latest_otp = OTP.query.order_by(OTP.id.desc()).first()
    latest_otp.otp_code_hash = hash_string("123456")
    db.session.commit()
    
    # Complete Stage 2
    verify_res = client.post(
        "/api/auth/verify-otp",
        headers={"Authorization": f"Bearer {temp_token}"},
        json={"otp_code": "123456"}
    )
    if verify_res.status_code != 200:
        raise RuntimeError(f"OTP verification failed for {username}: {verify_res.get_json()}")
        
    return verify_res.get_json()["access_token"]

def run_rbac_tests():
    print("=" * 70)
    print("RUNNING RBAC & ROLE MANAGEMENT INTEGRATION TESTS")
    print("=" * 70)
    
    app = create_app(config_class=TestConfig)
    client = app.test_client()
    
    with app.app_context():
        # Setup tables
        db.create_all()
        
        # 1. Seed Permissions
        print("1. Seeding permissions...")
        p_read_logs = Permission(name="logs:view", resource="logs", action="view", description="View logs")
        p_scan_net = Permission(name="network:scan", resource="network", action="scan", description="Scan network")
        p_role_create = Permission(name="role:create", resource="role", action="create", description="Create roles")
        p_role_read = Permission(name="role:read", resource="role", action="read", description="Read roles")
        p_role_update = Permission(name="role:update", resource="role", action="update", description="Update roles")
        p_role_delete = Permission(name="role:delete", resource="role", action="delete", description="Delete roles")
        p_role_assign = Permission(name="role:assign", resource="role", action="assign", description="Assign roles")
        
        db.session.add_all([
            p_read_logs, p_scan_net, p_role_create, 
            p_role_read, p_role_update, p_role_delete, p_role_assign
        ])
        
        # 2. Seed Roles
        print("2. Seeding roles...")
        role_super = Role(name="SuperAdmin", description="Super administrator")
        role_sec = Role(name="SecurityAdmin", description="Security administrator")
        role_analyst = Role(name="Analyst", description="Security analyst")
        
        # Associate permissions
        role_super.permissions.extend([
            p_read_logs, p_scan_net, p_role_create, 
            p_role_read, p_role_update, p_role_delete, p_role_assign
        ])
        role_sec.permissions.extend([
            p_role_create, p_role_read, p_role_update, p_role_delete, p_role_assign
        ])
        role_analyst.permissions.extend([
            p_read_logs, p_scan_net
        ])
        
        db.session.add_all([role_super, role_sec, role_analyst])
        
        # 3. Seed Users
        print("3. Seeding users...")
        pw_hash = hash_password("P@ssw0rd123!")
        
        user_super = User(username="superadmin", email="superadmin@shield.local", password_hash=pw_hash, status="active")
        user_sec = User(username="secadmin", email="secadmin@shield.local", password_hash=pw_hash, status="active")
        user_analyst = User(username="analyst01", email="analyst@shield.local", password_hash=pw_hash, status="active")
        
        # Map roles
        user_super.roles.append(role_super)
        user_sec.roles.append(role_sec)
        user_analyst.roles.append(role_analyst)
        
        db.session.add_all([user_super, user_sec, user_analyst])
        db.session.commit()
        
        print("[SUCCESS] Seeding complete. Performing tokens handshake...")
        
        # Get access tokens
        super_token = get_auth_token(client, "superadmin")
        sec_token = get_auth_token(client, "secadmin")
        analyst_token = get_auth_token(client, "analyst01")
        
        print("[SUCCESS] Access tokens retrieved. Starting tests.")
        
        # --- TEST 1: Retrieve Roles as SecurityAdmin ---
        print("\nTEST 1: Retrieving all roles as SecurityAdmin (expected: 200)...")
        res_roles = client.get("/api/roles", headers={"Authorization": f"Bearer {sec_token}"})
        assert res_roles.status_code == 200
        roles_list = res_roles.get_json()
        assert len(roles_list) == 3
        print(f"[SUCCESS] Roles retrieved successfully. Count: {len(roles_list)}")
        
        # --- TEST 2: Create a Role as SecurityAdmin ---
        print("\nTEST 2: Creating a new 'Auditor' role as SecurityAdmin (expected: 201)...")
        res_create = client.post(
            "/api/roles",
            headers={"Authorization": f"Bearer {sec_token}"},
            json={"name": "Auditor", "description": "System auditor with compliance access"}
        )
        assert res_create.status_code == 201
        auditor_role = res_create.get_json()
        assert auditor_role["name"] == "Auditor"
        auditor_id = auditor_role["id"]
        print(f"[SUCCESS] Role 'Auditor' created successfully (ID={auditor_id}).")
        
        # Check audit log for role creation
        create_audit = AuditLog.query.filter_by(action="ROLE_CREATE").first()
        assert create_audit is not None
        assert create_audit.details["name"] == "Auditor"
        print(f"[SUCCESS] Audit entry confirmed for ROLE_CREATE.")
        
        # --- TEST 3: Map Permissions to Auditor Role ---
        print("\nTEST 3: Mapping 'logs:view' permission to 'Auditor' (expected: 200)...")
        # Find permission id for logs:view
        logs_perm = Permission.query.filter_by(name="logs:view").first()
        res_map = client.post(
            f"/api/roles/{auditor_id}/permissions",
            headers={"Authorization": f"Bearer {sec_token}"},
            json={"permission_ids": [logs_perm.id]}
        )
        assert res_map.status_code == 200
        map_data = res_map.get_json()
        assert "logs:view" in map_data["assigned"]
        print(f"[SUCCESS] Permission mapping complete. Response: {map_data['message']}")
        
        # --- TEST 4: Assign Auditor Role to Analyst01 ---
        print("\nTEST 4: Assigning 'Auditor' role to user 'analyst01' (expected: 200)...")
        analyst_user = User.query.filter_by(username="analyst01").first()
        res_assign = client.post(
            f"/api/users/{analyst_user.id}/roles",
            headers={"Authorization": f"Bearer {sec_token}"},
            json={"role_ids": [auditor_id]}
        )
        assert res_assign.status_code == 200
        print(f"[SUCCESS] Role assigned to user. Response: {res_assign.get_json()['message']}")
        
        # Verify user has both Analyst and Auditor roles
        db.session.expire(analyst_user) # clear cache to reload relationship
        updated_analyst = User.query.filter_by(username="analyst01").first()
        roles_assigned = [r.name for r in updated_analyst.roles]
        assert "Analyst" in roles_assigned
        assert "Auditor" in roles_assigned
        print(f"[SUCCESS] Roles currently mapped to analyst01: {roles_assigned}")
        
        # --- TEST 5: Unauthorized Action (Analyst01 attempts to create a role) ---
        print("\nTEST 5: Attempting to create a role as Analyst01 (expected: 403 Forbidden)...")
        res_unauth = client.post(
            "/api/roles",
            headers={"Authorization": f"Bearer {analyst_token}"},
            json={"name": "Hacker", "description": "Illegal administrative role"}
        )
        assert res_unauth.status_code == 403
        print(f"[SUCCESS] Operation blocked with 403 Forbidden. Response: {res_unauth.get_json()}")
        
        # Verify unauthorized access audit log
        unauth_audit = AuditLog.query.filter_by(action="UNAUTHORIZED_ACCESS_ATTEMPT").first()
        assert unauth_audit is not None
        assert unauth_audit.user_id == analyst_user.id
        print(f"[SUCCESS] Unauthorized attempt successfully logged in AuditLog details: {unauth_audit.details}")
        
        # --- TEST 6: Delete Role as SuperAdmin ---
        print("\nTEST 6: Deleting the 'Auditor' role as SuperAdmin (expected: 200)...")
        res_delete = client.delete(
            f"/api/roles/{auditor_id}",
            headers={"Authorization": f"Bearer {super_token}"}
        )
        assert res_delete.status_code == 200
        print(f"[SUCCESS] Role deleted successfully. Response: {res_delete.get_json()}")
        
        # Verify role is removed from database
        deleted_role = db.session.get(Role, auditor_id)
        assert deleted_role is None
        print("[SUCCESS] Role was verified removed from the database.")
        
        # Verify Analyst user no longer has Auditor role
        db.session.expire(analyst_user)
        roles_post_delete = [r.name for r in analyst_user.roles]
        assert "Auditor" not in roles_post_delete
        print(f"[SUCCESS] Roles currently mapped to analyst01: {roles_post_delete}")
        
        print("\n" + "=" * 70)
        print("ALL RBAC & ROLE MANAGEMENT INTEGRATION TESTS PASSED COMPLETELY!")
        print("=" * 70)

if __name__ == "__main__":
    run_rbac_tests()
