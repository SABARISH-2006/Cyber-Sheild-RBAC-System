#!/usr/bin/env python3
"""Test that generate_login_id() method never regenerates an existing login_id."""
import sys
import io
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure UTF-8 output on Windows terminals
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from smart_rbac.models import User
from smart_rbac.app import create_app

def test_generate_method_immutability():
    """Verify generate_login_id() method never changes existing login_id."""
    print("\nTesting generate_login_id() Method Immutability...")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        # Get testuser_permanent using sqlite compatibility method
        user = User.find_by_username('testuser_permanent')
        
        if not user:
            print("Creating missing testuser_permanent user...")
            import bcrypt
            pw_hash = bcrypt.hashpw(b'permanent123', bcrypt.gensalt()).decode('utf-8')
            user = User(
                username='testuser_permanent',
                email='permanent@company.com',
                password_hash=pw_hash,
                role='Employee',
                status='active',
                login_id='EMP_PERM_999'
            )
            user.save()
        
        original_login_id = user.login_id
        print(f"Original Login ID: {original_login_id}")
        
        # Try to "generate" login_id again (should return existing, not regenerate)
        generated_again = user.generate_login_id()
        print(f"After generate_login_id(): {generated_again}")
        
        # Verify they're the same
        if original_login_id == generated_again:
            print("=" * 60)
            print(f"✓ SUCCESS: generate_login_id() returns EXISTING ID")
            print(f"  Method correctly prevents regeneration")
            print(f"  Fixed Login ID remains: {original_login_id}")
            return True
        else:
            print("=" * 60)
            print(f"✗ FAILURE: generate_login_id() regenerated the ID!")
            print(f"  Before: {original_login_id}")
            print(f"  After:  {generated_again}")
            return False

if __name__ == '__main__':
    try:
        success = test_generate_method_immutability()
        exit(0 if success else 1)
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        exit(1)
