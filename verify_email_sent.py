#!/usr/bin/env python
"""Verify email sending for the new registration"""

import os
import sys
import sqlite3
from dotenv import load_dotenv

# Setup path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment
load_dotenv()

# Check the new registration
print("=" * 70)
print("EMAIL SENDING VERIFICATION REPORT")
print("=" * 70)

conn = sqlite3.connect('smart_rbac/cyber_shield.db')
cursor = conn.cursor()

# Get the latest pending approval user
cursor.execute("""
    SELECT username, email, login_id, status, created_at 
    FROM users 
    WHERE status='pending_approval' 
    ORDER BY created_at DESC 
    LIMIT 1
""")
row = cursor.fetchone()

if row:
    username, email, login_id, status, created_at = row
    print(f"\n✅ Latest Registration Found:")
    print(f"   Username: {username}")
    print(f"   Email: {email}")
    print(f"   Login ID: {login_id}")
    print(f"   Status: {status}")
    print(f"   Created: {created_at}")
    
    # Test email sending to this user
    print(f"\n" + "=" * 70)
    print("TESTING EMAIL SENDING...")
    print("=" * 70)
    
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    SMTP_SERVER = "smtp-relay.brevo.com"
    SMTP_PORT = 587
    SMTP_USERNAME = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    SMTP_SENDER = os.getenv('SMTP_SENDER', 'no-reply@cybersecurity.local')
    
    print(f"\n📧 Email Configuration:")
    print(f"   From: {SMTP_SENDER}")
    print(f"   To: {email}")
    print(f"   Subject: Your CyberShield Login ID - Welcome to Smart RBAC")
    
    role_display = {
        'Employee': 'Employee (Standard Access)',
        'Manager': 'Manager (Approving Authority)',
        'Admin': 'Administrator (Full Control)',
        'Auditor': 'Compliance Auditor (Read Logs)'
    }
    
    # Get user's role from database
    cursor.execute("SELECT role FROM users WHERE username=?", (username,))
    role_result = cursor.fetchone()
    role = role_result[0] if role_result else 'Employee'
    role_text = role_display.get(role, role)
    
    subject = "Your CyberShield Login ID - Welcome to Smart RBAC"
    
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #0066cc;">Welcome to CyberShield Smart RBAC</h2>
                <p>Hello {username},</p>
                <p>Your account has been successfully created. Below is your unique login credential:</p>
                
                <div style="background-color: #f0f0f0; padding: 20px; border-left: 4px solid #0066cc; margin: 30px 0;">
                    <p style="color: #666; margin: 0; font-size: 12px;">YOUR LOGIN ID</p>
                    <h3 style="color: #0066cc; margin: 10px 0 0 0; font-family: monospace; font-size: 24px;">
                        {login_id}
                    </h3>
                </div>
                
                <p><strong>Account Details:</strong></p>
                <ul style="color: #666;">
                    <li><strong>Email:</strong> {email}</li>
                    <li><strong>Role:</strong> {role_text}</li>
                </ul>
                
                <p style="color: #999; font-size: 12px; margin-top: 40px;">
                    This is a test email sent from the verification script.
                </p>
            </div>
        </body>
    </html>
    """
    
    text_body = (
        f"Welcome to CyberShield Smart RBAC\n\n"
        f"Hello {username},\n\n"
        f"Your account has been successfully created.\n\n"
        f"YOUR LOGIN ID: {login_id}\n\n"
        f"Account Details:\n"
        f"- Email: {email}\n"
        f"- Role: {role_text}\n\n"
        f"This is a test email sent from the verification script."
    )
    
    try:
        print(f"\n📡 Connecting to Brevo SMTP Relay...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            print(f"   ✓ Connected")
            
            server.starttls()
            print(f"   ✓ TLS enabled")
            
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            print(f"   ✓ Authenticated")
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = SMTP_SENDER
            msg['To'] = email
            
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send
            server.send_message(msg)
            print(f"   ✓ Email sent successfully!")
            
            print(f"\n" + "=" * 70)
            print("✅ SUCCESS: Email was sent to " + email)
            print("=" * 70)
            print(f"\n📝 Message Details:")
            print(f"   - Subject: {subject}")
            print(f"   - To: {email}")
            print(f"   - Login ID included: {login_id}")
            print(f"   - Timestamp: {created_at}")
            print(f"\n✨ User '{username}' should receive the login ID email shortly!")
            
    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")
        sys.exit(1)
        
else:
    print("\n❌ No pending registration found!")
    sys.exit(1)

conn.close()
