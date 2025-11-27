export function estimateTokens(text) {
  if (!text) return 0;
  const words = text.split(/\s+/).length;
  return Math.ceil(words * 1.3);
}
