// backend/pipeline/pipelineController.js
import { callCore } from "./coreClient.js";
import * as mlClient from "./mlClient.js";
import { validateSanitize } from "./validators.js";
import { estimateTokens } from "./tokenEstimator.js";
import logger from "../utils/logger.js";

/**
 * Simple pipeline: call core -> call ml agent -> return combined result to caller.
 * The ML client returns an agent object:
 *   { verdict: "allow" | "sanitize", sanitized_prompt: string, explanation: string, confidence: number }
 *
 * This controller returns both the pipeline-friendly shape and the agent-style top-level fields
 * so frontend code that expects agent JSON will work.
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
    logger.info("pipeline:core_done", { correlationId, segments: coreResp?.segments?.length ?? 0 });
  } catch (err) {
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

  // 2) ML agent prediction (returns agent JSON)
  let mlResp;
  try {
    mlResp = await mlClient.predict(coreResp.cleanedPrompt, coreResp.segments, {
      correlationId,
    });

    if (!mlResp || typeof mlResp !== "object" || !["allow", "sanitize"].includes(mlResp.verdict)) {
      logger.warn("pipeline:ml_invalid_response_shape", { correlationId, raw: mlResp });
      throw new Error("invalid_ml_agent_response");
    }

    logger.info("pipeline:ml_done", {
      correlationId,
      verdict: mlResp.verdict,
      confidence: typeof mlResp.confidence === "number" ? mlResp.confidence : null,
    });
  } catch (err) {
    logger.warn("pipeline:ml_call_failed, using fallback", {
      correlationId,
      message: err?.message || String(err),
    });

    mlResp = {
      verdict: "sanitize",
      sanitized_prompt:
        "This prompt has been safely transformed to avoid harmful content.",
      explanation:
        "ML service unavailable or returned invalid output. Fallback sanitized prompt used.",
      confidence: 0.5,
      mlDown: true,
    };
  }

  // 3) Map agent verdict -> pipeline decision & create top-level agent fields
  const decision = mlResp.verdict === "allow" ? "allow" : "sanitize";
  const sanitizedPrompt =
    mlResp.verdict === "allow"
      ? String(prompt)
      : String(mlResp.sanitized_prompt || coreResp.cleanedPrompt || prompt);

  const explanation = mlResp.explanation || mlResp.note || "";
  const confidence = typeof mlResp.confidence === "number" ? mlResp.confidence : null;

  // 4) Build response for frontend that contains both shapes
  const response = {
    // agent-style top-level fields (WHAT YOUR FRONTEND EXPECTS)
    verdict: decision,
    sanitized_prompt: sanitizedPrompt,
    explanation,
    confidence,

    // pipeline-style fields (existing shape, kept for compatibility)
    decision,
    note: explanation,
    sanitizedPrompt,
    confidenceScore: confidence,

    // Useful payloads for downstream logic / UI
    core: coreResp, // { cleanedPrompt, segments, flags }
    ml: mlResp, // agent object: { verdict, sanitized_prompt, explanation, confidence }
    tokens: tokenCount,
    correlationId,
    audit: {
      core: coreResp,
      ml: mlResp,
      tokens: tokenCount,
    },
  };

  logger.info("pipeline:finish", { correlationId, tokens: tokenCount, decision });

  return response;
}
