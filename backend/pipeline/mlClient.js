// backend/pipeline/mlClient.js
import axios from 'axios';
import CircuitBreaker from 'opossum';
import logger from '../utils/logger.js';

// Prefer explicit ML_AGENT_URL, fallback to ML_URL -> replace /predict with /agent, else default to localhost
const ML_AGENT_URL = (process && process.env && process.env.ML_AGENT_URL)
  ? process.env.ML_AGENT_URL
  : (process && process.env && process.env.ML_URL)
    ? process.env.ML_URL.replace(/\/predict\/?$/, '/agent')
    : 'http://127.0.0.1:8000/agent';

// Axios call to ML agent endpoint
async function callMlAgent(payload) {
  const resp = await axios.post(ML_AGENT_URL, payload, { timeout: 8000 });
  return resp.data;
}

// Circuit breaker setup
const breaker = new CircuitBreaker(callMlAgent, {
  timeout: 10000,                 // opossum-level timeout (ms)
  errorThresholdPercentage: 50,   // when to open circuit
  resetTimeout: 30000             // ms before trying again
});

breaker.on('open', () => logger.warn('ml circuit open'));
breaker.on('halfOpen', () => logger.info('ml circuit half-open'));
breaker.on('close', () => logger.info('ml circuit closed'));
breaker.on('fallback', () => logger.warn('ml circuit fallback triggered'));

/**
 * Validate that the agent response matches the strict schema:
 * {
 *   verdict: "allow" | "sanitize",
 *   sanitized_prompt: string,
 *   explanation: string,
 *   confidence: number
 * }
 */
function validateAgentResponse(obj) {
  if (!obj || typeof obj !== 'object') return false;
  const { verdict, sanitized_prompt, explanation, confidence } = obj;
  if (verdict !== 'allow' && verdict !== 'sanitize') return false;
  if (typeof sanitized_prompt !== 'string') return false;
  if (typeof explanation !== 'string') return false;
  if (typeof confidence !== 'number' || Number.isNaN(confidence)) return false;
  return true;
}

export async function predict(cleanedPrompt, segments = [], opts = {}) {
  try {
    const payload = { prompt: cleanedPrompt, segments };
    if (opts && opts.correlationId) {
      // attach correlation id into payload headers via axios config using breaker wrapper not available here,
      // so include correlationId in payload as well for debugging if ML service expects it in body
      payload.correlation_id = opts.correlationId;
    }

    const raw = await breaker.fire(payload);

    // raw should be the single-agent JSON object
    if (!validateAgentResponse(raw)) {
      logger.warn('mlClient: invalid agent response shape', { raw });
      throw new Error('invalid_agent_response');
    }

    // Return raw agent object as-is (verdict, sanitized_prompt, explanation, confidence)
    return raw;
  } catch (err) {
    logger.warn('ml unavailable or invalid response, fallback used', { err: err?.message || String(err) });
    // Return a consistent fallback matching the agent schema
    return {
      verdict: 'sanitize',
      sanitized_prompt: 'This prompt has been safely transformed to avoid harmful content.',
      explanation: 'ML service unavailable or returned invalid output. Fallback sanitized prompt returned.',
      confidence: 0.5
    };
  }
}
