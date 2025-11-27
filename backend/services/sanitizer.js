export function applySanitizer(coreResp, ruleCheck) {
  let sanitized = coreResp.cleanedPrompt;
  const mapping = [];

  if (ruleCheck.redacts && ruleCheck.redacts.length) {
    ruleCheck.redacts.forEach((r, i) => {
      const placeholder = `[REDACTED_${i + 1}]`;
      sanitized = sanitized.replace(r.match, placeholder);
      mapping.push({ placeholder, original: r.match });
    });
  }

  return { sanitized, mapping };
}
