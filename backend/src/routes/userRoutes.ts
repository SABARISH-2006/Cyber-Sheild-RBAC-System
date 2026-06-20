import { Router } from 'express';
import { getUsers, createUser, updateUser, deleteUser } from '../controllers/userController.js';
import { authenticateToken } from '../middlewares/auth.js';
import { requirePermission } from '../middlewares/rbac.js';

const router = Router();

// Protect all routes with auth middleware
router.use(authenticateToken);

// GET /api/users - Read users (requires 'user:read' permission)
router.get('/', requirePermission('user:read'), getUsers);

// POST /api/users - Create user (requires 'user:create' permission)
router.post('/', requirePermission('user:create'), createUser);

// PUT /api/users/:id - Update user (requires 'user:update' permission)
router.put('/:id', requirePermission('user:update'), updateUser);

// DELETE /api/users/:id - Delete user (requires 'user:delete' permission)
router.delete('/:id', requirePermission('user:delete'), deleteUser);

export default router;
