import express from 'express';
import helmet from 'helmet';
import morgan from 'morgan';
import { v4 as uuidv4 } from 'uuid';

import sanitizeRoute from './routes/sanitize.js';
import logger from '../utils/logger.js';

const app = express();

app.use(helmet());
app.use(express.json({ limit: '128kb' }));
app.use(morgan('dev'));

// correlation ID middleware
app.use((req, res, next) => {
  req.correlationId = req.headers['x-correlation-id'] || uuidv4();
  res.setHeader('X-Correlation-ID', req.correlationId);
  next();
});

// health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', correlationId: req.correlationId });
});

// routes
app.use('/api/sanitize', sanitizeRoute);

// error handler
app.use((err, req, res, next) => {
  logger.error('Unhandled error', { err: err.message, correlationId: req.correlationId });
  res.status(500).json({ error: 'internal_error', correlationId: req.correlationId });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => logger.info(`Backend listening on ${PORT}`));
