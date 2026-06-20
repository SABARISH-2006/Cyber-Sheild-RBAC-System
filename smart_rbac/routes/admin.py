from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from datetime import datetime
import bcrypt

from smart_rbac.models import User, Role, Permission, AuditLog, db
from smart_rbac.utils.auth_helper import login_required, permission_required, get_current_user

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ==========================================
# USER MANAGEMENT ROUTES
# ==========================================

@admin_bp.route('/users', methods=['GET'])
@login_required
@permission_required('manage_users')
def users_list():
    """List all user accounts in the system."""
    users = User.get_all()
    # Sort in memory descending by created_at or username
    users.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
    roles = Role.get_all()
    return render_template('users.html', users=users, roles=roles)


@admin_bp.route('/users/create', methods=['POST'])
@login_required
@permission_required('manage_users')
def create_user():
    """Create a new user account."""
    admin_user = get_current_user()
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    role = request.form.get('role', 'Employee')

    if not username or not email or not password:
        flash("All fields are required.", "danger")
        return redirect(url_for('admin.users_list'))

    # Check duplicates
    dup = User.find_by_username(username) or User.find_by_email(email)
    if dup:
        flash("Username or Email already exists.", "danger")
        return redirect(url_for('admin.users_list'))

    try:
        pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_user = User(
            username=username,
            email=email,
            password_hash=pw_hash,
            role=role,
            status='active'
        )
        new_user.generate_login_id()
        new_user.save()
        
        # Log action
        audit = AuditLog(
            username=admin_user.username,
            action=f"ADMIN_CREATE_USER: Created user {username} with role {role}",
            ip_address=request.remote_addr or '127.0.0.1'
        )
        audit.save()
        
        flash(f"User '{username}' created successfully.", "success")
    except Exception as e:
        current_app.logger.error(f"Error creating user: {str(e)}")
        flash("Failed to create user.", "danger")

    return redirect(url_for('admin.users_list'))


@admin_bp.route('/users/edit/<string:user_id>', methods=['POST'])
@login_required
@permission_required('manage_users')
def edit_user(user_id):
    """Edit an existing user's details."""
    admin_user = get_current_user()
    user = User.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('admin.users_list'))

    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    role = request.form.get('role')
    status = request.form.get('status')
    password = request.form.get('password')

    if not username or not email or not role or not status:
        flash("Username, email, role, and status are required.", "danger")
        return redirect(url_for('admin.users_list'))

    # Check unique constraints
    dup_uname = User.find_by_username(username)
    dup_email = User.find_by_email(email)
    
    if (dup_uname and dup_uname.id != user_id) or (dup_email and dup_email.id != user_id):
        flash("Username or Email already in use by another user.", "danger")
        return redirect(url_for('admin.users_list'))

    try:
        user.username = username
        user.email = email
        user.role = role
        user.status = status
        
        if password:  # Optional password update
            user.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        user.save()

        audit = AuditLog(
            username=admin_user.username,
            action=f"ADMIN_EDIT_USER: Updated user {username} (Role: {role}, Status: {status})",
            ip_address=request.remote_addr or '127.0.0.1'
        )
        audit.save()
        flash(f"User '{username}' updated successfully.", "success")
    except Exception as e:
        current_app.logger.error(f"Error editing user: {str(e)}")
        flash("Failed to update user.", "danger")

    return redirect(url_for('admin.users_list'))


@admin_bp.route('/users/delete/<string:user_id>', methods=['POST'])
@login_required
@permission_required('manage_users')
def delete_user(user_id):
    """Delete a user account."""
    admin_user = get_current_user()
    if admin_user.id == user_id:
        flash("You cannot delete your own admin account.", "danger")
        return redirect(url_for('admin.users_list'))

    user = User.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('admin.users_list'))

    try:
        username = user.username
        user.delete()
        
        audit = AuditLog(
            username=admin_user.username,
            action=f"ADMIN_DELETE_USER: Deleted user account {username}",
            ip_address=request.remote_addr or '127.0.0.1'
        )
        audit.save()
        flash(f"User '{username}' deleted successfully.", "success")
    except Exception as e:
        current_app.logger.error(f"Error deleting user: {str(e)}")
        flash("Failed to delete user.", "danger")

    return redirect(url_for('admin.users_list'))


