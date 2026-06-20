from datetime import datetime
from backend_flask.app import db

# ==============================================================================
# Association Tables (Many-to-Many Mappings)
# ==============================================================================

# Table: user_roles - Maps Users to Roles
user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
)

# Table: role_permissions - Maps Roles to Permissions
role_permissions = db.Table(
    'role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)
)


# ==============================================================================
# Model Definitions
# ==============================================================================

class User(db.Model):
    """User Model - Stores credentials and profile information."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), nullable=False, unique=True, index=True)
    email = db.Column(db.String(100), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Enum('active', 'suspended', 'inactive', name='user_status_enum'), nullable=False, default='active', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    roles = db.relationship('Role', secondary=user_roles, back_populates='users')
    sessions = db.relationship('UserSession', back_populates='user', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', back_populates='user')
    otps = db.relationship('OTP', back_populates='user', cascade='all, delete-orphan')
    risk_scores = db.relationship('RiskScore', back_populates='user', cascade='all, delete-orphan')
    
    # Behavior alerts associated with this user, and alerts this user resolved
    behavior_alerts = db.relationship(
        'BehaviorAlert',
        foreign_keys='BehaviorAlert.user_id',
        back_populates='user',
        cascade='all, delete-orphan'
    )
    resolved_alerts = db.relationship(
        'BehaviorAlert',
        foreign_keys='BehaviorAlert.resolved_by',
        back_populates='resolver'
    )

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'roles': [role.name for role in self.roles]
        }


class Role(db.Model):
    """Role Model - Defines administrative or operational access levels."""
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False, unique=True, index=True)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = db.relationship('User', secondary=user_roles, back_populates='roles')
    permissions = db.relationship('Permission', secondary=role_permissions, back_populates='roles')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'permissions': [perm.name for perm in self.permissions]
        }


class Permission(db.Model):
    """Permission Model - Granular authorization nodes mapping resource + action."""
    __tablename__ = 'permissions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # e.g. 'user:create'
    resource = db.Column(db.String(50), nullable=False)           # e.g. 'user'
    action = db.Column(db.String(50), nullable=False)             # e.g. 'create'
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Composite Index for resource and action lookup
    __table_args__ = (
        db.Index('idx_permission_resource_action', 'resource', 'action'),
    )

    # Relationships
    roles = db.relationship('Role', secondary=role_permissions, back_populates='permissions')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'resource': self.resource,
            'action': self.action,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UserSession(db.Model):
    """UserSession Model - Tracks active user logins and token expiries."""
    __tablename__ = 'user_sessions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    ip_address = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.String(255), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='sessions')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AuditLog(db.Model):
    """AuditLog Model - Read-only registry of compliance and security events."""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    resource = db.Column(db.String(50), nullable=True)
    details = db.Column(db.JSON, nullable=True)  # Stores metadata such as {"diff": ...}
    ip_address = db.Column(db.String(45), nullable=False)
    status = db.Column(db.Enum('success', 'failure', name='audit_log_status_enum'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = db.relationship('User', back_populates='audit_logs')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'resource': self.resource,
            'details': self.details,
            'ip_address': self.ip_address,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class OTP(db.Model):
    """OTP Model - Handles secure One-Time Passwords for MFA/2FA & reset protocols."""
    __tablename__ = 'otps'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    otp_code_hash = db.Column(db.String(255), nullable=False)
    purpose = db.Column(db.String(50), nullable=False, default='2fa')  # e.g., '2fa', 'password_reset'
    is_used = db.Column(db.Boolean, nullable=False, default=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='otps')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'purpose': self.purpose,
            'is_used': self.is_used,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class RiskScore(db.Model):
    """RiskScore Model - Maintains calculated security risk indicators per user."""
    __tablename__ = 'risk_scores'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    score = db.Column(db.Float, nullable=False)  # Range: 0.0 (Safe) to 100.0 (Critical)
    factors = db.Column(db.JSON, nullable=True)  # Context e.g., {"failed_login_count": 3, "country_mismatch": true}
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = db.relationship('User', back_populates='risk_scores')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'score': self.score,
            'factors': self.factors,
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None
        }


class BehaviorAlert(db.Model):
    """BehaviorAlert Model - Captures, tracks, and documents threat alerts."""
    __tablename__ = 'behavior_alerts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    alert_type = db.Column(db.String(100), nullable=False)  # e.g., 'IMPOSSIBLE_TRAVEL', 'BRUTE_FORCE'
    severity = db.Column(db.Enum('low', 'medium', 'high', 'critical', name='alert_severity_enum'), nullable=False, default='medium', index=True)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.Enum('open', 'investigating', 'resolved', 'dismissed', name='alert_status_enum'), nullable=False, default='open', index=True)
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], back_populates='behavior_alerts')
    resolver = db.relationship('User', foreign_keys=[resolved_by], back_populates='resolved_alerts')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'description': self.description,
            'status': self.status,
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolved_by': self.resolved_by
        }
