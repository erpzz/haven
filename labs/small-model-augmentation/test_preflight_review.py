"""Second-pass tests: acceptance matrix and malformed wire inputs."""
import itertools
import json
import unittest

import preflight


class ReviewTests(unittest.TestCase):
    def test_cross_product(self):
        expected = ['alpha-9b', 'beta-4b', 'ALPHA-9B', None, '<MODEL_ID>', 'todo']
        requested = expected + [True, '']
        inventories = [[x] for x in expected] + [[], ['alpha-9b', 'beta-4b'],
                                                ['alpha-9b'] * 2, None, 'alpha-9b']
        contexts = [None, True, 8192, 63999, 64000, 65536, '65536', 65536.0]
        allowed = set(expected[:3])
        counts = {'pass': 0, 'block': 0}
        for e, r, inv, ctx in itertools.product(expected, requested, inventories, contexts):
            doc = dict(expected_model=e, requested_model=r, observed_model_ids=inv,
                       observed_context_tokens=ctx)
            want = 'pass' if (e in allowed and r == e and inv == [e]
                              and type(ctx) is int and ctx in (64000, 65536)) else 'block'
            result = preflight.parse(json.dumps(doc).encode())
            self.assertEqual(result['status'], want)
            self.assertEqual(not result['errors'], want == 'pass')
            self.assertIs(result['live_endpoint_verified'], False)
            self.assertIs(result['weight_identity_verified'], False)
            counts[want] += 1
        self.assertEqual(counts, {'pass': 6, 'block': 4218})

    def test_wire_mutations(self):
        raw = b'{"expected_model":"alpha-9b","requested_model":"alpha-9b","observed_model_ids":["alpha-9b"],"observed_context_tokens":64000}'
        self.assertEqual(preflight.parse(raw)['status'], 'pass')
        for bad in (raw[:-1] + b',"expected_model":"alpha-9b"}',
                    raw.replace(b'64000', b'NaN'), raw.replace(b'64000', b'Infinity'),
                    raw + b'{}', b'\xef\xbb\xbf' + raw,
                    raw.replace(b'alpha-9b', b'alpha-9b\\u0000'),
                    raw.replace(b'alpha-9b', b'alpha-9b\\u202e'),
                    raw.replace(b'alpha-9b', b'a' * 257)):
            self.assertEqual(preflight.parse(bad)['status'], 'block')
        self.assertEqual(preflight.parse(raw + b' ' * (preflight.MAX_BYTES-len(raw)))['status'], 'pass')
        self.assertEqual(preflight.parse(raw + b' ' * (preflight.MAX_BYTES-len(raw)+1))['errors'], ['INPUT_TOO_LARGE'])

    def test_receipt_redaction(self):
        marker = 'private-synthetic-marker'
        result = preflight.check(dict(expected_model=marker, requested_model='alpha-9b',
                                      observed_model_ids=['beta-4b'], observed_context_tokens=8192))
        self.assertNotIn(marker, json.dumps(result))
        self.assertEqual(set(result['errors']), {'REQUESTED_MODEL_MISMATCH',
                                                'OBSERVED_MODEL_MISMATCH',
                                                'CONTEXT_UNVERIFIED_OR_TOO_SMALL'})


if __name__ == '__main__':
    unittest.main()
