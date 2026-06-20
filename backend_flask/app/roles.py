from datetime import datetime
from flask import Blueprint, request, jsonify, g
from backend_flask.app import db
from backend_flask.app.models import User, Role, Permission, AuditLog, BehaviorAlert
from backend_flask.app.middleware import jwt_required

roles_bp = Blueprint("roles", __name__)

# ==============================================================================
# Role Management Routes
# ==============================================================================

@roles_bp.route("/api/roles", methods=["GET"])
@jwt_required("role:read")
def get_roles():
    """List all available roles in the system."""
    roles = Role.query.all()
    return jsonify([role.to_dict() for role in roles]), 200


@roles_bp.route("/api/roles/<int:role_id>", methods=["GET"])
@jwt_required("role:read")
def get_role_by_id(role_id):
    """Retrieve details for a specific role."""
    role = db.get_or_404(Role, role_id)
    return jsonify(role.to_dict()), 200


@roles_bp.route("/api/roles", methods=["POST"])
@jwt_required("role:create")
def create_role():
    """Create a new security role."""
    data = request.get_json() or {}
    name = data.get("name")
    description = data.get("description")
    
    ip_address = request.remote_addr or "0.0.0.0"
    
    if not name:
        return jsonify({"error": "Role name is required"}), 400
        
    # Check if role name already exists
    existing_role = Role.query.filter_by(name=name).first()
    if existing_role:
        return jsonify({"error": f"Role '{name}' already exists"}), 409
        
    role = Role(name=name, description=description)
    db.session.add(role)
    
    # Save audit entry
    audit_entry = AuditLog(
        user=g.current_user,
        action="ROLE_CREATE",
        resource=f"role:{name}",
        details={"name": name, "description": description},
        ip_address=ip_address,
        status="success"
    )
    db.session.add(audit_entry)
    db.session.commit()
    
    return jsonify(role.to_dict()), 201


@roles_bp.route("/api/roles/<int:role_id>", methods=["PUT"])
@jwt_required("role:update")
def update_role(role_id):
    """Update a role's name or description."""
    role = db.get_or_404(Role, role_id)
    data = request.get_json() or {}
    name = data.get("name")
    description = data.get("description")
    
    ip_address = request.remote_addr or "0.0.0.0"
    old_values = {"name": role.name, "description": role.description}
    
    if name:
        # Check if name is taken by another role
        existing_role = Role.query.filter_by(name=name).first()
        if existing_role and existing_role.id != role_id:
            return jsonify({"error": f"Role name '{name}' is already taken"}), 409
        role.name = name
        
    if description is not None:
        role.description = description
        
    role.updated_at = datetime.utcnow()
    
    # Save audit entry
    audit_entry = AuditLog(
        user=g.current_user,
        action="ROLE_UPDATE",
        resource=f"role:{role.name}",
        details={"old": old_values, "new": {"name": role.name, "description": role.description}},
        ip_address=ip_address,
        status="success"
    )
    db.session.add(audit_entry)
    db.session.commit()
    
    return jsonify(role.to_dict()), 200


@roles_bp.route("/api/roles/<int:role_id>", methods=["DELETE"])
@jwt_required("role:delete")
def delete_role(role_id):
    """Remove a security role."""
    role = db.get_or_404(Role, role_id)
    role_name = role.name
    
    ip_address = request.remote_addr or "0.0.0.0"
    
    # Prevent deleting critical default role
    if role_name == "SuperAdmin":
        return jsonify({"error": "Cannot delete the SuperAdmin role"}), 403
        
    db.session.delete(role)
    
    # Save audit entry
    audit_entry = AuditLog(
        user=g.current_user,
        action="ROLE_DELETE",
        resource=f"role:{role_name}",
        details={"name": role_name},
        ip_address=ip_address,
        status="success"
    )
    db.session.add(audit_entry)
    db.session.commit()
    
    return jsonify({"message": f"Role '{role_name}' deleted successfully"}), 200


# ==============================================================================
# Role-Permission Mapping Routes
# ==============================================================================

