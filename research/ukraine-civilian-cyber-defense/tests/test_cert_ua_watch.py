import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'watch'))
from cert_ua_watch import SOURCE, cert_url, parse_rss, update_state, main, markdown_brief

SAMPLE = '''<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>CERT-UA News</title>
<item><title>ClickFix phishing advisory</title><link>https://cert.gov.ua/article/1234</link>
<pubDate>Wed, 30 Sep 2026 12:00:00 +0300</pubDate><description>Phishing page &lt;b&gt;alert&lt;/b&gt;</description></item>
<item><title>Old advisory</title><link>https://cert.gov.ua/article/124</link>
<pubDate>Tue, 15 Sep 2026 10:00:00 +0300</pubDate></item>
</channel></rss>'''.encode('utf-8')


class AdvisoryTests(unittest.TestCase):
    def test_accepts_real_cert_ua_url_shape(self):
        self.assertEqual(cert_url('https://cert.gov.ua/article/6319983'), 'https://cert.gov.ua/article/6319983')
        self.assertIsNone(cert_url('https://cert.gov.ua/article/6319983/anything-else'))

    def test_parse_and_tag(self):
        rows = parse_rss(SAMPLE)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['published_utc'], '2026-09-30T09:00:00Z')
        self.assertIn('Social engineering / ClickFix', [x['category'] for x in rows[0]['review_suggestions']])
        self.assertNotIn('<b>', rows[0]['summary'])

    def test_baseline_no_alert(self):
        rows = parse_rss(SAMPLE)
        state, new, baseline = update_state(rows, None)
        self.assertTrue(baseline)
        self.assertEqual(new, [])
        self.assertEqual(len(state['seen_urls']), 2)

    def test_incremental_new_only(self):
        rows = parse_rss(SAMPLE)
        old = {'seen_urls': [rows[1]['url']]}
        state, new, baseline = update_state(rows, old)
        self.assertFalse(baseline)
        self.assertEqual(len(new), 1)
        self.assertEqual(new[0]['url'], rows[0]['url'])

    def test_does_not_leak_hostile_url(self):
        for url in ['http://cert.gov.ua/articles/1', 'https://evil.example/articles/1',
                    'https://cert.gov.ua.evil.example/articles/1', 'https://cert.gov.ua@evil.example/articles/1',
                    'https://cert.gov.ua/other/1']:
            self.assertIsNone(cert_url(url), url)

    def test_xml_entity_and_size(self):
        with self.assertRaises(ValueError):
            parse_rss(b'X' * 2_000_001)

    def test_invalid_feed_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            feed, state = root / 'feed.xml', root / 'state.json'
            feed.write_text('NOT XML')
            state.write_text('{"preserved": true}')
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(main(['--rss-file', str(feed), '--state', str(state), '--output-dir', str(root)]), 2)
            self.assertEqual(state.read_text(), '{"preserved": true}')

    def test_real_main_baseline_and_repeat(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            feed, state = root / 'feed.xml', root / 'state.json'
            feed.write_bytes(SAMPLE)
            args = ['--rss-file', str(feed), '--state', str(state), '--output-dir', str(root)]
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(args), 0)
                self.assertEqual(json.loads((root / 'new_advisories.json').read_text()), [])
                self.assertEqual(main(args), 0)
            self.assertEqual(json.loads((root / 'new_advisories.json').read_text()), [])

    def test_brief_contains_link_and_review_guidance(self):
        rows = parse_rss(SAMPLE)
        rendered = markdown_brief(rows, [rows[0]], False)
        self.assertIn('cert.gov.ua/article/1234', rendered)
        self.assertIn('analyst prompts', rendered)

if __name__ == '__main__':
    unittest.main()
