#!/usr/bin/env python3
"""
Migration script to add login_id column to users table.
Run this once to update the database schema.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'cyber_shield.db')

def migrate():
    """Add login_id column to users table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if login_id column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'login_id' in columns:
            print("✓ login_id column already exists in users table")
        else:
            print("Adding login_id column to users table...")
            # Add nullable column first (UNIQUE constraint will fail on NULL values)
            cursor.execute("""
                ALTER TABLE users
                ADD COLUMN login_id VARCHAR(50)
            """)
            conn.commit()
            print("✓ login_id column added (nullable)")
            
            # Create index on login_id
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS ix_users_login_id ON users(login_id)
            """)
            conn.commit()
            print("✓ Index created on login_id column")
        
        # Generate login_ids for users that don't have one
        cursor.execute("SELECT id, role FROM users WHERE login_id IS NULL ORDER BY id")
        users = cursor.fetchall()
        
        if users:
            print(f"\nGenerating login_ids for {len(users)} existing users...")
            role_prefixes = {
                'Employee': 'EMP',
                'Manager': 'MGR',
                'Admin': 'ADMIN',
                'Auditor': 'AUDIT'
            }
            
            role_counters = {}
            for user_id, role in users:
                prefix = role_prefixes.get(role, 'USER')
                if prefix not in role_counters:
                    # Count existing IDs with this prefix
                    cursor.execute(f"SELECT COUNT(*) FROM users WHERE login_id LIKE '{prefix}%'")
                    count = cursor.fetchone()[0] + 1
                    role_counters[prefix] = count
                else:
                    role_counters[prefix] += 1
                
                login_id = f"{prefix}{role_counters[prefix]:03d}"
                cursor.execute("UPDATE users SET login_id = ? WHERE id = ?", (login_id, user_id))
                print(f"  User ID {user_id}: {login_id}")
            
            conn.commit()
            print(f"✓ Generated login_ids for all users")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Migration error: {str(e)}")
        conn.close()
        return False

if __name__ == '__main__':
    success = migrate()
    exit(0 if success else 1)
