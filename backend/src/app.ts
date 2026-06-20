import express, { Request, Response, NextFunction } from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import authRoutes from './routes/authRoutes.js';
import userRoutes from './routes/userRoutes.js';
import { apiRateLimiter } from './middlewares/rateLimiter.js';
import logger from './config/logger.js';

dotenv.config();

const app = express();

// Standard Cors setup (in prod, restrict to specific origin)
app.use(cors({
  origin: '*', 
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization'],
}));

// Express parser configurations with tight payload bounds to prevent denial of service (DoS)
app.use(express.json({ limit: '10kb' }));
app.use(express.urlencoded({ extended: true, limit: '10kb' }));

// Apply rate limiter to all API endpoints
app.use('/api', apiRateLimiter);

// Register Routes
app.use('/api/auth', authRoutes);
app.use('/api/users', userRoutes);

// Basic Health Check
app.get('/health', (req: Request, res: Response) => {
  res.status(200).json({ status: 'UP', timestamp: new Date() });
});

// Centralized error handler
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
  logger.error('Unhandled request error', { error: err.message, stack: err.stack });
  res.status(500).json({ message: 'An internal server error occurred' });
});

export default app;
