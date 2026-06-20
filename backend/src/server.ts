import app from './app.js';
import db from './config/db.js';
import logger from './config/logger.js';
import { collection, query, limit, getDocs } from 'firebase/firestore';

const PORT = process.env.PORT || 5000;

const startServer = async () => {
  try {
    // 1. Verify database pool readiness
    logger.info('Verifying database connectivity...');
    const q = query(collection(db, 'permissions'), limit(1));
    await getDocs(q);
    logger.info('Database connection established successfully.');

    // 2. Start listening
    const server = app.listen(PORT, () => {
      logger.info(`RBAC Security Server is running on port ${PORT}`);
    });

    // Handle graceful shutdowns for container compliance
    const shutdown = () => {
      logger.info('Shutting down server gracefully...');
      server.close(() => {
        logger.info('HTTP server closed.');
        process.exit(0);
      });
    };

    process.on('SIGTERM', shutdown);
    process.on('SIGINT', shutdown);
  } catch (error) {
    logger.error('Failed to initialize server or database connection', { error });
    process.exit(1);
  }
};

startServer();

