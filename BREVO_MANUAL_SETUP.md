# Brevo Email System - Manual Setup Guide

## Current Status

```
✅ Python packages installed
✅ Configuration files in place  
✅ Environment variables loaded
❌ API KEY INVALID OR EXPIRED (401 Error)
```

## Quick Fix - 3 Steps

### Step 1: Get a Valid Brevo API Key

1. **Open Brevo Settings:**
   - Go to: https://app.brevo.com/settings/keys/api
   - Login to your Brevo account

2. **Create/Copy API Key:**
   - Click "Create a new API key" OR copy an existing one
   - It should look like: `xsmtpsib-XXXXXXXXXXXXXXXXXXXX...`
   - This is different from SMTP credentials

3. **Copy the Key:**
   - Select all and copy to clipboard
   - Keep it secret (don't share or commit to git)

### Step 2: Update .env File

**Edit** `e:\rbac-cybersecurity\.env`

```env
# Replace this line:
BREVO_API_KEY=xsmtpsib-PLACEHOLDER_BREVO_API_KEY_DO_NOT_COMMIT_SECRETS


# With your new API key:
BREVO_API_KEY=xsmtpsib-YOUR_NEW_API_KEY_HERE
```

Example format (yours will be longer):
```env
BREVO_API_KEY=xsmtpsib-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
```

### Step 3: Verify Sender Email

1. **Go to Brevo Senders:**
   - Visit: https://app.brevo.com/settings/addresses

2. **Check Email Status:**
   - Look for: `premkumarsanjay2006@gmail.com`
   - Status should show: ✓ Verified
   - If not verified, Brevo will send verification link to that email

## Testing Steps

Once you've updated the API key, test it systematically:

### Test 1: Diagnostic Check
```bash
cd e:\rbac-cybersecurity
python brevo_diagnostic.py
```

**Expected output:**
```
[CHECK 4] API CONNECTIVITY
  ✓ Brevo API responding
  Status: PASS
```

### Test 2: Full Email System Test
```bash
python test_brevo_email.py
```

**Expected output:**
```
✅ ALL TESTS PASSED! Brevo email system is working correctly.
```

### Test 3: Manual Email Test
```bash
python
```

Then paste this code:

```python
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask

# Load env vars
load_dotenv(Path.cwd() / '.env')

# Create app
app = Flask(__name__)
app.config['BREVO_API_KEY'] = os.getenv('BREVO_API_KEY')
app.config['BREVO_SENDER_EMAIL'] = os.getenv('BREVO_SENDER_EMAIL')
app.config['BREVO_SENDER_NAME'] = os.getenv('BREVO_SENDER_NAME')

# Import and test
from smart_rbac.utils.email_helper import send_reset_email

with app.app_context():
    result = send_reset_email(
        'premkumarsanjay2006@gmail.com',
        'testuser',
        'http://localhost:5000/reset-password?token=test123'
    )
    print(f"Email sent: {result}")
```

Press `Ctrl+D` to exit.

## Troubleshooting

### Issue: Still getting 401 error?

**Solution:**
1. Double-check the API key - copy it again from Brevo
2. Ensure there are no extra spaces before/after
3. Make sure you're using API key, not SMTP credentials
4. Verify sender email is marked as "Verified" in Brevo

### Issue: Email not arriving?

**Check:**
1. API key is valid (run `brevo_diagnostic.py`)
2. Sender email is verified in Brevo
3. Check Gmail spam folder
4. Add Brevo SPF/DKIM records (optional, for production)

### Issue: Need to verify email address in Brevo?

**Steps:**
1. Brevo sends verification email to: `premkumarsanjay2006@gmail.com`
2. Click the verification link in that email
3. Go back to https://app.brevo.com/settings/addresses
4. Status should now show ✓ Verified

## Testing Email Features

### After setup is working:

**Test 1: Password Recovery**
1. Go to: `http://localhost:5000/`
2. Click "Forgot Password"
3. Enter: `premkumarsanjay2006@gmail.com`
4. Check inbox for reset link

**Test 2: MFA OTP**
1. Go to: `http://localhost:5000/`
2. Login with valid credentials
3. Check inbox for OTP code
4. Enter code to complete login

## Terminal Commands Reference

```bash
# Check configuration
python brevo_diagnostic.py

# Run comprehensive tests
python test_brevo_email.py

# Interactive setup (if needed)
python setup_brevo_api_key.py

# View current .env config
type .env | findstr BREVO

# Start Flask app
python -m smart_rbac.app
```

## Additional Resources

- **Brevo API Docs:** https://developers.brevo.com/docs/send-transactional-emails
- **API Key Settings:** https://app.brevo.com/settings/keys/api
- **Sender Email Settings:** https://app.brevo.com/settings/addresses
- **Brevo Support:** https://www.brevo.com/contact-support/

---

## Quick Reference: What Each File Does

| File | Purpose |
|------|---------|
| `.env` | Stores API key and sender email |
| `smart_rbac/config.py` | Reads .env and makes available to app |
| `smart_rbac/utils/email_helper.py` | Sends emails via Brevo API |
| `test_brevo_email.py` | Comprehensive test suite |
| `brevo_diagnostic.py` | Quick status check |
| `setup_brevo_api_key.py` | Interactive setup wizard |

---

**Need help?** Re-run the diagnostic to see current status:
```bash
python brevo_diagnostic.py
```
