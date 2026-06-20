import datetime
import hashlib
import random
from flask import Blueprint, render_template, redirect, url_for, request, flash, session, make_response, jsonify, current_app
import bcrypt

from smart_rbac.models import User, OTP, AuditLog, Role, AccessRequest, BehaviorAlert, RiskScore, db
from smart_rbac.utils.auth_helper import generate_token, get_current_user
from smart_rbac.utils.risk_evaluator import evaluate_login_risk
from smart_rbac.utils.uba_engine import record_failed_attempt, trigger_time_anomaly_alert

auth_bp = Blueprint('auth', __name__)

def hash_otp(code):
    """Utility to SHA-256 hash an OTP code."""
    return hashlib.sha256(code.encode('utf-8')).hexdigest()

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle User Registration."""
    if get_current_user():
        return redirect(url_for('auth.dashboard_redirect'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'Employee')

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template('login.html', active_tab='register')

        # Check existing user
        existing_user = User.find_by_username(username) or User.find_by_email(email)
        if existing_user:
            flash("Username or Email already registered.", "danger")
            return render_template('login.html', active_tab='register')

        # Create user
        try:
            pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            new_user = User(
                username=username,
                email=email,
                password_hash=pw_hash,
                role=role,
                status='pending_approval'  # User starts in pending approval state
            )
            new_user.generate_login_id()
            new_user.save()

            # Create registration approval request
            from smart_rbac.models import RegistrationRequest
            reg_request = RegistrationRequest(
                user_id=new_user.id,
                username=username,
                email=email,
                role=role,
                login_id=new_user.login_id,
                status='pending'
            )
            reg_request.save()
            
            # Log registration
            audit = AuditLog(
                username=username,
                action="USER_REGISTRATION_INITIATED - Awaiting superadmin approval",
                ip_address=request.remote_addr or '127.0.0.1'
            )
            audit.save()

            # Send login_id via email
            from smart_rbac.utils.email_helper import send_login_id_email
            send_login_id_email(email, username, new_user.login_id, role)

            # Success message - inform user about approval process
            flash("Registration successful! Your request has been sent to the superadmin for approval. You will be able to login after approval.", "success")
            return render_template('login.html', active_tab='register')
        except Exception as e:
            current_app.logger.error(f"Registration error: {str(e)}")
            flash("An error occurred during registration. Please try again.", "danger")

    return render_template('login.html', active_tab='register')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle User Login with Multi-Factor Authentication (OTP) trigger."""
    if get_current_user():
        return redirect(url_for('auth.dashboard_redirect'))

    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        password = request.form.get('password', '')

        if not login_id or not password:
            flash("Login ID and password are required.", "danger")
            return render_template('login.html', active_tab='login')

        # Find user by login_id
        user = User.find_by_login_id(login_id)
        
        ip_addr = request.remote_addr or '127.0.0.1'

        if not user:
            # Fake hash comparison to mitigate user enumeration timing attacks
            bcrypt.checkpw(b"dummy", b"$2b$12$LpyO30f/F1b5f90F7qD2Qe9X8W.HpxsC2J7j1O74/uQ7X45W8rTdq")
            flash("Invalid credentials.", "danger")
            return render_template('login.html', active_tab='login')

        # Check if account is pending approval
        if user.status == 'pending_approval':
            flash("Your account registration is pending superadmin approval. You will be able to login once your account is approved. Please check your email for updates.", "warning")
            return render_template('login.html', active_tab='login')

        # Check if account is suspended/locked
        if user.status == 'suspended':
            flash("Your account is locked due to security anomalies or too many failed login attempts. Contact an Admin.", "danger")
            return render_template('login.html', active_tab='login')

        # Check password
        if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            is_locked = record_failed_attempt(user, ip_addr)
            if is_locked:
                flash("Your account has been locked due to 5 failed login attempts.", "danger")
            else:
                flash("Invalid credentials.", "danger")
            return render_template('login.html', active_tab='login')

        # Credentials valid - Parse User Agent fingerprints
        device = request.user_agent.platform or "Unknown OS/Device"
        browser = request.user_agent.browser or "Unknown Browser"
        user_agent_info = {
            'device': device,
            'browser': browser
        }

        # Evaluate risk score
        risk_record = evaluate_login_risk(user, user_agent_info, ip_addr)
        
        # Monitor for UBA anomalies
        trigger_time_anomaly_alert(user, ip_addr)

        # Generate 6-digit OTP code for EVERY successful login
        otp_code = f"{random.randint(100000, 999999)}"
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        
        # Deactivate any previous unused OTPs
        for o in OTP.find_by_field('user_id', user.id):
            if not o.is_used:
                o.is_used = True
                o.save()
        
        otp_record = OTP(
            user_id=user.id,
            otp_code_hash=hash_otp(otp_code),
            expires_at=expires_at,
            is_used=False
        )
        otp_record.save()

        # Store in session for OTP verification phase
        session['mfa_user_id'] = user.id
        session['mfa_device'] = device
        session['mfa_browser'] = browser
        session['mfa_risk_score'] = risk_record.score
        session['mfa_risk_level'] = risk_record.risk_level
        
        # Attempt to send OTP via mail
        from smart_rbac.utils.email_helper import send_otp_email
        email_sent = send_otp_email(user.email, user.username, otp_code)

        # Print/Log OTP for terminal simulation of the email/SMS transmission
        print(f"\n==================================================", flush=True)
        print(f"[SECURITY CONTROL] OTP VERIFICATION REQUIRED FOR USER: {user.username}", flush=True)
        print(f"[SECURITY CONTROL] RISK SCORE: {risk_record.score} | LEVEL: {risk_record.risk_level}", flush=True)
        print(f"[OTP SIMULATION] MFA CODE GENERATED: {otp_code}", flush=True)
        print(f"[OTP SIMULATION] EMAIL SENT STATUS: {email_sent}", flush=True)
        print(f"==================================================\n", flush=True)
        
        if email_sent:
            flash("Verification code sent to your registered email address.", "success")
        else:
            flash("Verification code generated. Code has been logged in the terminal console.", "warning")
            
        return redirect(url_for('auth.verify_otp'))

    return render_template('login.html', active_tab='login')


