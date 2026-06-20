import { Response } from 'express';
import bcrypt from 'bcrypt';
import { AuthenticatedRequest } from '../middlewares/auth.js';
import logger from '../config/logger.js';
import { UserModel, User } from '../models/User.js';
import { AuditLogModel } from '../models/AuditLog.js';

export const getUsers = async (req: AuthenticatedRequest, res: Response) => {
  try {
    const users = await UserModel.getAll();
    
    // Format roles as arrays instead of comma separated strings
    const formatted = users.map((u: any) => ({
      ...u,
      roles: u.roles || [],
    }));

    return res.status(200).json(formatted);
  } catch (error) {
    logger.error('Failed to get users list', { error });
    return res.status(500).json({ message: 'Database error' });
  }
};

export const createUser = async (req: AuthenticatedRequest, res: Response) => {
  const { username, email, password, roles } = req.body;

  if (!username || !email || !password) {
    return res.status(400).json({ message: 'Username, email and password are required' });
  }

  try {
    // 1. Hash Password
    const passwordHash = await bcrypt.hash(password, 12);
    const assignedRoles = roles || ['StandardUser'];
    const loginId = await UserModel.generateLoginId(assignedRoles[0]);

    // 2. Insert User
    const userId = await UserModel.create({
      loginId,
      username,
      email,
      password_hash: passwordHash,
      status: 'active',
      roles: assignedRoles
    });

    // Audit Log creation
    await AuditLogModel.create(
      req.user?.id || null,
      'USER_CREATION',
      'user',
      { new_username: username, assigned_roles: roles },
      req.ip || 'unknown',
      'success'
    );

    return res.status(201).json({ message: 'User created successfully', userId, loginId });
  } catch (error: any) {
    logger.error('Failed to create user', { error });
    if (error.code === 'ER_DUP_ENTRY') {
      return res.status(409).json({ message: 'Username or email already exists' });
    }
    return res.status(500).json({ message: 'Database error occurred during user creation' });
  }
};

export const updateUser = async (req: AuthenticatedRequest, res: Response) => {
  const { id } = req.params;
  const { email, status, roles } = req.body;

  try {
    // 1. Check if user exists
    const originalUser = await UserModel.findById(id);
    if (!originalUser) {
      return res.status(404).json({ message: 'User not found' });
    }

    // 2. Perform updates
    const updates: Partial<Pick<User, 'email' | 'status' | 'roles'>> = {};
    if (email !== undefined) updates.email = email;
    if (status !== undefined) updates.status = status;
    if (roles !== undefined) updates.roles = roles;

    await UserModel.update(id, updates);

    // Audit Log update
    await AuditLogModel.create(
      req.user?.id || null,
      'USER_UPDATE',
      'user',
      {
        target_user_id: id,
        target_username: originalUser.username,
        changes: updates,
      },
      req.ip || 'unknown',
      'success'
    );

    return res.status(200).json({ message: 'User updated successfully' });
  } catch (error: any) {
    logger.error('Failed to update user', { error });
    if (error.code === 'ER_DUP_ENTRY') {
      return res.status(409).json({ message: 'Email already exists' });
    }
    return res.status(500).json({ message: 'Database error occurred during user update' });
  }
};

export const deleteUser = async (req: AuthenticatedRequest, res: Response) => {
  const { id } = req.params;

  try {
    const existing = await UserModel.findById(id);
    if (!existing) {
      return res.status(404).json({ message: 'User not found' });
    }

    // Delete user
    await UserModel.delete(id);

    // Audit Log deletion
    await AuditLogModel.create(
      req.user?.id || null,
      'USER_DELETION',
      'user',
      { deleted_user_id: id, deleted_username: existing.username },
      req.ip || 'unknown',
      'success'
    );

    return res.status(200).json({ message: 'User deleted successfully' });
  } catch (error) {
    logger.error('Failed to delete user', { error });
    return res.status(500).json({ message: 'Database error' });
  }
};

