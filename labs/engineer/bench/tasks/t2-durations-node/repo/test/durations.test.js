import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseDuration } from '../src/durations.js';

test('seconds', () => assert.equal(parseDuration('45s'), 45));
test('minutes', () => assert.equal(parseDuration('2m'), 120));
test('hours', () => assert.equal(parseDuration('3h'), 10800));
test('rejects garbage', () => assert.throws(() => parseDuration('soon')));
