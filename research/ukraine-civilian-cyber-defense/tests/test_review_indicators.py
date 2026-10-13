import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'controls'))
from review_indicators import evaluate, good_indicator, csv_safe

NOW = datetime(2026, 10, 13, tzinfo=timezone.utc)


def manifest(**updates):
    base = {'type': 'domain', 'indicator': 'untrusted.example.org', 'source_url': 'https://cert.gov.ua/articles/121212',
            'approved': True, 'approved_by': 'Example defender analyst', 'confidence': 85,
            'expires_utc': (NOW + timedelta(days=4)).isoformat()}
    return base | updates


class ReviewTests(unittest.TestCase):
    def test_formula_injection_neutralized_for_csv_review(self):
        for payload in ['=HYPERLINK("https://example.org")', '+cmd', '-2+3', '@SUM(A1:A2)', ' \t=1+1', '\t=2+2']:
            self.assertTrue(csv_safe(payload).startswith("'"), payload)
        self.assertEqual(csv_safe('a.example.org'), 'a.example.org')
        self.assertEqual(csv_safe('https://cert.gov.ua/article/123'), 'https://cert.gov.ua/article/123')

    def test_valid_public_candidate(self):
        self.assertTrue(evaluate(manifest(), NOW)[0])

    def test_no_automatic_approval(self):
        self.assertFalse(evaluate(manifest(approved=False), NOW)[0])
        self.assertFalse(evaluate(manifest(approved_by=''), NOW)[0])

    def test_expired_indicators_hold(self):
        self.assertFalse(evaluate(manifest(expires_utc=(NOW - timedelta(days=1)).isoformat()), NOW)[0])

    def test_unreasonably_long_expiry_holds(self):
        self.assertFalse(evaluate(manifest(expires_utc=(NOW + timedelta(days=200)).isoformat()), NOW)[0])

    def test_bad_provenance_holds(self):
        self.assertFalse(evaluate(manifest(source_url='http://malware.example'), NOW)[0])

    def test_bad_confidence_holds(self):
        self.assertFalse(evaluate(manifest(confidence=10), NOW)[0])

    def test_ip_restrictions(self):
        self.assertTrue(good_indicator('ipv4', '8.8.8.8'))
        self.assertFalse(good_indicator('ipv4', '127.0.0.1'))
        self.assertFalse(good_indicator('ipv4', '192.168.1.1'))
        self.assertFalse(good_indicator('ipv4', '8.8.8.0/24'))
        self.assertFalse(good_indicator('ipv4', 'not-ip'))

    def test_domain_restrictions(self):
        for value in ['*.example.com', 'example.com/anything', 'https://example.com', 'domain.local', 'host.test']:
            self.assertFalse(good_indicator('domain', value))
        self.assertTrue(good_indicator('domain', 'a.example.org'))


if __name__ == '__main__':
    unittest.main()
