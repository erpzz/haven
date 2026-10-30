import { test } from 'node:test';
import assert from 'node:assert/strict';
import { memoize } from '../lib/memo.js';

test('hot keys stay cached', () => {
  let calls = 0;
  const sq = memoize((x) => { calls += 1; return x * x; }, 2);
  sq(1); sq(2); sq(1); sq(3); sq(1);
  assert.equal(calls, 3);
});
