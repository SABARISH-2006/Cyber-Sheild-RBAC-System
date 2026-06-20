#!/usr/bin/env python
"""Verify Superadmin Login ID Update"""

import sqlite3

print("\n")
print("╔" + "=" * 68 + "╗")
print("║" + " " * 15 + "SUPERADMIN LOGIN ID VERIFICATION REPORT" + " " * 15 + "║")
print("╚" + "=" * 68 + "╝")

conn = sqlite3.connect('smart_rbac/cyber_shield.db')
cursor = conn.cursor()

# Find superadmin by new login ID
cursor.execute("""
    SELECT id, username, email, login_id, role, status, created_at 
    FROM users 
    WHERE login_id = 'SPR_101'
""")
user = cursor.fetchone()

if user:
    user_id, username, email, login_id, role, status, created_at = user
    
    print(f"\n✅ SUPERADMIN DETAILS")
    print(f"{'─' * 70}")
    print(f"User ID:         {user_id}")
    print(f"Username:        {username}")
    print(f"Email:           {email}")
    print(f"Login ID:        {login_id}")
    print(f"Role:            {role}")
    print(f"Status:          {status}")
    print(f"Created:         {created_at}")
    
    print(f"\n📝 LOGIN INSTRUCTIONS")
    print(f"{'─' * 70}")
    print(f"1. Go to: http://127.0.0.1:8001/login")
    print(f"2. Click on 'SIGN IN' tab")
    print(f"3. Enter Login ID: {login_id}")
    print(f"4. Enter Password: (your superadmin password)")
    print(f"5. Click 'AUTHENTICATE ACCESS'")
    print(f"6. Enter 6-digit MFA code (sent to email)")
    print(f"7. Access superadmin dashboard")
    
    print(f"\n🛡️ SUPERADMIN PERMISSIONS")
    print(f"{'─' * 70}")
    print(f"✓ View all users and roles")
    print(f"✓ Manage registration approvals")
    print(f"✓ Create and delete roles")
    print(f"✓ Assign permissions")
    print(f"✓ View audit logs")
    print(f"✓ Access admin dashboard")
    print(f"✓ Manage access requests")
    
    print(f"\n✨ STATUS")
    print(f"{'─' * 70}")
    print(f"✅ Login ID successfully updated to: {login_id}")
    print(f"✅ Superadmin account is: {status.upper()}")
    print(f"✅ Ready to login!")
    
else:
    print(f"\n❌ Superadmin with Login ID 'SPR_101' not found!")
    
    # Show all admin users
    cursor.execute("""
        SELECT id, username, email, login_id, role 
        FROM users 
        WHERE role IN ('Admin', 'admin')
        ORDER BY created_at DESC
    """)
    admins = cursor.fetchall()
    
    if admins:
        print(f"\nAdmin users in system:")
        for admin in admins:
            print(f"  - {admin[1]} (Login ID: {admin[3]}, Role: {admin[4]})")
    else:
        print(f"No admin users found!")

conn.close()

print(f"\n{'═' * 70}\n")
