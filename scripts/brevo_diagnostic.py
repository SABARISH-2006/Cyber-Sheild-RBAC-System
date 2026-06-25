#!/usr/bin/env python3
"""
Brevo Email System - Diagnostic and Manual Setup Guide
Shows what works and what needs fixing
"""

import os
from pathlib import Path

def show_status():
    """Show current system status"""
    
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / '.env')
    
    print("\n" + "="*70)
    print("BREVO EMAIL SYSTEM - DIAGNOSTIC REPORT")
    print("="*70)
    
    # Check 1: Python packages
    print("\n✅ [CHECK 1] PYTHON PACKAGES")
    print("-" * 70)
    try:
        import requests
        import flask
        from dotenv import load_dotenv
        print("  ✓ requests library installed")
        print("  ✓ Flask installed")
        print("  ✓ python-dotenv installed")
        print("  Status: PASS")
    except ImportError as e:
        print(f"  ✗ Missing: {e}")
        print("  Status: FAIL")
    
    # Check 2: Configuration
    print("\n[CHECK 2] CONFIGURATION FILES")
    print("-" * 70)
    
    env_path = Path(__file__).parent.parent / '.env'
    config_path = Path(__file__).parent.parent / 'smart_rbac' / 'config.py'
    helper_path = Path(__file__).parent.parent / 'smart_rbac' / 'utils' / 'email_helper.py'
    
    print(f"  {'.env file':<30} {'✓' if env_path.exists() else '✗'}")
    print(f"  {'config.py':<30} {'✓' if config_path.exists() else '✗'}")
    print(f"  {'email_helper.py':<30} {'✓' if helper_path.exists() else '✗'}")
    
    if all([env_path.exists(), config_path.exists(), helper_path.exists()]):
        print("  Status: PASS")
    else:
        print("  Status: FAIL")
    
    # Check 3: Environment variables
    print("\n[CHECK 3] ENVIRONMENT VARIABLES")
    print("-" * 70)
    
    api_key = os.getenv('BREVO_API_KEY', 'NOT SET')
    sender_email = os.getenv('BREVO_SENDER_EMAIL', 'NOT SET')
    sender_name = os.getenv('BREVO_SENDER_NAME', 'NOT SET')
    
    key_status = "✓ FOUND" if api_key != 'NOT SET' else "✗ MISSING"
    email_status = "✓ FOUND" if sender_email != 'NOT SET' else "✗ MISSING"
    name_status = "✓ FOUND" if sender_name != 'NOT SET' else "✗ MISSING"
    
    print(f"  BREVO_API_KEY{' '*17} {key_status}")
    if api_key != 'NOT SET':
        print(f"    └─ {api_key[:20]}...{api_key[-10:]}")
    
    print(f"  BREVO_SENDER_EMAIL{' '*12} {email_status}")
    if sender_email != 'NOT SET':
        print(f"    └─ {sender_email}")
    
    print(f"  BREVO_SENDER_NAME{' '*13} {name_status}")
    if sender_name != 'NOT SET':
        print(f"    └─ {sender_name}")
    
    if api_key != 'NOT SET' and sender_email != 'NOT SET':
        print("  Status: PASS")
    else:
        print("  Status: FAIL")
    
    # Check 4: API Connectivity (Test last)
    print("\n[CHECK 4] API CONNECTIVITY")
    print("-" * 70)
    
    if api_key == 'NOT SET':
        print("  ✗ Cannot test - API key not configured")
        print("  Status: SKIP (fix CHECK 3 first)")
    else:
        import requests
        try:
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'api-key': api_key
            }
            
            payload = {
                'sender': {'name': 'Test', 'email': sender_email},
                'to': [{'email': 'test@example.com'}],
                'subject': 'Test',
                'htmlContent': '<p>Test</p>',
                'textContent': 'Test'
            }
            
            response = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201, 400]:
                print(f"  ✓ Brevo API responding")
                print(f"  Status: PASS")
            elif response.status_code == 401:
                print(f"  ✗ API Key Invalid or Expired (401)")
                print(f"  Details: {response.json()}")
                print(f"  Status: FAIL - Need new API key")
            else:
                print(f"  ✗ Unexpected response ({response.status_code})")
                print(f"  Status: FAIL")
                
        except requests.exceptions.RequestException as e:
            print(f"  ✗ Connection error: {str(e)}")
            print(f"  Status: FAIL")
    
    # Summary
    print("\n" + "="*70)
    print("ACTION ITEMS")
    print("="*70)
    
    print("\n1. VERIFY/UPDATE BREVO API KEY")
    print("   ├─ Go to: https://app.brevo.com/settings/keys/api")
    print("   ├─ Log in to your account")
    print("   ├─ Create or copy an API key (starts with 'xsmtpsib-')")
    print("   └─ Keep it secure - DON'T share or commit to git")
    
    print("\n2. VERIFY SENDER EMAIL IN BREVO")
    print("   ├─ Go to: https://app.brevo.com/settings/addresses")
    print("   ├─ Look for: premkumarsanjay2006@gmail.com")
    print("   └─ Status should be: 'Verified' ✓")
    
    print("\n3. UPDATE .env FILE")
    print("   └─ Replace current API key with new one:")
    print(f"      BREVO_API_KEY=xsmtpsib-YOUR_NEW_KEY_HERE")
    
    print("\n4. RUN TESTS")
    print("   └─ python test_brevo_email.py")
    
    print("\n" + "="*70)

if __name__ == '__main__':
    show_status()
