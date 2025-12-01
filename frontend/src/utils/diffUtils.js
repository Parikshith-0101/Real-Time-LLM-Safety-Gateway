/**
 * diffUtils.js
 * Utilities for computing text differences and formatting scores.
 */

/**
 * Computes a diff between original and sanitized text.
 * Tokenizes by whitespace and punctuation to provide granular diffs.
 * Returns an array of objects: { type: 'equal' | 'insert' | 'delete' | 'replace', value: string }
 *
 * @param {string} original
 * @param {string} sanitized
 * @returns {Array<{type: string, value: string}>}
 */
export const computeDiff = (original, sanitized) => {
  if (!original && !sanitized) return [];
  if (!original) return [{ type: "insert", value: sanitized }];
  if (!sanitized) return [{ type: "delete", value: original }];

  // Tokenize by whitespace and punctuation, keeping delimiters
  // This regex matches:
  // 1. Sequences of word characters (alphanumeric + underscore)
  // 2. Non-whitespace non-word characters (punctuation)
  // 3. Whitespace sequences
  const tokenize = (text) => {
    return text.split(/([a-zA-Z0-9_]+|[^a-zA-Z0-9_\s]+|\s+)/).filter((t) => t);
  };

  const oldTokens = tokenize(original);
  const newTokens = tokenize(sanitized);

  // Simple LCS (Longest Common Subsequence) implementation
  const dp = Array(oldTokens.length + 1)
    .fill(null)
    .map(() => Array(newTokens.length + 1).fill(0));

  for (let i = 1; i <= oldTokens.length; i++) {
    for (let j = 1; j <= newTokens.length; j++) {
      if (oldTokens[i - 1] === newTokens[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  let i = oldTokens.length;
  let j = newTokens.length;
  const diff = [];

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && oldTokens[i - 1] === newTokens[j - 1]) {
      diff.unshift({ type: "equal", value: oldTokens[i - 1] });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      diff.unshift({ type: "insert", value: newTokens[j - 1] });
      j--;
    } else if (i > 0 && (j === 0 || dp[i][j - 1] < dp[i - 1][j])) {
      diff.unshift({ type: "delete", value: oldTokens[i - 1] });
      i--;
    }
  }

  // Merge consecutive nodes of same type
  const mergedDiff = [];
  if (diff.length > 0) {
    let current = diff[0];
    for (let k = 1; k < diff.length; k++) {
      if (diff[k].type === current.type) {
        current.value += diff[k].value;
      } else {
        mergedDiff.push(current);
        current = diff[k];
      }
    }
    mergedDiff.push(current);
  }

  return mergedDiff;
};

/**
 * Validates and parses the agent response.
 * Expected schema:
 * {
 *   "verdict": "allow" | "sanitize",
 *   "sanitized_prompt": string,
 *   "explanation": string,
 *   "confidence": number
 * }
 *
 * @param {any} responseData - The raw JSON response from axios
 * @returns {{ok: boolean, data?: object, error?: string}}
 */
export const parseAgentResponse = (responseData) => {
  if (!responseData || typeof responseData !== "object") {
    return { ok: false, error: "Response is not a valid JSON object." };
  }

  const { verdict, sanitized_prompt, explanation, confidence } = responseData;

  // Validate required fields
  if (
    verdict === undefined ||
    sanitized_prompt === undefined ||
    explanation === undefined ||
    confidence === undefined
  ) {
    return {
      ok: false,
      error:
        "Missing required fields: verdict, sanitized_prompt, explanation, or confidence.",
    };
  }

  // Validate verdict enum
  if (verdict !== "allow" && verdict !== "sanitize") {
    return {
      ok: false,
      error: `Invalid verdict value: ${verdict}. Expected 'allow' or 'sanitize'.`,
    };
  }

  // Validate types
  if (typeof sanitized_prompt !== "string")
    return { ok: false, error: "sanitized_prompt must be a string." };
  if (typeof explanation !== "string")
    return { ok: false, error: "explanation must be a string." };
  if (typeof confidence !== "number")
    return { ok: false, error: "confidence must be a number." };

  return { ok: true, data: responseData };
};

/**
 * Formats confidence score as a percentage string.
 * @param {number} confidence - 0.0 to 1.0
 * @returns {string} - e.g. "95%"
 */
export const formatConfidence = (confidence) => {
  if (typeof confidence !== "number") return "0%";
  return `${Math.round(confidence * 100)}%`;
};
