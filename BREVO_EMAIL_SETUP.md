# Brevo Email Configuration Guide

This project now uses **Brevo API** (formerly Sendinblue) for reliable email delivery, replacing the previous SMTP configuration. This ensures emails are successfully delivered to Gmail and other email providers.

## What Was Fixed

- **Old Issue**: SMTP relay through `smtp-relay.brevo.com` sometimes fails to deliver emails, especially to Gmail
- **New Solution**: Direct Brevo REST API integration for guaranteed delivery
- **Benefits**: Better deliverability, tracking, and Gmail compatibility

## Setup Instructions

### 1. Get Your Brevo API Key

1. Go to [Brevo Console](https://app.brevo.com/)
2. Log in to your account
3. Navigate to **Settings** → **API & Apps** → **SMTP & API**
4. Under **API Keys** section, click **Create a new API key** (or use existing one)
5. Copy your **API Key** (it starts with `xsmtpsib-...`)

### 2. Verify Sender Email

1. In Brevo Console, go to **Senders**
2. Make sure your sender email (`premkumarsanjay2006@gmail.com`) is verified
3. If not verified, Brevo will send a verification link to that email

### 3. Update `.env` File

Add/Update these variables in your `.env` file:

```env
# Brevo Email Service Configuration (API Method - Recommended)
BREVO_API_KEY=xsmtpsib-your-api-key-here
BREVO_SENDER_EMAIL=premkumarsanjay2006@gmail.com
BREVO_SENDER_NAME=CyberShield Smart RBAC
```

Replace `xsmtpsib-your-api-key-here` with your actual Brevo API key.

### 4. Install Dependencies

Run the following command to install the required `requests` library:

```bash
cd smart_rbac
pip install -r requirements.txt
```

## How It Works

### Email Functions

The system now uses two main email functions via Brevo API:

#### 1. **send_reset_email()** - Password Recovery
- **Triggered when**: User clicks "Forgot Password" on login
- **Delivery**: Password reset link with 1-hour expiration
- **Template**: HTML formatted with branded styling

#### 2. **send_otp_email()** - MFA Verification
- **Triggered when**: User logs in (MFA required)
- **Delivery**: 6-digit OTP code with 5-minute expiration
- **Template**: HTML formatted with large, easy-to-read code

### Fallback Mechanism

If Brevo API fails or is not configured:
- Emails are logged to console for testing/debugging
- Users see appropriate flash messages
- System continues to work in development mode

## Testing

### Test Password Recovery

1. Go to login page → Click "Forgot Password"
2. Enter a registered email address
3. Check:
   - Email inbox for reset link
   - Application logs for confirmation
   - Console for fallback messages if API fails

### Test MFA OTP

1. Log in with valid credentials
2. OTP email should arrive within seconds
3. Check:
   - Email contains the 6-digit code
   - Code matches console output (if email fails)

## Troubleshooting

### Issue: "Email sending failed" or emails not arriving

**Solution 1**: Verify Brevo API Key
```python
# In Flask shell or app context
from flask import current_app
print(current_app.config.get('BREVO_API_KEY'))
```

**Solution 2**: Check sender email is verified in Brevo
- Log into Brevo console
- Go to Senders section
- Ensure `premkumarsanjay2006@gmail.com` shows "Verified" status

**Solution 3**: Check logs for API errors
```bash
# Look for error messages in application logs
# Format: "Brevo API error (XXX): [error details]"
```

**Solution 4**: Test Brevo API directly
```bash
curl -X POST https://api.brevo.com/v3/smtp/email \
  -H "api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "sender": {"email": "premkumarsanjay2006@gmail.com", "name": "CyberShield"},
    "to": [{"email": "your-test-email@gmail.com"}],
    "subject": "Test Email",
    "htmlContent": "<p>Test email from Brevo API</p>"
  }'
```

### Issue: Emails going to spam

**Solution**: Add SPF & DKIM records
- Brevo provides SPF/DKIM setup instructions
- Add them to your domain DNS settings (if applicable)
- This ensures Gmail won't mark emails as spam

### Issue: "User enumeration" - emails to non-existent users

**Current behavior**: System shows generic message without confirming if email exists (security best practice)

## API Response Codes

| Code | Status | Meaning |
|------|--------|---------|
| 200 | Success | Email queued for delivery |
| 201 | Created | Email accepted and processing |
| 400 | Bad Request | Invalid email format or payload |
| 401 | Unauthorized | Invalid or missing API key |
| 403 | Forbidden | API key doesn't have permission |
| 429 | Too Many Requests | Rate limit exceeded |

## Performance Notes

- **API Timeout**: Set to 10 seconds per request
- **Expected Delivery**: <1 second to inbox (usually)
- **Rate Limits**: Brevo free tier: ~500 emails/day
- **HTML Templates**: Automatically includes plain text fallback

## Security Notes

- ✅ API key stored securely in `.env` (never commit to git!)
- ✅ Password reset links expire in 1 hour
- ✅ OTP codes expire in 5 minutes
- ✅ No sensitive data logged in error messages
- ✅ HTML emails include unsubscribe/footer (Brevo requirement)

## Migration from SMTP

If you were using SMTP before:

**Old Code**: Used `smtplib` with SMTP credentials
**New Code**: Uses `requests` library with Brevo REST API

**Why the change?**
- SMTP relay is less reliable for Gmail delivery
- Direct API gives better control and tracking
- Brevo API handles rate limiting and authentication
- Better error responses and retry logic

---

## Support

For Brevo-specific issues:
- **Brevo Docs**: https://developers.brevo.com/docs/send-transactional-emails
- **Brevo Support**: https://www.brevo.com/contact-support/
- **API Status**: https://status.brevo.com/
