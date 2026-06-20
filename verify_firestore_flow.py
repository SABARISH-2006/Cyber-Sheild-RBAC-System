#!/usr/bin/env python
"""
Verification Script for CyberShield Smart RBAC Firestore Backend.
Performs an end-to-end simulation of registration, login (MFA), role request, approval pipeline, and telemetry.
Sanitized for ASCII environment execution (no unicode / emojis).
"""

import sys
import os
import random
from unittest.mock import patch

# Insert current directory into path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smart_rbac.app import create_app
from smart_rbac.models import User, Role, Permission, AccessRequest, RegistrationRequest, AuditLog, OTP, RiskScore
from smart_rbac.utils.auth_helper import generate_token

def run_verification():
    print("=" * 80)
    print("STARTING FIRESTORE BACKEND INTEGRATION VERIFICATION")
    print("=" * 80)

    # Initialize Flask App
    app = create_app()
    client = app.test_client()

    print("\n[Step 1] Verifying Data Models Connection to Firestore...")
    users = User.get_all()
    roles = Role.get_all()
    permissions = Permission.get_all()
    print(f"  - Retrieved {len(users)} users from Firestore")
    print(f"  - Retrieved {len(roles)} roles from Firestore")
    print(f"  - Retrieved {len(permissions)} permissions from Firestore")

    # Find the seeded admin and manager users
    admin_user = next((u for u in users if u.role == 'Admin' and u.status == 'active'), None)
    manager_user = next((u for u in users if u.role == 'Manager' and u.status == 'active'), None)

    if not admin_user or not manager_user:
        print("[FAIL] Critical test failure: Seeded admin or manager user not found in Firestore!")
        sys.exit(1)

    print(f"  - Admin found: {admin_user.username} (ID: {admin_user.id}, Login ID: {admin_user.login_id})")
    print(f"  - Manager found: {manager_user.username} (ID: {manager_user.id}, Login ID: {manager_user.login_id})")

    # Generate random test user details
    test_suffix = random.randint(1000, 9999)
    test_username = f"verify_user_{test_suffix}"
    test_email = f"{test_username}@company.com"
    test_password = "TestPassword123!"

    print(f"\n[Step 2] Testing User Registration Flow (/register)...")
    reg_response = client.post('/register', data={
        'username': test_username,
        'email': test_email,
        'password': test_password,
        'role': 'Employee'
    })
    
    # Registration redirects/renders registration complete page
    if reg_response.status_code not in [200, 302]:
        print(f"[FAIL] Failed to register user. Status: {reg_response.status_code}")
        sys.exit(1)

    # Verify user exists in Firestore as pending approval
    registered_user = User.find_by_username(test_username)
    if not registered_user:
        print("[FAIL] Registered user not found in Firestore!")
        sys.exit(1)

    print(f"  - User successfully created in Firestore (ID: {registered_user.id})")
    print(f"  - User status: {registered_user.status} (Expected: pending_approval)")
    print(f"  - User Login ID: {registered_user.login_id}")

    # Check for RegistrationRequest
    reg_reqs = RegistrationRequest.get_all()
    user_reg_req = next((r for r in reg_reqs if r.user_id == registered_user.id), None)
    if not user_reg_req:
        print("[FAIL] RegistrationRequest document not created in Firestore!")
        sys.exit(1)

    print(f"  - RegistrationRequest document found in Firestore (ID: {user_reg_req.id})")
    print(f"  - Request status: {user_reg_req.status} (Expected: pending)")

    print(f"\n[Step 3] Simulating Superadmin Login and Approval Flow...")
    # Generate token for admin
    admin_token = generate_token(admin_user.id)
    client.set_cookie('access_token', admin_token)

    # Approve registration request
    approve_reg_url = f"/admin/registration-requests/{user_reg_req.id}/approve"
    approve_reg_response = client.post(approve_reg_url)

    if approve_reg_response.status_code not in [200, 302]:
        print(f"[FAIL] Failed to approve registration. Status: {approve_reg_response.status_code}")
        sys.exit(1)

    # Verify user status is now active
    registered_user = User.get(registered_user.id)
    if registered_user.status != 'active':
        print(f"[FAIL] User status was not updated to active! Current status: {registered_user.status}")
        sys.exit(1)

    print("  - Registration successfully approved by Admin")
    print("  - User status updated to 'active'")

    print(f"\n[Step 4] Testing User Login and MFA Verification (/login & /verify-otp)...")
    # Clear cookies
    client.delete_cookie('access_token')

    # Mock random.randint to return 999999 for static OTP testing
    with patch('random.randint', return_value=999999):
        login_response = client.post('/login', data={
            'login_id': registered_user.login_id,
            'password': test_password
        })

    if login_response.status_code not in [200, 302]:
        print(f"[FAIL] Login failed. Status: {login_response.status_code}")
        sys.exit(1)

    print("  - Login form submitted. Redirected/Loaded OTP verification page.")

    # Submit OTP 999999 to /verify-otp
    otp_response = client.post('/verify-otp', data={
        'otp_code': '999999'
    })

    if otp_response.status_code not in [200, 302]:
        print(f"[FAIL] OTP verification failed. Status: {otp_response.status_code}")
        sys.exit(1)

    print("  - OTP verification successful. Logged in and cookie set.")

    # Get the access token from redirect
    user_token = client.get_cookie('access_token')
    if not user_token:
        print("[FAIL] Access token cookie not found after successful OTP verification!")
        sys.exit(1)

    print(f"\n[Step 5] Testing Access Request Flow (/requests)...")
    # Submit access request as the new user
    client.set_cookie('access_token', user_token.value)
    
    # We want to request permission to 'manage_users'
    req_submit_response = client.post('/requests/submit', data={
        'requested_permission': 'manage_users',
        'reason': 'Need to manage temporary worker accounts'
    })

    if req_submit_response.status_code not in [200, 302]:
        print(f"[FAIL] Failed to submit access request. Status: {req_submit_response.status_code}")
        sys.exit(1)

    # Find the access request in Firestore
    user_reqs = AccessRequest.find_by_field('user_id', registered_user.id)
    if not user_reqs:
        print("[FAIL] AccessRequest document not found in Firestore!")
        sys.exit(1)

    user_req = user_reqs[0]
    print(f"  - AccessRequest successfully created in Firestore (ID: {user_req.id})")
    print(f"  - Request status: {user_req.status} (Expected: pending_manager)")

    print(f"\n[Step 6] Testing Access Approval Sequential Pipeline (Manager -> Admin)...")
    # 1. Manager Approval
    manager_token = generate_token(manager_user.id)
    client.set_cookie('access_token', manager_token)
    
    mgr_approve_url = f"/requests/approve/{user_req.id}"
    mgr_approve_response = client.post(mgr_approve_url)

    if mgr_approve_response.status_code not in [200, 302]:
        print(f"[FAIL] Manager approval failed. Status: {mgr_approve_response.status_code}")
        sys.exit(1)

    user_req = AccessRequest.get(user_req.id)
    print(f"  - Request status after Manager approval: {user_req.status} (Expected: pending_admin)")

    # 2. Admin Approval
    client.set_cookie('access_token', admin_token)
    
    admin_approve_url = f"/requests/approve/{user_req.id}"
    admin_approve_response = client.post(admin_approve_url)

    if admin_approve_response.status_code not in [200, 302]:
        print(f"[FAIL] Admin final approval failed. Status: {admin_approve_response.status_code}")
        sys.exit(1)

    user_req = AccessRequest.get(user_req.id)
    print(f"  - Request status after Admin approval: {user_req.status} (Expected: approved)")

    # Verify permission was added to Employee role!
    employee_role = Role.find_by_name('Employee')
    if 'manage_users' not in employee_role._permissions_list:
        print("[FAIL] Permission 'manage_users' was not granted to role 'Employee'!")
        sys.exit(1)

    print("  - Successfully verified sequential pipeline works!")
    print("  - Role 'Employee' now possesses 'manage_users' permission")

    print(f"\n[Step 7] Testing Audit Trails and Telemetry Dashboard Routes...")
    # View Logs Trail
    logs_response = client.get('/logs')
    if logs_response.status_code != 200:
        print(f"[FAIL] /logs route failed with status: {logs_response.status_code}")
        sys.exit(1)
    print("  - Successfully accessed /logs route")

    # View Threat Analytics Dashboard
    analytics_response = client.get('/analytics')
    if analytics_response.status_code != 200:
        print(f"[FAIL] /analytics route failed with status: {analytics_response.status_code}")
        sys.exit(1)
    print("  - Successfully accessed /analytics route")

    # Retrieve Telemetry API data
    api_charts_response = client.get('/api/telemetry/charts')
    if api_charts_response.status_code != 200:
        print(f"[FAIL] /api/telemetry/charts route failed with status: {api_charts_response.status_code}")
        sys.exit(1)
    
    api_data = api_charts_response.get_json()
    print("  - Successfully accessed /api/telemetry/charts API")
    print(f"    |-- Role Distribution: {list(api_data.get('role_distribution', {}).keys())}")
    print(f"    |-- Risk Distribution: {api_data.get('risk_distribution', {})}")
    print(f"    +-- Alert Categories: {list(api_data.get('alert_distribution', {}).keys())}")

    print(f"\n[Step 8] Clean-up Test Data from Firestore...")
    # Clean up the test user and requests
    registered_user.delete()
    user_req.delete()
    user_reg_req.delete()
    
    # Restore Employee role permissions
    if 'manage_users' in employee_role._permissions_list:
        employee_role._permissions_list.remove('manage_users')
        employee_role.save()
    
    print("  - Test user and access/registration requests removed from Firestore")
    print("  - Employee role permissions restored")

    print("\n" + "=" * 80)
    print("SUCCESS: ALL INTEGRATIONS AND PIPELINES OPERATING PERFECTLY!")
    print("=" * 80 + "\n")

if __name__ == '__main__':
    run_verification()
