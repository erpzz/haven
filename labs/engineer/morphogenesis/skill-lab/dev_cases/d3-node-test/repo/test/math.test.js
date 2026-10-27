import { test } from 'node:test';
import assert from 'node:assert/strict';
import { clamp, double } from '../lib/math.js';

test('clamp keeps values in range', () => {
  assert.equal(clamp(5, 0, 10), 5);
});

test('double', () => {
  assert.equal(double(4), 8);
});
