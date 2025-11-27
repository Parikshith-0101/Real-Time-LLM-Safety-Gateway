const BLOCK_PATTERNS = [
  /ignore (previous )?instructions/i,
  /reveal (the )?system prompt/i,
  /(rm -rf|DROP\s+TABLE|DELETE\s+FROM)/i
];

const REDACT_PATTERNS = [
  /passwords?[:=]\s*\S+/i,
  /api[_-]?key[:=]\s*\S+/i,
  /secret[:=]\s*\S+/i
];

export function check(coreResp, mlResp) {
  const text = coreResp.cleanedPrompt || '';

  // deterministic block
  for (const p of BLOCK_PATTERNS) {
    if (p.test(text)) {
      return {
        block: true,
        decision: 'block',
        reason: 'deterministic_block',
        pattern: String(p)
      };
    }
  }

  // redaction matches
  const redacts = [];
  for (const p of REDACT_PATTERNS) {
    const re = new RegExp(p, 'gi');
    let m;
    while ((m = re.exec(text))) {
      redacts.push({ match: m[0], index: m.index });
    }
  }

  const detScore = redacts.length > 0 ? 0.9 : 0;
  const mlScore = mlResp.score ?? 0.5;

  const finalScore = 0.7 * detScore + 0.3 * mlScore;
  const decision = finalScore >= 0.8 ? 'block' : finalScore >= 0.6 ? 'review' : 'allow';

  return {
    block: false,
    redacts,
    detScore,
    mlScore,
    finalScore,
    decision
  };
}
