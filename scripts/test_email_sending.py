#!/usr/bin/env python
"""Test script for verifying SMTP email delivery"""

import os
import sys
import sqlite3
from dotenv import load_dotenv

from pathlib import Path

# Setup path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Load environment variables
load_dotenv(ROOT_DIR / '.env')

# Test 1: Check database tables and pending registrations
print("=" * 60)
print("TEST 1: Check Database Structure and Pending Registrations")
print("=" * 60)

conn = sqlite3.connect(ROOT_DIR / 'database' / 'cyber_shield.db')
cursor = conn.cursor()

# First, find all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print(f"\nTables in database: {', '.join([t[0] for t in tables])}")

# Find the user table (could be 'user' or 'users')
user_table = None
for table in tables:
    if table[0] in ['user', 'users']:
        user_table = table[0]
        break

if not user_table:
    print("ERROR: Could not find user table!")
    conn.close()
    sys.exit(1)

print(f"Using table: {user_table}")

# Check pending registrations
cursor.execute(f"SELECT username, email, login_id, status FROM {user_table} WHERE status='pending_approval' LIMIT 10")
rows = cursor.fetchall()

if rows:
    print(f"\nFound {len(rows)} pending registration(s):")
    for row in rows:
        print(f"  - Username: {row[0]}")
        print(f"    Email: {row[1]}")
        print(f"    Login ID: {row[2]}")
        print(f"    Status: {row[3]}")
        print()
else:
    print("\nNo pending registrations found")
    # Show all users for debugging
    cursor.execute(f"SELECT username, email, login_id, status FROM {user_table} ORDER BY created_at DESC LIMIT 5")
    rows = cursor.fetchall()
    if rows:
        print("\nLast 5 users registered:")
        for row in rows:
            print(f"  - {row[0]} ({row[1]}) - Status: {row[3]}")

conn.close()

# Test 2: Test SMTP Connection
print("=" * 60)
print("TEST 2: Test Brevo SMTP Relay Connection")
print("=" * 60)

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = "smtp-relay.brevo.com"
SMTP_PORT = 587
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
SMTP_SENDER = os.getenv('SMTP_SENDER', 'no-reply@cybersecurity.local')

print(f"\nBrevo SMTP Server: {SMTP_SERVER}:{SMTP_PORT}")
print(f"SMTP Username: {SMTP_USERNAME[:10]}..." if SMTP_USERNAME else "NOT CONFIGURED")
print(f"SMTP Password: {'CONFIGURED' if SMTP_PASSWORD else 'NOT CONFIGURED'}")
print(f"Sender Email: {SMTP_SENDER}")

if not SMTP_USERNAME or not SMTP_PASSWORD:
    print("\n❌ ERROR: SMTP credentials not configured in .env file")
    sys.exit(1)

try:
    print("\nAttempting to connect to Brevo SMTP Relay...")
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
        print("✓ SMTP connection established")
        
        print("Upgrading to TLS...")
        server.starttls()
        print("✓ TLS upgrade successful")
        
        print("Authenticating with Brevo credentials...")
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        print("✓ Authentication successful")
        
        print("\n✅ Brevo SMTP Relay is working correctly!")
        
except smtplib.SMTPAuthenticationError as e:
    print(f"\n❌ SMTP Authentication Failed: {str(e)}")
    sys.exit(1)
except smtplib.SMTPException as e:
    print(f"\n❌ SMTP Error: {str(e)}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Connection Error: {str(e)}")
    sys.exit(1)

print("\n" + "=" * 60)
print("All tests passed! SMTP relay is configured correctly.")
print("=" * 60)
