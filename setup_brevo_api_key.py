#!/usr/bin/env python3
"""
Brevo API Key Setup and Validation
Interactive script to configure and test your Brevo API key
"""

import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv, dotenv_values

def get_brevo_api_key():
    """Get API key from user input"""
    print("\n" + "="*70)
    print("BREVO API KEY SETUP")
    print("="*70)
    
    print("\nTo get your Brevo API key:")
    print("  1. Go to: https://app.brevo.com/settings/keys/api")
    print("  2. Log in to your Brevo account")
    print("  3. Click 'Create a new API key' or copy existing one")
    print("  4. It should start with 'xsmtpsib-'")
    
    api_key = input("\nEnter your Brevo API key (or press Enter to skip): ").strip()
    return api_key if api_key else None

def get_sender_email():
    """Get sender email from user input"""
    print("\nTo verify your sender email in Brevo:")
    print("  1. Go to: https://app.brevo.com/settings/addresses")
    print("  2. Make sure your email is 'Verified'")
    print("  3. If not verified, Brevo will send you a link")
    
    sender_email = input("\nEnter sender email (current: premkumarsanjay2006@gmail.com): ").strip()
    return sender_email if sender_email else "premkumarsanjay2006@gmail.com"

def test_api_key(api_key):
    """Test if API key is valid"""
    print("\n" + "="*70)
    print("TESTING API KEY")
    print("="*70)
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'api-key': api_key
    }
    
    payload = {
        'sender': {
            'name': 'CyberShield Test',
            'email': 'test@example.com'
        },
        'to': [{'email': 'test@example.com'}],
        'subject': 'API Test',
        'htmlContent': '<p>Test</p>',
        'textContent': 'Test'
    }
    
    try:
        print("\nSending test request to Brevo API...")
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code in [200, 201]:
            print("\n✅ API key is VALID!")
            return True
        elif response.status_code == 400:
            print("\n✅ API key is VALID! (400 is normal for test email)")
            return True
        elif response.status_code == 401:
            print("\n❌ API key is INVALID or EXPIRED!")
            print(f"Error: {response.text}")
            return False
        else:
            print(f"\n⚠ Unexpected response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ Connection error: {str(e)}")
        return False

def update_env_file(api_key, sender_email):
    """Update .env file with new configuration"""
    env_path = Path(__file__).parent / '.env'
    
    print("\n" + "="*70)
    print("UPDATING .env FILE")
    print("="*70)
    
    # Read current .env
    env_vars = dotenv_values(env_path)
    
    # Update Brevo variables
    env_vars['BREVO_API_KEY'] = api_key
    env_vars['BREVO_SENDER_EMAIL'] = sender_email
    env_vars['BREVO_SENDER_NAME'] = 'CyberShield Smart RBAC'
    
    # Write back to .env
    with open(env_path, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    print(f"\n✅ Updated .env file:")
    print(f"  BREVO_API_KEY={api_key[:20]}...{api_key[-10:]}")
    print(f"  BREVO_SENDER_EMAIL={sender_email}")
    print(f"  BREVO_SENDER_NAME=CyberShield Smart RBAC")

def main():
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*18 + "BREVO EMAIL CONFIGURATION SETUP" + " "*18 + "║")
    print("╚" + "="*68 + "╝")
    
    # Step 1: Get API key
    api_key = get_brevo_api_key()
    if not api_key:
        print("\n❌ API key is required!")
        return 1
    
    # Step 2: Test API key
    if not test_api_key(api_key):
        print("\n⚠ API key validation failed!")
        retry = input("\nRetry with different key? (y/n): ").strip().lower()
        if retry == 'y':
            return main()
        else:
            print("\n❌ Setup cancelled.")
            return 1
    
    # Step 3: Get sender email
    sender_email = get_sender_email()
    
    # Step 4: Update .env
    update_env_file(api_key, sender_email)
    
    print("\n" + "="*70)
    print("✅ SETUP COMPLETE!")
    print("="*70)
    print("\nNext steps:")
    print("  1. Verify sender email in Brevo: https://app.brevo.com/settings/addresses")
    print("  2. Run tests again: python test_brevo_email.py")
    print("  3. Test password recovery: /forgot-password")
    print("="*70)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
