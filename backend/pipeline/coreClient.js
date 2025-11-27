// backend/pipeline/coreClient.js
import axios from 'axios';
import logger from '../utils/logger.js';

// safe env read; make sure dotenv is loaded BEFORE imports (see step 3)
const CORE_URL = (typeof globalThis !== 'undefined' && globalThis.process && globalThis.process.env && globalThis.process.env.CORE_URL)
  ? globalThis.process.env.CORE_URL
  : 'http://127.0.0.1:3000/process';

// export a non-conflicting name
export async function callCore(prompt, opts = {}) {
  try {
    const headers = {};
    if (opts.correlationId) headers['X-Correlation-ID'] = opts.correlationId;
    const resp = await axios.post(CORE_URL, { prompt }, { timeout: 3000, headers });
    return resp.data;
  } catch (err) {
    logger.warn('coreClient failed, using fallback', { err: err?.message || String(err) });
    return fallbackProcess(prompt);
  }
}

function fallbackProcess(prompt) {
  const normalize = (s) => {
    try {
      return s.normalize('NFKC').replace(/[\u200B-\u200D\uFEFF]/g, '');
    } catch {
      return s;
    }
  };
  const cleanedPrompt = normalize(prompt || "");
  const segments = (cleanedPrompt || '').split(/\n{2,}/).map((p, i) => ({
    id: i + 1,
    type: 'text',
    text: p.trim()
  }));
  const flags = { highEntropySegments: [] };
  return { cleanedPrompt, segments, flags };
}
