import axios from 'axios';
import logger from '../utils/logger.js';

const CORE_URL = process.env.CORE_URL || 'http://core:5000/process';

export async function process(prompt, opts = {}) {
  try {
    const resp = await axios.post(CORE_URL, { prompt }, { timeout: 3000 });
    return resp.data; 
  } catch (err) {
    logger.warn('coreClient failed, using fallback', { err: err.message });
    return fallbackProcess(prompt);
  }
}

function fallbackProcess(prompt) {
  const cleanedPrompt = (prompt || '').normalize('NFKC').replace(/[\u200B-\u200D\uFEFF]/g, '');
  const segments = cleanedPrompt.split(/\n{2,}/).map((p, i) => ({
    id: i + 1,
    type: 'text',
    text: p.trim()
  }));
  const flags = { highEntropySegments: [] };
  return { cleanedPrompt, segments, flags };
}
