-- RBAC Cybersecurity Project Database Seeds
USE rbac_security_db;

-- -----------------------------------------------------------------------------
-- Seed Permissions
-- -----------------------------------------------------------------------------
INSERT INTO permissions (name, resource, action, description) VALUES
-- User management permissions
('user:create', 'user', 'create', 'Create new system users'),
('user:read', 'user', 'read', 'View system users detail'),
('user:update', 'user', 'update', 'Modify user details, statuses'),
('user:delete', 'user', 'delete', 'Remove system users'),

-- Role management permissions
('role:create', 'role', 'create', 'Create new security roles'),
('role:read', 'role', 'read', 'View security roles'),
('role:update', 'role', 'update', 'Modify role descriptions and names'),
('role:delete', 'role', 'delete', 'Remove security roles'),
('role:assign', 'role', 'assign', 'Assign or revoke roles from users'),

-- Cybersecurity specific operational permissions
('network:scan', 'network', 'scan', 'Execute network security scanning'),
('system:configure', 'system', 'configure', 'Configure firewalls, IDS/IPS system parameters'),
('audit:read', 'audit', 'read', 'Access and inspect system audit trails'),
('logs:view', 'logs', 'view', 'View system logs');

-- -----------------------------------------------------------------------------
-- Seed Roles
-- -----------------------------------------------------------------------------
INSERT INTO roles (name, description) VALUES
('SuperAdmin', 'Unrestricted administrative access to all resources'),
('SecurityAdmin', 'Manage users, roles, permissions, and security parameters'),
('Analyst', 'Perform scans, monitor traffic, and view security logs'),
('Auditor', 'Read-only access to users, roles, and security audit logs');

-- -----------------------------------------------------------------------------
-- Seed Role-Permission Mappings
-- -----------------------------------------------------------------------------
-- Helper variables for mapping
SET @super_admin_role_id = (SELECT id FROM roles WHERE name = 'SuperAdmin');
SET @security_admin_role_id = (SELECT id FROM roles WHERE name = 'SecurityAdmin');
SET @analyst_role_id = (SELECT id FROM roles WHERE name = 'Analyst');
SET @auditor_role_id = (SELECT id FROM roles WHERE name = 'Auditor');

-- SuperAdmin gets all permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT @super_admin_role_id, id FROM permissions;

-- SecurityAdmin gets user, role, logs, and system config permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT @security_admin_role_id, id FROM permissions
WHERE resource IN ('user', 'role', 'system', 'logs');

-- Analyst gets read users, read roles, network scan, and view logs
INSERT INTO role_permissions (role_id, permission_id)
SELECT @analyst_role_id, id FROM permissions
WHERE name IN ('user:read', 'role:read', 'network:scan', 'logs:view');

-- Auditor gets read users, read roles, and audit read permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT @auditor_role_id, id FROM permissions
WHERE name IN ('user:read', 'role:read', 'audit:read', 'logs:view');

-- -----------------------------------------------------------------------------
-- Seed Users (Initial accounts)
-- Passwords hash stands for: P@ssw0rd123! (hashed using bcrypt work factor 12)
-- -----------------------------------------------------------------------------
INSERT INTO users (username, email, password_hash, status) VALUES
('superadmin', 'superadmin@cybersecurity.local', '$2b$12$K1Hk7L2vPz293nJ2O3g8U.C43bfeG5l5hD8B1C8nC4v3O.D1i3R5e', 'active'),
('secadmin', 'secadmin@cybersecurity.local', '$2b$12$K1Hk7L2vPz293nJ2O3g8U.C43bfeG5l5hD8B1C8nC4v3O.D1i3R5e', 'active'),
('analyst01', 'analyst01@cybersecurity.local', '$2b$12$K1Hk7L2vPz293nJ2O3g8U.C43bfeG5l5hD8B1C8nC4v3O.D1i3R5e', 'active'),
('auditor01', 'auditor01@cybersecurity.local', '$2b$12$K1Hk7L2vPz293nJ2O3g8U.C43bfeG5l5hD8B1C8nC4v3O.D1i3R5e', 'active');

-- -----------------------------------------------------------------------------
-- Seed User-Role Mappings
-- -----------------------------------------------------------------------------
INSERT INTO user_roles (user_id, role_id) VALUES
((SELECT id FROM users WHERE username = 'superadmin'), @super_admin_role_id),
((SELECT id FROM users WHERE username = 'secadmin'), @security_admin_role_id),
((SELECT id FROM users WHERE username = 'analyst01'), @analyst_role_id),
((SELECT id FROM users WHERE username = 'auditor01'), @auditor_role_id);
