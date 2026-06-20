from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from smart_rbac.models import AccessRequest, User, Role, Permission, AuditLog
from smart_rbac.utils.auth_helper import login_required, get_current_user

requests_bp = Blueprint('requests', __name__)

@requests_bp.route('/requests', methods=['GET'])
@login_required
def list_requests():
    """List access upgrade requests based on user role permissions."""
    user = get_current_user()
    
    # Query permissions list to let employees choose what they want to request
    permissions = Permission.get_all()
    permissions.sort(key=lambda x: x.name)
    
    if user.role == 'Admin':
        # Admin can view all requests
        requests_list = AccessRequest.get_all()
    elif user.role == 'Manager':
        # Manager can view all requests (they filter/approve manager-level)
        requests_list = AccessRequest.get_all()
    else:
        # Employees only see their own requests
        requests_list = AccessRequest.find_by_field('user_id', user.id)

    requests_list.sort(key=lambda x: x.timestamp or datetime.min, reverse=True)

    return render_template('requests.html', requests=requests_list, permissions=permissions, user=user)


@requests_bp.route('/requests/submit', methods=['POST'])
@login_required
def submit_request():
    """Submit a new access permission request."""
    user = get_current_user()
    requested_permission = request.form.get('requested_permission', '').strip()
    reason = request.form.get('reason', '').strip()

    if not requested_permission or not reason:
        flash("Permission name and justification reason are required.", "danger")
        return redirect(url_for('requests.list_requests'))

    try:
        new_request = AccessRequest(
            user_id=user.id,
            requested_permission=requested_permission,
            reason=reason,
            status='pending_manager'
        )
        new_request.save()
        
        # Log audit entry
        audit = AuditLog(
            username=user.username,
            action=f"ACCESS_REQUEST_SUBMITTED: Requested permission {requested_permission}",
            ip_address=request.remote_addr or '127.0.0.1'
        )
        audit.save()
        
        flash("Access request successfully submitted. Awaiting manager approval.", "success")
    except Exception as e:
        current_app.logger.error(f"Error submitting request: {str(e)}")
        flash("Failed to submit request.", "danger")

    return redirect(url_for('requests.list_requests'))


@requests_bp.route('/requests/approve/<string:req_id>', methods=['POST'])
@login_required
def approve_request(req_id):
    """Approve request in the sequential pipeline (Manager -> Admin)."""
    user = get_current_user()
    req_obj = AccessRequest.get(req_id)

    if not req_obj:
        flash("Request not found.", "danger")
        return redirect(url_for('requests.list_requests'))

    try:
        # 1. Manager Approval Stage
        if req_obj.status == 'pending_manager':
            if user.role not in ['Manager', 'Admin']:
                flash("Unauthorized: Only Managers or Admins can perform initial approvals.", "danger")
                return redirect(url_for('requests.list_requests'))
                
            req_obj.status = 'pending_admin'
            req_obj.approved_by = f"Manager ({user.username})"
            req_obj.save()
            
            audit = AuditLog(
                username=user.username,
                action=f"ACCESS_REQUEST_APPROVED_BY_MANAGER: Approved request ID {req_id} for user ID {req_obj.user_id}",
                ip_address=request.remote_addr or '127.0.0.1'
            )
            audit.save()
            flash("Request approved by Manager. Now awaiting Admin approval.", "success")

        # 2. Admin Approval Stage
        elif req_obj.status == 'pending_admin':
            if user.role != 'Admin':
                flash("Unauthorized: Only Admins can perform final approval.", "danger")
                return redirect(url_for('requests.list_requests'))
                
            # Perform final approval: grant the permission to the user's role
            target_user = User.get(req_obj.user_id)
            if not target_user:
                flash("Target user not found.", "danger")
                return redirect(url_for('requests.list_requests'))

            role_obj = Role.find_by_name(target_user.role)
            perm_obj = Permission.find_by_name(req_obj.requested_permission)
            
            if not role_obj:
                flash(f"Role '{target_user.role}' not found.", "danger")
                return redirect(url_for('requests.list_requests'))

            if not perm_obj:
                # Dynamically create the permission if it doesn't exist
                perm_obj = Permission(
                    id=req_obj.requested_permission,
                    name=req_obj.requested_permission,
                    description="Dynamically added via approved access request"
                )
                perm_obj.save()

            # Append the permission to the role
            if perm_obj.name not in role_obj._permissions_list:
                role_obj.permissions.append(perm_obj)
                role_obj.save()

            req_obj.status = 'approved'
            req_obj.approved_by = f"{req_obj.approved_by or 'Manager'}, Admin ({user.username})"
            req_obj.save()
            
            audit = AuditLog(
                username=user.username,
                action=f"ACCESS_REQUEST_APPROVED_BY_ADMIN: Granted permission {req_obj.requested_permission} to role {role_obj.name}",
                ip_address=request.remote_addr or '127.0.0.1'
            )
            audit.save()
            flash(f"Request finalized. Permission '{req_obj.requested_permission}' has been granted to role '{role_obj.name}'.", "success")
            
        else:
            flash("Request is not in an approvable state.", "danger")
            
    except Exception as e:
        current_app.logger.error(f"Error approving request: {str(e)}")
        flash("Failed to approve request.", "danger")

    return redirect(url_for('requests.list_requests'))


@requests_bp.route('/requests/reject/<string:req_id>', methods=['POST'])
@login_required
def reject_request(req_id):
    """Reject a permission request."""
    user = get_current_user()
    req_obj = AccessRequest.get(req_id)

    if not req_obj:
        flash("Request not found.", "danger")
        return redirect(url_for('requests.list_requests'))

    if user.role not in ['Manager', 'Admin']:
        flash("Unauthorized: Only Managers or Admins can reject requests.", "danger")
        return redirect(url_for('requests.list_requests'))

    try:
        req_obj.status = 'rejected'
        req_obj.approved_by = f"Rejected by {user.role} ({user.username})"
        req_obj.save()
        
        audit = AuditLog(
            username=user.username,
            action=f"ACCESS_REQUEST_REJECTED: Rejected request ID {req_id} for user ID {req_obj.user_id}",
            ip_address=request.remote_addr or '127.0.0.1'
        )
        audit.save()
        flash("Access request rejected.", "warning")
    except Exception as e:
        current_app.logger.error(f"Error rejecting request: {str(e)}")
        flash("Failed to reject request.", "danger")

    return redirect(url_for('requests.list_requests'))
