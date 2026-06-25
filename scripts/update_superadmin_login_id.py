#!/usr/bin/env python
"""Update superadmin login ID"""

import sqlite3

print("=" * 70)
print("SUPERADMIN LOGIN ID UPDATE")
print("=" * 70)

from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
conn = sqlite3.connect(ROOT_DIR / 'database' / 'cyber_shield.db')
cursor = conn.cursor()

# Find SABARISH K C user
cursor.execute("SELECT id, username, email, login_id, role, status FROM users WHERE username LIKE '%SABARISH%' OR username LIKE '%sabarish%'")
user = cursor.fetchone()

if user:
    user_id, username, email, current_login_id, role, status = user
    print(f"\n✅ Found User:")
    print(f"   ID: {user_id}")
    print(f"   Username: {username}")
    print(f"   Email: {email}")
    print(f"   Current Login ID: {current_login_id}")
    print(f"   Role: {role}")
    print(f"   Status: {status}")
    
    # Update login_id to SPR_101
    print(f"\n🔄 Updating Login ID to: SPR_101...")
    cursor.execute("UPDATE users SET login_id = 'SPR_101' WHERE id = ?", (user_id,))
    conn.commit()
    
    # Verify update
    cursor.execute("SELECT login_id FROM users WHERE id = ?", (user_id,))
    new_login_id = cursor.fetchone()[0]
    
    if new_login_id == 'SPR_101':
        print(f"✅ Login ID Successfully Updated!")
        print(f"\n📊 Updated User Details:")
        print(f"   Username: {username}")
        print(f"   New Login ID: {new_login_id}")
        print(f"   Role: {role}")
        print(f"   Status: {status}")
        print(f"\n✨ Superadmin can now login with Login ID: SPR_101")
    else:
        print(f"❌ Update Failed!")
else:
    print(f"\n❌ User 'SABARISH K C' not found in database!")
    print(f"\nSearching for all users...")
    cursor.execute("SELECT id, username, email, login_id, role FROM users ORDER BY created_at DESC LIMIT 10")
    users = cursor.fetchall()
    print(f"\nRecent users:")
    for u in users:
        print(f"  - {u[1]} ({u[2]}) - Role: {u[4]} - Login ID: {u[3]}")

conn.close()
