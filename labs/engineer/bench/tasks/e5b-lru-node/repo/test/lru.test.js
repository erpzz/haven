import { test } from 'node:test';
import assert from 'node:assert/strict';
import { LRU } from '../lib/lru.js';

test('evicts least recently used', () => {
  const c = new LRU(2);
  c.set('a', 1); c.set('b', 2);
  assert.equal(c.get('a'), 1);
  c.set('c', 3);
  assert.equal(c.get('b'), undefined);
  assert.equal(c.get('a'), 1);
});

test('overwriting a key does not evict', () => {
  const c = new LRU(2);
  c.set('a', 1); c.set('b', 2); c.set('b', 3);
  assert.equal(c.get('a'), 1);
  assert.equal(c.get('b'), 3);
  assert.equal(c.map.size, 2);
});
