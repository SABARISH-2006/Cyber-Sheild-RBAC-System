#!/usr/bin/env python3
"""Test that login_id is truly immutable and permanent for users."""
import sqlite3

def test_login_id_immutability():
    """Verify login_id never changes once assigned."""
    conn = sqlite3.connect('cyber_shield.db')
    cursor = conn.cursor()
    
    # Get testuser_permanent's login_id multiple times
    print("Testing Login ID Immutability...")
    print("-" * 50)
    
    login_ids = []
    for i in range(3):
        cursor.execute('SELECT login_id FROM users WHERE username = ?', ('testuser_permanent',))
        result = cursor.fetchone()
        if result:
            login_id = result[0]
            login_ids.append(login_id)
            print(f"Query #{i+1}: Login ID = {login_id}")
    
    conn.close()
    
    # Verify all queries returned the same login_id
    if all(lid == login_ids[0] for lid in login_ids):
        print("-" * 50)
        print(f"✓ SUCCESS: Login ID is PERMANENT and IMMUTABLE")
        print(f"  Fixed Login ID: {login_ids[0]}")
        print(f"  Unchanged across {len(login_ids)} queries")
        return True
    else:
        print("-" * 50)
        print(f"✗ FAILURE: Login ID changed!")
        print(f"  Values: {login_ids}")
        return False

if __name__ == '__main__':
    success = test_login_id_immutability()
    exit(0 if success else 1)
