import os
from flask import Flask, render_template, redirect, url_for, request, flash, make_response
import bcrypt

from smart_rbac.config import Config
from smart_rbac.models import db, User, Role, Permission, AuditLog, RiskScore
from smart_rbac.utils.auth_helper import login_required, get_current_user

# Import Blueprints
from smart_rbac.routes.auth import auth_bp
from smart_rbac.routes.admin import admin_bp
from smart_rbac.routes.requests import requests_bp
from smart_rbac.routes.telemetry import telemetry_bp

def create_app():
    """Application factory pattern."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Bind database ORM compatibility wrapper
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(requests_bp)
    app.register_blueprint(telemetry_bp)

    # 1. Custom template context processor for permission validation and user injection
    @app.context_processor
    def inject_context():
        user = get_current_user()
        def has_permission(perm_name):
            if not user:
                return False
            
            # Admins have master bypass
            if user.role and user.role.lower() == 'admin':
                return True
                
            # Query role permissions
            role_obj = Role.find_by_name(user.role)
            if role_obj:
                return perm_name in role_obj._permissions_list
            return False
        return dict(has_permission=has_permission, user=user)

    # 2. General application views
    @app.route('/profile')
    @login_required
    def profile_view():
        user = get_current_user()
        return render_template('profile.html', user=user)

    @app.route('/profile/update', methods=['POST'])
    @login_required
    def profile_update():
        user = get_current_user()
        email = request.form.get('email', '').strip()
        if not email:
            flash("Email is required.", "danger")
            return redirect(url_for('profile_view'))

        # Check duplicate email
        dup = User.find_by_email(email)
        if dup and dup.id != user.id:
            flash("Email is already registered by another account.", "danger")
            return redirect(url_for('profile_view'))

        try:
            user.email = email
            user.save()
            
            audit = AuditLog(
                username=user.username,
                action="USER_EMAIL_UPDATE: Self updated email",
                ip_address=request.remote_addr or '127.0.0.1'
            )
            audit.save()
            flash("Profile email updated successfully.", "success")
        except Exception as e:
            app.logger.error(f"Error updating profile: {str(e)}")
            flash("Failed to update profile email.", "danger")

        return redirect(url_for('profile_view'))

    @app.route('/profile/change-password', methods=['POST'])
    @login_required
    def profile_change_password():
        user = get_current_user()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_new_password = request.form.get('confirm_new_password', '')

        if not current_password or not new_password or not confirm_new_password:
            flash("All password fields are required.", "danger")
            return redirect(url_for('profile_view'))

        if new_password != confirm_new_password:
            flash("New password confirmation does not match.", "danger")
            return redirect(url_for('profile_view'))

        # Validate current password
        if not bcrypt.checkpw(current_password.encode('utf-8'), user.password_hash.encode('utf-8')):
            flash("Incorrect current password.", "danger")
            return redirect(url_for('profile_view'))

        try:
            pw_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            user.password_hash = pw_hash
            user.save()
            
            audit = AuditLog(
                username=user.username,
                action="USER_PASSWORD_CHANGE: Self reset password credentials",
                ip_address=request.remote_addr or '127.0.0.1'
            )
            audit.save()
            
            flash("Password updated successfully.", "success")
        except Exception as e:
            app.logger.error(f"Error changing password: {str(e)}")
            flash("Failed to change password.", "danger")

        return redirect(url_for('profile_view'))

    @app.route('/profile/photo', methods=['POST'])
    @login_required
    def profile_photo_upload():
        user = get_current_user()
        if 'profile_photo' not in request.files:
            flash("No file part provided.", "danger")
            return redirect(url_for('profile_view'))
            
        file = request.files['profile_photo']
        if file.filename == '':
            flash("No file selected.", "danger")
            return redirect(url_for('profile_view'))
            
        if file:
            # Validate extension
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in ['.png', '.jpg', '.jpeg', '.gif']:
                flash("Invalid image type. Allowed: PNG, JPG, JPEG, GIF.", "danger")
                return redirect(url_for('profile_view'))
                
            # Create uploads directory
            uploads_dir = os.path.join(app.static_folder, 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            
            # Save file
            filename = f"user_{user.id}{ext}"
            file_path = os.path.join(uploads_dir, filename)
            file.save(file_path)
            
            # Update user
            user.profile_photo = f"uploads/{filename}"
            user.save()
            
            # Add audit log
            audit = AuditLog(
                username=user.username,
                action="USER_PROFILE_PHOTO_UPLOAD: Self uploaded profile image",
                ip_address=request.remote_addr or '127.0.0.1'
            )
            audit.save()
            
            flash("Profile photo updated successfully.", "success")
            
        return redirect(url_for('profile_view'))

    @app.route('/settings')
    @login_required
    def settings_view():
        user = get_current_user()
        return render_template('settings.html', user=user)

    # 3. DB Schema Build & Seeding
    with app.app_context():
        db.create_all()
        seed_database()

    return app

def seed_database():
    """Seed default roles, permissions, and starting test identities if they don't exist."""
    # A. Seed fine-grained privileges
    permissions_list = [
        ('view_dashboard', 'Permission to view core system metrics dashboard'),
        ('manage_users', 'Permission to provision, edit, and delete user identities'),
        ('manage_roles', 'Permission to assign privileges and clone role matrix profiles'),
        ('view_audit_logs', 'Permission to query and export security audit compliance logs'),
        ('view_analytics', 'Permission to view behavioral UBA engine threat reports'),
        ('request_access', 'Permission to request ad-hoc privilege upgrades sequential pipeline')
    ]
    
    for p_name, p_desc in permissions_list:
        perm = Permission.find_by_name(p_name)
        if not perm:
            perm = Permission(id=p_name, name=p_name, description=p_desc)
            perm.save()

    # B. Seed system roles & map permissions
    roles_list = [
        ('Admin', 'Administrator with full system control', [
            'view_dashboard', 'manage_users', 'manage_roles', 'view_audit_logs', 'view_analytics', 'request_access'
        ]),
        ('Manager', 'Management authority with approval capability', [
            'view_dashboard', 'request_access'
        ]),
        ('Employee', 'Standard employee user', [
            'view_dashboard', 'request_access'
        ]),
        ('Auditor', 'Compliance auditor for checking logs and analytics', [
            'view_dashboard', 'view_audit_logs', 'view_analytics', 'request_access'
        ])
    ]

    for r_name, r_desc, r_perms in roles_list:
        role = Role.find_by_name(r_name)
        if not role:
            role = Role(id=r_name, name=r_name, description=r_desc, permissions=r_perms)
            role.save()
        else:
            role._permissions_list = r_perms
            role.save()

    # C. Seed initial test accounts (Passwords default: username + 123)
    accounts = [
        ('admin', 'admin@company.com', 'admin123', 'Admin'),
        ('manager', 'manager@company.com', 'manager123', 'Manager'),
        ('employee', 'employee@company.com', 'employee123', 'Employee'),
        ('auditor', 'auditor@company.com', 'auditor123', 'Auditor')
    ]

    for uname, email, pwd, role_name in accounts:
        user = User.find_by_username(uname)
        if not user:
            pw_hash = bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            new_user = User(
                username=uname,
                email=email,
                password_hash=pw_hash,
                role=role_name,
                status='active'
            )
            new_user.generate_login_id()
            new_user.save()
            
            # Add a seed low risk record to avoid empty graphs
            rs = RiskScore(
                user_id=new_user.id,
                score=10.0,
                risk_level='Low',
                factors='["First time setup"]'
            )
            rs.save()

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 8001))
    if port == 5000:
        port = 8001
    print("\n==================================================")
    print("CYBER SHIELD SMART RBAC POLICY SERVER STARTING...")
    print(f"DEVELOPMENT DEV HOST: http://127.0.0.1:{port}")
    print("DEFAULT LOGINS: admin/admin123, manager/manager123")
    print("                employee/employee123, auditor/auditor123")
    print("==================================================\n")
    app.run(host='127.0.0.1', port=port, debug=True)
