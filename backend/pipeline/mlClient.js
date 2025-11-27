import axios from 'axios';
import CircuitBreaker from 'opossum';
import logger from '../utils/logger.js';

const ML_URL = process.env.ML_URL || 'http://ml:8000/predict';

// Axios call to ml
async function callMl(payload) {
  const resp = await axios.post(ML_URL, payload, { timeout: 2500 });
  return resp.data;
}

// Circuit breaker setup
const breaker = new CircuitBreaker(callMl, {
  timeout: 5000,
  errorThresholdPercentage: 50,
  resetTimeout: 30000
});

breaker.on('open', () => logger.warn('ml circuit open'));
breaker.on('close', () => logger.info('ml circuit closed'));

export async function predict(cleanedPrompt, segments, opts = {}) {
  try {
    const payload = { prompt: cleanedPrompt, segments };
    return await breaker.fire(payload);
  } catch (err) {
    logger.warn('ml unavailable, fallback used', { err: err.message });
    return { score: 0.5, labels: {}, mlDown: true };
  }
}
