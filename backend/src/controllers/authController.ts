import { Request, Response } from 'express';
import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import crypto from 'crypto';
import logger from '../config/logger.js';
import { AuthenticatedRequest } from '../middlewares/auth.js';
import { UserModel } from '../models/User.js';
import { SessionModel } from '../models/Session.js';
import { AuditLogModel } from '../models/AuditLog.js';

export const login = async (req: Request, res: Response) => {
  const { loginId, password } = req.body;

  if (!loginId || !password) {
    return res.status(400).json({ message: 'Login ID and password are required' });
  }

  try {
    // 1. Fetch user detail
    const user = await UserModel.findByLoginId(loginId);

    if (!user) {
      logger.warn(`Failed login attempt: user not found: ${loginId}`);
      await AuditLogModel.create(null, 'LOGIN_FAILED', 'auth', { loginId, reason: 'User not found' }, req.ip || 'unknown', 'failure');
      return res.status(401).json({ message: 'Invalid credentials' });
    }

    // 2. Check user status
    if (user.status !== 'active') {
      logger.warn(`Suspended or inactive user attempt to login: ${loginId}`);
      await AuditLogModel.create(user.id || null, 'LOGIN_FAILED', 'auth', { loginId, reason: `User account status is ${user.status}` }, req.ip || 'unknown', 'failure');
      return res.status(403).json({ message: `Your account is ${user.status}. Contact support.` });
    }

    // 3. Verify password hash
    const isMatch = await bcrypt.compare(password, user.password_hash);
    if (!isMatch) {
      logger.warn(`Failed login attempt: incorrect password: ${loginId}`);
      await AuditLogModel.create(user.id || null, 'LOGIN_FAILED', 'auth', { loginId, reason: 'Incorrect password' }, req.ip || 'unknown', 'failure');
      return res.status(401).json({ message: 'Invalid credentials' });
    }

    // 4. Generate JWT
    const secret = process.env.JWT_SECRET || 'fallback_secret';
    const token = jwt.sign(
      { id: user.id, username: user.username, email: user.email },
      secret,
      { expiresIn: (process.env.JWT_EXPIRY || '1h') as any }
    );

    // 5. Hash token for database storage
    const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
    const expiry = new Date();
    expiry.setHours(expiry.getHours() + 1); // 1 hour session expiry matches JWT default

    // 6. Save session in user_sessions
    await SessionModel.create(user.id!, tokenHash, req.ip || 'unknown', req.headers['user-agent'] as string || null, expiry);

    // 7. Log successful login to Audit Logs
    await AuditLogModel.create(user.id!, 'LOGIN_SUCCESS', 'auth', {}, req.ip || 'unknown', 'success');

    return res.status(200).json({
      message: 'Login successful',
      token,
      user: {
        id: user.id,
        loginId: user.loginId,
        username: user.username,
        email: user.email,
      },
    });
  } catch (error) {
    logger.error('Login system error', { error });
    return res.status(500).json({ message: 'An internal server error occurred' });
  }
};

export const logout = async (req: AuthenticatedRequest, res: Response) => {
  if (!req.user) {
    return res.status(401).json({ message: 'Unauthorized' });
  }

  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(400).json({ message: 'Missing token header' });
  }

  try {
    const tokenHash = crypto.createHash('sha256').update(token).digest('hex');

    // Remove user session (token revocation)
    await SessionModel.deleteByTokenHash(tokenHash);

    // Audit Log logout
    await AuditLogModel.create(req.user.id, 'LOGOUT', 'auth', {}, req.ip || 'unknown', 'success');

    return res.status(200).json({ message: 'Logout successful' });
  } catch (error) {
    logger.error('Logout system error', { error });
    return res.status(500).json({ message: 'An internal server error occurred' });
  }
};