@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    """Verify 2FA security code."""
    user_id = session.get('mfa_user_id')
    if not user_id:
        flash("MFA session expired. Please sign in again.", "danger")
        return redirect(url_for('auth.login'))

    user = User.get(user_id)
    if not user:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        otp_code = request.form.get('otp_code', '').strip()
        
        # Retrieve latest unused, unexpired OTP
        user_otps = OTP.find_by_field('user_id', user.id)
        active_otps = []
        for o in user_otps:
            if not o.is_used:
                exp = o.expires_at
                if isinstance(exp, str):
                    try:
                        exp = datetime.datetime.fromisoformat(exp.replace('Z', ''))
                    except Exception:
                        exp = datetime.datetime.utcnow()
                if exp > datetime.datetime.utcnow():
                    active_otps.append(o)
        
        active_otps.sort(key=lambda x: x.created_at or datetime.datetime.min, reverse=True)
        otp_record = active_otps[0] if active_otps else None

        ip_addr = request.remote_addr or '127.0.0.1'

        if otp_record and otp_record.otp_code_hash == hash_otp(otp_code):
            # Success: Mark OTP as used
            otp_record.is_used = True
            otp_record.save()
            
            # Reset login attempts & update fingerprints
            user.failed_login_attempts = 0
            user.last_login_device = session.get('mfa_device')
            user.last_login_browser = session.get('mfa_browser')
            user.save()

            risk_score = session.get('mfa_risk_score', 10.0)
            risk_level = session.get('mfa_risk_level', 'Low')

            # Audit success with MFA
            audit = AuditLog(
                username=user.username,
                action=f"LOGIN_SUCCESS_WITH_MFA (Risk Score: {risk_score} - {risk_level})",
                ip_address=ip_addr
            )
            audit.save()

            # Clean session keys
            session.pop('mfa_user_id', None)
            session.pop('mfa_device', None)
            session.pop('mfa_browser', None)
            session.pop('mfa_risk_score', None)
            session.pop('mfa_risk_level', None)

            # Generate token and set cookie
            token = generate_token(user.id)
            resp = make_response(redirect(url_for('auth.dashboard')))
            resp.set_cookie('access_token', token, httponly=True, secure=False)
            return resp
        else:
            # Log failed OTP
            audit = AuditLog(
                username=user.username,
                action="MFA_VERIFICATION_FAILED",
                ip_address=ip_addr
            )
            audit.save()
            
            flash("Invalid or expired verification code.", "danger")

    return render_template('otp.html', username=user.username)


