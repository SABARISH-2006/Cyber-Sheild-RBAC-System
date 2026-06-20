import { Response, NextFunction } from 'express';
import { AuthenticatedRequest } from './auth.js';
import logger from '../config/logger.js';
import { AuditLogModel } from '../models/AuditLog.js';

export const requirePermission = (requiredPermission: string) => {
  return async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
    if (!req.user) {
      return res.status(401).json({ message: 'Unauthorized' });
    }

    const hasPermission = req.user.permissions.includes(requiredPermission);

    if (!hasPermission) {
      logger.warn(
        `Unauthorized access attempt: User ${req.user.username} (ID: ${req.user.id}) tried to execute ${requiredPermission}`
      );

      // Log failure to audit log
      try {
        await AuditLogModel.create(
          req.user.id,
          'UNAUTHORIZED_ACCESS_ATTEMPT',
          requiredPermission.split(':')[0] || 'unknown',
          {
            required_permission: requiredPermission,
            user_roles: req.user.roles,
          },
          req.ip || 'unknown',
          'failure'
        );
      } catch (logError) {
        logger.error('Failed to log unauthorized access to audit_logs', { logError });
      }

      return res.status(403).json({
        message: `Forbidden: You do not have permission to execute action: ${requiredPermission}`,
      });
    }

    next();
  };
};

export const requireRole = (requiredRole: string) => {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
    if (!req.user) {
      return res.status(401).json({ message: 'Unauthorized' });
    }

    const hasRole = req.user.roles.includes(requiredRole);

    if (!hasRole) {
      logger.warn(
        `Unauthorized role access attempt: User ${req.user.username} (ID: ${req.user.id}) requested role: ${requiredRole}`
      );
      return res.status(403).json({
        message: `Forbidden: This resource requires role: ${requiredRole}`,
      });
    }

    next();
  };
};

