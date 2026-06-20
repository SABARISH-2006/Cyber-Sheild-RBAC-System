#!/usr/bin/env python3
"""Test that generate_login_id() method never regenerates an existing login_id."""
import sys
sys.path.insert(0, '/e/rbac-cybersecurity')

from smart_rbac.models import db, User
from smart_rbac.app import create_app

def test_generate_method_immutability():
    """Verify generate_login_id() method never changes existing login_id."""
    print("\nTesting generate_login_id() Method Immutability...")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        # Get testuser_permanent
        user = db.session.scalar(db.select(User).where(User.username == 'testuser_permanent'))
        
        if not user:
            print("✗ User not found!")
            return False
        
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
