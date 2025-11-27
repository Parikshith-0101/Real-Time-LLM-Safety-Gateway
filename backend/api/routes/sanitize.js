import express from 'express';
import * as pipeline from '../../pipeline/pipelineController.js';
import logger from '../../utils/logger.js';

const router = express.Router();

router.post('/', async (req, res) => {
  try {
    const payload = req.body || {};
    const correlationId = req.correlationId;
    logger.info('Received sanitize request', { correlationId });

    const result = await pipeline.handleSanitizeRequest(payload, { correlationId });
    res.json(result);

  } catch (err) {
    logger.error('sanitize route error', { message: err.message });
    if (err.isJoi || err.message?.startsWith('validation_error')) {
      return res.status(400).json({ error: 'invalid_request', message: err.message });
    }
    res.status(500).json({ error: 'server_error' });
  }
});

export default router;