@admin_bp.route('/users/unlock/<string:user_id>', methods=['POST'])
@login_required
@permission_required('manage_users')
def unlock_user(user_id):
    """Unlock a locked out account."""
    admin_user = get_current_user()
    user = User.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('admin.users_list'))

    try:
        user.failed_login_attempts = 0
        user.status = 'active'
        user.save()
        
        audit = AuditLog(
            username=admin_user.username,
            action=f"ADMIN_UNLOCK_USER: Unlocked account for {user.username}",
            ip_address=request.remote_addr or '127.0.0.1'
        )
        audit.save()
        flash(f"Account for '{user.username}' unlocked successfully.", "success")
    except Exception as e:
        current_app.logger.error(f"Error unlocking user: {str(e)}")
        flash("Failed to unlock user.", "danger")

    return redirect(url_for('admin.users_list'))


# ==========================================
# ROLE & PERMISSION MANAGEMENT ROUTES
# ==========================================

@admin_bp.route('/roles', methods=['GET'])
@login_required
@permission_required('manage_roles')
def roles_list():
    """List all security roles and edit/assign mappings."""
    roles = Role.get_all()
    permissions = Permission.get_all()
    return render_template('roles.html', roles=roles, permissions=permissions)


@admin_bp.route('/roles/create', methods=['POST'])
@login_required
@permission_required('manage_roles')
def create_role():
    """Create a new role."""
    admin_user = get_current_user()
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    permission_ids = request.form.getlist('permissions')

    if not name:
        flash("Role name is required.", "danger")
        return redirect(url_for('admin.roles_list'))

    # Check duplicate role
    dup = Role.find_by_name(name)
    if dup:
        flash(f"Role '{name}' already exists.", "danger")
        return redirect(url_for('admin.roles_list'))

    try:
        # In Firestore, doc ID is name
        new_role = Role(id=name, name=name, description=description, permissions=permission_ids)
        new_role.save()
        
        audit = AuditLog(
            username=admin_user.username,
            action=f"ADMIN_CREATE_ROLE: Created role {name}",
            ip_address=request.remote_addr or '127.0.0.1'
        )
        audit.save()
        flash(f"Role '{name}' created successfully.", "success")
    except Exception as e:
        current_app.logger.error(f"Error creating role: {str(e)}")
        flash("Failed to create role.", "danger")

    return redirect(url_for('admin.roles_list'))


@admin_bp.route('/roles/edit/<string:role_id>', methods=['POST'])
@login_required
@permission_required('manage_roles')
def edit_role(role_id):
    """Edit an existing role description and set permissions list."""
    admin_user = get_current_user()
    role = Role.get(role_id)
    if not role:
        flash("Role not found.", "danger")
        return redirect(url_for('admin.roles_list'))

    description = request.form.get('description', '').strip()
    permission_ids = request.form.getlist('permissions')

    try:
        role.description = description
        role._permissions_list = permission_ids
        role.save()

        audit = AuditLog(
            username=admin_user.username,
            action=f"ADMIN_EDIT_ROLE: Modified permissions for role {role.name}",
            ip_address=request.remote_addr or '127.0.0.1'
        )
        audit.save()
        flash(f"Role '{role.name}' updated successfully.", "success")
    except Exception as e:
        current_app.logger.error(f"Error editing role: {str(e)}")
        flash("Failed to update role.", "danger")

    return redirect(url_for('admin.roles_list'))


