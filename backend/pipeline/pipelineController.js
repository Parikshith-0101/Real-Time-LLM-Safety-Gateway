import { callCore } from './coreClient.js'; 
import * as mlClient from './mlClient.js';
import { validateSanitize } from './validators.js';
import { estimateTokens } from './tokenEstimator.js';
import * as rulesEngine from '../services/rulesEngine.js';
import * as sanitizer from '../services/sanitizer.js';
import logger from '../utils/logger.js';

export async function handleSanitizeRequest(payload, opts = {}) {
  const { correlationId } = opts;

  // validate
  const { error, value } = validateSanitize(payload);
  if (error) {
    const err = new Error('validation_error: ' + error.details.map(d => d.message).join('; '));
    err.isJoi = true;
    throw err;
  }

  const { prompt, userId } = value;
  logger.info('pipeline:start', { correlationId, userId });

  // token estimate
  const tokenCount = estimateTokens(prompt);

  // call core python service
const coreResp = await callCore(prompt, { correlationId });
  logger.info('pipeline:core_done', { correlationId });

  // call ml python service
  const mlResp = await mlClient.predict(coreResp.cleanedPrompt, coreResp.segments, { correlationId });
  logger.info('pipeline:ml_done', { correlationId, mlScore: mlResp.score });

  // run rules
  const ruleCheck = rulesEngine.check(coreResp, mlResp);

  if (ruleCheck.block) {
    return {
      decision: 'block',
      reason: ruleCheck.reason,
      pattern: ruleCheck.pattern,
      audit: { core: coreResp, ml: mlResp, tokens: tokenCount }
    };
  }

  const sanitizedObj = sanitizer.applySanitizer(coreResp, ruleCheck);

  return {
    decision: ruleCheck.decision,
    score: ruleCheck.finalScore,
    sanitizedPrompt: sanitizedObj.sanitized,
    mapping: sanitizedObj.mapping,
    audit: {
      core: coreResp,
      ml: mlResp,
      tokens: tokenCount
    }
  };
}
