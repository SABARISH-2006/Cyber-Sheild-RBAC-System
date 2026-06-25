"""
Migration script to add registration_requests table for registration approval workflow.
Run this once after updating the models.
"""
import sqlite3
import os

# Path to the database file
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'cyber_shield.db')

def migrate():
    """Create registration_requests table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Create registration_requests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registration_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                username VARCHAR(50) NOT NULL,
                email VARCHAR(100) NOT NULL,
                role VARCHAR(50) NOT NULL,
                login_id VARCHAR(50) NOT NULL,
                status VARCHAR(25) NOT NULL DEFAULT 'pending',
                approval_notes VARCHAR(255),
                approved_by VARCHAR(50),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                approved_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # Create index on created_at for sorting
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_registration_requests_created_at 
            ON registration_requests(created_at)
        ''')
        
        conn.commit()
        print("✅ Successfully created registration_requests table!")
        
    except sqlite3.OperationalError as e:
        print(f"❌ Table might already exist: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