@admin_bp.route('/roles/clone', methods=['POST'])
@login_required
@permission_required('manage_roles')
def clone_role():
    """Clone an existing role with all its permission mappings."""
    admin_user = get_current_user()
    source_role_id = request.form.get('source_role_id')
    target_role_name = request.form.get('target_role_name', '').strip()
    target_description = request.form.get('target_description', '').strip()

    if not source_role_id or not target_role_name:
        flash("Source role and new role name are required.", "danger")
        return redirect(url_for('admin.roles_list'))

    # Check duplicate
    dup = Role.find_by_name(target_role_name)
    if dup:
        flash(f"Role '{target_role_name}' already exists.", "danger")
        return redirect(url_for('admin.roles_list'))

    source_role = Role.get(source_role_id)
    if not source_role:
        flash("Source role not found.", "danger")
        return redirect(url_for('admin.roles_list'))

    try:
        # doc ID is the new role name
        new_role = Role(
            id=target_role_name,
            name=target_role_name, 
            description=target_description or f"Clone of {source_role.name}",
            permissions=list(source_role._permissions_list)
        )
        new_role.save()
        
        audit = AuditLog(
            username=admin_user.username,
            action=f"ADMIN_CLONE_ROLE: Cloned role {source_role.name} into {target_role_name}",
            ip_address=request.remote_addr or '127.0.0.1'
        )
        audit.save()
        flash(f"Role '{source_role.name}' successfully cloned to '{target_role_name}'.", "success")
    except Exception as e:
        current_app.logger.error(f"Error cloning role: {str(e)}")
        flash("Failed to clone role.", "danger")

    return redirect(url_for('admin.roles_list'))


@admin_bp.route('/roles/delete/<string:role_id>', methods=['POST'])
@login_required
@permission_required('manage_roles')
def delete_role(role_id):
    """Delete a custom role."""
    admin_user = get_current_user()
    role = Role.get(role_id)
    if not role:
        flash("Role not found.", "danger")
        return redirect(url_for('admin.roles_list'))

    # Prevent deleting primary system roles
    if role.name in ['Admin', 'Manager', 'Employee', 'Auditor']:
        flash(f"System role '{role.name}' cannot be deleted.", "danger")
        return redirect(url_for('admin.roles_list'))

    try:
        name = role.name
        role.delete()
        
        audit = AuditLog(
            username=admin_user.username,
            action=f"ADMIN_DELETE_ROLE: Deleted role {name}",
            ip_address=request.remote_addr or '127.0.0.1'
        )
        audit.save()
        flash(f"Role '{name}' deleted successfully.", "success")
    except Exception as e:
        current_app.logger.error(f"Error deleting role: {str(e)}")
        flash("Failed to delete role.", "danger")

    return redirect(url_for('admin.roles_list'))


@admin_bp.route('/permissions', methods=['GET'])
@login_required
@permission_required('manage_roles')
def permissions_list():
    """List all fine-grained privileges in the system."""
    permissions = Permission.get_all()
    permissions.sort(key=lambda x: x.name)
    return render_template('permissions.html', permissions=permissions)


# ==========================================
# REGISTRATION APPROVAL ROUTES
# ==========================================

@admin_bp.route('/registration-requests', methods=['GET'])
@login_required
@permission_required('manage_users')
def registration_requests_list():
    """List all pending registration requests for superadmin approval."""
    from smart_rbac.models import RegistrationRequest
    
    status_filter = request.args.get('status', 'pending')
    
    all_requests = RegistrationRequest.get_all()
    
    if status_filter == 'pending':
        requests = [r for r in all_requests if r.status == 'pending']
        requests.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
    elif status_filter == 'approved':
        requests = [r for r in all_requests if r.status == 'approved']
        requests.sort(key=lambda x: x.approved_at or datetime.min, reverse=True)
    elif status_filter == 'rejected':
        requests = [r for r in all_requests if r.status == 'rejected']
        requests.sort(key=lambda x: x.approved_at or datetime.min, reverse=True)
    else:
        requests = all_requests
        requests.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
    
    return render_template('admin/registration_requests.html', requests=requests, current_status=status_filter)