@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    """Resend a new 6-digit OTP code to the user."""
    user_id = session.get('mfa_user_id')
    if not user_id:
        flash("MFA session expired. Please sign in again.", "danger")
        return redirect(url_for('auth.login'))

    user = User.get(user_id)
    if not user:
        return redirect(url_for('auth.login'))

    otp_code = f"{random.randint(100000, 999999)}"
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)

    # Deactivate previous unused OTPs
    for o in OTP.find_by_field('user_id', user.id):
        if not o.is_used:
            o.is_used = True
            o.save()

    otp_record = OTP(
        user_id=user.id,
        otp_code_hash=hash_otp(otp_code),
        expires_at=expires_at,
        is_used=False
    )
    otp_record.save()

    # Attempt to send OTP via mail
    from smart_rbac.utils.email_helper import send_otp_email
    email_sent = send_otp_email(user.email, user.username, otp_code)

    # Print/Log OTP for console simulation fallback
    print(f"\n==================================================", flush=True)
    print(f"[SECURITY CONTROL] RESEND OTP REQUESTED FOR: {user.username}", flush=True)
    print(f"[SECURITY CONTROL] MFA CODE GENERATED: {otp_code}", flush=True)
    print(f"[SECURITY CONTROL] EMAIL SENT STATUS: {email_sent}", flush=True)
    print(f"==================================================\n", flush=True)

    if email_sent:
        flash("A new verification code has been sent to your email address.", "success")
    else:
        flash("A new verification code has been logged in the terminal console.", "warning")

    return redirect(url_for('auth.verify_otp'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot Password page and recovery flow."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = User.find_by_email(email)
        if user:
            # Generate code or token link
            reset_token = hashlib.sha256(f"{user.username}-{random.random()}".encode()).hexdigest()
            
            # Create OTP record for password reset (reusing the OTP model)
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            # Mark previous unused reset tokens as used/invalidated
            for o in OTP.find_by_field('user_id', user.id):
                if not o.is_used:
                    o.is_used = True
                    o.save()
            
            otp_record = OTP(
                user_id=user.id,
                otp_code_hash=hash_otp(reset_token),
                expires_at=expires_at,
                is_used=False
            )
            otp_record.save()
            
            reset_link = url_for('auth.reset_password', token=reset_token, _external=True)
            
            # Attempt to send SMTP email
            from smart_rbac.utils.email_helper import send_reset_email
            email_sent = send_reset_email(user.email, user.username, reset_link)
            
            if email_sent:
                flash("A password reset link has been sent to your email address.", "success")
            else:
                # Log fallback console simulation
                current_app.logger.warning(f"[RESET SIMULATION] LINK: {reset_link}")
                print(f"\n==================================================", flush=True)
                print(f"[SECURITY ALERT] FORGOT PASSWORD RESET REQUEST FOR: {user.username}", flush=True)
                print(f"[RESET SIMULATION] LINK: {reset_link}", flush=True)
                print(f"==================================================\n", flush=True)
                flash("If email exists, a password reset link has been logged in the terminal console.", "success")
        else:
            flash("If email exists, a password reset link has been logged in the terminal console.", "success")
        return redirect(url_for('auth.login'))

    return render_template('login.html', active_tab='forgot')


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Handle password reset verification and submission."""
    token = request.args.get('token') or request.form.get('token')
    if not token:
        flash("Invalid or missing reset token.", "danger")
        return redirect(url_for('auth.login'))
        
    hashed = hash_otp(token)
    active_otps = OTP.find_by_field('otp_code_hash', hashed)
    otp_record = None
    for o in active_otps:
        if not o.is_used:
            exp = o.expires_at
            if isinstance(exp, str):
                try:
                    exp = datetime.datetime.fromisoformat(exp.replace('Z', ''))
                except Exception:
                    exp = datetime.datetime.utcnow()
            if exp > datetime.datetime.utcnow():
                otp_record = o
                break
    
    if not otp_record:
        flash("The password reset link is invalid or has expired.", "danger")
        return redirect(url_for('auth.login'))
        
    user = User.get(otp_record.user_id)
    if not user:
        flash("User associated with reset token not found.", "danger")
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not new_password or not confirm_password:
            flash("All password fields are required.", "danger")
            return render_template('reset_password.html', token=token)
            
        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('reset_password.html', token=token)
            
        try:
            pw_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            user.password_hash = pw_hash
            user.save()
            
            otp_record.is_used = True
            otp_record.save()
            
            # Log the password reset audit
            audit = AuditLog(
                username=user.username,
                action="USER_PASSWORD_RESET_RECOVERY",
                ip_address=request.remote_addr or '127.0.0.1'
            )
            audit.save()
            
            flash("Your password has been successfully reset! You can now login.", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            current_app.logger.error(f"Error resetting password: {str(e)}")
            flash("Failed to reset password. Please try again.", "danger")
            
    return render_template('reset_password.html', token=token)


@auth_bp.route('/logout')
def logout():
    """Clear session cookies and log out user."""
    user = get_current_user()
    if user:
        audit = AuditLog(
            username=user.username,
            action="LOGOUT",
            ip_address=request.remote_addr or '127.0.0.1'
        )
        audit.save()

    resp = make_response(redirect(url_for('auth.login')))
    resp.delete_cookie('access_token')
    session.clear()
    return resp


@auth_bp.route('/dashboard-redirect')
def dashboard_redirect():
    """Redirect user based on active session status."""
    return redirect(url_for('auth.dashboard'))


@auth_bp.route('/')
@auth_bp.route('/dashboard')
def dashboard():
    """Core entry page / main security monitor dashboard."""
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))
    
    # Calculate stats using Firestore
    all_users = User.get_all()
    users_count = len(all_users)
    
    all_access = AccessRequest.get_all()
    pending_requests_count = sum(1 for r in all_access if r.status in ['pending_manager', 'pending_admin'])
    
    all_alerts = BehaviorAlert.get_all()
    open_alerts_count = sum(1 for a in all_alerts if a.status == 'open')
    
    all_scores = RiskScore.get_all()
    total_score = sum(s.score for s in all_scores)
    avg_risk_score = total_score / len(all_scores) if all_scores else 0.0
    
    all_logs = AuditLog.get_all()
    all_logs.sort(key=lambda x: x.timestamp or datetime.datetime.min, reverse=True)
    recent_logs = all_logs[:5]
    
    stats = {
        'users_count': users_count,
        'pending_requests_count': pending_requests_count,
        'open_alerts_count': open_alerts_count,
        'avg_risk_score': avg_risk_score,
        'recent_logs': recent_logs
    }
    
    return render_template('dashboard.html', user=user, stats=stats)
