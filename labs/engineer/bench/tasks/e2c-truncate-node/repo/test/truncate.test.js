import { test } from 'node:test';
import assert from 'node:assert/strict';
import { truncate } from '../lib/truncate.js';

test('short text unchanged', () => assert.equal(truncate('hi', 5), 'hi'));
test('result never longer than max', () => assert.equal(truncate('abcdefgh', 5).length, 5));
test('ends with ellipsis', () => assert.equal(truncate('abcdefgh', 5), 'abcd…'));