@admin_bp.route('/registration-requests/<string:req_id>/approve', methods=['POST'])
@login_required
@permission_required('manage_users')
def approve_registration(req_id):
    """Approve a registration request and activate the user account."""
    from smart_rbac.models import RegistrationRequest
    
    admin_user = get_current_user()
    reg_request = RegistrationRequest.get(req_id)
    
    if not reg_request:
        flash("Registration request not found.", "danger")
        return redirect(url_for('admin.registration_requests_list'))
    
    if reg_request.status != 'pending':
        flash(f"Cannot approve: Request status is {reg_request.status}.", "warning")
        return redirect(url_for('admin.registration_requests_list'))
    
    try:
        # Update registration request
        reg_request.status = 'approved'
        reg_request.approved_by = admin_user.username
        reg_request.approved_at = datetime.utcnow()
        reg_request.save()
        
        # Activate user account
        user = User.get(reg_request.user_id)
        if user:
            user.status = 'active'
            user.save()
            
            # Log action
            audit = AuditLog(
                username=admin_user.username,
                action=f"ADMIN_APPROVE_REGISTRATION: Approved user '{user.username}' with role '{user.role}'",
                ip_address=request.remote_addr or '127.0.0.1'
            )
            audit.save()
        
        flash(f"Registration approved for user '{reg_request.username}'.", "success")
        
        # Log to console for audit trail
        print(f"\n==================================================", flush=True)
        print(f"[REGISTRATION APPROVED] USER: {reg_request.username}", flush=True)
        print(f"[LOGIN ID]: {reg_request.login_id}", flush=True)
        print(f"[EMAIL]: {reg_request.email}", flush=True)
        print(f"[ROLE]: {reg_request.role}", flush=True)
        print(f"[APPROVED BY]: {admin_user.username}", flush=True)
        print(f"[TIMESTAMP]: {datetime.utcnow()}", flush=True)
        print(f"==================================================\n", flush=True)
        
    except Exception as e:
        current_app.logger.error(f"Error approving registration: {str(e)}")
        flash("Failed to approve registration.", "danger")
    
    return redirect(url_for('admin.registration_requests_list', status='pending'))


@admin_bp.route('/registration-requests/<string:req_id>/reject', methods=['POST'])
@login_required
@permission_required('manage_users')
def reject_registration(req_id):
    """Reject a registration request and delete the user account."""
    from smart_rbac.models import RegistrationRequest
    
    admin_user = get_current_user()
    reg_request = RegistrationRequest.get(req_id)
    
    if not reg_request:
        flash("Registration request not found.", "danger")
        return redirect(url_for('admin.registration_requests_list'))
    
    if reg_request.status != 'pending':
        flash(f"Cannot reject: Request status is {reg_request.status}.", "warning")
        return redirect(url_for('admin.registration_requests_list'))
    
    try:
        approval_notes = request.form.get('approval_notes', 'No reason provided')
        
        # Update registration request
        reg_request.status = 'rejected'
        reg_request.approved_by = admin_user.username
        reg_request.approval_notes = approval_notes
        reg_request.approved_at = datetime.utcnow()
        reg_request.save()
        
        # Get user info before deletion
        user = User.get(reg_request.user_id)
        username = user.username if user else reg_request.username
        
        # Delete user account
        if user:
            user.delete()
            
            # Log action
            audit = AuditLog(
                username=admin_user.username,
                action=f"ADMIN_REJECT_REGISTRATION: Rejected and deleted user '{username}' - Reason: {approval_notes}",
                ip_address=request.remote_addr or '127.0.0.1'
            )
            audit.save()
        
        flash(f"Registration rejected for user '{reg_request.username}'.", "success")
        
        # Log to console for audit trail
        print(f"\n==================================================", flush=True)
        print(f"[REGISTRATION REJECTED] USER: {reg_request.username}", flush=True)
        print(f"[LOGIN ID]: {reg_request.login_id}", flush=True)
        print(f"[EMAIL]: {reg_request.email}", flush=True)
        print(f"[ROLE]: {reg_request.role}", flush=True)
        print(f"[REJECTED BY]: {admin_user.username}", flush=True)
        print(f"[REASON]: {approval_notes}", flush=True)
        print(f"[TIMESTAMP]: {datetime.utcnow()}", flush=True)
        print(f"==================================================\n", flush=True)
        
    except Exception as e:
        current_app.logger.error(f"Error rejecting registration: {str(e)}")
        flash("Failed to reject registration.", "danger")
    
    return redirect(url_for('admin.registration_requests_list', status='pending'))
