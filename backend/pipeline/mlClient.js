// backend/pipeline/mlClient.js
import axios from 'axios';
import CircuitBreaker from 'opossum';
import logger from '../utils/logger.js';

// safe env read (process exists in Node)
const ML_URL = (process && process.env && process.env.ML_URL) ? process.env.ML_URL : 'http://127.0.0.1:8000/predict';

// Axios call to ml
async function callMl(payload) {
  const resp = await axios.post(ML_URL, payload, { timeout: 8000 }); // 8s axios timeout
  return resp.data;
}

// Circuit breaker setup
const breaker = new CircuitBreaker(callMl, {
  timeout: 10000,                 // opossum-level timeout (ms)
  errorThresholdPercentage: 50,   // when to open circuit
  resetTimeout: 30000             // ms before trying again
});

breaker.on('open', () => logger.warn('ml circuit open'));
breaker.on('halfOpen', () => logger.info('ml circuit half-open'));
breaker.on('close', () => logger.info('ml circuit closed'));
breaker.on('fallback', () => logger.warn('ml circuit fallback triggered'));

function normalizeMlResponse(data) {
  // Accept multiple possible shapes from ML service and normalize to { simple_scores, meta }
  if (!data || typeof data !== 'object') {
    return { simple_scores: { malicious: 0, persona: 0, infoleak: 0, codeexec: 0 }, meta: { scores: {}, segment_scores: [] } };
  }

  // If ML returns { simple_scores, meta } already — use as-is
  if (data.simple_scores && data.meta) {
    return { simple_scores: data.simple_scores, meta: data.meta };
  }

  // If ML returns { scores, meta } or { score, labels } shape — map best-effort
  if (data.scores && typeof data.scores === 'object') {
    return { simple_scores: data.scores, meta: data.meta || {} };
  }

  // If ML returns single score (e.g. { score: 0.5, labels: {} })
  if (typeof data.score === 'number') {
    return {
      simple_scores: { malicious: data.score, persona: 0, infoleak: 0, codeexec: 0 },
      meta: { scores: { overall: data.score }, labels: data.labels || {} }
    };
  }

  // fallback default
  return { simple_scores: { malicious: 0, persona: 0, infoleak: 0, codeexec: 0 }, meta: { scores: {}, segment_scores: [] } };
}

export async function predict(cleanedPrompt, segments = [], opts = {}) {
  try {
    const payload = { prompt: cleanedPrompt, segments };
    const raw = await breaker.fire(payload);
    const normalized = normalizeMlResponse(raw);
    return normalized; // { simple_scores, meta }
  } catch (err) {
    logger.warn('ml unavailable, fallback used', { err: err?.message || String(err) });
    // Return the same normalized fallback shape so pipeline can rely on structure
    return {
      simple_scores: { malicious: 0.0, persona: 0.0, infoleak: 0.0, codeexec: 0.0 },
      meta: { scores: {}, segment_scores: [] , mlDown: true}
    };
  }
}
