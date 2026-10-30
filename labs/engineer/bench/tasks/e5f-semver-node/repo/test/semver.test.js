import { test } from 'node:test';
import assert from 'node:assert/strict';
import { compare, sort } from '../lib/semver.js';

test('numeric parts compare as numbers', () => {
  assert.equal(compare('1.10.0', '1.9.0'), 1);
  assert.equal(compare('2.0.0', '10.0.0'), -1);
});

test('prerelease is lower than release', () => {
  assert.equal(compare('1.0.0-rc.1', '1.0.0'), -1);
  assert.equal(compare('1.0.0', '1.0.0-alpha'), 1);
});

test('prerelease identifiers', () => {
  assert.equal(compare('1.0.0-rc.2', '1.0.0-rc.10'), -1);
  assert.equal(compare('1.0.0-alpha', '1.0.0-alpha.1'), -1);
});

test('sort', () => {
  assert.deepEqual(sort(['1.0.0', '1.0.0-rc.1', '0.9.12', '0.9.2']), ['0.9.2', '0.9.12', '1.0.0-rc.1', '1.0.0']);
});
