#!/usr/bin/env python
"""Test password recovery email sending"""

import os
import sys
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows terminals
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load environment
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

print("=" * 70)
print("PASSWORD RECOVERY EMAIL TEST")
print("=" * 70)

SMTP_SERVER = "smtp-relay.brevo.com"
SMTP_PORT = 587
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
SMTP_SENDER = os.getenv('SMTP_SENDER', 'no-reply@cybersecurity.local')

# Test email
test_email = "emailtest.final@company.com"
username = "emailtest_final"
reset_link = "http://127.0.0.1:8001/reset-password/abc123def456"

subject = "Password Reset Request - CyberShield Smart RBAC"

html_body = f"""
<html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #0066cc;">Password Reset Request</h2>
            <p>Hello {username},</p>
            <p>You requested a password reset for your CyberShield account.</p>
            <p>Please click the link below to reset your password:</p>
            <p style="text-align: center; margin: 30px 0;">
                <a href="{reset_link}" style="background-color: #0066cc; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    Reset Password
                </a>
            </p>
            <p style="color: #666; font-size: 14px;">
                Or copy this link: <br/>{reset_link}
            </p>
            <p style="color: #999; font-size: 12px; margin-top: 40px;">
                This link will expire in 1 hour.<br/>
                If you did not request this, please ignore this email.
            </p>
        </div>
    </body>
</html>
"""

text_body = (
    f"Hello {username},\n\n"
    f"You requested a password reset for your CyberShield account.\n"
    f"Please click the link below to reset your password:\n\n"
    f"{reset_link}\n\n"
    f"This link will expire in 1 hour.\n\n"
    f"If you did not request this, please ignore this email."
)

print(f"\n📧 Email Configuration:")
print(f"   From: {SMTP_SENDER}")
print(f"   To: {test_email}")
print(f"   Username: {username}")
print(f"   Subject: {subject}")

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
        msg['To'] = test_email
        
        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send
        server.send_message(msg)
        print(f"   ✓ Email sent successfully!")
        
        print(f"\n" + "=" * 70)
        print("✅ SUCCESS: Password recovery email was sent!")
        print("=" * 70)
        print(f"\n✨ Password recovery emails are working correctly!")
        
except Exception as e:
    print(f"\n❌ FAILED: {str(e)}")
    sys.exit(1)