@roles_bp.route("/api/roles/<int:role_id>/permissions", methods=["POST"])
@jwt_required("role:assign")
def assign_permissions_to_role(role_id):
    """Map a set of permissions to a role."""
    role = db.get_or_404(Role, role_id)
    data = request.get_json() or {}
    permission_ids = data.get("permission_ids")
    
    ip_address = request.remote_addr or "0.0.0.0"
    
    if not permission_ids or not isinstance(permission_ids, list):
        return jsonify({"error": "List of permission_ids is required"}), 400
        
    added_perms = []
    for perm_id in permission_ids:
        perm = db.session.get(Permission, perm_id)
        if perm and perm not in role.permissions:
            role.permissions.append(perm)
            added_perms.append(perm.name)
            
    if added_perms:
        role.updated_at = datetime.utcnow()
        # Audit log the assignment
        audit_entry = AuditLog(
            user=g.current_user,
            action="ROLE_PERMISSIONS_ASSIGN",
            resource=f"role:{role.name}",
            details={"role": role.name, "assigned_permissions": added_perms},
            ip_address=ip_address,
            status="success"
        )
        db.session.add(audit_entry)
        db.session.commit()
        
    return jsonify({
        "message": f"Permissions mapped successfully to role '{role.name}'",
        "assigned": added_perms,
        "role": role.to_dict()
    }), 200


@roles_bp.route("/api/roles/<int:role_id>/permissions", methods=["DELETE"])
@jwt_required("role:assign")
def revoke_permissions_from_role(role_id):
    """Revoke a set of permissions from a role."""
    role = db.get_or_404(Role, role_id)
    data = request.get_json() or {}
    permission_ids = data.get("permission_ids")
    
    ip_address = request.remote_addr or "0.0.0.0"
    
    if not permission_ids or not isinstance(permission_ids, list):
        return jsonify({"error": "List of permission_ids is required"}), 400
        
    revoked_perms = []
    for perm_id in permission_ids:
        perm = db.session.get(Permission, perm_id)
        if perm and perm in role.permissions:
            role.permissions.remove(perm)
            revoked_perms.append(perm.name)
            
    if revoked_perms:
        role.updated_at = datetime.utcnow()
        # Audit log the revocation
        audit_entry = AuditLog(
            user=g.current_user,
            action="ROLE_PERMISSIONS_REVOKE",
            resource=f"role:{role.name}",
            details={"role": role.name, "revoked_permissions": revoked_perms},
            ip_address=ip_address,
            status="success"
        )
        db.session.add(audit_entry)
        db.session.commit()
        
    return jsonify({
        "message": f"Permissions revoked successfully from role '{role.name}'",
        "revoked": revoked_perms,
        "role": role.to_dict()
    }), 200


# ==============================================================================
# User-Role Assignment Routes
# ==============================================================================

@roles_bp.route("/api/users/<int:user_id>/roles", methods=["POST"])
@jwt_required("role:assign")
def assign_roles_to_user(user_id):
    """Assign a set of roles to a user."""
    user = db.get_or_404(User, user_id)
    data = request.get_json() or {}
    role_ids = data.get("role_ids")
    
    ip_address = request.remote_addr or "0.0.0.0"
    
    if not role_ids or not isinstance(role_ids, list):
        return jsonify({"error": "List of role_ids is required"}), 400
        
    added_roles = []
    for r_id in role_ids:
        role = db.session.get(Role, r_id)
        if role and role not in user.roles:
            user.roles.append(role)
            added_roles.append(role.name)
            
    if added_roles:
        user.updated_at = datetime.utcnow()
        # Audit log the assignment
        audit_entry = AuditLog(
            user=g.current_user,
            action="USER_ROLES_ASSIGN",
            resource=f"user:{user.username}",
            details={"username": user.username, "assigned_roles": added_roles},
            ip_address=ip_address,
            status="success"
        )
        db.session.add(audit_entry)
        db.session.commit()
        
    return jsonify({
        "message": f"Roles assigned successfully to user '{user.username}'",
        "assigned": added_roles,
        "user": user.to_dict()
    }), 200


