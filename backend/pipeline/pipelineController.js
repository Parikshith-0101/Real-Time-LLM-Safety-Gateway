// backend/pipeline/pipelineController.js
import { callCore } from "./coreClient.js";
import * as mlClient from "./mlClient.js";
import { validateSanitize } from "./validators.js";
import { estimateTokens } from "./tokenEstimator.js";
import logger from "../utils/logger.js";

/**
 * Simple pipeline: call core -> call ml -> return combined result to caller.
 * No deterministic rules or sanitizer applied here.
 */
export async function handleSanitizeRequest(payload, opts = {}) {
  const { correlationId } = opts || {};

  // Validate
  const { error, value } = validateSanitize(payload);
  if (error) {
    const err = new Error(
      "validation_error: " + error.details.map((d) => d.message).join("; ")
    );
    err.isJoi = true;
    throw err;
  }
  const { prompt, userId } = value;

  logger.info("pipeline:start", { correlationId, userId });

  // Estimate tokens (optional, for telemetry)
  const tokenCount = estimateTokens(prompt);

  // 1) Core processing (normalization/segmentation/etc)
  let coreResp;
  try {
    coreResp = await callCore(prompt, { correlationId });
    logger.info("pipeline:core_done", { correlationId });
  } catch (err) {
    // coreClient should already have a fallback; log & propagate minimum info
    logger.warn("pipeline:core_call_failed", {
      correlationId,
      message: err?.message || String(err),
    });
    coreResp = {
      cleanedPrompt: prompt,
      segments: [{ id: 1, type: "text", text: prompt }],
      flags: {},
    };
  }

  // 2) ML prediction
  let mlResp;
  try {
    // mlClient.predict should return an object: { simple_scores, meta } or similar
    mlResp = await mlClient.predict(coreResp.cleanedPrompt, coreResp.segments, {
      correlationId,
    });
    // compute a single mlScore (max across simple_scores) for logging/UI
    const mlScores = mlResp?.simple_scores || {};
    const mlScore = Object.values(mlScores).length
      ? Math.max(...Object.values(mlScores))
      : mlResp?.meta?.max_score ?? null;
    logger.info("pipeline:ml_done", { correlationId, mlScore });
  } catch (err) {
    logger.warn("pipeline:ml_call_failed, using fallback", {
      correlationId,
      message: err?.message || String(err),
    });
    // simple fallback shape — keep consistent with your future ML responses
    mlResp = {
      simple_scores: { malicious: 0, persona: 0, infoleak: 0, codeexec: 0 },
      meta: { segment_scores: [], scores: {} },
    };
  }

  // 3) Build a simple response that the frontend/consumer can use immediately
  const response = {
    decision: "defer", // not decided here (agent/engine to decide later). Use 'defer' or 'noop'
    note: "core + ml responses returned. Decisioning deferred to agent.",

    // Useful payloads for downstream logic / UI
    core: coreResp, // { cleanedPrompt, segments, flags }
    ml: mlResp, // { simple_scores, meta } (from your ML service)
    tokens: tokenCount,
    correlationId,
  };

  // Log the outcome (you can adjust detail level)
  logger.info("pipeline:finish", { correlationId, tokens: tokenCount });

  return response;
}
