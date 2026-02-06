const DEFAULT_FONT = "12px monospace";

export function createMeasureCache(measureFn) {
  if (typeof measureFn !== "function") {
    throw new Error("measureFn is required");
  }
  const cache = new Map();
  const stats = { hits: 0, misses: 0 };

  function cacheKey(text, font) {
    return `${font}::${String(text ?? "")}`;
  }

  function measureText(text, options = {}) {
    const font = options.font ?? DEFAULT_FONT;
    const key = cacheKey(text, font);
    if (cache.has(key)) {
      stats.hits += 1;
      return { ...cache.get(key), cacheHit: true };
    }
    stats.misses += 1;
    const result = measureFn(text, { ...options, font });
    cache.set(key, result);
    return { ...result, cacheHit: false };
  }

  return { measureText, stats, cache };
}
