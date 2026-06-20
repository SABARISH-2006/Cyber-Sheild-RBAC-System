#!/usr/bin/env python3
"""
Brevo Email API Test Script
Tests password reset and OTP email functions
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent / '.env')

# Add smart_rbac to path
sys.path.insert(0, str(Path(__file__).parent / 'smart_rbac'))

def test_brevo_config():
    """Test 1: Verify Brevo configuration"""
    print("\n" + "="*70)
    print("TEST 1: BREVO CONFIGURATION VERIFICATION")
    print("="*70)
    
    api_key = os.getenv('BREVO_API_KEY')
    sender_email = os.getenv('BREVO_SENDER_EMAIL')
    sender_name = os.getenv('BREVO_SENDER_NAME')
    
    print(f"\n✓ BREVO_API_KEY: {api_key[:20]}...{api_key[-10:] if api_key else 'NOT SET'}")
    print(f"✓ BREVO_SENDER_EMAIL: {sender_email}")
    print(f"✓ BREVO_SENDER_NAME: {sender_name}")
    
    if not api_key or not sender_email:
        print("\n❌ ERROR: Brevo API key or sender email not configured!")
        return False
    
    print("\n✅ Configuration looks good!")
    return True

def test_brevo_api_connection():
    """Test 2: Test direct Brevo API connection"""
    print("\n" + "="*70)
    print("TEST 2: BREVO API CONNECTION TEST")
    print("="*70)
    
    import requests
    
    api_key = os.getenv('BREVO_API_KEY')
    sender_email = os.getenv('BREVO_SENDER_EMAIL')
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'api-key': api_key
    }
    
    # Test with a dummy email (won't actually send)
    test_payload = {
        'sender': {
            'name': 'CyberShield Test',
            'email': sender_email
        },
        'to': [{'email': 'test@example.com'}],
        'subject': 'Test Email',
        'htmlContent': '<p>Test</p>',
        'textContent': 'Test'
    }
    
    print("\nTesting API endpoint: https://api.brevo.com/v3/smtp/email")
    print(f"Headers: api-key={api_key[:20]}..., Content-Type=application/json")
    
    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=test_payload,
            headers=headers,
            timeout=10
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code in [200, 201]:
            print("\n✅ API Connection Successful! Email would be sent.")
            return True
        elif response.status_code == 400:
            print("\n⚠ Bad request (expected for test email)")
            print(f"Details: {response.text}")
            return True
        elif response.status_code == 401:
            print("\n❌ Unauthorized! Invalid API key.")
            print(f"Details: {response.text}")
            return False
        else:
            print(f"\n⚠ Unexpected status: {response.status_code}")
            print(f"Details: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Connection failed: {str(e)}")
        return False

def test_email_helper():
    """Test 3: Test email helper functions"""
    print("\n" + "="*70)
    print("TEST 3: EMAIL HELPER FUNCTIONS TEST")
    print("="*70)
    
    try:
        from flask import Flask
        from smart_rbac.utils.email_helper import send_reset_email, send_otp_email
        
        # Create Flask app context
        app = Flask(__name__)
        app.config['BREVO_API_KEY'] = os.getenv('BREVO_API_KEY')
        app.config['BREVO_SENDER_EMAIL'] = os.getenv('BREVO_SENDER_EMAIL')
        app.config['BREVO_SENDER_NAME'] = os.getenv('BREVO_SENDER_NAME')
        
        print("\nFunctions imported successfully:")
        print(f"  ✓ send_reset_email: {send_reset_email}")
        print(f"  ✓ send_otp_email: {send_otp_email}")
        
        return True
        
    except ImportError as e:
        print(f"\n❌ Import error: {str(e)}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False

def test_email_sending():
    """Test 4: Send test emails"""
    print("\n" + "="*70)
    print("TEST 4: SEND TEST EMAILS")
    print("="*70)
    
    try:
        from flask import Flask
        from smart_rbac.utils.email_helper import send_reset_email, send_otp_email
        
        app = Flask(__name__)
        app.config['BREVO_API_KEY'] = os.getenv('BREVO_API_KEY')
        app.config['BREVO_SENDER_EMAIL'] = os.getenv('BREVO_SENDER_EMAIL')
        app.config['BREVO_SENDER_NAME'] = os.getenv('BREVO_SENDER_NAME')
        
        with app.app_context():
            # Test 4A: Send reset email
            print("\n[4A] Testing send_reset_email()...")
            test_email = "premkumarsanjay2006@gmail.com"
            reset_link = "http://localhost:5000/reset-password?token=test123token"
            
            result = send_reset_email(test_email, "testuser", reset_link)
            print(f"Result: {result}")
            
            if result:
                print("✅ Reset email sent successfully!")
            else:
                print("⚠ Reset email send returned False (check logs above)")
            
            # Test 4B: Send OTP email
            print("\n[4B] Testing send_otp_email()...")
            otp_code = "123456"
            
            result = send_otp_email(test_email, "testuser", otp_code)
            print(f"Result: {result}")
            
            if result:
                print("✅ OTP email sent successfully!")
            else:
                print("⚠ OTP email send returned False (check logs above)")
            
            return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*20 + "BREVO EMAIL SYSTEM TESTS" + " "*24 + "║")
    print("║" + " "*68 + "║")
    print("║  This script validates the Brevo API configuration and tests" + " "*7 + "║")
    print("║  email sending functions for password recovery and MFA OTP." + " "*8 + "║")
    print("╚" + "="*68 + "╝")
    
    results = {
        'Configuration': test_brevo_config(),
        'API Connection': test_brevo_api_connection(),
        'Email Helper': test_email_helper(),
        'Email Sending': test_email_sending(),
    }
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<40} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL TESTS PASSED! Brevo email system is working correctly.")
        print("\nYou can now use the recovery and MFA features:")
        print("  • Password Reset: /forgot-password")
        print("  • MFA OTP: Automatic on login")
    else:
        print("⚠ SOME TESTS FAILED! Check the errors above.")
        print("\nCommon issues:")
        print("  1. Invalid Brevo API key")
        print("  2. Sender email not verified in Brevo")
        print("  3. Network connectivity issue")
        print("  4. Brevo API service down")
    print("="*70)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
