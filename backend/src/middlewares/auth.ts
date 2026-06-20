import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import crypto from 'crypto';
import logger from '../config/logger.js';
import { SessionModel } from '../models/Session.js';
import { UserModel } from '../models/User.js';

export interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    username: string;
    email: string;
    roles: string[];
    permissions: string[];
  };
}

export const authenticateToken = async (
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({ message: 'Authentication token required' });
  }

  try {
    const secret = process.env.JWT_SECRET || 'fallback_secret';
    const decoded = jwt.verify(token, secret) as {
      id: string;
      username: string;
      email: string;
    };

    // 1. Hash the token to compare with the database storage
    const tokenHash = crypto.createHash('sha256').update(token).digest('hex');

    // 2. Verify session exists and is active in DB
    const session = await SessionModel.findActiveSession(tokenHash);

    if (!session) {
      logger.warn(`Unauthorized attempt with expired or revoked token: ${decoded.username}`);
      return res.status(401).json({ message: 'Session expired or revoked' });
    }

    // 3. Fetch user details and permissions
    const user = await UserModel.findById(decoded.id);

    if (!user || user.status !== 'active') {
      return res.status(403).json({ message: 'User account is inactive or suspended' });
    }

    const permissions = await UserModel.getPermissions(decoded.id);

    req.user = {
      id: decoded.id,
      username: decoded.username,
      email: decoded.email,
      roles: user.roles || [],
      permissions: permissions,
    };

    next();
  } catch (error) {
    logger.error('Token verification error', { error });
    return res.status(403).json({ message: 'Invalid or expired token' });
  }
};

