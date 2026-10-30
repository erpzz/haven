import { LRU } from './lru.js';

export function memoize(fn, capacity = 2) {
  const cache = new LRU(capacity);
  const wrapped = (...args) => {
    const key = JSON.stringify(args);
    const hit = cache.get(key);
    if (hit !== undefined) return hit;
    const value = fn(...args);
    cache.set(key, value);
    return value;
  };
  wrapped.cache = cache;
  return wrapped;
}
