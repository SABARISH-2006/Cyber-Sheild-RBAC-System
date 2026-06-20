import dotenv from 'dotenv';
dotenv.config();

import { PermissionModel } from './models/Permission.js';
import { RoleModel } from './models/Role.js';
import { UserModel } from './models/User.js';

const permissions = [
  // User management
  { name: 'user:create', resource: 'user', action: 'create', description: 'Create new system users' },
  { name: 'user:read', resource: 'user', action: 'read', description: 'View system users detail' },
  { name: 'user:update', resource: 'user', action: 'update', description: 'Modify user details, statuses' },
  { name: 'user:delete', resource: 'user', action: 'delete', description: 'Remove system users' },
  // Role management
  { name: 'role:create', resource: 'role', action: 'create', description: 'Create new security roles' },
  { name: 'role:read', resource: 'role', action: 'read', description: 'View security roles' },
  { name: 'role:update', resource: 'role', action: 'update', description: 'Modify role descriptions and names' },
  { name: 'role:delete', resource: 'role', action: 'delete', description: 'Remove security roles' },
  { name: 'role:assign', resource: 'role', action: 'assign', description: 'Assign or revoke roles from users' },
  // Cybersecurity operations
  { name: 'network:scan', resource: 'network', action: 'scan', description: 'Execute network security scanning' },
  { name: 'system:configure', resource: 'system', action: 'configure', description: 'Configure firewalls, IDS/IPS system parameters' },
  { name: 'audit:read', resource: 'audit', action: 'read', description: 'Access and inspect system audit trails' },
  { name: 'logs:view', resource: 'logs', action: 'view', description: 'View system logs' }
];

const roles = [
  {
    name: 'SuperAdmin',
    description: 'Unrestricted administrative access to all resources',
    permissions: permissions.map(p => p.name)
  },
  {
    name: 'SecurityAdmin',
    description: 'Manage users, roles, permissions, and security parameters',
    permissions: permissions.filter(p => ['user', 'role', 'system', 'logs'].includes(p.resource)).map(p => p.name)
  },
  {
    name: 'Analyst',
    description: 'Perform scans, monitor traffic, and view security logs',
    permissions: ['user:read', 'role:read', 'network:scan', 'logs:view']
  },
  {
    name: 'Auditor',
    description: 'Read-only access to users, roles, and security audit logs',
    permissions: ['user:read', 'role:read', 'audit:read', 'logs:view']
  }
];

const users = [
  {
    username: 'superadmin',
    email: 'superadmin@cybersecurity.local',
    password_hash: '$2b$12$K1Hk7L2vPz293nJ2O3g8U.C43bfeG5l5hD8B1C8nC4v3O.D1i3R5e',
    status: 'active' as const,
    roles: ['SuperAdmin']
  },
  {
    username: 'secadmin',
    email: 'secadmin@cybersecurity.local',
    password_hash: '$2b$12$K1Hk7L2vPz293nJ2O3g8U.C43bfeG5l5hD8B1C8nC4v3O.D1i3R5e',
    status: 'active' as const,
    roles: ['SecurityAdmin']
  },
  {
    username: 'analyst01',
    email: 'analyst01@cybersecurity.local',
    password_hash: '$2b$12$K1Hk7L2vPz293nJ2O3g8U.C43bfeG5l5hD8B1C8nC4v3O.D1i3R5e',
    status: 'active' as const,
    roles: ['Analyst']
  },
  {
    username: 'auditor01',
    email: 'auditor01@cybersecurity.local',
    password_hash: '$2b$12$K1Hk7L2vPz293nJ2O3g8U.C43bfeG5l5hD8B1C8nC4v3O.D1i3R5e',
    status: 'active' as const,
    roles: ['Auditor']
  }
];

const seed = async () => {
  console.log('Seeding Firestore Database...');

  try {
    // 1. Seed Permissions
    console.log('Seeding permissions...');
    for (const p of permissions) {
      const existing = await PermissionModel.findByName(p.name);
      if (!existing) {
        await PermissionModel.create(p);
        console.log(`Created permission: ${p.name}`);
      } else {
        console.log(`Permission ${p.name} already exists.`);
      }
    }

    // 2. Seed Roles
    console.log('Seeding roles...');
    for (const r of roles) {
      const existing = await RoleModel.findByName(r.name);
      if (!existing) {
        await RoleModel.create(r.name, r.description, r.permissions);
        console.log(`Created role: ${r.name}`);
      } else {
        console.log(`Role ${r.name} already exists.`);
      }
    }

    // 3. Seed Users
    console.log('Seeding users...');
    for (const u of users) {
      const existing = await UserModel.findByUsername(u.username);
      if (!existing) {
        await UserModel.create(u);
        console.log(`Created user: ${u.username}`);
      } else {
        console.log(`User ${u.username} already exists.`);
      }
    }

    console.log('Seeding completed successfully!');
    process.exit(0);
  } catch (error) {
    console.error('Seeding failed:', error);
    process.exit(1);
  }
};

seed();
