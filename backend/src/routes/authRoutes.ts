import { Router } from 'express';
import { login, logout } from '../controllers/authController.js';
import { authenticateToken } from '../middlewares/auth.js';
import { authRateLimiter } from '../middlewares/rateLimiter.js';

const router = Router();

// /api/auth/login
router.post('/login', authRateLimiter, login);

// /api/auth/logout
router.post('/logout', authenticateToken, logout);

export default router;