@roles_bp.route("/api/users/<int:user_id>/roles", methods=["DELETE"])
@jwt_required("role:assign")
def revoke_roles_from_user(user_id):
    """Revoke a set of roles from a user."""
    user = db.get_or_404(User, user_id)
    data = request.get_json() or {}
    role_ids = data.get("role_ids")
    
    ip_address = request.remote_addr or "0.0.0.0"
    
    if not role_ids or not isinstance(role_ids, list):
        return jsonify({"error": "List of role_ids is required"}), 400
        
    revoked_roles = []
    for r_id in role_ids:
        role = db.session.get(Role, r_id)
        if role and role in user.roles:
            # Prevent removing the final SuperAdmin role from superadmin to avoid lockout
            if user.username == "superadmin" and role.name == "SuperAdmin":
                continue
            user.roles.remove(role)
            revoked_roles.append(role.name)
            
    if revoked_roles:
        user.updated_at = datetime.utcnow()
        # Audit log the revocation
        audit_entry = AuditLog(
            user=g.current_user,
            action="USER_ROLES_REVOKE",
            resource=f"user:{user.username}",
            details={"username": user.username, "revoked_roles": revoked_roles},
            ip_address=ip_address,
            status="success"
        )
        db.session.add(audit_entry)
        db.session.commit()
        
    return jsonify({
        "message": f"Roles revoked successfully from user '{user.username}'",
        "revoked": revoked_roles,
        "user": user.to_dict()
    }), 200


# ==============================================================================
# Permission Directory Routes
# ==============================================================================

@roles_bp.route("/api/permissions", methods=["GET"])
@jwt_required("role:read")
def get_permissions():
    """List all available system permissions."""
    permissions = Permission.query.all()
    return jsonify([p.to_dict() for p in permissions]), 200


# ==============================================================================
# Security Telemetry, Audits, and Anomaly Alerts Routes
# ==============================================================================

@roles_bp.route("/api/admin/audit-logs", methods=["GET"])
@jwt_required("audit:read")
def get_admin_audit_logs():
    """Retrieve filtered system audit trail logs."""
    action = request.args.get("action")
    status = request.args.get("status")
    user_id = request.args.get("user_id")
    
    query = AuditLog.query
    if action:
        query = query.filter_by(action=action)
    if status:
        query = query.filter_by(status=status)
    if user_id:
        query = query.filter_by(user_id=int(user_id))
        
    logs = query.order_by(AuditLog.created_at.desc()).limit(100).all()
    return jsonify([log.to_dict() for log in logs]), 200


@roles_bp.route("/api/admin/behavior-alerts", methods=["GET"])
@jwt_required("logs:view")
def get_admin_behavior_alerts():
    """Retrieve all logged user behavior anomaly alerts."""
    status = request.args.get("status")
    
    query = BehaviorAlert.query
    if status:
        query = query.filter_by(status=status)
        
    alerts = query.order_by(BehaviorAlert.triggered_at.desc()).all()
    return jsonify([alert.to_dict() for alert in alerts]), 200


@roles_bp.route("/api/admin/behavior-alerts/<int:alert_id>/resolve", methods=["POST"])
@jwt_required("system:configure")
def resolve_admin_behavior_alert(alert_id):
    """Resolve a pending threat behavior alert."""
    alert = db.get_or_404(BehaviorAlert, alert_id)
    
    ip_address = request.remote_addr or "0.0.0.0"
    
    if alert.status == "resolved":
        return jsonify({"message": "Alert is already resolved"}), 200
        
    alert.status = "resolved"
    alert.resolved_by = g.current_user.id
    alert.resolved_at = datetime.utcnow()
    
    # Audit log the resolution action
    from backend_flask.app.services.audit_service import log_audit_event
    log_audit_event(
        user_id=g.current_user.id,
        action="BEHAVIOR_ALERT_RESOLVED",
        resource=f"alert:{alert.alert_type}",
        details={"alert_id": alert_id, "resolved_for_user": alert.user.username},
        ip_address=ip_address,
        status="success"
    )
    
    return jsonify({
        "message": f"Alert {alert_id} marked as resolved",
        "alert": alert.to_dict()
    }), 200

