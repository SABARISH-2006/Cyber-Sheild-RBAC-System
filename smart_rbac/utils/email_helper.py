import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

# Brevo SMTP Configuration (Fixed IP relay - no IP whitelisting required)
BREVO_SMTP_SERVER = "smtp-relay.brevo.com"
BREVO_SMTP_PORT = 587

def _send_email_via_brevo_smtp(to_email, subject, html_body, text_body):
    """
    Send email via Brevo SMTP Relay (Fixed IP - no IP whitelist issues).
    This is more stable than REST API for dynamic IP environments.
    """
    smtp_username = current_app.config.get('SMTP_USERNAME')
    smtp_password = current_app.config.get('SMTP_PASSWORD')
    sender_email = current_app.config.get('SMTP_SENDER', 'no-reply@cybersecurity.local')
    
    if not smtp_username or not smtp_password:
        current_app.logger.error("Brevo SMTP credentials not configured.")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = to_email
        
        # Attach both text and HTML versions
        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send via Brevo SMTP Relay
        with smtplib.SMTP(BREVO_SMTP_SERVER, BREVO_SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        current_app.logger.info(f"Email sent successfully to {to_email} via Brevo SMTP Relay")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        current_app.logger.error(f"Brevo SMTP authentication failed: {str(e)}")
        return False
    except smtplib.SMTPException as e:
        current_app.logger.error(f"Brevo SMTP error: {str(e)}")
        return False
    except Exception as e:
        current_app.logger.error(f"Failed to send email via Brevo SMTP: {str(e)}")
        return False


def send_reset_email(to_email, username, reset_link):
    """
    Send a password reset email using Brevo SMTP Relay.
    Falls back to console logging if Brevo SMTP is not configured or fails.
    """
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
    
    # Use Brevo SMTP Relay (Fixed IP - no IP whitelist issues)
    email_sent = _send_email_via_brevo_smtp(to_email, subject, html_body, text_body)
    
    if not email_sent:
        # Fallback to console logging
        current_app.logger.warning(f"Email delivery to {to_email} via Brevo failed. Logging to console.")
        print(f"\n==================================================", flush=True)
        print(f"[SECURITY ALERT] FORGOT PASSWORD RESET REQUEST FOR: {username}", flush=True)
        print(f"[RESET SIMULATION] EMAIL: {to_email}", flush=True)
        print(f"[RESET LINK]: {reset_link}", flush=True)
        print(f"==================================================\n", flush=True)
        return False
    
    return True


def send_otp_email(to_email, username, otp_code):
    """
    Send an MFA verification OTP code email using Brevo SMTP Relay.
    Falls back to console logging if Brevo SMTP is not configured or fails.
    """
    subject = "CyberShield MFA Verification Code"
    
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #0066cc;">MFA Verification Code</h2>
                <p>Hello {username},</p>
                <p>Your CyberShield access verification code is:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <div style="font-size: 36px; font-weight: bold; letter-spacing: 5px; color: #0066cc; font-family: monospace;">
                        {otp_code}
                    </div>
                </div>
                <p style="color: #999; font-size: 12px;">
                    This code will expire in 5 minutes.<br/>
                    If you did not request this, please change your password immediately.
                </p>
            </div>
        </body>
    </html>
    """
    
    text_body = (
        f"Hello {username},\n\n"
        f"Your CyberShield access verification code is: {otp_code}\n\n"
        f"This code will expire in 5 minutes.\n\n"
        f"If you did not request this, please change your password immediately."
    )
    
    # Use Brevo SMTP Relay (Fixed IP - no IP whitelist issues)
    email_sent = _send_email_via_brevo_smtp(to_email, subject, html_body, text_body)
    
    if not email_sent:
        # Fallback to console logging
        current_app.logger.warning(f"Email delivery to {to_email} via Brevo failed. Logging to console.")
        print(f"\n==================================================", flush=True)
        print(f"[SECURITY CONTROL] OTP VERIFICATION REQUIRED FOR USER: {username}", flush=True)
        print(f"[OTP SIMULATION] MFA CODE GENERATED: {otp_code}", flush=True)
        print(f"[OTP SIMULATION] EMAIL STATUS: FAILED - Check Brevo API key configuration", flush=True)
        print(f"==================================================\n", flush=True)
        return False
    
    return True


def send_login_id_email(to_email, username, login_id, role):
    """
    Send the user's assigned Login ID via email during registration.
    Falls back to console logging if Brevo API is not configured or fails.
    """
    subject = "Your CyberShield Login ID - Welcome to Smart RBAC"
    
    role_display = {
        'Employee': 'Employee (Standard Access)',
        'Manager': 'Manager (Approving Authority)',
        'Admin': 'Administrator (Full Control)',
        'Auditor': 'Compliance Auditor (Read Logs)'
    }
    role_text = role_display.get(role, role)
    
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
                    <li><strong>Email:</strong> {to_email}</li>
                    <li><strong>Role:</strong> {role_text}</li>
                </ul>
                
                <p><strong>How to Sign In:</strong></p>
                <ol style="color: #666;">
                    <li>Visit the CyberShield authentication portal</li>
                    <li>Select "SIGN IN" tab</li>
                    <li>Enter your <strong>Login ID: {login_id}</strong></li>
                    <li>Enter your password</li>
                    <li>Complete the 6-digit MFA verification code</li>
                </ol>
                
                <p style="color: #999; font-size: 12px; margin-top: 40px;">
                    <strong>Security Note:</strong> Your login ID is permanently assigned and unique to your account. 
                    Keep it secure and do not share it with anyone.<br/>
                    If you did not create this account, please contact your administrator immediately.
                </p>
            </div>
        </body>
    </html>
    """
    
    text_body = (
        f"Welcome to CyberShield Smart RBAC\n\n"
        f"Hello {username},\n\n"
        f"Your account has been successfully created. Below is your unique login credential:\n\n"
        f"YOUR LOGIN ID: {login_id}\n\n"
        f"Account Details:\n"
        f"- Email: {to_email}\n"
        f"- Role: {role_text}\n\n"
        f"How to Sign In:\n"
        f"1. Visit the CyberShield authentication portal\n"
        f"2. Select SIGN IN tab\n"
        f"3. Enter your Login ID: {login_id}\n"
        f"4. Enter your password\n"
        f"5. Complete the 6-digit MFA verification code\n\n"
        f"Security Note: Your login ID is permanently assigned and unique to your account. "
        f"Keep it secure and do not share it with anyone.\n"
        f"If you did not create this account, please contact your administrator immediately."
    )
    
    # Use Brevo SMTP Relay (Fixed IP - no IP whitelist issues)
    email_sent = _send_email_via_brevo_smtp(to_email, subject, html_body, text_body)
    
    if not email_sent:
        # Fallback to console logging
        current_app.logger.warning(f"Email delivery to {to_email} via Brevo SMTP failed. Logging to console.")
        print(f"\n==================================================", flush=True)
        print(f"[REGISTRATION CONFIRMATION] USER: {username}", flush=True)
        print(f"[LOGIN ID ASSIGNED]: {login_id}", flush=True)
        print(f"[EMAIL ADDRESS]: {to_email}", flush=True)
        print(f"[ROLE ASSIGNED]: {role_text}", flush=True)
        print(f"[EMAIL SENT STATUS]: FAILED - Check Brevo SMTP configuration", flush=True)
        print(f"==================================================\n", flush=True)
        return False
    else:
        # Email sent successfully - log confirmation for audit trail
        print(f"\n==================================================", flush=True)
        print(f"[REGISTRATION CONFIRMATION] USER: {username}", flush=True)
        print(f"[LOGIN ID ASSIGNED]: {login_id}", flush=True)
        print(f"[EMAIL ADDRESS]: {to_email}", flush=True)
        print(f"[ROLE ASSIGNED]: {role_text}", flush=True)
        print(f"[EMAIL SENT STATUS]: SUCCESS - Email delivered via Brevo", flush=True)
        print(f"==================================================\n", flush=True)
    
    return True
